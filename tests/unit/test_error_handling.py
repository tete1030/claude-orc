"""Unit tests for error handling and fail-fast behavior"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import time

from orchestrator.src.orchestrator import (
    Orchestrator, OrchestratorConfig, Command
)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import SessionTestHelper, MockTmuxHelper


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling and fail-fast philosophy"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.session_helper = SessionTestHelper()
        self.temp_session_dir = self.session_helper.create_session_dir()
        
        self.config = OrchestratorConfig(
            session_name="test-agents",
            session_dir=self.temp_session_dir
        )
        self.orchestrator = Orchestrator(self.config)
        
    def tearDown(self):
        """Clean up after tests"""
        self.orchestrator.stop()
        self.session_helper.cleanup()
        
    def test_send_message_missing_to_agent_raises(self):
        """Test that send_message without to_agent raises ValueError"""
        cmd = Command(
            uuid="test",
            timestamp=time.time(),
            sender_type="user",
            agent_name="sender",
            command_type="send_message",
            to_agent=None  # Missing required field
        )
        
        with self.assertRaises(ValueError) as cm:
            self.orchestrator._handle_send_message(cmd)
            
        self.assertIn("missing required to_agent field", str(cm.exception))
        
    def test_send_message_unknown_agent_raises(self):
        """Test that send_message to unknown agent raises ValueError"""
        self.orchestrator.register_agent("agent1", "session-1", "prompt")
        
        cmd = Command(
            uuid="test",
            timestamp=time.time(),
            sender_type="user",
            agent_name="agent1",
            command_type="send_message",
            to_agent="unknown_agent"
        )
        
        with self.assertRaises(ValueError) as cm:
            self.orchestrator._handle_send_message(cmd)
            
        self.assertIn("Unknown target agent", str(cm.exception))
        
    def test_context_status_unknown_agent_raises(self):
        """Test that context_status for unknown agent raises ValueError"""
        cmd = Command(
            uuid="test",
            timestamp=time.time(),
            sender_type="user",
            agent_name="unknown",
            command_type="context_status"
        )
        
        with self.assertRaises(ValueError) as cm:
            self.orchestrator._handle_context_status(cmd)
            
        self.assertIn("not found or has no monitor", str(cm.exception))
        
    def test_list_agents_unknown_requester_raises(self):
        """Test that list_agents from unknown agent raises ValueError"""
        cmd = Command(
            uuid="test",
            timestamp=time.time(),
            sender_type="user",
            agent_name="unknown",
            command_type="list_agents"
        )
        
        with self.assertRaises(ValueError) as cm:
            self.orchestrator._handle_list_agents(cmd)
            
        self.assertIn("Requesting agent", str(cm.exception))
        self.assertIn("not found", str(cm.exception))
        
    def test_mailbox_check_unknown_agent_raises(self):
        """Test that mailbox_check from unknown agent raises ValueError"""
        cmd = Command(
            uuid="test",
            timestamp=time.time(),
            sender_type="user",
            agent_name="unknown",
            command_type="mailbox_check"
        )
        
        with self.assertRaises(ValueError) as cm:
            self.orchestrator._handle_mailbox_check(cmd)
            
        self.assertIn("Requesting agent", str(cm.exception))
        self.assertIn("not found", str(cm.exception))
        
    def test_process_command_with_handler_error_propagates(self):
        """Test that errors in command handlers propagate (fail-fast)"""
        # Create a command that will trigger an error
        cmd = Command(
            uuid="test",
            timestamp=time.time(),
            sender_type="user",
            agent_name="unknown",
            command_type="send_message",
            to_agent="also_unknown"
        )
        
        # Errors should propagate, not be caught and logged
        with self.assertRaises(ValueError):
            self.orchestrator._process_command(cmd)
            
    def test_config_without_claude_binary_raises(self):
        """Test that config without claude binary raises ValueError"""
        with patch('subprocess.run') as mock_run:
            # Make 'which claude' fail
            mock_run.return_value = MagicMock(returncode=1)
            
            with patch('os.path.exists') as mock_exists:
                # Make all common paths not exist
                mock_exists.return_value = False
                
                with self.assertRaises(ValueError) as cm:
                    config = OrchestratorConfig(claude_bin="")
                    
                self.assertIn("Could not find Claude binary", str(cm.exception))
                
    def test_send_to_agent_enforces_fail_fast(self):
        """Test that send_to_agent raises exception instead of returning False"""
        # Don't register any agents
        
        with self.assertRaises(ValueError) as cm:
            self.orchestrator.send_to_agent("unknown", "message")
            
        self.assertIn("Unknown agent", str(cm.exception))
        
    @patch('orchestrator.src.orchestrator.SessionMonitor')
    @patch('os.makedirs')
    def test_monitor_loop_exception_handling(self, mock_makedirs, mock_monitor_class):
        """Test that monitor loop handles exceptions without crashing"""
        # Mock directory creation
        mock_makedirs.return_value = None
        
        # Set up a monitor that throws an exception
        mock_monitor = MagicMock()
        mock_monitor.get_new_messages.side_effect = Exception("Test exception")
        mock_monitor_class.return_value = mock_monitor
        
        # Create session file and start orchestrator
        session_id = "test-session"
        self.session_helper.create_session_file(self.temp_session_dir, session_id)
        
        mock_tmux = MockTmuxHelper.create_mock_tmux(success=True, session_ids=[session_id])
        self.orchestrator.tmux = mock_tmux
        
        self.orchestrator.register_agent("agent1", "placeholder", "prompt")
        self.orchestrator.start()
        
        # Let it run briefly - should not crash
        time.sleep(0.2)
        
        # Orchestrator should still be running despite exception
        self.assertTrue(self.orchestrator.running)
        
        self.orchestrator.stop()


if __name__ == '__main__':
    unittest.main()