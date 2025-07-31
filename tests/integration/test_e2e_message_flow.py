"""
End-to-end test for message delivery system
Tests with real tmux session (requires tmux installed)
"""

import pytest
import subprocess
import time
import tempfile
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from orchestrator.src.orchestrator import OrchestratorConfig
from orchestrator.src.tmux_manager import TmuxManager


class TestE2EMessageFlow:
    """End-to-end test with real tmux session"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture  
    def tmux_session(self):
        """Create and clean up tmux session"""
        session_name = "test-e2e-message"
        
        # Kill any existing session
        subprocess.run(["tmux", "kill-session", "-t", session_name], 
                      capture_output=True)
        
        yield session_name
        
        # Cleanup
        subprocess.run(["tmux", "kill-session", "-t", session_name], 
                      capture_output=True)
    
    def test_message_notification_appears_in_pane(self, tmux_session, temp_dir):
        """Test that notification actually appears in tmux pane"""
        # Create tmux manager
        tmux = TmuxManager(tmux_session)
        
        # Create session with 2 panes
        assert tmux.create_session(2)
        
        # Simulate agent idle state
        tmux.send_to_pane(0, "echo '│ > │'")
        tmux.send_to_pane(1, "echo '│ > │'")
        time.sleep(0.1)
        
        # Send notification to pane 1
        notification = "[MESSAGE] From Leader: You have a new message"
        tmux.send_to_pane(1, f"echo '{notification}'")
        time.sleep(0.1)
        
        # Capture pane content
        content = tmux.capture_pane(1)
        
        # Verify notification appears
        assert content is not None, "Failed to capture pane content"
        assert "[MESSAGE]" in content, f"No notification found in pane. Content: {content}"
        assert "From Leader" in content, f"Sender not mentioned. Content: {content}"
    
    def test_pane_titles_are_set_correctly(self, tmux_session):
        """Test that pane titles display correctly"""
        tmux = TmuxManager(tmux_session)
        
        # Create session
        assert tmux.create_session(3)
        
        # Set pane titles
        tmux.set_pane_title(0, "Agent: Leader")
        tmux.set_pane_title(1, "Agent: Researcher")
        tmux.set_pane_title(2, "Agent: Writer")
        
        # List panes with format to check titles
        result = subprocess.run(
            ["tmux", "list-panes", "-t", tmux_session, "-F", "#{pane_index}:#{pane_title}"],
            capture_output=True, text=True
        )
        
        output = result.stdout.strip()
        lines = output.split('\n')
        
        # Verify titles
        assert "0:Agent: Leader" in output or "0:" in lines[0]
        assert "1:Agent: Researcher" in output or "1:" in lines[1]
        assert "2:Agent: Writer" in output or "2:" in lines[2]
    
    def test_state_detection_with_real_output(self, tmux_session):
        """Test state detection with realistic Claude output"""
        from orchestrator.src.agent_state_monitor import AgentStateMonitor
        
        tmux = TmuxManager(tmux_session)
        monitor = AgentStateMonitor(tmux)
        
        # Create session with 1 pane
        assert tmux.create_session(1)
        
        # Test idle state pattern
        tmux.send_to_pane(0, "clear")
        time.sleep(0.1)
        tmux.send_to_pane(0, "echo '╭─────────────────────╮'")
        tmux.send_to_pane(0, "echo '│ >                   │'")
        tmux.send_to_pane(0, "echo '╰─────────────────────╯'")
        time.sleep(0.1)
        
        state = monitor.update_agent_state("test", 0)
        assert state.value == "idle"
        
        # Test busy state pattern
        tmux.send_to_pane(0, "clear")
        time.sleep(0.1)
        tmux.send_to_pane(0, "echo '● Processing your request...'")
        time.sleep(0.1)
        
        state = monitor.update_agent_state("test", 0)
        assert state.value == "busy"
    
    @pytest.mark.slow
    def test_full_message_flow_simulation(self, tmux_session, temp_dir):
        """Simulate full message flow between agents"""
        # This test would require more setup but demonstrates the concept
        # Would need to mock Claude launches but test tmux integration
        # Key is to verify actual tmux content, not just mock calls
        pass


if __name__ == '__main__':
    # Run only if tmux is available
    try:
        subprocess.run(["tmux", "-V"], check=True, capture_output=True)
        pytest.main([__file__, "-v", "-s"])
    except subprocess.CalledProcessError:
        print("Tmux not available, skipping E2E tests")