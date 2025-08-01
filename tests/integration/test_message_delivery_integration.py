"""
Integration tests for message delivery system
Tests the full flow from MCP message to tmux notification
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch, call

from src.orchestrator_enhanced import EnhancedOrchestrator
from src.orchestrator import OrchestratorConfig, Agent
from src.mcp_central_server import CentralMCPServer
from src.agent_state_monitor import AgentState


class TestMessageDeliveryIntegration:
    """Test full integration of message delivery system"""
    
    @pytest.fixture
    def setup_orchestrator(self):
        """Set up orchestrator with mocked tmux"""
        config = OrchestratorConfig(
            session_name="test-session",
            poll_interval=0.1
        )
        
        with patch('orchestrator.src.orchestrator.TmuxManager') as mock_tmux_class:
            orchestrator = EnhancedOrchestrator(config)
            
            # Mock tmux instance
            mock_tmux = MagicMock()
            orchestrator.tmux = mock_tmux
            
            # Set up agents
            orchestrator.agents = {
                "Leader": Agent(name="Leader", session_id="s1", pane_index=0,
                              session_file="/tmp/s1.jsonl", system_prompt="prompt"),
                "Researcher": Agent(name="Researcher", session_id="s2", pane_index=1,
                              session_file="/tmp/s2.jsonl", system_prompt="prompt")
            }
            orchestrator.mailbox = {"Leader": [], "Researcher": []}
            
            # Initialize enhanced features by mocking the parent start
            with patch('orchestrator.src.orchestrator.Orchestrator.start', return_value=True):
                orchestrator.start()
            
            # Mock tmux methods
            mock_tmux.send_to_pane.return_value = True
            mock_tmux.capture_pane.return_value = "│ > │"  # Idle state
            
            yield orchestrator, mock_tmux
    
    def test_mcp_message_triggers_notification(self, setup_orchestrator):
        """Test that MCP message delivery triggers tmux notification"""
        orchestrator, mock_tmux = setup_orchestrator
        
        # Create MCP server
        mcp_server = CentralMCPServer(orchestrator, port=8765)
        
        # Send message through MCP
        result = mcp_server._send_message("Leader", "Researcher", "Test message")
        
        assert result == "Message sent to Researcher"
        
        # Verify tmux notification was sent
        calls = mock_tmux.send_to_pane.call_args_list
        
        # Should have at least 2 calls: notification + prompt
        assert len(calls) >= 2
        
        # Check notification call
        notification_call = calls[0]
        assert notification_call[0][0] == 1  # Researcher pane index
        assert "[MESSAGE]" in notification_call[0][1]
        assert "Leader" in notification_call[0][1]
        
        # Check prompt call
        prompt_call = calls[1]
        assert prompt_call[0][0] == 1  # Researcher pane index
        assert "check_messages" in prompt_call[0][1]
    
    def test_message_queued_when_agent_busy(self, setup_orchestrator):
        """Test that messages are queued when agent is busy"""
        orchestrator, mock_tmux = setup_orchestrator
        
        # Set agent as busy
        mock_tmux.capture_pane.return_value = "● Processing request"
        
        # Create MCP server
        mcp_server = CentralMCPServer(orchestrator, port=8765)
        
        # Send message
        result = mcp_server._send_message("Leader", "Researcher", "Urgent task")
        
        assert result == "Message sent to Researcher"
        
        # Verify no immediate notification was sent
        assert mock_tmux.send_to_pane.call_count == 0
        
        # Check message was queued
        assert orchestrator.state_monitor.has_pending_messages("Researcher")
    
    def test_pane_title_setting(self, setup_orchestrator):
        """Test that pane titles are set correctly"""
        orchestrator, mock_tmux = setup_orchestrator
        
        # Simulate setting pane titles
        for agent in orchestrator.agents.values():
            orchestrator.tmux.set_pane_title(agent.pane_index, f"Agent: {agent.name}")
        
        # Verify tmux commands were called
        assert mock_tmux.set_pane_title.call_count == 2
        
        # Check specific calls
        calls = mock_tmux.set_pane_title.call_args_list
        assert calls[0][0] == (0, "Agent: Leader")
        assert calls[1][0] == (1, "Agent: Researcher")
    
    def test_state_detection_patterns(self, setup_orchestrator):
        """Test that state detection works with realistic output"""
        orchestrator, mock_tmux = setup_orchestrator
        
        # Test various Claude outputs
        test_cases = [
            ("│ > │", AgentState.IDLE),
            ("● I'll analyze this request", AgentState.BUSY),
            ("Error: MCP connection failed", AgentState.ERROR),
            ("Goodbye!", AgentState.QUIT),
            ("Some random output", AgentState.UNKNOWN)
        ]
        
        for output, expected_state in test_cases:
            mock_tmux.capture_pane.return_value = output
            state = orchestrator.state_monitor.update_agent_state("Leader", 0)
            assert state == expected_state, f"Failed for output: {output}"
    
    @pytest.mark.asyncio
    async def test_async_message_flow(self, setup_orchestrator):
        """Test async message flow through MCP server"""
        orchestrator, mock_tmux = setup_orchestrator
        
        # Create and start MCP server
        mcp_server = CentralMCPServer(orchestrator, port=8765)
        
        # Simulate MCP request
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "send_message",
                "arguments": {
                    "to": "Researcher",
                    "message": "Please research AI trends"
                }
            }
        }
        
        # Process request
        response = await mcp_server._process_request("Leader", request_data)
        
        # Check response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" not in response
        assert response["result"]["content"][0]["text"] == "Message sent to Researcher"
        
        # Verify notification was sent
        assert mock_tmux.send_to_pane.called


if __name__ == '__main__':
    pytest.main([__file__, "-v"])