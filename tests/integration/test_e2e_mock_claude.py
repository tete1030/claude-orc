"""End-to-end test with mock Claude"""

import unittest
import tempfile
import os
import json
import time
import threading
import subprocess
from unittest.mock import patch, MagicMock

from orchestrator.src.orchestrator import Orchestrator, OrchestratorConfig


class MockClaude:
    """Mock Claude process that simulates Claude behavior"""
    
    def __init__(self, session_file: str, agent_name: str):
        self.session_file = session_file
        self.agent_name = agent_name
        self.running = False
        self.thread = None
        self.message_count = 0
        
    def start(self):
        """Start the mock Claude process"""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stop the mock Claude process"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            
    def _run(self):
        """Simulate Claude writing to session file"""
        time.sleep(0.5)  # Initial startup delay
        
        # Write initial greeting
        self._write_assistant_message(
            f"[FROM: {self.agent_name}] Hello! I am the {self.agent_name} agent ready to help."
        )
        
        # Simulate different behaviors based on agent name
        if self.agent_name == "master":
            self._simulate_master_behavior()
        elif self.agent_name == "worker":
            self._simulate_worker_behavior()
            
    def _simulate_master_behavior(self):
        """Simulate master agent behavior"""
        time.sleep(1)
        
        # Send task to worker
        message = '''[FROM: master] I need to delegate a task to the worker.
<orc-command type="send_message">
  <from>master</from>
  <to>worker</to>
  <title>Analysis Task</title>
  <content>Please analyze the system performance metrics</content>
  <priority>normal</priority>
</orc-command>'''
        self._write_assistant_message(message)
        
        # Check agent list
        time.sleep(1)
        self._write_assistant_message(
            "[FROM: master] Let me check available agents\n<orc-command type=\"list_agents\"></orc-command>"
        )
        
    def _simulate_worker_behavior(self):
        """Simulate worker agent behavior"""
        # Periodically check mailbox
        check_count = 0
        while self.running and check_count < 5:
            time.sleep(2)
            self._write_assistant_message(
                f"[FROM: worker] Checking for tasks... (check {check_count + 1})\n"
                "<orc-command type=\"mailbox_check\"></orc-command>"
            )
            check_count += 1
            
    def _write_assistant_message(self, content: str):
        """Write an assistant message to the session file"""
        self.message_count += 1
        message = {
            "uuid": f"mock-{self.agent_name}-{self.message_count}",
            "sessionId": os.path.basename(self.session_file).replace('.jsonl', ''),
            "type": "assistant",
            "timestamp": time.time(),
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": content}
                ]
            }
        }
        
        with open(self.session_file, 'a') as f:
            f.write(json.dumps(message) + '\n')


