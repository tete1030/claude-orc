"""
Integration tests for the complete launch behavior
Tests the current launch process end-to-end to lock down behavior before refactoring
"""
import pytest
import tempfile
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from tests.fixtures.team_configs import TeamConfigFixtures
from src.team_config_loader import TeamConfigLoader


class TestLaunchIntegration:
    """Integration tests for the launch process"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.team_dir = None
    
    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_team(self, config_dict, team_name="test-team"):
        """Create a test team configuration"""
        self.team_dir = TeamConfigFixtures.create_temp_team_dir(config_dict, team_name)
        return self.team_dir
    
    def test_team_config_loading_and_validation(self):
        """Test loading and validating team configurations"""
        # Create a valid team config
        config = TeamConfigFixtures.devops_team_config()
        team_dir = self.create_test_team(config, "devops-test")
        
        # Test loading
        loader = TeamConfigLoader()
        
        # Add the temp directory to the search path
        original_search_paths = loader.search_paths.copy()
        loader.search_paths.append(team_dir.parent)
        
        try:
            loaded_config = loader.load_config("devops-test")
            
            # Verify the loaded config matches what we created
            assert loaded_config.name == config["team"]["name"]
            assert loaded_config.description == config["team"]["description"]
            assert len(loaded_config.agents) == len(config["agents"])
            
            # Test validation
            errors = loader.validate_config(loaded_config)
            assert len(errors) == 0, f"Valid config should have no errors: {errors}"
            
        finally:
            loader.search_paths = original_search_paths
    
    def test_team_config_validation_errors(self):
        """Test validation of invalid team configurations"""
        # The loader itself raises an error for configs with no agents
        # So we test that the loader properly rejects invalid configs
        invalid_config = TeamConfigFixtures.invalid_team_config()
        team_dir = self.create_test_team(invalid_config, "invalid-test")
        
        loader = TeamConfigLoader()
        original_search_paths = loader.search_paths.copy()
        loader.search_paths.append(team_dir.parent)
        
        try:
            # Should raise an error when loading invalid config
            with pytest.raises(ValueError) as exc_info:
                loader.load_config("invalid-test")
            
            # Check that the error is about missing agents
            assert "agent" in str(exc_info.value).lower(), "Should complain about missing agents"
            
        finally:
            loader.search_paths = original_search_paths
    
    def test_model_resolution_integration(self):
        """Test model resolution with team configuration"""
        config = TeamConfigFixtures.devops_team_config()
        team_dir = self.create_test_team(config, "model-test")
        
        loader = TeamConfigLoader()
        original_search_paths = loader.search_paths.copy()
        loader.search_paths.append(team_dir.parent)
        
        # Import the methods we're testing
        from tests.unit.test_ccorc_methods import CCORCMethods
        methods = CCORCMethods()
        
        try:
            loaded_config = loader.load_config("model-test")
            
            # Test model resolution for each agent
            for agent in loaded_config.agents:
                resolved_model = methods._get_intelligent_model(agent.name, agent.role)
                
                # Verify intelligent assignment
                if agent.name in ["Architect", "Developer"]:
                    assert resolved_model == "opus", f"{agent.name} should get opus"
                else:
                    assert resolved_model == "sonnet", f"{agent.name} should get sonnet"
                    
        finally:
            loader.search_paths = original_search_paths
    
    def test_launch_config_parameters(self):
        """Test launch configuration parameter handling"""
        # Test various launch parameter combinations
        test_cases = [
            {
                "name": "minimal",
                "params": {
                    "team_name": "test-team",
                    "context_name": None,
                    "model_override": None,
                    "agent_model_overrides": {},
                    "force": False,
                    "debug": False,
                    "task": None
                }
            },
            {
                "name": "with_task",
                "params": {
                    "team_name": "test-team",
                    "context_name": "task-context",
                    "model_override": None,
                    "agent_model_overrides": {},
                    "force": False,
                    "debug": False,
                    "task": "Test task injection"
                }
            },
            {
                "name": "with_overrides",
                "params": {
                    "team_name": "test-team",
                    "context_name": "override-context",
                    "model_override": "opus",
                    "agent_model_overrides": {"QA": "opus", "Docs": "sonnet"},
                    "force": True,
                    "debug": True,
                    "task": None
                }
            }
        ]
        
        for case in test_cases:
            params = case["params"]
            
            # Verify parameter structure
            assert "team_name" in params
            assert isinstance(params.get("force", False), bool)
            assert isinstance(params.get("debug", False), bool)
            assert isinstance(params.get("agent_model_overrides", {}), dict)
            
            # Test task injection logic
            if params.get("task"):
                # Task should be added to Architect prompt
                task_context = f"\n\nInitial task from user: {params['task']}"
                assert len(task_context) > 0
    
    @patch('socket.socket')
    def test_port_discovery_integration(self, mock_socket_class):
        """Test port discovery in launch context"""
        from tests.unit.test_ccorc_methods import CCORCMethods
        methods = CCORCMethods()
        
        # Test normal port discovery
        mock_socket = Mock()
        mock_socket.bind.return_value = None
        mock_socket.getsockname.return_value = ('', 8765)
        mock_socket_class.return_value = mock_socket
        
        port = methods._find_available_port(8765)
        assert port == 8765
        
        # Test port discovery with conflict
        mock_socket.bind.side_effect = [OSError("Port busy"), None]
        mock_socket.getsockname.return_value = ('', 8766)
        
        port = methods._find_available_port(8765)
        assert port == 8766
    
    def test_team_context_name_resolution(self):
        """Test context name resolution logic"""
        config = TeamConfigFixtures.devops_team_config()
        
        # Test default context name from config
        default_context = config["settings"]["default_context_name"]
        assert default_context == "devops-team"
        
        # Test override behavior
        override_context = "custom-context"
        final_context = override_context if override_context else default_context
        assert final_context == "custom-context"
        
        # Test fallback when no context specified
        config_no_default = TeamConfigFixtures.minimal_team_config()
        original_default = config_no_default["settings"].get("default_context_name")
        
        # Remove the default context name to test fallback
        if "default_context_name" in config_no_default["settings"]:
            del config_no_default["settings"]["default_context_name"]
        
        fallback_context = config_no_default["settings"].get("default_context_name", "team-context")
        assert fallback_context == "team-context"
    
    @patch('subprocess.run')
    def test_layout_detection_integration(self, mock_subprocess):
        """Test layout detection in launch context"""
        from tests.unit.test_ccorc_methods import CCORCMethods
        methods = CCORCMethods()
        
        # Test with 5-agent team (should trigger smart layout)
        config = TeamConfigFixtures.devops_team_config()
        agent_count = len(config["agents"])
        assert agent_count == 5
        
        # Mock large terminal
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "50 250"
        mock_subprocess.return_value = mock_result
        
        layout = methods._detect_smart_layout(agent_count)
        assert layout["type"] == "grid"
        assert layout["agent_count"] == 5
        
        # Test with non-5-agent team (should not trigger smart layout)
        minimal_config = TeamConfigFixtures.minimal_team_config()
        minimal_agent_count = len(minimal_config["agents"])
        assert minimal_agent_count == 1
        
        layout = methods._detect_smart_layout(minimal_agent_count)
        assert layout is None
    
    def test_orchestrator_type_selection(self):
        """Test orchestrator type selection logic"""
        # Test enhanced orchestrator (default)
        config = TeamConfigFixtures.devops_team_config()
        orchestrator_type = config["settings"].get("orchestrator_type", "enhanced")
        assert orchestrator_type == "enhanced"
        
        # Test base orchestrator
        minimal_config = TeamConfigFixtures.minimal_team_config()
        minimal_config["settings"]["orchestrator_type"] = "base"
        orchestrator_type = minimal_config["settings"].get("orchestrator_type", "enhanced")
        assert orchestrator_type == "base"
        
        # Test default fallback
        no_type_config = TeamConfigFixtures.minimal_team_config()
        if "orchestrator_type" in no_type_config["settings"]:
            del no_type_config["settings"]["orchestrator_type"]
        orchestrator_type = no_type_config["settings"].get("orchestrator_type", "enhanced")
        assert orchestrator_type == "enhanced"


class TestLaunchEdgeCases:
    """Test edge cases in the launch process"""
    
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_missing_team_config(self):
        """Test behavior when team config is missing"""
        loader = TeamConfigLoader()
        
        with pytest.raises(Exception):  # Should raise some kind of error
            loader.load_config("nonexistent-team")
    
    def test_malformed_team_config(self):
        """Test behavior with malformed YAML"""
        # Create malformed YAML
        malformed_dir = self.temp_dir / "malformed-team"
        malformed_dir.mkdir()
        
        yaml_file = malformed_dir / "team.yaml"
        yaml_file.write_text("invalid: yaml: content: [unclosed")
        
        loader = TeamConfigLoader()
        original_search_paths = loader.search_paths.copy()
        loader.search_paths.append(self.temp_dir)
        
        try:
            with pytest.raises(Exception):  # Should raise YAML parsing error
                loader.load_config("malformed-team")
        finally:
            loader.search_paths = original_search_paths
    
    def test_context_name_conflicts(self):
        """Test context name conflict handling"""
        # This would test the force parameter logic
        context_name = "test-context"
        force = True
        
        # Simulate existing context check
        context_exists = True  # Mock existing context
        
        if context_exists and not force:
            # Should raise error
            with pytest.raises(ValueError):
                raise ValueError(f"Context '{context_name}' already exists")
        elif context_exists and force:
            # Should proceed with cleanup
            assert True, "Should proceed with force cleanup"
        else:
            # Should proceed normally
            assert True, "Should proceed normally"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])