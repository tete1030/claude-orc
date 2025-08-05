"""
Unit tests for Team Launch Service

Tests the team launching functionality.
Note: Intelligent model assignment tests removed since _get_intelligent_model() method no longer exists.
Model assignment is now handled by configuration, not automatic assignment.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

from src.services.team_launch_service import TeamLaunchService
from src.team_context_manager import TeamContextAgentInfo


class TestTeamLaunchService:
    """Test the team launch service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_port_service = Mock()
        self.mock_orchestrator_factory = Mock()
        self.mock_mcp_server_manager = Mock()
        self.mock_signal_handler = Mock()
        self.mock_context_persistence = Mock()
        self.mock_cleanup_callback = Mock()
        
        self.service = TeamLaunchService(
            port_service=self.mock_port_service,
            orchestrator_factory=self.mock_orchestrator_factory,
            mcp_server_manager=self.mock_mcp_server_manager,
            signal_handler=self.mock_signal_handler,
            context_persistence=self.mock_context_persistence,
            cleanup_callback=self.mock_cleanup_callback
        )
    
    # Intelligent model assignment tests removed - _get_intelligent_model() method no longer exists
    # Model assignment is now handled by configuration, not automatic assignment
    
    def test_service_initialization(self):
        """Test that the service initializes properly with dependencies"""
        assert self.service is not None
        assert hasattr(self.service, 'port_service')
        assert hasattr(self.service, 'orchestrator_factory')
        assert hasattr(self.service, 'mcp_server_manager')
        assert hasattr(self.service, 'signal_handler')
        assert hasattr(self.service, 'context_persistence')