class TestE2EMockClaude(unittest.TestCase):
    """End-to-end tests using mock Claude processes"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = OrchestratorConfig(
            session_name="test-e2e",
            session_dir=self.temp_dir.name,
            poll_interval=0.2
        )
        self.orchestrator = Orchestrator(self.config)
        
        # Mock tmux but track Claude launches
        self.mock_tmux = MagicMock()
        self.mock_tmux.create_session.return_value = True
        self.mock_tmux.set_pane_title.return_value = True
        self.mock_tmux.send_to_pane.return_value = True
        
        # Capture Claude launch parameters
        self.claude_launches = []
        self.mock_claudes = {}
        
        def capture_claude_launch(pane_index, agent_name, agent_prompt, 
                                working_dir=None, claude_bin=None, mcp_config=None):
            # Generate a session ID for this agent
            session_id = f"test-session-{agent_name}"
            
            self.claude_launches.append({
                'pane_index': pane_index,
                'agent_name': agent_name,
                'session_id': session_id,
                'agent_prompt': agent_prompt
            })
            
            # Create session file
            session_file = os.path.join(self.temp_dir.name, f"{session_id}.jsonl")
            
            # Create and start mock Claude
            mock_claude = MockClaude(session_file, agent_name)
            self.mock_claudes[session_id] = mock_claude
            mock_claude.start()
            
            return session_id
            
        self.mock_tmux.launch_claude_in_pane.side_effect = capture_claude_launch
        self.orchestrator.tmux = self.mock_tmux
        
        # Capture messages sent to panes
        self.pane_messages = {0: [], 1: []}
        
        def capture_send(pane_index, message):
            if pane_index in self.pane_messages:
                self.pane_messages[pane_index].append(message)
            return True
            
        self.mock_tmux.send_to_pane.side_effect = capture_send
        
    def tearDown(self):
        """Clean up"""
        # Stop mock Claudes
        for mock_claude in self.mock_claudes.values():
            mock_claude.stop()
            
        self.orchestrator.stop()
        self.temp_dir.cleanup()
        
    @patch('os.makedirs')
    def test_full_two_agent_workflow(self, mock_makedirs):
        """Test complete two-agent workflow with mock Claude"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agents
        self.orchestrator.register_agent(
            name="master",
            session_id="e2e-master",
            system_prompt="You are the master agent",
            working_dir="/tmp"
        )
        
        self.orchestrator.register_agent(
            name="worker",
            session_id="e2e-worker",
            system_prompt="You are the worker agent",
            working_dir="/tmp"
        )
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Wait for mock Claudes to initialize and communicate
        time.sleep(5)
        
        # Verify Claude launches
        self.assertEqual(len(self.claude_launches), 2)
        self.assertEqual(self.claude_launches[0]['agent_name'], 'master')
        self.assertEqual(self.claude_launches[1]['agent_name'], 'worker')
        
        # Check that worker received the message via mailbox response
        # (mailbox gets cleared after checking, so we check pane messages instead)
        
        # Check that master received agent list
        master_messages = self.pane_messages[0]
        self.assertTrue(any("[ORC RESPONSE: list_agents]" in msg for msg in master_messages))
        
        # Check that worker received mailbox responses  
        worker_pane_messages = self.pane_messages[1]
        mailbox_responses = [msg for msg in worker_pane_messages 
                           if "[ORC RESPONSE: mailbox]" in msg]
        self.assertTrue(len(mailbox_responses) > 0)
        
        # Verify at least one mailbox check found the message
        self.assertTrue(any("Analysis Task" in msg for msg in worker_pane_messages))
        
    def test_mock_claude_session_file_format(self):
        """Test that mock Claude writes correct session file format"""
        # Create a single mock Claude
        session_file = os.path.join(self.temp_dir.name, "test-session.jsonl")
        mock_claude = MockClaude(session_file, "test")
        
        # Start and let it write a message
        mock_claude.start()
        time.sleep(1)
        mock_claude.stop()
        
        # Verify file exists and is valid JSONL
        self.assertTrue(os.path.exists(session_file))
        
        with open(session_file, 'r') as f:
            lines = f.readlines()
            
        self.assertTrue(len(lines) > 0)
        
        # Parse and verify first message
        first_msg = json.loads(lines[0])
        self.assertEqual(first_msg['type'], 'assistant')
        self.assertIn('uuid', first_msg)
        self.assertIn('sessionId', first_msg)
        self.assertIn('timestamp', first_msg)
        self.assertIn('message', first_msg)
        self.assertIn('content', first_msg['message'])
        
    @patch('os.makedirs')
    def test_orchestrator_processes_mock_claude_commands(self, mock_makedirs):
        """Test that orchestrator correctly processes commands from mock Claude"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register single agent
        self.orchestrator.register_agent(
            name="test_agent",
            session_id="test-session",
            system_prompt="Test agent"
        )
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Get session file path - should use the generated session ID
        session_file = os.path.join(self.temp_dir.name, "test-session-test_agent.jsonl")
        
        # Manually write a command as if from Claude
        command_msg = {
            "uuid": "manual-test-1",
            "sessionId": "test-session",
            "type": "assistant",
            "timestamp": time.time(),
            "message": {
                "content": [{
                    "type": "text",
                    "text": "<orc-command type=\"context_status\"></orc-command>"
                }]
            }
        }
        
        with open(session_file, 'a') as f:
            f.write(json.dumps(command_msg) + '\n')
            
        # Wait for processing
        time.sleep(0.5)
        
        # Verify response was sent
        agent_messages = self.pane_messages[0]
        self.assertTrue(any("[ORC RESPONSE: context_status]" in msg for msg in agent_messages))
        
    @patch('os.makedirs')
    def test_stress_test_multiple_messages(self, mock_makedirs):
        """Stress test with rapid message sending"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agents
        self.orchestrator.register_agent("sender", "stress-sender", "Sender")
        self.orchestrator.register_agent("receiver", "stress-receiver", "Receiver")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Get sender session file - should use generated session ID
        sender_file = os.path.join(self.temp_dir.name, "test-session-sender.jsonl")
        
        # Send many messages rapidly
        for i in range(10):
            msg_data = {
                "uuid": f"stress-{i}",
                "sessionId": "test-session-sender",
                "type": "user",
                "timestamp": time.time(),
                "message": {
                    "content": f'''<orc-command type="send_message">
  <from>sender</from>
  <to>receiver</to>
  <title>Message {i}</title>
  <content>Test content {i}</content>
</orc-command>'''
                }
            }
            
            with open(sender_file, 'a') as f:
                f.write(json.dumps(msg_data) + '\n')
                
            time.sleep(0.05)  # Small delay between messages
            
        # Wait for processing
        time.sleep(1)
        
        # Verify all messages arrived
        self.assertEqual(len(self.orchestrator.mailbox["receiver"]), 10)
        
        # Verify message order preserved
        messages = self.orchestrator.mailbox["receiver"]
        for i, msg in enumerate(messages):
            self.assertEqual(msg["title"], f"Message {i}")


if __name__ == '__main__':
    unittest.main()