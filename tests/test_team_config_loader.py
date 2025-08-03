#!/usr/bin/env python3
"""Unit tests for the team configuration loader module."""

import json
import pytest
import tempfile
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from team_config_loader import TeamConfigLoader, TeamConfig, Agent


class TestTeamConfigLoader:
    """Test cases for TeamConfigLoader."""
    
    def test_default_search_paths(self):
        """Test that default search paths are set correctly."""
        loader = TeamConfigLoader()
        assert len(loader.search_paths) == 2
        assert loader.search_paths[0] == Path("teams")
        assert loader.search_paths[1] == Path("examples/teams")
    
    def test_custom_search_paths(self):
        """Test setting custom search paths."""
        custom_paths = [Path("/tmp/teams"), Path("/opt/teams")]
        loader = TeamConfigLoader(search_paths=custom_paths)
        assert loader.search_paths == custom_paths
    
    def test_default_settings(self):
        """Test default settings are initialized."""
        loader = TeamConfigLoader()
        assert loader.default_settings["default_session_name"] == "team-session"
        assert loader.default_settings["default_model"] == "claude-3.5-sonnet"
        assert loader.default_settings["orchestrator_type"] == "enhanced"
    
    def test_find_config_file_not_found(self):
        """Test finding config file that doesn't exist."""
        loader = TeamConfigLoader(search_paths=[Path("/nonexistent")])
        result = loader.find_config_file("test-config")
        assert result is None
    
    def test_find_config_file_with_json(self, tmp_path):
        """Test finding JSON config file."""
        # Create test config file
        config_file = tmp_path / "test-config.json"
        config_file.write_text("{}")
        
        loader = TeamConfigLoader(search_paths=[tmp_path])
        result = loader.find_config_file("test-config")
        assert result == config_file
        
        # Test with extension
        result = loader.find_config_file("test-config.json")
        assert result == config_file
    
    def test_load_prompt_file(self, tmp_path):
        """Test loading prompt file."""
        # Create test prompt file
        prompt_file = tmp_path / "architect.md"
        prompt_content = "You are the architect agent."
        prompt_file.write_text(prompt_content)
        
        loader = TeamConfigLoader()
        result = loader.load_prompt_file("architect.md", tmp_path)
        assert result == prompt_content
    
    def test_load_prompt_file_not_found(self, tmp_path):
        """Test loading non-existent prompt file."""
        loader = TeamConfigLoader()
        result = loader.load_prompt_file("nonexistent.md", tmp_path)
        assert result is None
    
    def test_parse_json_config(self, tmp_path):
        """Test parsing JSON configuration."""
        config_data = {
            "team": {
                "name": "Test Team",
                "description": "Test description"
            },
            "agents": [
                {
                    "name": "Agent1",
                    "role": "Role1"
                }
            ]
        }
        
        config_file = tmp_path / "test.json"
        config_json = json.dumps(config_data)
        
        loader = TeamConfigLoader()
        parsed = loader.parse_config_data(config_json, config_file)
        
        assert parsed["team"]["name"] == "Test Team"
        assert len(parsed["agents"]) == 1
        assert parsed["agents"][0]["name"] == "Agent1"
    
    def test_load_config_complete(self, tmp_path):
        """Test loading a complete configuration."""
        # Create config directory
        config_dir = tmp_path / "teams"
        config_dir.mkdir()
        
        # Create config file
        config_data = {
            "team": {
                "name": "DevOps Team",
                "description": "Development team"
            },
            "agents": [
                {
                    "name": "Architect",
                    "role": "Team Lead",
                    "model": "claude-3.5-sonnet"
                },
                {
                    "name": "Developer",
                    "role": "Software Engineer"
                }
            ],
            "settings": {
                "default_session_name": "devops-session"
            }
        }
        
        config_file = config_dir / "devops.json"
        config_file.write_text(json.dumps(config_data, indent=2))
        
        # Create prompt file
        prompt_file = config_dir / "architect.md"
        prompt_file.write_text("You are the architect.")
        
        # Load config
        loader = TeamConfigLoader(search_paths=[tmp_path])
        team_config = loader.load_config("teams/devops")
        
        assert team_config.name == "DevOps Team"
        assert team_config.description == "Development team"
        assert len(team_config.agents) == 2
        assert team_config.agents[0].name == "Architect"
        assert team_config.agents[0].role == "Team Lead"
        assert team_config.agents[0].model == "claude-3.5-sonnet"
        assert team_config.agents[0].prompt == "You are the architect."
        assert team_config.agents[1].name == "Developer"
        assert team_config.settings["default_session_name"] == "devops-session"
        assert team_config.settings["orchestrator_type"] == "enhanced"  # default
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent config."""
        loader = TeamConfigLoader()
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_config("nonexistent")
        assert "not found" in str(exc_info.value)
    
    def test_load_config_missing_team_section(self, tmp_path):
        """Test loading config without team section."""
        config_data = {"agents": []}
        config_file = tmp_path / "bad.json"
        config_file.write_text(json.dumps(config_data))
        
        loader = TeamConfigLoader(search_paths=[tmp_path])
        with pytest.raises(ValueError) as exc_info:
            loader.load_config("bad")
        assert "must have a 'team' section" in str(exc_info.value)
    
    def test_load_config_no_agents(self, tmp_path):
        """Test loading config without agents."""
        config_data = {
            "team": {"name": "Empty Team"},
            "agents": []
        }
        config_file = tmp_path / "empty.json"
        config_file.write_text(json.dumps(config_data))
        
        loader = TeamConfigLoader(search_paths=[tmp_path])
        with pytest.raises(ValueError) as exc_info:
            loader.load_config("empty")
        assert "at least one agent" in str(exc_info.value)
    
    def test_validate_config_valid(self):
        """Test validating a valid configuration."""
        config = TeamConfig(
            name="Test Team",
            description="Test",
            agents=[
                Agent(name="Agent1", role="Role1")
            ],
            settings={"orchestrator_type": "enhanced"}
        )
        
        loader = TeamConfigLoader()
        errors = loader.validate_config(config)
        assert len(errors) == 0
    
    def test_validate_config_invalid(self):
        """Test validating invalid configurations."""
        loader = TeamConfigLoader()
        
        # No name
        config = TeamConfig(name="", description="Test")
        errors = loader.validate_config(config)
        assert "Team name is required" in errors
        
        # No agents
        config = TeamConfig(name="Test", description="Test", agents=[])
        errors = loader.validate_config(config)
        assert "At least one agent is required" in errors
        
        # Invalid orchestrator type
        config = TeamConfig(
            name="Test",
            description="Test",
            agents=[Agent(name="A", role="R")],
            settings={"orchestrator_type": "invalid"}
        )
        errors = loader.validate_config(config)
        assert any("orchestrator_type" in e for e in errors)
        
        # Duplicate agent names
        config = TeamConfig(
            name="Test",
            description="Test",
            agents=[
                Agent(name="Agent", role="Role1"),
                Agent(name="Agent", role="Role2")
            ]
        )
        errors = loader.validate_config(config)
        assert any("Duplicate agent names" in e for e in errors)
    
    def test_get_agent_by_name(self):
        """Test finding agent by name."""
        config = TeamConfig(
            name="Test",
            description="Test",
            agents=[
                Agent(name="Architect", role="Lead"),
                Agent(name="Developer", role="Engineer")
            ]
        )
        
        loader = TeamConfigLoader()
        
        # Found
        agent = loader.get_agent_by_name(config, "Architect")
        assert agent is not None
        assert agent.name == "Architect"
        assert agent.role == "Lead"
        
        # Case insensitive
        agent = loader.get_agent_by_name(config, "architect")
        assert agent is not None
        assert agent.name == "Architect"
        
        # Not found
        agent = loader.get_agent_by_name(config, "NonExistent")
        assert agent is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])