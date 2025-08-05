"""
REAL integration test - no mocks, actual components
"""

import pytest
import subprocess
import time
import os
import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.orchestrator_enhanced import EnhancedOrchestrator
from src.orchestrator import OrchestratorConfig
from src.mcp_central_server import CentralMCPServer
import asyncio
import threading


class TestRealIntegration:
    """Test with REAL components - no mocks"""
    
    @pytest.fixture
    def cleanup_tmux(self):
        """Clean up tmux sessions before and after tests"""
        session_name = "test-real-integration"
        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
        yield session_name
        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
    
    def test_message_delivery_actually_works(self, cleanup_tmux):
        """Test that messages ACTUALLY get delivered - no mocks"""
        session_name = cleanup_tmux
        
        # Create REAL orchestrator
        config = OrchestratorConfig(
            session_name=session_name,
            poll_interval=0.1
        )
        
        orchestrator = EnhancedOrchestrator(config)
        
        # Register agents (won't launch Claude, but will create tmux panes)
        orchestrator.register_agent("TestAgent1", "session1", "Test agent 1", working_dir=None)
        orchestrator.register_agent("TestAgent2", "session2", "Test agent 2", working_dir=None) 
        
        # Start MCP server in background
        mcp_port = 8767
        mcp_server = CentralMCPServer(orchestrator, port=mcp_port)
        
        async def run_mcp():
            await mcp_server.run_forever()
        
        mcp_thread = threading.Thread(target=lambda: asyncio.run(run_mcp()), daemon=True)
        mcp_thread.start()
        time.sleep(1)
        
        # Start orchestrator (creates tmux session)
        assert orchestrator.start(mcp_port=mcp_port)
        
        # Wait for initialization
        time.sleep(2)
        
        # Simulate agent being idle by sending text to pane
        subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:0.0", "clear", "Enter"])
        subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:0.0", "echo '│ > │'", "Enter"])
        subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:0.1", "clear", "Enter"])
        subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:0.1", "echo '│ > │'", "Enter"])
        time.sleep(0.5)
        
        # Send REAL message through the system
        success = orchestrator.send_message_to_agent("TestAgent2", "TestAgent1", "Hello from test", "normal")
        assert success
        
        # Wait for delivery
        time.sleep(1)
        
        # Capture REAL tmux pane content
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", f"{session_name}:0.1", "-p"],
            capture_output=True, text=True
        )
        
        pane_content = result.stdout
        
        # VERIFY: Message notification actually appears
        assert "[MESSAGE]" in pane_content, f"No notification found in pane. Content: {pane_content}"
        assert "TestAgent1" in pane_content, f"Sender not mentioned. Content: {pane_content}"
        
        # Clean up
        orchestrator.stop()
    
    def test_pane_titles_actually_display(self, cleanup_tmux):
        """Test that pane titles ACTUALLY show up in tmux"""
        session_name = cleanup_tmux
        
        # Create session manually to test just titles
        subprocess.run(["tmux", "new-session", "-d", "-s", session_name])
        subprocess.run(["tmux", "split-window", "-h", "-t", session_name])
        
        # Set pane titles using actual tmux commands
        subprocess.run(["tmux", "set-option", "-t", session_name, "pane-border-status", "top"])
        subprocess.run(["tmux", "select-pane", "-t", f"{session_name}:0.0", "-T", "Test Agent 1"])
        subprocess.run(["tmux", "select-pane", "-t", f"{session_name}:0.1", "-T", "Test Agent 2"])
        
        # Get pane info
        result = subprocess.run(
            ["tmux", "list-panes", "-t", session_name, "-F", "#{pane_index}:#{pane_title}"],
            capture_output=True, text=True
        )
        
        output = result.stdout.strip()
        
        # Verify titles are set
        assert "Test Agent 1" in output or "0:Test Agent 1" in output
        assert "Test Agent 2" in output or "1:Test Agent 2" in output
    
    def test_state_detection_with_real_tmux(self, cleanup_tmux):
        """Test state detection with REAL tmux content"""
        from src.agent_state_monitor import AgentStateMonitor, AgentState
        from src.tmux_manager import TmuxManager
        
        session_name = cleanup_tmux
        
        # Create real tmux session
        tmux = TmuxManager(session_name)
        assert tmux.create_session(1)
        
        monitor = AgentStateMonitor(tmux)
        
        # Test with real tmux content
        test_cases = [
            ("echo '│ > │'", AgentState.IDLE),
            ("echo '● Processing request...'", AgentState.BUSY),
            ("echo 'Error: Connection failed'", AgentState.ERROR)
        ]
        
        for command, expected_state in test_cases:
            # Clear and send command
            subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:0.0", "clear", "Enter"])
            subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:0.0", command, "Enter"])
            time.sleep(0.2)
            
            # Detect state
            state = monitor.update_agent_state("test", 0)
            assert state == expected_state, f"Wrong state for '{command}': got {state}, expected {expected_state}"


if __name__ == '__main__':
    # Check if tmux is available
    try:
        subprocess.run(["tmux", "-V"], check=True, capture_output=True)
        pytest.main([__file__, "-v", "-s"])
    except subprocess.CalledProcessError:
        print("ERROR: tmux not available. Integration tests require tmux!")
        sys.exit(1)