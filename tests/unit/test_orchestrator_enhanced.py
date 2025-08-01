"""
Unit tests for EnhancedOrchestrator
"""

import unittest
from unittest.mock import MagicMock, patch
import time
import threading

from src.orchestrator_enhanced import EnhancedOrchestrator
from src.orchestrator import Orchestrator, OrchestratorConfig, Agent
from src.agent_state_monitor import AgentState


class TestEnhancedOrchestrator(unittest.TestCase):
    """Test enhanced orchestrator functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = OrchestratorConfig(
            session_name="test-session",
            poll_interval=0.1
        )
        
        with patch('src.orchestrator.TmuxManager'):
            self.orchestrator = EnhancedOrchestrator(self.config)
            self.orchestrator.tmux = MagicMock()
            
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.orchestrator, 'running'):
            self.orchestrator.running = False
            
    @patch('src.orchestrator_enhanced.AgentStateMonitor')
    @patch('src.orchestrator_enhanced.MessageDeliverySystem')
    def test_start_initializes_enhanced_features(self, mock_delivery_class, mock_monitor_class):
        """Test that start initializes state monitor and message delivery"""
        # Register an agent first (required for start)
        self.orchestrator.agents = {
            "TestAgent": Agent(name="TestAgent", session_id="test", pane_index=0,
                             session_file="/tmp/test.jsonl", system_prompt="prompt")
        }
        
        # Mock tmux operations
        self.orchestrator.tmux.create_session.return_value = True
        self.orchestrator.tmux.simple_launcher.launch_agent.return_value = "session-123"
        
        result = self.orchestrator.start()
            
        self.assertTrue(result)
        self.assertIsNotNone(self.orchestrator.state_monitor)
        self.assertIsNotNone(self.orchestrator.message_delivery)
        
        # Check monitor was initialized with tmux
        mock_monitor_class.assert_called_once_with(self.orchestrator.tmux)
        
        # Check delivery was initialized with orchestrator, tmux, and monitor
        mock_delivery_class.assert_called_once()
        
    @patch('threading.Thread')
    def test_start_creates_monitor_thread(self, mock_thread_class):
        """Test that start creates and starts monitor thread"""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        # Register an agent first
        self.orchestrator.agents = {
            "TestAgent": Agent(name="TestAgent", session_id="test", pane_index=0,
                             session_file="/tmp/test.jsonl", system_prompt="prompt")
        }
        
        # Mock tmux operations
        self.orchestrator.tmux.create_session.return_value = True
        self.orchestrator.tmux.simple_launcher.launch_agent.return_value = "session-123"
        
        self.orchestrator.start()
            
        # Check thread was created with correct target
        mock_thread_class.assert_called_once()
        call_kwargs = mock_thread_class.call_args[1]
        self.assertEqual(call_kwargs['target'], self.orchestrator._state_monitor_loop)
        self.assertTrue(call_kwargs['daemon'])
        
        # Check thread was started
        mock_thread.start.assert_called_once()
        
    def test_send_message_with_enhanced_delivery(self):
        """Test send_message_to_agent uses enhanced delivery when available"""
        self.orchestrator.message_delivery = MagicMock()
        self.orchestrator.message_delivery.send_message_to_agent.return_value = True
        
        result = self.orchestrator.send_message_to_agent(
            "Agent1", "Agent2", "Test message", "high"
        )
        
        self.assertTrue(result)
        self.orchestrator.message_delivery.send_message_to_agent.assert_called_once_with(
            "Agent1", "Agent2", "Test message", "high"
        )
        
    def test_send_message_fallback_without_enhanced_delivery(self):
        """Test send_message_to_agent falls back when enhanced delivery not available"""
        self.orchestrator.message_delivery = None
        
        # Set up agent for the test
        self.orchestrator.agents = {
            "Agent1": Agent(name="Agent1", session_id="s1", pane_index=0,
                          session_file="/tmp/s1.jsonl", system_prompt="prompt")
        }
        self.orchestrator.mailbox = {}
        
        # Mock the parent's send_message_to_agent method
        with patch.object(Orchestrator, 'send_message_to_agent', return_value=True) as mock_parent:
            result = self.orchestrator.send_message_to_agent(
                "Agent1", "Agent2", "Test message", "normal"
            )
        
        self.assertTrue(result)
        # Verify parent method was called with correct args
        mock_parent.assert_called_once_with(
            "Agent1", "Agent2", "Test message", "normal"
        )
        
    def test_get_agent_state(self):
        """Test getting agent state"""
        # Set up agent
        self.orchestrator.agents = {
            "Agent1": Agent(name="Agent1", session_id="s1", pane_index=0,
                          session_file="/tmp/s1.jsonl", system_prompt="prompt")
        }
        
        # Set up mock state monitor
        self.orchestrator.state_monitor = MagicMock()
        self.orchestrator.state_monitor.update_agent_state.return_value = AgentState.BUSY
        
        state = self.orchestrator.get_agent_state("Agent1")
        
        self.assertEqual(state, "busy")
        self.orchestrator.state_monitor.update_agent_state.assert_called_once_with("Agent1", 0)
        
    def test_get_agent_state_unknown_agent(self):
        """Test getting state for unknown agent returns None"""
        self.orchestrator.agents = {}
        self.orchestrator.state_monitor = MagicMock()
        
        state = self.orchestrator.get_agent_state("Unknown")
        
        self.assertIsNone(state)
        
    def test_get_all_agent_states(self):
        """Test getting all agent states"""
        # Set up agents
        self.orchestrator.agents = {
            "Agent1": Agent(name="Agent1", session_id="s1", pane_index=0,
                          session_file="/tmp/s1.jsonl", system_prompt="prompt"),
            "Agent2": Agent(name="Agent2", session_id="s2", pane_index=1,
                          session_file="/tmp/s2.jsonl", system_prompt="prompt")
        }
        
        # Mock get_agent_state
        self.orchestrator.get_agent_state = MagicMock(side_effect=["idle", "busy"])
        
        states = self.orchestrator.get_all_agent_states()
        
        self.assertEqual(states, {"Agent1": "idle", "Agent2": "busy"})
        
    def test_wait_for_agent_idle_success(self):
        """Test waiting for agent to become idle succeeds"""
        self.orchestrator.agents = {"Agent1": MagicMock()}
        self.orchestrator.state_monitor = MagicMock()
        
        # Mock get_agent_state to return busy twice then idle
        self.orchestrator.get_agent_state = MagicMock(
            side_effect=["busy", "busy", "idle"]
        )
        
        result = self.orchestrator.wait_for_agent_idle("Agent1", timeout=5)
        
        self.assertTrue(result)
        self.assertEqual(self.orchestrator.get_agent_state.call_count, 3)
        
    def test_wait_for_agent_idle_timeout(self):
        """Test waiting for agent times out"""
        self.orchestrator.agents = {"Agent1": MagicMock()}
        self.orchestrator.state_monitor = MagicMock()
        
        # Mock get_agent_state to always return busy
        self.orchestrator.get_agent_state = MagicMock(return_value="busy")
        
        result = self.orchestrator.wait_for_agent_idle("Agent1", timeout=1)
        
        self.assertFalse(result)
        
    def test_send_direct_input(self):
        """Test sending direct input to agent"""
        self.orchestrator.message_delivery = MagicMock()
        self.orchestrator.message_delivery.send_text_to_agent_input.return_value = True
        
        result = self.orchestrator.send_direct_input("Agent1", "list_agents")
        
        self.assertTrue(result)
        self.orchestrator.message_delivery.send_text_to_agent_input.assert_called_once_with(
            "Agent1", "list_agents"
        )
        
    def test_send_command(self):
        """Test sending command to agent"""
        self.orchestrator.message_delivery = MagicMock()
        self.orchestrator.message_delivery.send_command_to_agent.return_value = True
        
        result = self.orchestrator.send_command("Agent1", "check_messages")
        
        self.assertTrue(result)
        self.orchestrator.message_delivery.send_command_to_agent.assert_called_once_with(
            "Agent1", "check_messages"
        )
        
    def test_state_monitor_loop_updates_states(self):
        """Test that monitor loop updates agent states"""
        # Set up running state
        self.orchestrator.running = True
        self.orchestrator.monitor_interval = 0.01
        
        # Set up agents
        self.orchestrator.agents = {
            "Agent1": Agent(name="Agent1", session_id="s1", pane_index=0,
                          session_file="/tmp/s1.jsonl", system_prompt="prompt")
        }
        
        # Set up mocks
        self.orchestrator.state_monitor = MagicMock()
        self.orchestrator.message_delivery = MagicMock()
        
        # Run loop briefly
        loop_thread = threading.Thread(target=self.orchestrator._state_monitor_loop)
        loop_thread.daemon = True
        loop_thread.start()
        
        time.sleep(0.05)
        self.orchestrator.running = False
        loop_thread.join(timeout=1)
        
        # Check that state was updated
        self.orchestrator.state_monitor.update_agent_state.assert_called()
        self.orchestrator.message_delivery.check_and_deliver_pending_messages.assert_called()
        
    def test_state_monitor_loop_handles_exceptions(self):
        """Test that monitor loop continues after exceptions"""
        self.orchestrator.running = True
        self.orchestrator.monitor_interval = 0.01
        self.orchestrator.agents = {"Agent1": MagicMock()}
        
        # Mock to raise exception
        self.orchestrator.state_monitor = MagicMock()
        self.orchestrator.state_monitor.update_agent_state.side_effect = Exception("Test error")
        self.orchestrator.message_delivery = MagicMock()
        
        # Run loop briefly
        loop_thread = threading.Thread(target=self.orchestrator._state_monitor_loop)
        loop_thread.daemon = True
        loop_thread.start()
        
        time.sleep(0.05)
        self.orchestrator.running = False
        loop_thread.join(timeout=1)
        
        # Should have called update multiple times despite exceptions
        self.assertGreater(self.orchestrator.state_monitor.update_agent_state.call_count, 1)


if __name__ == '__main__':
    unittest.main()