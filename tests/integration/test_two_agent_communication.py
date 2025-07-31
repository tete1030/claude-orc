"""Integration tests for two-agent communication"""

import unittest
import tempfile
import os
import json
import time
import threading
from typing import Optional
from unittest.mock import patch, MagicMock

from orchestrator.src.orchestrator import Orchestrator, OrchestratorConfig


class TestTwoAgentCommunication(unittest.TestCase):
    """Test two-agent communication scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for session files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Configure orchestrator
        self.config = OrchestratorConfig(
            session_name="test-integration",
            session_dir=self.temp_dir.name,
            poll_interval=0.1,
            interrupt_cooldown=0.5
        )
        
        self.orchestrator = Orchestrator(self.config)
        
        # Mock tmux operations
        self.mock_tmux = MagicMock()
        self.mock_tmux.create_session.return_value = True
        self.mock_tmux.set_pane_title.return_value = True
        self.mock_tmux.launch_claude_in_pane.return_value = True
        self.mock_tmux.send_to_pane.return_value = True
        self.orchestrator.tmux = self.mock_tmux
        
        # Capture messages sent to panes
        self.pane_messages = {0: [], 1: []}
        
        def capture_send(pane_index, message):
            self.pane_messages[pane_index].append(message)
            return True
            
        self.mock_tmux.send_to_pane.side_effect = capture_send
        
    def tearDown(self):
        """Clean up test environment"""
        self.orchestrator.stop()
        self.temp_dir.cleanup()
        
    def create_session_file(self, session_id: str) -> str:
        """Create a session file for testing"""
        filepath = os.path.join(self.temp_dir.name, f"{session_id}.jsonl")
        # Create empty file
        with open(filepath, 'w'):
            pass
        return filepath
        
    def write_message_to_session(self, session_file: str, message_type: str, 
                                content: str, uuid: Optional[str] = None):
        """Write a message to session file"""
        if uuid is None:
            uuid = f"test-{time.time()}"
            
        message_content: dict = {}
        if message_type == "user":
            message_content["content"] = content
        elif message_type == "assistant":
            message_content["content"] = [
                {"type": "text", "text": content}
            ]
            
        data = {
            "uuid": uuid,
            "sessionId": os.path.basename(session_file).replace('.jsonl', ''),
            "type": message_type,
            "timestamp": time.time(),
            "message": message_content
        }
            
        with open(session_file, 'a') as f:
            f.write(json.dumps(data) + '\n')
            
    @patch('os.makedirs')
    def test_basic_message_passing(self, mock_makedirs):
        """Test basic message passing between two agents"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agents
        self.orchestrator.register_agent("master", "session-master", "You are the master agent")
        self.orchestrator.register_agent("worker", "session-worker", "You are the worker agent")
        
        # Create session files
        master_file = self.create_session_file("session-master")
        self.create_session_file("session-worker")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Simulate master sending message to worker
        message_content = '''I need help with a task.
<orc-command type="send_message">
  <from>master</from>
  <to>worker</to>
  <title>Task Assignment</title>
  <content>Please analyze the data</content>
  <priority>normal</priority>
</orc-command>'''
        
        self.write_message_to_session(master_file, "user", message_content)
        
        # Give time for message processing
        time.sleep(0.3)
        
        # Verify worker's mailbox has the message
        self.assertEqual(len(self.orchestrator.mailbox["worker"]), 1)
        msg = self.orchestrator.mailbox["worker"][0]
        self.assertEqual(msg["from"], "master")
        self.assertEqual(msg["title"], "Task Assignment")
        self.assertEqual(msg["content"], "Please analyze the data")
        
    @patch('os.makedirs')
    def test_high_priority_interrupt(self, mock_makedirs):
        """Test high priority message sends interrupt"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agents
        self.orchestrator.register_agent("agent1", "session-1", "Agent 1")
        self.orchestrator.register_agent("agent2", "session-2", "Agent 2")
        
        # Create session files
        agent1_file = self.create_session_file("session-1")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Send high priority message
        message_content = '''<orc-command type="send_message">
  <from>agent1</from>
  <to>agent2</to>
  <title>URGENT</title>
  <content>Critical issue detected!</content>
  <priority>high</priority>
</orc-command>'''
        
        self.write_message_to_session(agent1_file, "user", message_content)
        
        # Give time for processing
        time.sleep(0.3)
        
        # Verify interrupt was sent to agent2's pane
        agent2_messages = self.pane_messages[1]  # agent2 is pane 1
        self.assertTrue(any("[INTERRUPT FROM: agent1]" in msg for msg in agent2_messages))
        self.assertTrue(any("URGENT" in msg for msg in agent2_messages))
        
    @patch('os.makedirs')
    def test_mailbox_check_workflow(self, mock_makedirs):
        """Test mailbox check and retrieval workflow"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agents
        self.orchestrator.register_agent("receiver", "session-rcv", "Receiver")
        self.orchestrator.register_agent("sender", "session-snd", "Sender")
        
        # Create session files
        receiver_file = self.create_session_file("session-rcv")
        sender_file = self.create_session_file("session-snd")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # First, sender sends a normal priority message
        send_message = '''<orc-command type="send_message">
  <from>sender</from>
  <to>receiver</to>
  <title>Status Update</title>
  <content>Task completed successfully</content>
  <priority>normal</priority>
</orc-command>'''
        
        self.write_message_to_session(sender_file, "assistant", send_message)
        time.sleep(0.2)
        
        # Verify message is in mailbox
        self.assertEqual(len(self.orchestrator.mailbox["receiver"]), 1)
        
        # Receiver checks mailbox
        check_message = '<orc-command type="mailbox_check"></orc-command>'
        self.write_message_to_session(receiver_file, "user", check_message)
        time.sleep(0.2)
        
        # Verify receiver got the mailbox contents
        receiver_messages = self.pane_messages[0]  # receiver is pane 0
        mailbox_response = [msg for msg in receiver_messages if "[ORC RESPONSE: mailbox]" in msg]
        self.assertTrue(len(mailbox_response) > 0)
        self.assertTrue(any("Status Update" in msg for msg in receiver_messages))
        
        # Verify mailbox was cleared
        self.assertEqual(len(self.orchestrator.mailbox["receiver"]), 0)
        
    @patch('os.makedirs')
    def test_list_agents_command(self, mock_makedirs):
        """Test list_agents command"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register multiple agents
        self.orchestrator.register_agent("agent1", "session-1", "Agent 1")
        self.orchestrator.register_agent("agent2", "session-2", "Agent 2")
        self.orchestrator.register_agent("agent3", "session-3", "Agent 3")
        
        # Create session file for agent1
        agent1_file = self.create_session_file("session-1")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Agent1 requests agent list
        list_command = '<orc-command type="list_agents"></orc-command>'
        self.write_message_to_session(agent1_file, "user", list_command)
        time.sleep(0.2)
        
        # Verify agent1 received the list
        agent1_messages = self.pane_messages[0]
        list_response = [msg for msg in agent1_messages if "[ORC RESPONSE: list_agents]" in msg]
        self.assertTrue(len(list_response) > 0)
        
        # Check all agents are listed
        response_text = '\n'.join(agent1_messages)
        self.assertIn("agent1", response_text)
        self.assertIn("agent2", response_text)
        self.assertIn("agent3", response_text)
        
    @patch('os.makedirs')
    def test_context_status_command(self, mock_makedirs):
        """Test context_status command"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agent
        self.orchestrator.register_agent("test_agent", "session-test", "Test agent")
        
        # Create session file
        test_file = self.create_session_file("session-test")
        
        # Write some data to make file larger
        for i in range(50):
            self.write_message_to_session(test_file, "user", f"Test message {i}")
            
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Request context status
        status_command = '<orc-command type="context_status"></orc-command>'
        self.write_message_to_session(test_file, "user", status_command)
        time.sleep(0.2)
        
        # Verify response
        agent_messages = self.pane_messages[0]
        status_response = [msg for msg in agent_messages if "[ORC RESPONSE: context_status]" in msg]
        self.assertTrue(len(status_response) > 0)
        self.assertTrue(any("Session file size:" in msg for msg in agent_messages))
        
    @patch('os.makedirs')
    def test_interrupt_cooldown_prevents_spam(self, mock_makedirs):
        """Test that interrupt cooldown prevents spam"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agents
        self.orchestrator.register_agent("spammer", "session-spam", "Spammer")
        self.orchestrator.register_agent("victim", "session-victim", "Victim")
        
        # Create session file
        spammer_file = self.create_session_file("session-spam")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Send multiple high priority messages rapidly
        for i in range(3):
            message = f'''<orc-command type="send_message">
  <from>spammer</from>
  <to>victim</to>
  <title>Interrupt {i}</title>
  <priority>high</priority>
</orc-command>'''
            self.write_message_to_session(spammer_file, "user", message, 
                                        uuid=f"spam-{i}")
            time.sleep(0.1)  # Less than cooldown period
            
        # Give time for processing
        time.sleep(0.3)
        
        # Only first message should be interrupt, rest go to mailbox
        victim_messages = self.pane_messages[1]
        interrupt_count = sum(1 for msg in victim_messages if "[INTERRUPT FROM:" in msg)
        self.assertEqual(interrupt_count, 1)
        
        # Rest should be in mailbox
        self.assertEqual(len(self.orchestrator.mailbox["victim"]), 2)
        
    @patch('os.makedirs')
    def test_bidirectional_communication(self, mock_makedirs):
        """Test bidirectional communication between agents"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agents
        self.orchestrator.register_agent("alice", "session-alice", "Alice agent")
        self.orchestrator.register_agent("bob", "session-bob", "Bob agent")
        
        # Create session files
        alice_file = self.create_session_file("session-alice")
        bob_file = self.create_session_file("session-bob")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # Alice sends to Bob
        alice_msg = '''<orc-command type="send_message">
  <from>alice</from>
  <to>bob</to>
  <title>Hello</title>
  <content>How are you?</content>
</orc-command>'''
        self.write_message_to_session(alice_file, "assistant", alice_msg)
        time.sleep(0.2)
        
        # Bob checks mailbox
        bob_check = '<orc-command type="mailbox_check"></orc-command>'
        self.write_message_to_session(bob_file, "user", bob_check)
        time.sleep(0.2)
        
        # Verify Bob received message
        bob_messages = self.pane_messages[1]
        self.assertTrue(any("How are you?" in msg for msg in bob_messages))
        
        # Bob responds to Alice
        bob_response = '''<orc-command type="send_message">
  <from>bob</from>
  <to>alice</to>
  <title>Re: Hello</title>
  <content>I'm doing well, thanks!</content>
</orc-command>'''
        self.write_message_to_session(bob_file, "assistant", bob_response)
        time.sleep(0.2)
        
        # Alice checks mailbox
        alice_check = '<orc-command type="mailbox_check"></orc-command>'
        self.write_message_to_session(alice_file, "user", alice_check)
        time.sleep(0.2)
        
        # Verify Alice received response
        alice_messages = self.pane_messages[0]
        self.assertTrue(any("I'm doing well, thanks!" in msg for msg in alice_messages))
        
    @patch('os.makedirs')
    def test_external_controller_interface(self, mock_makedirs):
        """Test external controller can send messages to agents"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register agent
        self.orchestrator.register_agent("agent", "session-1", "Test agent")
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # External controller sends message
        result = self.orchestrator.send_to_agent("agent", "External control message")
        self.assertTrue(result)
        
        # Verify message was sent
        agent_messages = self.pane_messages[0]
        self.assertIn("External control message", agent_messages)
        
        # Test sending to unknown agent
        result = self.orchestrator.send_to_agent("unknown", "Test")
        self.assertFalse(result)
        
    @patch('os.makedirs')
    def test_concurrent_message_processing(self, mock_makedirs):
        """Test that multiple agents can send messages concurrently"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Register three agents
        self.orchestrator.register_agent("agent1", "session-1", "Agent 1")
        self.orchestrator.register_agent("agent2", "session-2", "Agent 2")
        self.orchestrator.register_agent("agent3", "session-3", "Agent 3")
        
        # Create session files
        files = {
            "agent1": self.create_session_file("session-1"),
            "agent2": self.create_session_file("session-2"),
            "agent3": self.create_session_file("session-3")
        }
        
        # Start orchestrator
        self.assertTrue(self.orchestrator.start())
        
        # All agents send messages simultaneously
        def send_messages(agent_name, target, file_path):
            for i in range(3):
                msg = f'''<orc-command type="send_message">
  <from>{agent_name}</from>
  <to>{target}</to>
  <title>Message {i}</title>
  <content>Content from {agent_name}</content>
</orc-command>'''
                self.write_message_to_session(file_path, "user", msg,
                                            uuid=f"{agent_name}-{i}")
                time.sleep(0.05)
                
        # Create threads for concurrent sending
        threads = [
            threading.Thread(target=send_messages, args=("agent1", "agent2", files["agent1"])),
            threading.Thread(target=send_messages, args=("agent2", "agent3", files["agent2"])),
            threading.Thread(target=send_messages, args=("agent3", "agent1", files["agent3"]))
        ]
        
        # Start all threads
        for t in threads:
            t.start()
            
        # Wait for completion
        for t in threads:
            t.join()
            
        # Give time for processing
        time.sleep(0.5)
        
        # Verify all messages were delivered
        self.assertEqual(len(self.orchestrator.mailbox["agent1"]), 3)
        self.assertEqual(len(self.orchestrator.mailbox["agent2"]), 3)
        self.assertEqual(len(self.orchestrator.mailbox["agent3"]), 3)


if __name__ == '__main__':
    unittest.main()