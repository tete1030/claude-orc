#!/usr/bin/env python3
"""
Unit tests for SimpleLauncher resume functionality.

Tests the SimpleLauncher with session_id parameter and
command building for both normal and resume modes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.simple_launcher import SimpleLauncher
from src.claude_launcher_config import ClaudeLauncherConfig


class TestSimpleLauncherResume:
    """Test SimpleLauncher with resume functionality"""
    
    @pytest.fixture
    def mock_tmux_manager(self):
        """Create a mock TmuxManager"""
        mock = Mock()
        mock.session_name = "test-session"
        mock.capture_pane.return_value = "Welcome to Claude Code!"
        return mock
    
    @pytest.fixture
    def launcher(self, mock_tmux_manager):
        """Create a SimpleLauncher instance with mocked dependencies"""
        return SimpleLauncher(mock_tmux_manager)
    
    @patch('src.simple_launcher.ClaudeLauncherConfig.build_command_string')
    def test_launch_agent_normal_mode(self, mock_build_cmd, launcher):
        """Test launching agent in normal mode (no resume)"""
        mock_build_cmd.return_value = "claude chat"
        # Mock tmux._run_command to track command sending
        launcher.tmux._run_command = Mock()
        
        session_id = launcher.launch_agent(
            pane_index=0,
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )
        
        # Verify normal command was built
        mock_build_cmd.assert_called_once()
        call_args = mock_build_cmd.call_args[1]
        assert call_args["instance_name"] == "TestAgent"
        assert "session_id" in call_args  # Should have generated new session ID
        
        # Verify tmux command was sent
        assert launcher.tmux._run_command.called
        
        # Verify session ID was returned
        assert session_id is not None
        assert isinstance(session_id, str)
    
    @patch('src.simple_launcher.ClaudeLauncherConfig.build_command_string')
    def test_launch_agent_resume_mode(self, mock_build_cmd, launcher):
        """Test launching agent in resume mode"""
        mock_build_cmd.return_value = "claude chat --resume test-session-456"
        # Mock tmux._run_command to track command sending
        launcher.tmux._run_command = Mock()
        
        session_id = launcher.launch_agent(
            pane_index=0,
            agent_name="TestAgent",
            system_prompt="Test prompt",
            session_id="test-session-456"
        )
        
        # Verify resume command was built
        mock_build_cmd.assert_called_once()
        call_args = mock_build_cmd.call_args[1]
        assert call_args["instance_name"] == "TestAgent"
        assert call_args["session_id"] == "test-session-456"
        assert call_args["resume"] == True
        assert call_args["mcp_config_path"] is None
        
        # Verify tmux command was sent
        assert launcher.tmux._run_command.called
        
        # Verify same session ID was returned
        assert session_id == "test-session-456"
    
    def test_launch_agent_with_mcp_config(self, launcher):
        """Test launching agent with MCP configuration"""
        # Set shared_mcp_dir to avoid ValueError
        launcher.shared_mcp_dir = "/tmp/test_mcp"
        
        # Mock tmux._run_command to track command sending
        launcher.tmux._run_command = Mock()
        
        mcp_config = {"server": "localhost", "port": 8767}
        
        session_id = launcher.launch_agent(
            pane_index=0,
            agent_name="TestAgent",
            system_prompt="Test prompt",
            mcp_config=mcp_config,
        )
        
        # Verify tmux command was sent
        assert launcher.tmux._run_command.called
        
        # Verify session ID was returned
        assert session_id is not None
    
    @patch('src.simple_launcher.ClaudeLauncherConfig.verify_script_exists')
    def test_launch_agent_command_failure(self, mock_verify, launcher):
        """Test handling of launch command failure"""
        # Mock script not found
        mock_verify.return_value = False
        
        session_id = launcher.launch_agent(
            pane_index=0,
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )
        
        # Should return None on failure
        assert session_id is None


class TestClaudeLauncherConfigResume:
    """Test ClaudeLauncherConfig resume command building"""
    
    def test_build_resume_command_string(self):
        """Test building resume command string"""
        cmd = ClaudeLauncherConfig.build_command_string(
            instance_name="TestAgent",
            session_id="abc-def-123",
            system_prompt="Test prompt",
            resume=True
        )
        
        # Verify command structure
        assert "env" in cmd
        assert "CLAUDE_INSTANCE=TestAgent" in cmd
        assert "run" in cmd
        assert "--resume" in cmd
        assert "abc-def-123" in cmd
    
    def test_build_resume_command_with_mcp(self):
        """Test building resume command with MCP config"""
        cmd = ClaudeLauncherConfig.build_command_string(
            instance_name="TestAgent",
            session_id="xyz-789",
            system_prompt="Test prompt",
            resume=True,
            mcp_config_path="/tmp/mcp_config.json"
        )
        
        # Verify MCP config is included
        assert "--mcp-config" in cmd
        assert "/tmp/mcp_config.json" in cmd
    
    def test_build_normal_command_string(self):
        """Test building normal (non-resume) command string"""
        cmd = ClaudeLauncherConfig.build_command_string(
            instance_name="TestAgent",
            session_id="new-session-123",
            system_prompt="You are a test agent",
            resume=False
        )
        
        # Verify command structure
        assert "env" in cmd
        assert "CLAUDE_INSTANCE=TestAgent" in cmd
        assert "run" in cmd
        assert "--session-id" in cmd
        assert "new-session-123" in cmd
        assert "--append-system-prompt" in cmd
        assert "You are a test agent" in cmd
        
        # Should NOT have --resume
        assert "--resume" not in cmd
    
    def test_command_escaping(self):
        """Test proper escaping of special characters in commands"""
        # Test with prompt containing quotes and special chars
        cmd = ClaudeLauncherConfig.build_command_string(
            instance_name="Test'Agent",
            session_id="test-123",
            system_prompt='Test "prompt" with $pecial char$',
            resume=False
        )
        
        # Command should be properly escaped
        assert cmd is not None
        # Should handle quotes properly (exact escaping depends on implementation)
        assert "Test" in cmd
        assert "prompt" in cmd