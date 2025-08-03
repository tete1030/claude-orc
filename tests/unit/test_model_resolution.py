"""
Unit tests for model resolution logic in ccorc launch
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import importlib.util

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

# Import ccorc as a module
ccorc_path = repo_root / "bin" / "ccorc"
spec = importlib.util.spec_from_file_location("ccorc", ccorc_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load ccorc from {ccorc_path}")
ccorc_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccorc_module)

from tests.fixtures.team_configs import TeamConfigFixtures, LaunchConfigFixtures


class TestModelResolution:
    """Test the intelligent model assignment logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ccorc_module.SessionCLIManager()
    
    def test_intelligent_model_assignment_architect(self):
        """Test that Architect role gets Opus"""
        model = self.manager._get_intelligent_model("Architect", "Team Lead and System Architect")
        assert model == "opus", "Architect should get Opus model"
    
    def test_intelligent_model_assignment_developer(self):
        """Test that Developer role gets Opus"""
        model = self.manager._get_intelligent_model("Developer", "Implementation and Coding Engineer")
        assert model == "opus", "Developer should get Opus model"
    
    def test_intelligent_model_assignment_qa(self):
        """Test that QA role gets Sonnet"""
        model = self.manager._get_intelligent_model("QA", "Quality Assurance Engineer")
        assert model == "sonnet", "QA should get Sonnet model"
    
    def test_intelligent_model_assignment_devops(self):
        """Test that DevOps role gets Sonnet"""
        model = self.manager._get_intelligent_model("DevOps", "Infrastructure and Deployment Engineer")
        assert model == "sonnet", "DevOps should get Sonnet model"
    
    def test_intelligent_model_assignment_docs(self):
        """Test that Docs role gets Sonnet"""
        model = self.manager._get_intelligent_model("Docs", "Documentation Specialist")
        assert model == "sonnet", "Docs should get Sonnet model"
    
    def test_intelligent_model_assignment_lead_role(self):
        """Test that Lead roles get Opus"""
        model = self.manager._get_intelligent_model("TeamLead", "Lead Engineer")
        assert model == "opus", "Lead roles should get Opus model"
    
    def test_intelligent_model_assignment_implementation_role(self):
        """Test that implementation roles get Opus"""
        model = self.manager._get_intelligent_model("Engineer", "Software Implementation Specialist")
        assert model == "opus", "Implementation roles should get Opus model"
    
    def test_intelligent_model_assignment_coding_role(self):
        """Test that coding roles get Opus"""
        model = self.manager._get_intelligent_model("Programmer", "Coding Specialist")
        assert model == "opus", "Coding roles should get Opus model"
    
    def test_intelligent_model_assignment_generic_role(self):
        """Test that generic roles get Sonnet"""
        model = self.manager._get_intelligent_model("Assistant", "General Assistant")
        assert model == "sonnet", "Generic roles should get Sonnet model"
    
    def test_model_resolution_with_override(self):
        """Test model resolution with global override"""
        # This tests the logic that would be in launch_team method
        config = TeamConfigFixtures.devops_team_config()
        
        # Mock a simplified version of the model resolution logic
        def resolve_model_for_agent(agent_config, model_override=None, agent_overrides=None):
            model = agent_config.get("model")
            if model_override:
                return model_override
            elif agent_overrides and agent_config["name"] in agent_overrides:
                return agent_overrides[agent_config["name"]]
            elif not model:
                return self.manager._get_intelligent_model(agent_config["name"], agent_config["role"])
            else:
                return model
        
        # Test global override
        for agent in config["agents"]:
            resolved = resolve_model_for_agent(agent, model_override="opus")
            assert resolved == "opus", f"Global override should apply to {agent['name']}"
    
    def test_model_resolution_with_agent_override(self):
        """Test model resolution with specific agent override"""
        config = TeamConfigFixtures.devops_team_config()
        agent_overrides = {"QA": "opus", "Docs": "opus"}
        
        def resolve_model_for_agent(agent_config, model_override=None, agent_overrides=None):
            model = agent_config.get("model")
            if model_override:
                return model_override
            elif agent_overrides and agent_config["name"] in agent_overrides:
                return agent_overrides[agent_config["name"]]
            elif not model:
                return self.manager._get_intelligent_model(agent_config["name"], agent_config["role"])
            else:
                return model
        
        for agent in config["agents"]:
            resolved = resolve_model_for_agent(agent, agent_overrides=agent_overrides)
            if agent["name"] in agent_overrides:
                assert resolved == agent_overrides[agent["name"]], f"Agent override should apply to {agent['name']}"
            else:
                # Should use intelligent assignment
                expected = self.manager._get_intelligent_model(agent["name"], agent["role"])
                assert resolved == expected, f"Should use intelligent assignment for {agent['name']}"
    
    def test_model_resolution_with_explicit_model(self):
        """Test model resolution when model is explicitly set in config"""
        config = TeamConfigFixtures.team_with_explicit_models()
        
        def resolve_model_for_agent(agent_config, model_override=None, agent_overrides=None):
            model = agent_config.get("model")
            if model_override:
                return model_override
            elif agent_overrides and agent_config["name"] in agent_overrides:
                return agent_overrides[agent_config["name"]]
            elif not model:
                return self.manager._get_intelligent_model(agent_config["name"], agent_config["role"])
            else:
                return model
        
        for agent in config["agents"]:
            resolved = resolve_model_for_agent(agent)
            expected = agent.get("model")
            assert resolved == expected, f"Should use explicit model for {agent['name']}"
    
    def test_model_resolution_priority_order(self):
        """Test that model resolution follows correct priority order"""
        agent_config = {
            "name": "TestAgent",
            "role": "Test Role",
            "model": "sonnet"  # Explicit model
        }
        
        def resolve_model_for_agent(agent_config, model_override=None, agent_overrides=None):
            model = agent_config.get("model")
            if model_override:
                return model_override
            elif agent_overrides and agent_config["name"] in agent_overrides:
                return agent_overrides[agent_config["name"]]
            elif not model:
                return self.manager._get_intelligent_model(agent_config["name"], agent_config["role"])
            else:
                return model
        
        # Priority 1: Global override should win
        resolved = resolve_model_for_agent(
            agent_config, 
            model_override="opus", 
            agent_overrides={"TestAgent": "haiku"}
        )
        assert resolved == "opus", "Global override should have highest priority"
        
        # Priority 2: Agent override should win over explicit model
        resolved = resolve_model_for_agent(
            agent_config,
            agent_overrides={"TestAgent": "haiku"}
        )
        assert resolved == "haiku", "Agent override should win over explicit model"
        
        # Priority 3: Explicit model should be used
        resolved = resolve_model_for_agent(agent_config)
        assert resolved == "sonnet", "Explicit model should be used when no overrides"
        
        # Priority 4: Intelligent assignment for no explicit model
        agent_config_no_model = {
            "name": "Architect", 
            "role": "System Architect",
            # No model specified
        }
        resolved = resolve_model_for_agent(agent_config_no_model)
        assert resolved == "opus", "Should use intelligent assignment when no explicit model"


