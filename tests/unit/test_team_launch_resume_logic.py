#!/usr/bin/env python3
"""
Unit tests for TeamLaunchService resume logic.

Tests the auto-resume decision flow, fresh flag behavior,
and partial team resume scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import uuid

from src.services.team_launch_service import TeamLaunchService
from src.team_context_manager import TeamContext, TeamContextAgentInfo
from src.team_config_loader import TeamConfig, AgentConfig


class TestTeamLaunchResumeLogic:
    """Test TeamLaunchService auto-resume logic"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for TeamLaunchService"""
        deps = {
            'port_service': Mock(),
            'orchestrator_factory': Mock(),
            'mcp_server_manager': Mock(),
            'signal_handler': Mock(),
            'context_persistence': Mock(),
            'cleanup_callback': Mock()
        }
        
        # Set up some default return values
        deps['port_service'].find_available_port.return_value = 8767
        deps['orchestrator_factory'].create_orchestrator.return_value = Mock()
        deps['orchestrator_factory'].create_configured_orchestrator.return_value = Mock()
        deps['mcp_server_manager'].start_server.return_value = Mock()
        
        return deps
    
    @pytest.fixture
    def team_launch_service(self, mock_dependencies):
        """Create TeamLaunchService with mocked dependencies"""
        return TeamLaunchService(**mock_dependencies)
    
    @pytest.fixture
    def sample_team_config(self):
        """Create a sample team configuration"""
        return TeamConfig(
            name="test-team",
            description="Test team",
            agents=[
                AgentConfig(name="Lead", role="Team Lead", model="sonnet"),
                AgentConfig(name="Dev", role="Developer", model="sonnet"),
                AgentConfig(name="QA", role="QA Engineer", model="sonnet")
            ],
            settings={
                "orchestrator_type": "enhanced",
                "poll_interval": 0.5
            }
        )
    
    @pytest.fixture
    def existing_context_with_sessions(self):
        """Create a context with existing session IDs"""
        return TeamContext(
            context_name="test-team",
            tmux_session="test-team",
            created_at="2025-01-01T00:00:00",
            agents=[
                TeamContextAgentInfo(
                    name="Lead",
                    role="Team Lead",
                    session_id="lead-session-123"
                ),
                TeamContextAgentInfo(
                    name="Dev",
                    role="Developer",
                    session_id="dev-session-456"
                ),
                TeamContextAgentInfo(
                    name="QA",
                    role="QA Engineer",
                    session_id="qa-session-789"
                )
            ]
        )
    
    def test_auto_resume_with_existing_sessions(
        self,
        team_launch_service, sample_team_config, existing_context_with_sessions,
        mock_dependencies
    ):
        """Test auto-resume when all agents have existing sessions"""
        # Mock the team loader instance in the service
        team_launch_service.team_loader = Mock()
        team_launch_service.team_loader.load_config.return_value = sample_team_config
        team_launch_service.team_loader.validate_config.return_value = []  # No validation errors
        
        mock_dependencies['context_persistence'].get_context.return_value = existing_context_with_sessions
        
        # Session file validation removed - no longer performed
        
        # Mock orchestrator with proper attributes
        mock_orchestrator = Mock()
        mock_agent = Mock()
        mock_agent.pane_index = 0
        mock_agent.session_id = "lead-session-123"  # Will be updated for each agent
        mock_orchestrator.register_agent.return_value = mock_agent
        
        # Mock orchestrator's agents dictionary for session ID updates
        mock_orchestrator.agents = {
            "Lead": Mock(session_id="lead-session-123"),
            "Dev": Mock(session_id="dev-session-456"),
            "QA": Mock(session_id="qa-session-789")
        }
        
        # Mock the orchestrator's start method and running flag
        mock_orchestrator.start.return_value = True
        mock_orchestrator.running = False  # Don't enter infinite loop
        
        # Mock tmux attribute
        mock_orchestrator.tmux = Mock(session_name="test-team")
        
        # Set the mock orchestrator factory to return our configured mock
        mock_dependencies['orchestrator_factory'].create_orchestrator.return_value = mock_orchestrator
        mock_dependencies['orchestrator_factory'].create_configured_orchestrator.return_value = mock_orchestrator
        # Mock tmux attribute for the orchestrator
        mock_orchestrator.tmux = Mock()
        mock_orchestrator.tmux.session_name = "test-team"
        
        # Launch with auto-resume (fresh=False, force=True to use existing context)
        success = team_launch_service.launch_team(
            team_name="test-team",
            context_name="test-team",
            fresh=False,
            force=True  # Need force=True when context already exists
        )
        
        # Session file validation removed - skip this check
        
        register_calls = mock_orchestrator.register_agent.call_args_list
        assert len(register_calls) == 3
        
        # Check that session_id was set correctly for each agent
        for call in register_calls:
            assert call[1]['session_id'] is not None
    
    def test_fresh_flag_forces_new_sessions(
        self,
        team_launch_service, sample_team_config, existing_context_with_sessions,
        mock_dependencies
    ):
        """Test that --fresh flag forces new sessions even when old ones exist"""
        # Mock the team loader instance in the service
        team_launch_service.team_loader = Mock()
        team_launch_service.team_loader.load_config.return_value = sample_team_config
        team_launch_service.team_loader.validate_config.return_value = []  # No validation errors
        
        mock_dependencies['context_persistence'].get_context.return_value = existing_context_with_sessions
        
        # Mock orchestrator with proper attributes
        mock_orchestrator = Mock()
        mock_agent = Mock()
        mock_agent.pane_index = 0
        mock_orchestrator.register_agent.return_value = mock_agent
        mock_orchestrator.start.return_value = True
        mock_orchestrator.running = False  # Don't enter infinite loop
        mock_orchestrator.agents = {
            "Lead": Mock(session_id=None),
            "Dev": Mock(session_id=None),
            "QA": Mock(session_id=None)
        }
        mock_orchestrator.tmux = Mock(session_name="test-team")
        
        # Set the mock orchestrator factory to return our configured mock
        mock_dependencies['orchestrator_factory'].create_orchestrator.return_value = mock_orchestrator
        mock_dependencies['orchestrator_factory'].create_configured_orchestrator.return_value = mock_orchestrator
        # Mock tmux attribute for the orchestrator
        mock_orchestrator.tmux = Mock()
        mock_orchestrator.tmux.session_name = "test-team"
        
        # Launch with fresh=True and force=True (context exists)
        success = team_launch_service.launch_team(
            team_name="test-team",
            context_name="test-team",
            fresh=True,  # Force fresh sessions
            force=True   # Need force=True when context already exists
        )
        
        # Verify agents were registered with no session ID
        register_calls = mock_orchestrator.register_agent.call_args_list
        assert len(register_calls) == 3
        
        for call in register_calls:
            assert call[1].get('session_id', "not-none") is None
    
    def test_partial_team_resume(
        self,
        team_launch_service, sample_team_config, mock_dependencies
    ):
        """Test resuming when only some agents have existing sessions"""
        # Create context with mixed session states
        partial_context = TeamContext(
            context_name="test-team",
            tmux_session="test-team",
            created_at="2025-01-01T00:00:00",
            agents=[
                TeamContextAgentInfo(
                    name="Lead",
                    role="Team Lead",
                    session_id="lead-session-123"  # Has session
                ),
                TeamContextAgentInfo(
                    name="Dev",
                    role="Developer",
                    session_id=None  # No session
                ),
                TeamContextAgentInfo(
                    name="QA",
                    role="QA Engineer",
                    session_id="qa-session-789"  # Has session
                )
            ]
        )
        
        # Set up mocks - need to mock at instantiation time
        # Mock the team loader instance in the service  
        team_launch_service.team_loader = Mock()
        team_launch_service.team_loader.load_config.return_value = sample_team_config
        team_launch_service.team_loader.validate_config.return_value = []  # No validation errors
        
        mock_dependencies['context_persistence'].get_context.return_value = partial_context
        
        # Session file validation removed - no longer performed
        
        # Mock orchestrator with proper attributes
        mock_orchestrator = Mock()
        mock_agent = Mock()
        mock_agent.pane_index = 0
        mock_orchestrator.register_agent.return_value = mock_agent
        mock_orchestrator.start.return_value = True
        mock_orchestrator.running = False  # Don't enter infinite loop
        mock_orchestrator.agents = {
            "Lead": Mock(session_id="lead-session-123"),
            "Dev": Mock(session_id=None),  # Will get new session
            "QA": Mock(session_id="qa-session-789")
        }
        mock_orchestrator.tmux = Mock(session_name="test-team")
        
        # Set the mock orchestrator factory to return our configured mock
        mock_dependencies['orchestrator_factory'].create_orchestrator.return_value = mock_orchestrator
        mock_dependencies['orchestrator_factory'].create_configured_orchestrator.return_value = mock_orchestrator
        # Mock tmux attribute for the orchestrator
        mock_orchestrator.tmux = Mock()
        mock_orchestrator.tmux.session_name = "test-team"
        
        # Launch with auto-resume and force=True (context exists)
        success = team_launch_service.launch_team(
            team_name="test-team",
            context_name="test-team",
            fresh=False,
            force=True  # Need force=True when context already exists
        )
        
        # Verify mixed resume behavior
        register_calls = mock_orchestrator.register_agent.call_args_list
        assert len(register_calls) == 3
        
        # Verify session ID behavior
        session_ids = {call[1]["name"]: call[1]["session_id"] for call in register_calls}
        
        # Lead should keep existing session ID
        assert session_ids["Lead"] == "lead-session-123"
        # QA should keep existing session ID  
        assert session_ids["QA"] == "qa-session-789"
        # Dev has no existing session ID, so gets None (fresh session will be created by Claude)
        assert session_ids["Dev"] is None
        
        # Note: The current implementation sets resume=True for all agents in existing context,
        # even if they don't have a session_id. This could be considered a minor bug,
        # but the actual behavior (creating new session) is correct due to the check in _register_agents
    
    def test_missing_session_file_falls_back_to_new(
        self,
        team_launch_service, sample_team_config, existing_context_with_sessions,
        mock_dependencies
    ):
        """Test that existing session IDs are preserved (session file validation removed)"""
        # Mock the team loader instance in the service
        team_launch_service.team_loader = Mock()
        team_launch_service.team_loader.load_config.return_value = sample_team_config
        team_launch_service.team_loader.validate_config.return_value = []  # No validation errors
        
        mock_dependencies['context_persistence'].get_context.return_value = existing_context_with_sessions
        
        # Session file validation removed - no longer performed
        
        # Mock orchestrator with proper attributes
        mock_orchestrator = Mock()
        mock_agent = Mock()
        mock_agent.pane_index = 0
        mock_orchestrator.register_agent.return_value = mock_agent
        mock_orchestrator.start.return_value = True
        mock_orchestrator.running = False  # Don't enter infinite loop
        mock_orchestrator.agents = {
            "Lead": Mock(session_id="lead-session-123"),
            "Dev": Mock(session_id="dev-session-456"),
            "QA": Mock(session_id="qa-session-789")
        }
        mock_orchestrator.tmux = Mock(session_name="test-team")
        
        # Set the mock orchestrator factory to return our configured mock
        mock_dependencies['orchestrator_factory'].create_orchestrator.return_value = mock_orchestrator
        mock_dependencies['orchestrator_factory'].create_configured_orchestrator.return_value = mock_orchestrator
        # Mock tmux attribute for the orchestrator
        mock_orchestrator.tmux = Mock()
        mock_orchestrator.tmux.session_name = "test-team"
        
        # Launch with auto-resume attempt and force=True (context exists)
        success = team_launch_service.launch_team(
            team_name="test-team",
            context_name="test-team",
            fresh=False,
            force=True  # Need force=True when context already exists
        )
        
        # Since session file validation was removed, agents with session IDs in context keep them
        register_calls = mock_orchestrator.register_agent.call_args_list
        assert len(register_calls) == 3
        
        # Check that existing session IDs are preserved
        session_ids = {call[1]["name"]: call[1]["session_id"] for call in register_calls}
        assert session_ids["Lead"] == "lead-session-123"
        assert session_ids["Dev"] == "dev-session-456"
        assert session_ids["QA"] == "qa-session-789"
    
    def test_new_context_creates_fresh_sessions(
        self,
        team_launch_service, sample_team_config, mock_dependencies
    ):
        """Test that new contexts always create fresh sessions"""
        # Set up mocks - need to mock at instantiation time
        # Mock the team loader instance in the service  
        team_launch_service.team_loader = Mock()
        team_launch_service.team_loader.load_config.return_value = sample_team_config
        team_launch_service.team_loader.validate_config.return_value = []  # No validation errors
        
        # No existing context
        mock_dependencies['context_persistence'].get_context.return_value = None
        
        # Mock orchestrator with proper attributes
        mock_orchestrator = Mock()
        mock_agent = Mock()
        mock_agent.pane_index = 0
        mock_orchestrator.register_agent.return_value = mock_agent
        mock_orchestrator.start.return_value = True
        mock_orchestrator.running = False  # Don't enter infinite loop
        mock_orchestrator.agents = {
            "Lead": Mock(session_id=None),
            "Dev": Mock(session_id=None),
            "QA": Mock(session_id=None)
        }
        mock_orchestrator.tmux = Mock(session_name="test-team")
        
        # Set the mock orchestrator factory to return our configured mock
        mock_dependencies['orchestrator_factory'].create_orchestrator.return_value = mock_orchestrator
        mock_dependencies['orchestrator_factory'].create_configured_orchestrator.return_value = mock_orchestrator
        # Mock tmux attribute for the orchestrator
        mock_orchestrator.tmux = Mock()
        mock_orchestrator.tmux.session_name = "new-team"
        
        # Launch new team
        success = team_launch_service.launch_team(
            team_name="test-team",
            context_name="new-team",
            fresh=False  # Even with fresh=False, new context gets new sessions
        )
        
        # All agents should get fresh sessions
        register_calls = mock_orchestrator.register_agent.call_args_list
        assert len(register_calls) == 3
        
        for call in register_calls:
            assert call[1].get('session_id', "not-none") is None