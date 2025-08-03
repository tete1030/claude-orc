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
        
    def test_send_message_to_error_agent_succeeds(self):
        """Test sending message to agent in error state succeeds (state-agnostic delivery)"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.ERROR
        
        result = self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
        self.assertTrue(result)
        self.mock_tmux.send_to_pane.assert_called_once()
        
    def test_send_message_to_quit_agent_succeeds(self):
        """Test sending message to quit agent succeeds (state-agnostic delivery)"""
        self.mock_state_monitor.update_agent_state.return_value = AgentState.QUIT
        
        result = self.delivery.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
        self.assertTrue(result)
        self.mock_tmux.send_to_pane.assert_called_once()
        
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
        
    def test_reminder_system_complete_flow(self):
        """Test complete reminder system flow"""
        # 1. Agent is BUSY with unread messages → No reminder sent
        self.mock_state_monitor.update_agent_state.return_value = AgentState.BUSY
        self.mock_orchestrator.mailbox["Agent1"] = [
            {'from': 'Agent2', 'message': 'Unread message'}
        ]
        
        self.delivery.check_and_deliver_pending_messages()
        
        # No reminders should be sent to busy agent
        calls = self.mock_tmux.send_to_pane.call_args_list
        busy_reminder_calls = [call for call in calls if "Reminder" in str(call)]
        self.assertEqual(len(busy_reminder_calls), 0, "No reminders should be sent to busy agent")
        
        # Reset mock
        self.mock_tmux.reset_mock()
        
        # 2. Agent becomes IDLE → Reminder sent once
        self.mock_state_monitor.update_agent_state.return_value = AgentState.IDLE
        
        self.delivery.check_and_deliver_pending_messages()
        
        # Should send exactly one reminder
        calls = self.mock_tmux.send_to_pane.call_args_list
        idle_reminder_calls = [call for call in calls if "Reminder" in str(call)]
        self.assertEqual(len(idle_reminder_calls), 1, "Should send exactly one reminder to idle agent")
        
        # Reset mock
        self.mock_tmux.reset_mock()
        
        # 3. Agent stays IDLE → No duplicate reminders
        self.delivery.check_and_deliver_pending_messages()
        
        # Should not send another reminder
        calls = self.mock_tmux.send_to_pane.call_args_list
        duplicate_reminder_calls = [call for call in calls if "Reminder" in str(call)]
        self.assertEqual(len(duplicate_reminder_calls), 0, "Should not send duplicate reminders")
        
        # 4. New message arrives → Reminder flag resets automatically
        # Reset mock
        self.mock_tmux.reset_mock()
        
        # Send new message (this will reset the reminder flag)
        result = self.delivery.send_message_to_agent(
            "Agent2", "Agent1", "New message after check", "normal"
        )
        self.assertTrue(result)
        
        # Reset mock to check only reminder calls
        self.mock_tmux.reset_mock()
        
        # Should send reminder again since flag was reset by new message
        self.delivery.check_and_deliver_pending_messages()
        
        calls = self.mock_tmux.send_to_pane.call_args_list
        reset_reminder_calls = [call for call in calls if "Reminder" in str(call)]
        self.assertEqual(len(reset_reminder_calls), 1, "Should send reminder again after flag reset by new message")

    def test_reminder_flag_reset_on_new_message(self):
        """Test that reminder flag resets when new messages arrive"""
        # Set up agent as idle with reminder already sent
        self.mock_state_monitor.update_agent_state.return_value = AgentState.IDLE
        self.mock_orchestrator.mailbox["Agent1"] = [
            {'from': 'Agent2', 'message': 'First message'}
        ]
        
        # Send first reminder
        self.delivery.check_and_deliver_pending_messages()
        
        # Reset mock
        self.mock_tmux.reset_mock()
        
        # Check again - should not send duplicate
        self.delivery.check_and_deliver_pending_messages()
        calls = self.mock_tmux.send_to_pane.call_args_list
        self.assertEqual(len([call for call in calls if "Reminder" in str(call)]), 0)
        
        # Reset mock
        self.mock_tmux.reset_mock()
        
        # Simulate new message arriving (which resets the flag in send_message_to_agent)
        result = self.delivery.send_message_to_agent(
            "Agent2", "Agent1", "New message", "normal"
        )
        self.assertTrue(result)
        
        # Reset mock to check only reminder calls
        self.mock_tmux.reset_mock()
        
        # Now check_and_deliver should send reminder again
        self.delivery.check_and_deliver_pending_messages()
        
        calls = self.mock_tmux.send_to_pane.call_args_list
        reminder_calls = [call for call in calls if "Reminder" in str(call)]
        self.assertEqual(len(reminder_calls), 1, "Should send reminder after new message resets flag")

    def test_no_reminders_for_non_idle_states(self):
        """Test that reminders are only sent to idle agents"""
        states_to_test = [AgentState.BUSY, AgentState.WRITING, AgentState.ERROR, AgentState.QUIT, AgentState.INITIALIZING]
        
        for state in states_to_test:
            with self.subTest(state=state):
                # Reset mock
                self.mock_tmux.reset_mock()
                
                # Set agent state and add unread messages
                self.mock_state_monitor.update_agent_state.return_value = state
                self.mock_orchestrator.mailbox["Agent1"] = [
                    {'from': 'Agent2', 'message': f'Message for {state.value} agent'}
                ]
                
                self.delivery.check_and_deliver_pending_messages()
                
                # Should not send any reminders
                calls = self.mock_tmux.send_to_pane.call_args_list
                reminder_calls = [call for call in calls if "Reminder" in str(call)]
                self.assertEqual(len(reminder_calls), 0, f"Should not send reminders to {state.value} agent")
        
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