"""
Unit tests for AgentStateMonitor
"""

import unittest
from unittest.mock import MagicMock, patch
import time

from orchestrator.src.agent_state_monitor import (
    AgentStateMonitor, AgentState, AgentStatus
)


class TestAgentStateMonitor(unittest.TestCase):
    """Test agent state monitoring functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_tmux = MagicMock()
        self.monitor = AgentStateMonitor(self.mock_tmux)
        
    def test_detect_idle_state_with_prompt_box(self):
        """Test detection of idle state with prompt box"""
        pane_content = """
[DEBUG] Some previous output
Ready for input

╭──────────────────────────────────────╮
│ >                                    │
╰──────────────────────────────────────╯
  ? for shortcuts           Debug mode
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.IDLE)
        
    def test_detect_busy_state_with_processing(self):
        """Test detection of busy state"""
        pane_content = """
● I'll search for information about AI trends
[DEBUG] Executing hooks for Stop
Processing request...
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.BUSY)
        
    def test_detect_error_state(self):
        """Test detection of error state"""
        pane_content = """
Error: MCP error -32603: Cannot connect to host localhost:8767
Failed to initialize connection
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.ERROR)
        
    def test_detect_quit_state(self):
        """Test detection of quit state"""
        pane_content = """
Saving session...
Goodbye!
Process terminated with exit code 0
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.QUIT)
        
    def test_update_agent_state_creates_new_status(self):
        """Test that updating state creates new agent status"""
        self.mock_tmux.capture_pane.return_value = "│ > │"
        
        state = self.monitor.update_agent_state("TestAgent", 0)
        
        self.assertEqual(state, AgentState.IDLE)
        self.assertIn("TestAgent", self.monitor.agent_states)
        self.assertEqual(self.monitor.agent_states["TestAgent"].state, AgentState.IDLE)
        
    def test_update_agent_state_tracks_changes(self):
        """Test that state changes are tracked"""
        # First update - idle
        self.mock_tmux.capture_pane.return_value = "│ > │"
        self.monitor.update_agent_state("TestAgent", 0)
        
        # Second update - busy
        self.mock_tmux.capture_pane.return_value = "✽ Processing… (5s · ↑ 0 tokens · esc to interrupt)"
        with patch.object(self.monitor.logger, 'info') as mock_log:
            state = self.monitor.update_agent_state("TestAgent", 0)
            
        self.assertEqual(state, AgentState.BUSY)
        mock_log.assert_called_with("Agent TestAgent state changed: idle -> busy")
        
    def test_is_agent_busy(self):
        """Test busy state checking"""
        # Agent not registered
        self.assertFalse(self.monitor.is_agent_busy("Unknown"))
        
        # Set agent as busy
        self.monitor.agent_states["TestAgent"] = AgentStatus(
            state=AgentState.BUSY,
            last_update=time.time()
        )
        self.assertTrue(self.monitor.is_agent_busy("TestAgent"))
        
    def test_queue_message_for_agent(self):
        """Test message queueing"""
        message = {"from": "Sender", "content": "Test message"}
        
        self.monitor.queue_message_for_agent("TestAgent", message)
        
        self.assertIn("TestAgent", self.monitor.agent_states)
        self.assertEqual(len(self.monitor.agent_states["TestAgent"].pending_messages), 1)
        self.assertEqual(self.monitor.agent_states["TestAgent"].messages_sent_while_busy, 1)
        
    def test_get_pending_messages_clears_queue(self):
        """Test that getting pending messages clears the queue"""
        message1 = {"from": "Sender1", "content": "Message 1"}
        message2 = {"from": "Sender2", "content": "Message 2"}
        
        self.monitor.queue_message_for_agent("TestAgent", message1)
        self.monitor.queue_message_for_agent("TestAgent", message2)
        
        messages = self.monitor.get_pending_messages("TestAgent")
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], message1)
        self.assertEqual(messages[1], message2)
        
        # Queue should be cleared
        self.assertEqual(len(self.monitor.agent_states["TestAgent"].pending_messages), 0)
        self.assertEqual(self.monitor.agent_states["TestAgent"].messages_sent_while_busy, 0)
        
    def test_has_pending_messages(self):
        """Test checking for pending messages"""
        self.assertFalse(self.monitor.has_pending_messages("Unknown"))
        
        self.monitor.queue_message_for_agent("TestAgent", {"content": "test"})
        self.assertTrue(self.monitor.has_pending_messages("TestAgent"))
        
        self.monitor.get_pending_messages("TestAgent")
        self.assertFalse(self.monitor.has_pending_messages("TestAgent"))
        
    def test_get_agent_summary(self):
        """Test getting summary of all agents"""
        # Set up some agents
        self.monitor.agent_states["Agent1"] = AgentStatus(
            state=AgentState.IDLE,
            last_update=time.time()
        )
        self.monitor.agent_states["Agent2"] = AgentStatus(
            state=AgentState.BUSY,
            last_update=time.time()
        )
        self.monitor.queue_message_for_agent("Agent2", {"content": "test"})
        
        summary = self.monitor.get_agent_summary()
        
        self.assertIn("Agent1", summary)
        self.assertIn("Agent2", summary)
        self.assertEqual(summary["Agent1"]["state"], "idle")
        self.assertEqual(summary["Agent2"]["state"], "busy")
        self.assertEqual(summary["Agent2"]["pending_messages"], 1)
        
    def test_idle_detection_with_prompt_character(self):
        """Test idle detection with Claude's prompt box format"""
        pane_content = """
Some output
Another line
│ >  │
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.IDLE)
        
    def test_writing_state_detection(self):
        """Test writing state when there's text in the prompt box"""
        pane_content = """
Some output
Another line
│ > check_messages │
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.WRITING)
        
    def test_unknown_state_detection(self):
        """Test unknown state when patterns don't match"""
        pane_content = """
Some random output
Without any specific patterns
Just text
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.UNKNOWN)


if __name__ == '__main__':
    unittest.main()