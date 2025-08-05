"""Unit tests for TmuxManager"""

import unittest
from unittest.mock import patch, MagicMock, call
import subprocess
from src.tmux_manager import TmuxManager, TmuxPane


class TestTmuxManager(unittest.TestCase):
    """Test cases for TmuxManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tmux_manager = TmuxManager("test-session")
        
    @patch('subprocess.run')
    def test_session_exists_true(self, mock_run):
        """Test session_exists returns True when session exists"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.tmux_manager.session_exists()
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["tmux", "has-session", "-t", "test-session"],
            check=False, capture_output=True, text=False
        )
        
    @patch('subprocess.run')
    def test_session_exists_false(self, mock_run):
        """Test session_exists returns False when session doesn't exist"""
        mock_run.return_value = MagicMock(returncode=1)
        
        result = self.tmux_manager.session_exists()
        
        self.assertFalse(result)
        
    @patch('subprocess.run')
    def test_create_session_success(self, mock_run):
        """Test successful session creation"""
        # Create enough mock returns for all tmux commands
        # We need ~21 commands for a 2-pane session
        mock_returns = [MagicMock(returncode=1)]  # has-session returns 1 (doesn't exist)
        mock_returns.extend([MagicMock(returncode=0)] * 25)  # All other commands succeed
        mock_run.side_effect = mock_returns
        
        result = self.tmux_manager.create_session(2)
        
        self.assertTrue(result)
        # Check that tmux commands were called
        calls = mock_run.call_args_list
        # Should have at least: has-session, new-session, various set-options, 
        # bind-keys, split-window, select-layout
        self.assertGreaterEqual(len(calls), 15)
        
        # Verify key commands were called
        has_session_call = calls[0]
        self.assertIn("has-session", str(has_session_call))
        
        # Find new-session call
        new_session_calls = [c for c in calls if "new-session" in str(c)]
        self.assertEqual(len(new_session_calls), 1)
        
    @patch('subprocess.run')
    def test_create_session_failure(self, mock_run):
        """Test session creation failure"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "tmux")
        
        result = self.tmux_manager.create_session(2)
        
        self.assertFalse(result)
        
    @patch('subprocess.run')
    def test_send_to_pane_success(self, mock_run):
        """Test successful command send to pane"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.tmux_manager.send_to_pane(0, "echo test")
        
        self.assertTrue(result)
        # Now sends two commands: text then Enter
        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call(
            ["tmux", "send-keys", "-t", "test-session:0.0", "-l", "echo test"],
            check=True, capture_output=False, text=False
        )
        mock_run.assert_any_call(
            ["tmux", "send-keys", "-t", "test-session:0.0", "Enter"],
            check=True, capture_output=False, text=False
        )
        
    @patch('subprocess.run')
    def test_capture_pane_success(self, mock_run):
        """Test successful pane capture"""
        mock_run.return_value = MagicMock(returncode=0, stdout="pane content")
        
        result = self.tmux_manager.capture_pane(0)
        
        self.assertEqual(result, "pane content")
        mock_run.assert_called_once_with(
            ["tmux", "capture-pane", "-t", "test-session:0.0", "-p"],
            check=True, capture_output=True, text=True
        )
        
    @patch('subprocess.run')
    def test_list_panes_success(self, mock_run):
        """Test successful pane listing"""
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="0:80:24:1\n1:80:24:0\n"
        )
        
        panes = self.tmux_manager.list_panes()
        
        self.assertEqual(len(panes), 2)
        self.assertEqual(panes[0].index, 0)
        self.assertEqual(panes[0].width, 80)
        self.assertEqual(panes[0].height, 24)
        self.assertTrue(panes[0].active)
        self.assertFalse(panes[1].active)
        
    @patch('subprocess.run')
    def test_set_pane_title(self, mock_run):
        """Test setting pane title"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.tmux_manager.set_pane_title(0, "Test Title")
        
        self.assertTrue(result)
        # Should have two calls: set pane-border-status and pane-border-format
        self.assertEqual(mock_run.call_count, 2)
        
    @patch('subprocess.run')
    def test_kill_session_success(self, mock_run):
        """Test successful session kill"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.tmux_manager.kill_session()
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["tmux", "kill-session", "-t", "test-session"],
            check=True, capture_output=False, text=False
        )
        
    def test_launch_claude_in_pane_integration(self):
        """Test launching Claude in pane with actual integration points"""
        # Create a custom tmux manager with mocked subprocess but real logic
        with patch('subprocess.run') as mock_run:
            # Mock successful subprocess calls
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            
            # Test without working directory
            with patch.object(self.tmux_manager.simple_launcher, 'launch_agent', 
                            return_value="session-123") as mock_launch:
                result = self.tmux_manager.launch_claude_in_pane(
                    pane_index=0,
                    agent_name="test-agent",
                    agent_prompt="Test prompt"
                )
                
                self.assertEqual(result, "session-123")
                mock_launch.assert_called_once_with(
                    pane_index=0,
                    agent_name="test-agent",
                    system_prompt="Test prompt",
                    mcp_config=None,
                    session_id=None
                )
                
            # Test with working directory
            with patch.object(self.tmux_manager.simple_launcher, 'launch_agent', 
                            return_value="session-456") as mock_launch:
                result = self.tmux_manager.launch_claude_in_pane(
                    pane_index=1,
                    agent_name="worker-agent",
                    agent_prompt="Worker prompt",
                    working_dir="/tmp/work"
                )
                
                self.assertEqual(result, "session-456")
                # Verify cd command was sent
                cd_calls = [c for c in mock_run.call_args_list 
                           if 'cd /tmp/work' in str(c)]
                self.assertTrue(len(cd_calls) > 0, "Expected cd command to be sent")
                mock_launch.assert_called_once_with(
                    pane_index=1,
                    agent_name="worker-agent",
                    system_prompt="Worker prompt",
                    mcp_config=None,
                    session_id=None
                )
    
    @patch('subprocess.run')
    def test_launch_claude_in_pane_failure(self, mock_run):
        """Test launching Claude in pane when launch fails"""
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock launcher to return None (failure)
        with patch.object(self.tmux_manager.simple_launcher, 'launch_agent', 
                        return_value=None) as mock_launch:
            result = self.tmux_manager.launch_claude_in_pane(
                pane_index=0,
                agent_name="test-agent",
                agent_prompt="Test prompt"
            )
            
            self.assertIsNone(result)
            mock_launch.assert_called_once()


if __name__ == '__main__':
    unittest.main()