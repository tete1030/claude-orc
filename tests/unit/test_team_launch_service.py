"""
Unit tests for Team Launch Service

Tests the team launching functionality including model resolution.
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
    
    def test_intelligent_model_assignment_architect(self):
        """Test that Architect role gets Opus"""
        model = self.service._get_intelligent_model("Architect", "Team Lead and System Architect")
        assert model == "opus", "Architect should get Opus model"
    
    def test_intelligent_model_assignment_developer(self):
        """Test that Developer role gets Opus"""
        model = self.service._get_intelligent_model("Developer", "Implementation and Coding Engineer")
        assert model == "opus", "Developer should get Opus model"
    
    def test_intelligent_model_assignment_qa(self):
        """Test that QA role gets Sonnet"""
        model = self.service._get_intelligent_model("QA", "Quality Assurance Engineer")
        assert model == "sonnet", "QA should get Sonnet model"
    
    def test_intelligent_model_assignment_devops(self):
        """Test that DevOps role gets Sonnet"""
        model = self.service._get_intelligent_model("DevOps", "Infrastructure and Deployment Engineer")
        assert model == "sonnet", "DevOps should get Sonnet model"
    
    def test_intelligent_model_assignment_docs(self):
        """Test that Docs role gets Sonnet"""
        model = self.service._get_intelligent_model("Docs", "Documentation Engineer")
        assert model == "sonnet", "Docs should get Sonnet model"
    
    def test_intelligent_model_assignment_lead_role(self):
        """Test that roles with 'lead' keyword get Opus"""
        model = self.service._get_intelligent_model("TeamLead", "Project Lead")
        assert model == "opus", "Lead roles should get Opus model"
        
        model = self.service._get_intelligent_model("TechLead", "Technical Leadership")
        assert model == "opus", "Lead roles should get Opus model"
    
    def test_intelligent_model_assignment_implementation_role(self):
        """Test that roles with 'implementation' keyword get Opus"""
        model = self.service._get_intelligent_model("Backend", "Implementation Engineer")
        assert model == "opus", "Implementation roles should get Opus model"
    
    def test_intelligent_model_assignment_coding_role(self):
        """Test that roles with 'coding' keyword get Opus"""
        model = self.service._get_intelligent_model("Engineer", "Coding Specialist")
        assert model == "opus", "Coding roles should get Opus model"
    
    def test_intelligent_model_assignment_generic_role(self):
        """Test that generic roles get Sonnet"""
        model = self.service._get_intelligent_model("Analyst", "Data Analyst")
        assert model == "sonnet", "Generic roles should get Sonnet model"
        
        model = self.service._get_intelligent_model("Support", "Support Engineer") 
        assert model == "sonnet", "Generic roles should get Sonnet model"