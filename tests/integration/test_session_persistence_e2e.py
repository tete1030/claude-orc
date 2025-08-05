#!/usr/bin/env python3
"""
Integration tests for session persistence end-to-end functionality.

Tests the complete flow of launching teams, capturing session IDs,
stopping teams, and resuming with the same sessions.
"""

import pytest
import json
import os
import time
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock
import uuid

from src.team_context_manager import TeamContextManager, TeamContext, TeamContextAgentInfo
from src.services.team_launch_service import TeamLaunchService
from src.team_config_loader import TeamConfig, AgentConfig
from src.simple_launcher import SimpleLauncher
from src.tmux_manager import TmuxManager


class TestSessionPersistenceE2E:
    """End-to-end tests for session persistence"""
    
    @pytest.fixture
    def temp_registry_path(self, tmp_path):
        """Create a temporary registry path"""
        registry_file = tmp_path / "test_contexts.json"
        return str(registry_file)
    
    @pytest.fixture
    def context_manager(self, temp_registry_path):
        """Create a context manager with temporary registry"""
        return TeamContextManager(registry_path=temp_registry_path)
    
    @pytest.fixture
    def test_team_config(self):
        """Create a test team configuration"""
        return TeamConfig(
            name="e2e-test-team",
            description="End-to-end test team",
            agents=[
                AgentConfig(name="Leader", role="Team Leader", model="sonnet"),
                AgentConfig(name="Worker", role="Worker", model="sonnet")
            ],
            settings={
                "orchestrator_type": "base",
                "poll_interval": 0.5
            }
        )
    
    def test_session_persistence_full_workflow(self, context_manager, test_team_config, tmp_path):
        """Test complete session persistence workflow"""
        context_name = "e2e-test"
        
        # Step 1: Create initial context with no session IDs
        initial_agents = [
            TeamContextAgentInfo(name="Leader", role="Team Leader"),
            TeamContextAgentInfo(name="Worker", role="Worker")
        ]
        
        context = context_manager.create_context(
            context_name=context_name,
            agents=initial_agents,
            tmux_session="e2e-test-session"
        )
        
        # Verify initial state - no session IDs
        assert context.agents[0].session_id is None
        assert context.agents[1].session_id is None
        
        # Step 2: Simulate team launch with session ID assignment
        session_ids = {
            "Leader": str(uuid.uuid4()),
            "Worker": str(uuid.uuid4())
        }
        
        # Update agents with session IDs (simulating what TeamLaunchService does)
        updated_agents = []
        for agent in context.agents:
            agent.session_id = session_ids[agent.name]
            updated_agents.append(agent)
        
        # Update context with session IDs
        context_manager.update_context(
            context_name,
            agents=updated_agents
        )
        
        # Step 3: Reload context and verify session IDs are persisted
        reloaded_context = context_manager.get_context(context_name)
        assert reloaded_context is not None
        assert reloaded_context.agents[0].session_id == session_ids["Leader"]
        assert reloaded_context.agents[1].session_id == session_ids["Worker"]
        
        # Step 4: Simulate session file creation
        for agent_name, session_id in session_ids.items():
            # Create mock session files
            escaped_cwd = os.getcwd().replace('/', '-')
            if escaped_cwd.startswith('-'):
                escaped_cwd = escaped_cwd[1:]  # Remove leading dash
            session_dir = tmp_path / ".claude" / "projects" / escaped_cwd
            session_dir.mkdir(parents=True, exist_ok=True)
            session_file = session_dir / f"{session_id}.jsonl"
            session_file.write_text('{"mock": "session data"}')
        
        # Step 5: Test resume decision logic
        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create a minimal TeamLaunchService to test session validation
            mock_deps = {
                'port_service': Mock(),
                'orchestrator_factory': Mock(),
                'mcp_server_manager': Mock(),
                'signal_handler': Mock(),
                'context_persistence': context_manager,
                'cleanup_callback': Mock()
            }
            
            launch_service = TeamLaunchService(**mock_deps)
            
            # Session file validation removed - no longer performed
            # Skip session file existence checks
        
        # Step 6: Test fresh flag behavior
        # Even with existing sessions, fresh flag should force new ones
        fresh_session_ids = {
            "Leader": str(uuid.uuid4()),
            "Worker": str(uuid.uuid4())
        }
        
        # Update with fresh session IDs
        fresh_agents = []
        for agent in reloaded_context.agents:
            agent.session_id = fresh_session_ids[agent.name]
            fresh_agents.append(agent)
        
        context_manager.update_context(
            context_name,
            agents=fresh_agents
        )
        
        # Verify fresh session IDs are different
        fresh_context = context_manager.get_context(context_name)
        assert fresh_context.agents[0].session_id != session_ids["Leader"]
        assert fresh_context.agents[1].session_id != session_ids["Worker"]
    
    def test_registry_persistence_across_restarts(self, temp_registry_path):
        """Test that context registry persists across manager restarts"""
        context_name = "persistence-test"
        session_id = str(uuid.uuid4())
        
        # Create context with first manager instance
        manager1 = TeamContextManager(registry_path=temp_registry_path)
        agents = [
            TeamContextAgentInfo(
                name="TestAgent",
                role="Tester",
                session_id=session_id
            )
        ]
        
        manager1.create_context(
            context_name=context_name,
            agents=agents,
            tmux_session="test-session"
        )
        
        # Create new manager instance (simulating restart)
        manager2 = TeamContextManager(registry_path=temp_registry_path)
        
        # Verify context is loaded from disk
        loaded_context = manager2.get_context(context_name)
        assert loaded_context is not None
        assert loaded_context.context_name == context_name
        assert len(loaded_context.agents) == 1
        assert loaded_context.agents[0].session_id == session_id
    
    def test_partial_session_recovery(self, context_manager, tmp_path):
        """Test recovering when only some agents have valid sessions"""
        context_name = "partial-recovery"
        
        # Create context with two agents having sessions
        agents = [
            TeamContextAgentInfo(
                name="Agent1",
                role="Role1",
                session_id=str(uuid.uuid4())
            ),
            TeamContextAgentInfo(
                name="Agent2",
                role="Role2",
                session_id=str(uuid.uuid4())
            )
        ]
        
        context = context_manager.create_context(
            context_name=context_name,
            agents=agents,
            tmux_session="partial-test"
        )
        
        # Create session file for only the first agent
        escaped_cwd = os.getcwd().replace('/', '-')
        if escaped_cwd.startswith('-'):
            escaped_cwd = escaped_cwd[1:]  # Remove leading dash
        session_dir = tmp_path / ".claude" / "projects" / escaped_cwd
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Only create session file for Agent1
        session_file1 = session_dir / f"{agents[0].session_id}.jsonl"
        session_file1.write_text('{"mock": "session data"}')
        
        # Agent2's session file is missing (simulating deletion or corruption)
        
        # Test session validation
        with patch('pathlib.Path.home', return_value=tmp_path):
            mock_deps = {
                'port_service': Mock(),
                'orchestrator_factory': Mock(),
                'mcp_server_manager': Mock(),
                'signal_handler': Mock(),
                'context_persistence': context_manager,
                'cleanup_callback': Mock()
            }
            
            launch_service = TeamLaunchService(**mock_deps)
            
            # Session file validation removed - no longer performed
            # Skip session file existence checks
    
    @patch('src.simple_launcher.ClaudeLauncherConfig.verify_script_exists')
    def test_launcher_integration_with_resume(self, mock_verify):
        """Test SimpleLauncher integration with resume functionality"""
        # Mock script verification
        mock_verify.return_value = True
        
        # Create a mock tmux manager
        tmux_manager = Mock()
        tmux_manager.session_name = "test-session"
        # Mock capture_pane to return a string, not Mock
        tmux_manager.capture_pane.return_value = "Welcome to Claude Code!"
        # Mock _run_command to simulate command execution
        tmux_manager._run_command = Mock()
        
        launcher = SimpleLauncher(tmux_manager)
        
        # Test normal launch
        new_session = launcher.launch_agent(
            pane_index=0,
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )
        
        assert new_session is not None
        assert isinstance(new_session, str)
        assert tmux_manager._run_command.called
        
        # Reset mock
        tmux_manager._run_command.reset_mock()
        
        # Test resume launch
        resumed_session = launcher.launch_agent(
            pane_index=0,
            agent_name="TestAgent",
            system_prompt="Test prompt",
            session_id="existing-session-456"
        )
        
        assert resumed_session == "existing-session-456"
        assert tmux_manager._run_command.called
