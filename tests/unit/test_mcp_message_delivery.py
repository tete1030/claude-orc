"""
Unit tests for MCP message delivery integration
"""

import unittest
from unittest.mock import MagicMock, patch

from orchestrator.src.mcp_central_server import CentralMCPServer
from orchestrator.src.orchestrator_enhanced import EnhancedOrchestrator
from orchestrator.src.orchestrator import OrchestratorConfig, Agent
from orchestrator.src.agent_state_monitor import AgentState


class TestMCPMessageDelivery(unittest.TestCase):
    """Test that MCP messages trigger proper notifications"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create enhanced orchestrator
        self.config = OrchestratorConfig(
            session_name="test-session",
            poll_interval=0.1
        )
        
        with patch('orchestrator.src.orchestrator.TmuxManager'):
            self.orchestrator = EnhancedOrchestrator(self.config)
            self.orchestrator.tmux = MagicMock()
            
            # Mock the enhanced features
            self.orchestrator.state_monitor = MagicMock()
            self.orchestrator.message_delivery = MagicMock()
            
            # Set up agents
            self.orchestrator.agents = {
                "Agent1": Agent(name="Agent1", session_id="s1", pane_index=0,
                              session_file="/tmp/s1.jsonl", system_prompt="prompt"),
                "Agent2": Agent(name="Agent2", session_id="s2", pane_index=1,
                              session_file="/tmp/s2.jsonl", system_prompt="prompt")
            }
            self.orchestrator.mailbox = {"Agent1": [], "Agent2": []}
            
        # Create MCP server
        self.mcp_server = CentralMCPServer(self.orchestrator, port=8765)
        
    def test_mcp_send_message_calls_enhanced_delivery(self):
        """Test that MCP send_message uses enhanced delivery system"""
        # Mock the enhanced send_message_to_agent to return True
        self.orchestrator.send_message_to_agent = MagicMock(return_value=True)
        
        # Call the MCP _send_message method
        result = self.mcp_server._send_message("Agent1", "Agent2", "Test message")
        
        # Verify enhanced delivery was called
        self.orchestrator.send_message_to_agent.assert_called_once_with(
            "Agent2", "Agent1", "Test message", priority="normal"
        )
        self.assertEqual(result, "Message sent to Agent2")
        
    def test_mcp_send_message_fallback_without_enhanced(self):
        """Test fallback when enhanced delivery not available"""
        # Create a fresh orchestrator without enhanced features
        config = OrchestratorConfig(
            session_name="test-session",
            poll_interval=0.1
        )
        
        with patch('orchestrator.src.orchestrator.TmuxManager'):
            # Use base Orchestrator instead of EnhancedOrchestrator
            from orchestrator.src.orchestrator import Orchestrator
            basic_orchestrator = Orchestrator(config)
            basic_orchestrator.tmux = MagicMock()
            
            # Set up agents
            basic_orchestrator.agents = {
                "Agent1": Agent(name="Agent1", session_id="s1", pane_index=0,
                              session_file="/tmp/s1.jsonl", system_prompt="prompt"),
                "Agent2": Agent(name="Agent2", session_id="s2", pane_index=1,
                              session_file="/tmp/s2.jsonl", system_prompt="prompt")
            }
            basic_orchestrator.mailbox = {"Agent1": [], "Agent2": []}
            
            # Create MCP server with basic orchestrator
            basic_mcp_server = CentralMCPServer(basic_orchestrator, port=8766)
            
            # Call the MCP _send_message method
            result = basic_mcp_server._send_message("Agent1", "Agent2", "Test message")
            
            # Verify message was added to mailbox
            self.assertEqual(len(basic_orchestrator.mailbox["Agent2"]), 1)
            self.assertEqual(basic_orchestrator.mailbox["Agent2"][0]["from"], "Agent1")
            self.assertEqual(basic_orchestrator.mailbox["Agent2"][0]["message"], "Test message")
            self.assertEqual(result, "Message sent to Agent2")
        
    def test_mcp_send_message_to_unknown_agent(self):
        """Test sending message to unknown agent"""
        result = self.mcp_server._send_message("Agent1", "Unknown", "Test message")
        
        self.assertEqual(result, "Error: Agent 'Unknown' not found")
        
    def test_enhanced_delivery_triggers_notification(self):
        """Test that enhanced delivery triggers notification when agent is idle"""
        # Set up the message delivery mock
        self.orchestrator.message_delivery.send_message_to_agent.return_value = True
        
        # Set agent as idle
        self.orchestrator.state_monitor.update_agent_state.return_value = AgentState.IDLE
        
        # Send message through orchestrator
        result = self.orchestrator.send_message_to_agent(
            "Agent2", "Agent1", "Test message", "normal"
        )
        
        self.assertTrue(result)
        self.orchestrator.message_delivery.send_message_to_agent.assert_called_once_with(
            "Agent2", "Agent1", "Test message", "normal"
        )
        
    def test_integration_mcp_to_notification(self):
        """Test full integration from MCP call to notification"""
        # Set up mocks for the full flow
        self.orchestrator.send_message_to_agent = MagicMock(return_value=True)
        self.orchestrator.message_delivery.send_message_to_agent.return_value = True
        self.orchestrator.state_monitor.update_agent_state.return_value = AgentState.IDLE
        
        # Directly call the internal method that handles send_message
        result = self.mcp_server._send_message("Agent1", "Agent2", "Hello from MCP")
        
        # Verify the result
        self.assertEqual(result, "Message sent to Agent2")
        
        # Verify enhanced delivery was used
        self.orchestrator.send_message_to_agent.assert_called_once()
        call_args = self.orchestrator.send_message_to_agent.call_args[0]
        self.assertEqual(call_args[0], "Agent2")  # to_agent
        self.assertEqual(call_args[1], "Agent1")  # from_agent
        self.assertEqual(call_args[2], "Hello from MCP")  # message


if __name__ == '__main__':
    unittest.main()