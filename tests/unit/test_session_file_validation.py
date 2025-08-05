#!/usr/bin/env python3
"""
Unit tests for session file validation functionality.

Tests the _session_file_exists() method and related session
file path handling logic.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

from src.services.team_launch_service import TeamLaunchService


class TestSessionFileValidation:
    """Test session file validation logic"""
    
    @pytest.fixture
    def team_launch_service(self):
        """Create a TeamLaunchService instance with minimal dependencies"""
        # Create minimal mock dependencies
        mock_port_service = MagicMock()
        mock_orchestrator_factory = MagicMock()
        mock_mcp_server = MagicMock()
        mock_signal_handler = MagicMock()
        mock_context_persistence = MagicMock()
        
        service = TeamLaunchService(
            port_service=mock_port_service,
            orchestrator_factory=mock_orchestrator_factory,
            mcp_server_manager=mock_mcp_server,
            signal_handler=mock_signal_handler,
            context_persistence=mock_context_persistence
        )
        
        return service
    
    def test_session_file_exists_with_valid_file(self, team_launch_service, tmp_path):
        """Test _session_file_exists with an existing session file"""
        # Create a mock session file
        session_id = "test-session-123"
        working_dir = str(tmp_path / "project")
        os.makedirs(working_dir, exist_ok=True)
        
        # Create expected session file path
        escaped_cwd = working_dir.replace('/', '-')
        if escaped_cwd.startswith('-'):
            escaped_cwd = escaped_cwd[1:]  # Remove leading dash
        session_dir = tmp_path / ".claude" / "projects" / escaped_cwd
        session_dir.mkdir(parents=True)
        session_file = session_dir / f"{session_id}.jsonl"
        session_file.touch()
        
        # Mock Path.home() to return our tmp_path
        with patch('pathlib.Path.home', return_value=tmp_path):
            exists = team_launch_service._session_file_exists(session_id, working_dir)
        
        assert exists is True
    
    def test_session_file_exists_with_missing_file(self, team_launch_service, tmp_path):
        """Test _session_file_exists when session file doesn't exist"""
        session_id = "missing-session-456"
        working_dir = str(tmp_path / "project")
        
        # Mock Path.home() to return our tmp_path
        with patch('pathlib.Path.home', return_value=tmp_path):
            exists = team_launch_service._session_file_exists(session_id, working_dir)
        
        assert exists is False
    
    def test_session_file_exists_with_current_dir(self, team_launch_service, tmp_path):
        """Test _session_file_exists using current working directory"""
        session_id = "current-dir-session"
        
        # Create a mock current working directory
        mock_cwd = str(tmp_path / "current_project")
        os.makedirs(mock_cwd, exist_ok=True)
        
        # Create expected session file
        escaped_cwd = mock_cwd.replace('/', '-')
        if escaped_cwd.startswith('-'):
            escaped_cwd = escaped_cwd[1:]  # Remove leading dash
        session_dir = tmp_path / ".claude" / "projects" / escaped_cwd
        session_dir.mkdir(parents=True)
        session_file = session_dir / f"{session_id}.jsonl"
        session_file.touch()
        
        # Mock both Path.home() and os.getcwd()
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('os.getcwd', return_value=mock_cwd):
                # Call without working_dir parameter
                exists = team_launch_service._session_file_exists(session_id)
        
        assert exists is True
    
    def test_escaped_working_directory_handling(self, team_launch_service):
        """Test proper escaping of working directory paths"""
        # Test various path formats
        test_cases = [
            ("/home/user/project", "home-user-project"),  # Leading dash removed
            ("/var/lib/app", "var-lib-app"),  # Leading dash removed
            ("/", ""),  # Just dash becomes empty after removal
            ("/path/with spaces/dir", "path-with spaces-dir"),  # Leading dash removed
            ("/path/with/many/nested/dirs", "path-with-many-nested-dirs")  # Leading dash removed
        ]
        
        for working_dir, expected_escaped in test_cases:
            # Manually test the escaping logic
            escaped = working_dir.replace('/', '-')
            if escaped.startswith('-'):
                escaped = escaped[1:]  # Remove leading dash
            assert escaped == expected_escaped
    
    def test_session_file_path_construction(self, team_launch_service, tmp_path):
        """Test the full session file path construction"""
        session_id = "path-test-789"
        working_dir = "/home/user/my-project"
        
        expected_escaped = "home-user-my-project"  # Leading dash removed
        expected_path = tmp_path / ".claude" / "projects" / expected_escaped / f"{session_id}.jsonl"
        
        # Mock Path.home()
        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create the expected file to test path construction
            expected_dir = tmp_path / ".claude" / "projects" / expected_escaped
            expected_dir.mkdir(parents=True)
            expected_file = expected_dir / f"{session_id}.jsonl"
            expected_file.touch()
            
            # Verify it finds the file at the expected path
            exists = team_launch_service._session_file_exists(session_id, working_dir)
            assert exists is True
            
            # Also test with non-existent file to ensure path is correct
            os.remove(expected_file)
            exists = team_launch_service._session_file_exists(session_id, working_dir)
            assert exists is False
    
    def test_session_file_exists_with_special_chars(self, team_launch_service, tmp_path):
        """Test session file validation with special characters in paths"""
        session_id = "special-chars-abc"
        working_dir = str(tmp_path / "project-with-dashes_and_underscores")
        os.makedirs(working_dir, exist_ok=True)
        
        # Create expected session file
        escaped_cwd = working_dir.replace('/', '-')
        if escaped_cwd.startswith('-'):
            escaped_cwd = escaped_cwd[1:]  # Remove leading dash
        session_dir = tmp_path / ".claude" / "projects" / escaped_cwd
        session_dir.mkdir(parents=True)
        session_file = session_dir / f"{session_id}.jsonl"
        session_file.touch()
        
        with patch('pathlib.Path.home', return_value=tmp_path):
            exists = team_launch_service._session_file_exists(session_id, working_dir)
        
        assert exists is True
    
    def test_session_file_exists_none_session_id(self, team_launch_service):
        """Test _session_file_exists with None session_id"""
        # Should handle None gracefully
        exists = team_launch_service._session_file_exists(None, "/some/path")
        assert exists is False
    
    def test_session_file_exists_empty_session_id(self, team_launch_service):
        """Test _session_file_exists with empty session_id"""
        # Should handle empty string gracefully
        exists = team_launch_service._session_file_exists("", "/some/path")
        assert exists is False