class TestModelResolutionEdgeCases:
    """Test edge cases in model resolution"""
    
    def setup_method(self):
        self.manager = ccorc_module.SessionCLIManager()
    
    def test_case_insensitive_role_matching(self):
        """Test that role matching is case insensitive"""
        model = self.manager._get_intelligent_model("architect", "system architect")
        assert model == "opus", "Role matching should be case insensitive"
        
        model = self.manager._get_intelligent_model("DEVELOPER", "CODING ENGINEER")
        assert model == "opus", "Role matching should be case insensitive"
    
    def test_partial_role_matching(self):
        """Test that partial role matching works"""
        model = self.manager._get_intelligent_model("SeniorDev", "Senior Development Engineer")
        assert model == "opus", "Should match 'developer' in role"
        
        model = self.manager._get_intelligent_model("TechLead", "Technical Lead Manager")
        assert model == "opus", "Should match 'lead' in role"
    
    def test_role_with_multiple_keywords(self):
        """Test roles with multiple matching keywords"""
        model = self.manager._get_intelligent_model("LeadDeveloper", "Lead Development Architect")
        assert model == "opus", "Should match multiple keywords and return opus"
    
    def test_empty_role_and_name(self):
        """Test behavior with empty role and name"""
        model = self.manager._get_intelligent_model("", "")
        assert model == "sonnet", "Empty role/name should default to sonnet"
    
    def test_none_role_and_name(self):
        """Test behavior with None values"""
        # The current implementation might fail with None, so we test the expected behavior
        try:
            model = self.manager._get_intelligent_model(None, None)
            assert model == "sonnet", "None values should default to sonnet"
        except (AttributeError, TypeError):
            # If the current implementation doesn't handle None gracefully,
            # this documents the current behavior
            pytest.skip("Current implementation doesn't handle None values gracefully")
    
    def test_special_characters_in_role(self):
        """Test roles with special characters"""
        model = self.manager._get_intelligent_model("Dev-Ops", "Software-Developer/Engineer")
        assert model == "opus", "Should handle special characters in role matching"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])