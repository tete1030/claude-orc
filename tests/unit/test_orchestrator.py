"""Unit tests for Orchestrator"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import json
import time
import os
import tempfile
import shutil
from datetime import datetime
from queue import Queue

from src.orchestrator import (
    Orchestrator, OrchestratorConfig, Agent, Command
)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import SessionTestHelper, MockTmuxHelper


class TestOrchestrator(unittest.TestCase):
    """Test cases for Orchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.session_helper = SessionTestHelper()
        self.temp_session_dir = self.session_helper.create_session_dir()
        
        self.config = OrchestratorConfig(
            context_name="test-agents",
            poll_interval=0.1,
            interrupt_cooldown=1.0,
            session_dir=self.temp_session_dir
        )
        self.orchestrator = Orchestrator(self.config)
        
    def tearDown(self):
        """Clean up after tests"""
        self.orchestrator.stop()
        self.session_helper.cleanup()
        
    def test_register_agent_success(self):
        """Test successful agent registration"""
        # Should not raise exception
        self.orchestrator.register_agent(
            name="test_agent",
            session_id="session-123",
            system_prompt="You are a test agent",
            working_dir="/tmp/test"
        )
        
        self.assertIn("test_agent", self.orchestrator.agents)
        self.assertIn("test_agent", self.orchestrator.mailbox)
        
        agent = self.orchestrator.agents["test_agent"]
        self.assertEqual(agent.name, "test_agent")
        self.assertEqual(agent.session_id, "session-123")
        self.assertEqual(agent.pane_index, 0)
        
    def test_register_agent_duplicate(self):
        """Test registering duplicate agent"""
        self.orchestrator.register_agent("agent1", "session-1", "prompt")
        
        # Should raise ValueError for duplicate
        with self.assertRaises(ValueError) as cm:
            self.orchestrator.register_agent("agent1", "session-2", "prompt")
        
        self.assertIn("already registered", str(cm.exception))
        self.assertEqual(len(self.orchestrator.agents), 1)
        
    @patch('src.orchestrator.SessionMonitor')
    @patch('os.makedirs')
    def test_start_success(self, mock_makedirs, mock_monitor_class):
        """Test successful orchestrator start"""
        # Mock directory creation to avoid permission issues
        mock_makedirs.return_value = None
        
        # Set up session IDs that will be returned
        session_id1 = "test-session-1"
        session_id2 = "test-session-2"
        
        # Create mock tmux with specific session IDs
        mock_tmux = MockTmuxHelper.create_mock_tmux(
            success=True, 
            session_ids=[session_id1, session_id2]
        )
        self.orchestrator.tmux = mock_tmux
        
        # Create real session files that will be found
        self.session_helper.create_session_file(self.temp_session_dir, session_id1)
        self.session_helper.create_session_file(self.temp_session_dir, session_id2)
        
        # Register agents
        self.orchestrator.register_agent("agent1", "placeholder-1", "prompt1")
        self.orchestrator.register_agent("agent2", "placeholder-2", "prompt2")
        
        # Start orchestrator
        result = self.orchestrator.start()
        
        self.assertTrue(result)
        self.assertTrue(self.orchestrator.running)
        self.assertIsNotNone(self.orchestrator.monitors_thread)
        
        # Verify tmux operations
        mock_tmux.create_session.assert_called_once_with(2, force=False)
        self.assertEqual(mock_tmux.set_pane_title.call_count, 2)
        self.assertEqual(mock_tmux.launch_claude_in_pane.call_count, 2)
        
        # Verify monitors were created for both agents
        self.assertEqual(mock_monitor_class.call_count, 2)
        
        # Verify the monitor was called with correct session files
        expected_calls = [
            call(os.path.join(self.temp_session_dir, f"{session_id1}.jsonl"), "agent1"),
            call(os.path.join(self.temp_session_dir, f"{session_id2}.jsonl"), "agent2")
        ]
        mock_monitor_class.assert_has_calls(expected_calls, any_order=True)
        
    def test_start_no_agents(self):
        """Test starting with no agents registered"""
        result = self.orchestrator.start()
        
        self.assertFalse(result)
        self.assertFalse(self.orchestrator.running)
        
    @patch('os.makedirs')
    def test_start_tmux_failure(self, mock_makedirs):
        """Test start failure when tmux session creation fails"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Mock tmux on the orchestrator instance
        mock_tmux = MagicMock()
        mock_tmux.create_session.return_value = False
        self.orchestrator.tmux = mock_tmux
        
        self.orchestrator.register_agent("agent1", "session-1", "prompt")
        result = self.orchestrator.start()
        
        self.assertFalse(result)
        self.assertFalse(self.orchestrator.running)
        
    def test_process_command_send_message(self):
        """Test processing send_message command"""
        # Register agents
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        self.orchestrator.register_agent("agent2", "session-2", "prompt2")
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        
        # Create command
        cmd = Command(
            uuid="test-uuid",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="send_message",
            from_agent="agent1",
            to_agent="agent2",
            title="Test Message",
            content="Hello agent2",
            priority="normal"
        )
        
        # Process command
        self.orchestrator._process_command(cmd)
        
        # Verify message added to mailbox
        self.assertEqual(len(self.orchestrator.mailbox["agent2"]), 1)
        msg = self.orchestrator.mailbox["agent2"][0]
        self.assertEqual(msg["from"], "agent1")
        self.assertEqual(msg["title"], "Test Message")
        
    def test_process_command_high_priority_interrupt(self):
        """Test high priority message sends interrupt"""
        # Register agents
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        self.orchestrator.register_agent("agent2", "session-2", "prompt2")
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        
        # Create high priority command
        cmd = Command(
            uuid="test-uuid",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="send_message",
            from_agent="agent1",
            to_agent="agent2",
            title="Urgent",
            content="Urgent message",
            priority="high"
        )
        
        # Process command
        self.orchestrator._process_command(cmd)
        
        # Verify interrupt sent
        self.orchestrator.tmux.send_to_pane.assert_called_once()
        call_args = self.orchestrator.tmux.send_to_pane.call_args[0]
        self.assertEqual(call_args[0], 1)  # agent2 pane index
        self.assertIn("[INTERRUPT FROM: agent1]", call_args[1])
        
    def test_interrupt_cooldown(self):
        """Test interrupt cooldown prevents spam"""
        # Register agents
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        self.orchestrator.register_agent("agent2", "session-2", "prompt2")
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        
        # Send first interrupt
        cmd1 = Command(
            uuid="uuid-1",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="send_message",
            to_agent="agent2",
            priority="high"
        )
        self.orchestrator._process_command(cmd1)
        
        # Try to send second interrupt immediately
        cmd2 = Command(
            uuid="uuid-2",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="send_message",
            to_agent="agent2",
            priority="high"
        )
        self.orchestrator._process_command(cmd2)
        
        # Only one interrupt should be sent
        self.assertEqual(self.orchestrator.tmux.send_to_pane.call_count, 1)
        # Second message should be in mailbox
        self.assertEqual(len(self.orchestrator.mailbox["agent2"]), 1)
        
    def test_handle_list_agents(self):
        """Test list_agents command handler"""
        # Register agents
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        self.orchestrator.register_agent("agent2", "session-2", "prompt2")
        
        # Add message to agent2 mailbox
        self.orchestrator.mailbox["agent2"].append({"test": "message"})
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        
        # Create command
        cmd = Command(
            uuid="test-uuid",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="list_agents"
        )
        
        # Process command
        self.orchestrator._process_command(cmd)
        
        # Verify response sent
        self.orchestrator.tmux.send_to_pane.assert_called_once()
        call_args = self.orchestrator.tmux.send_to_pane.call_args[0]
        self.assertEqual(call_args[0], 0)  # agent1 pane index
        
        response = call_args[1]
        self.assertIn("[ORC RESPONSE: list_agents]", response)
        self.assertIn("agent1", response)
        self.assertIn("agent2", response)
        self.assertIn("mailbox_count", response)
        
    def test_handle_mailbox_check_with_messages(self):
        """Test mailbox_check with pending messages"""
        # Register agent
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        
        # Add messages to mailbox
        self.orchestrator.mailbox["agent1"] = [
            {
                "from": "agent2",
                "to": "agent1",
                "title": "Message 1",
                "content": "Content 1",
                "timestamp": datetime.now().isoformat(),
                "priority": "normal"
            },
            {
                "from": "agent3",
                "to": "agent1",
                "title": "Message 2",
                "content": "Content 2",
                "timestamp": datetime.now().isoformat(),
                "priority": "high"
            }
        ]
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        
        # Create command
        cmd = Command(
            uuid="test-uuid",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="mailbox_check"
        )
        
        # Process command
        self.orchestrator._process_command(cmd)
        
        # Verify response
        self.orchestrator.tmux.send_to_pane.assert_called_once()
        response = self.orchestrator.tmux.send_to_pane.call_args[0][1]
        
        self.assertIn("[ORC RESPONSE: mailbox]", response)
        self.assertIn("2 messages", response)
        self.assertIn("Message 1", response)
        self.assertIn("Message 2", response)
        
        # Verify mailbox cleared
        self.assertEqual(len(self.orchestrator.mailbox["agent1"]), 0)
        
    def test_handle_mailbox_check_empty(self):
        """Test mailbox_check with no messages"""
        # Register agent
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        
        # Create command
        cmd = Command(
            uuid="test-uuid",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="mailbox_check"
        )
        
        # Process command
        self.orchestrator._process_command(cmd)
        
        # Verify response
        response = self.orchestrator.tmux.send_to_pane.call_args[0][1]
        self.assertIn("No new messages", response)
        
    def test_handle_context_status(self):
        """Test context_status command"""
        # Register agent
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        
        # Mock monitor
        mock_monitor = MagicMock()
        mock_monitor.get_file_size.return_value = 500000  # 500KB
        self.orchestrator.agents["agent1"].monitor = mock_monitor
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        
        # Create command
        cmd = Command(
            uuid="test-uuid",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="context_status"
        )
        
        # Process command
        self.orchestrator._process_command(cmd)
        
        # Verify response
        response = self.orchestrator.tmux.send_to_pane.call_args[0][1]
        self.assertIn("[ORC RESPONSE: context_status]", response)
        self.assertIn("500,000 bytes", response)
        # 500KB = ~5000 lines, which is less than default threshold of 10000
        self.assertNotIn("WARNING", response)
        
    def test_send_to_agent(self):
        """Test sending direct message to agent"""
        # Register agent
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        
        # Mock tmux
        self.orchestrator.tmux = MagicMock()
        self.orchestrator.tmux.send_to_pane.return_value = True
        
        # Send message
        result = self.orchestrator.send_to_agent("agent1", "Test message")
        
        self.assertTrue(result)
        self.orchestrator.tmux.send_to_pane.assert_called_once_with(0, "Test message")
        
    def test_send_to_unknown_agent(self):
        """Test sending message to unknown agent"""
        # Should raise ValueError for unknown agent
        with self.assertRaises(ValueError) as cm:
            self.orchestrator.send_to_agent("unknown", "Test")
        
        self.assertIn("Unknown agent", str(cm.exception))
        
    def test_get_agent_status(self):
        """Test getting agent status"""
        # Register agent
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        
        # Add mailbox message
        self.orchestrator.mailbox["agent1"].append({"test": "message"})
        
        # Mock monitor
        mock_monitor = MagicMock()
        mock_monitor.get_file_size.return_value = 12345
        self.orchestrator.agents["agent1"].monitor = mock_monitor
        
        # Get status
        status = self.orchestrator.get_agent_status("agent1")
        
        self.assertIsNotNone(status)
        self.assertEqual(status["name"], "agent1")
        self.assertEqual(status["session_id"], "session-1")
        self.assertEqual(status["mailbox_count"], 1)
        self.assertEqual(status["session_file_size"], 12345)
        
    def test_get_unknown_agent_status(self):
        """Test getting status of unknown agent"""
        status = self.orchestrator.get_agent_status("unknown")
        self.assertIsNone(status)
        
    def test_get_all_agent_status(self):
        """Test getting status of all agents"""
        # Register agents
        self.orchestrator.register_agent("agent1", "session-1", "prompt1")
        self.orchestrator.register_agent("agent2", "session-2", "prompt2")
        
        # Get all status
        all_status = self.orchestrator.get_all_agent_status()
        
        self.assertEqual(len(all_status), 2)
        self.assertIn("agent1", all_status)
        self.assertIn("agent2", all_status)
        
    @patch('src.orchestrator.SessionMonitor')
    @patch('os.makedirs')
    def test_monitor_loop_processes_commands(self, mock_makedirs, mock_monitor_class):
        """Test monitor loop processes commands from agents"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Set up session ID
        session_id = "test-session-monitor"
        
        # Create mock tmux
        mock_tmux = MockTmuxHelper.create_mock_tmux(success=True, session_ids=[session_id])
        self.orchestrator.tmux = mock_tmux
        
        # Create real session file
        session_file = self.session_helper.create_session_file(self.temp_session_dir, session_id)
        
        # Mock monitor with commands
        mock_monitor = MagicMock()
        mock_monitor.get_file_size.return_value = 1000
        mock_message = MagicMock()
        mock_command = Command(
            uuid="test-uuid",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="list_agents"
        )
        
        # Return messages once then empty
        mock_monitor.get_new_messages.side_effect = [[mock_message], []]
        mock_monitor.extract_commands.return_value = [mock_command]
        mock_monitor_class.return_value = mock_monitor
        
        # Register agent and start
        self.orchestrator.register_agent("agent1", "placeholder", "prompt1")
        self.orchestrator.start()
        
        # Let monitor loop run briefly
        time.sleep(0.2)
        
        # Verify command was processed
        self.assertTrue(mock_monitor.get_new_messages.called)
        self.assertTrue(mock_monitor.extract_commands.called)
        
        # Verify the monitor was created with the correct session file
        mock_monitor_class.assert_called_with(session_file, "agent1")
        
        # Stop orchestrator
        self.orchestrator.stop()


if __name__ == '__main__':
    unittest.main()