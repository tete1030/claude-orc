"""
Unit tests for MessageDeliverySystem
"""

import unittest
from unittest.mock import MagicMock
import time

from src.message_delivery import MessageDeliverySystem, MessageNotification
from src.agent_state_monitor import AgentState
from src.orchestrator import Agent


class TestMessageDeliverySystem(unittest.TestCase):
    """Test message delivery functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_orchestrator = MagicMock()
        self.mock_tmux = MagicMock()
        self.mock_state_monitor = MagicMock()
        
        # Set up mock agents
        self.mock_orchestrator.agents = {
            "Agent1": Agent(name="Agent1", session_id="session1", pane_index=0, 
                          session_file="/tmp/session1.jsonl", system_prompt="prompt1"),
            "Agent2": Agent(name="Agent2", session_id="session2", pane_index=1,
                          session_file="/tmp/session2.jsonl", system_prompt="prompt2")
        }
        self.mock_orchestrator.mailbox = {}
        
        self.delivery = MessageDeliverySystem(
            self.mock_orchestrator,
            self.mock_tmux,
            self.mock_state_monitor
        )
        
    def test_send_message_to_idle_agent(self):
        """Test sending message to idle agent delivers immediately"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.IDLE
        
        result = self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
        self.assertTrue(result)
        # Should send only one notification with check_messages reminder
        calls = self.mock_tmux.send_to_pane.call_args_list
        self.assertEqual(len(calls), 1)  # Only one notification
        notification = calls[0][0][1]
        self.assertIn("[MESSAGE]", notification)
        self.assertIn("check_messages", notification)
        self.assertIn("Agent2", notification)  # Should mention sender
        # Check message was added to mailbox
        self.assertIn("Agent1", self.mock_orchestrator.mailbox)
        self.assertEqual(len(self.mock_orchestrator.mailbox["Agent1"]), 1)
        
    def test_send_message_to_busy_agent_notifies(self):
        """Test sending message to busy agent sends notification"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.BUSY
        
        result = self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
        self.assertTrue(result)
        # Should send notification even though busy
        calls = self.mock_tmux.send_to_pane.call_args_list
        self.assertEqual(len(calls), 1)
        notification = calls[0][0][1]
        self.assertIn("[MESSAGE]", notification)
        self.assertIn("check_messages", notification)
        self.assertIn("Agent2", notification)
        # Should also add to mailbox
        self.assertIn("Agent1", self.mock_orchestrator.mailbox)
        self.assertEqual(len(self.mock_orchestrator.mailbox["Agent1"]), 1)
        
    def test_send_message_to_error_agent_fails(self):
        """Test sending message to agent in error state fails"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.ERROR
        
        result = self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
        self.assertFalse(result)
        self.mock_tmux.send_to_pane.assert_not_called()
        
    def test_send_message_to_quit_agent_fails(self):
        """Test sending message to quit agent fails"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.QUIT
        
        result = self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
        self.assertFalse(result)
        self.mock_tmux.send_to_pane.assert_not_called()
        
    def test_send_message_to_unknown_agent_fails(self):
        """Test sending message to unknown agent fails"""
        result = self.delivery.send_message_to_agent(
            "UnknownAgent", "Agent1", "Test message", "normal"
        )
        
        self.assertFalse(result)
        
    def test_deliver_message_adds_to_mailbox(self):
        """Test message delivery adds to mailbox"""
        # Set agent as idle so it delivers immediately
        self.mock_state_monitor.update_agent_state.return_value = AgentState.IDLE
        
        result = self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
        self.assertTrue(result)
        self.assertIn("Agent1", self.mock_orchestrator.mailbox)
        self.assertEqual(len(self.mock_orchestrator.mailbox["Agent1"]), 1)
        
    def test_check_and_deliver_pending_messages(self):
        """Test checking and delivering pending messages"""
        # Set up agent as idle with unread messages in mailbox
        self.mock_state_monitor.update_agent_state.return_value = AgentState.IDLE
        self.mock_state_monitor.has_pending_messages.return_value = True
        self.mock_state_monitor.get_pending_messages.return_value = [
            {'from': 'Agent2', 'to': 'Agent1', 'message': 'Message 1'},
            {'from': 'Agent2', 'to': 'Agent1', 'message': 'Message 2'}
        ]
        # Set up mailbox with existing messages
        self.mock_orchestrator.mailbox["Agent1"] = [
            {'from': 'Agent2', 'message': 'Old message'}
        ]
        
        self.delivery.check_and_deliver_pending_messages()
        
        # Should send idle reminder about unread messages
        calls = self.mock_tmux.send_to_pane.call_args_list
        self.assertTrue(any("[MESSAGE]" in str(call) for call in calls))
        self.assertTrue(any("Reminder" in str(call) for call in calls))
        
    def test_send_text_to_agent_input(self):
        """Test sending text to agent input field"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.IDLE
        self.mock_tmux.type_in_pane.return_value = True
        
        result = self.delivery.send_text_to_agent_input("Agent1", "list_agents")
        
        self.assertTrue(result)
        self.mock_tmux.type_in_pane.assert_called_once_with(0, "list_agents")
        
    def test_send_text_to_unknown_agent_fails(self):
        """Test sending text to unknown agent fails"""
        result = self.delivery.send_text_to_agent_input("Unknown", "text")
        
        self.assertFalse(result)
        self.mock_tmux.type_in_pane.assert_not_called()
        
    def test_send_command_to_agent(self):
        """Test sending command to agent"""
        self.mock_tmux.send_to_pane.return_value = True
        
        result = self.delivery.send_command_to_agent("Agent1", "check_messages")
        
        self.assertTrue(result)
        self.mock_tmux.send_to_pane.assert_called_once_with(0, "check_messages")
        
    def test_custom_notification_format(self):
        """Test custom notification format"""
        custom_notification = MessageNotification(
            prefix="[NEW MSG]",
            notification_format="{prefix} From {sender}: new message!"
        )
        
        delivery = MessageDeliverySystem(
            self.mock_orchestrator,
            self.mock_tmux,
            self.mock_state_monitor,
            custom_notification
        )
        
        self.mock_state_monitor.update_agent_state.return_value = AgentState.IDLE
        
        delivery.send_message_to_agent("Agent1", "Agent2", "Test", "normal")
        
        # Check custom format was used
        calls = self.mock_tmux.send_to_pane.call_args_list
        self.assertIn("[NEW MSG]", calls[0][0][1])
        self.assertIn("From Agent2", calls[0][0][1])
        
    def test_message_priority_preserved(self):
        """Test that message priority is preserved in mailbox"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.BUSY
        
        self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Urgent task", "high"
        )
        
        # Check mailbox has priority preserved
        self.assertIn("Agent1", self.mock_orchestrator.mailbox)
        self.assertEqual(self.mock_orchestrator.mailbox["Agent1"][0]['priority'], 'high')
        # Check notification was sent despite busy state
        self.mock_tmux.send_to_pane.assert_called_once()


if __name__ == '__main__':
    unittest.main()