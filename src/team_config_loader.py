#!/usr/bin/env python3
"""Team Configuration Loader Module

This module handles loading and parsing team configuration files
for the Claude Multi-Agent Orchestrator system.

Configuration files can be in YAML or JSON format and are searched
in the following order:
1. teams/ directory
2. examples/teams/ directory

Example configuration structure:
{
  "team": {
    "name": "DevOps Team",
    "description": "Development and Operations team"
  },
  "agents": [
    {
      "name": "Architect",
      "role": "Team Lead",
      "model": "sonnet"
    }
  ],
  "settings": {
    "default_context_name": "team-session",
    "default_model": "sonnet",
    "orchestrator_type": "enhanced"
  }
}
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Any, cast
from dataclasses import dataclass, field


class AgentConfig(TypedDict, total=False):
    """Type definition for agent configuration."""

    name: str
    role: str
    model: Optional[str]
    prompt_file: Optional[str]


class TeamSettings(TypedDict, total=False):
    """Type definition for team settings."""

    default_context_name: str
    default_model: str
    orchestrator_type: str


class TeamConfigData(TypedDict):
    """Type definition for complete team configuration."""

    team: Dict[str, str]
    agents: List[AgentConfig]
    settings: TeamSettings


@dataclass
class AgentConfig:
    """Represents an agent in the team."""

    name: str
    role: str
    model: Optional[str] = None
    prompt: Optional[str] = None
    prompt_file: Optional[str] = None


@dataclass
class TeamConfig:
    """Represents a complete team configuration."""

    name: str
    description: str
    agents: List[AgentConfig] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    config_path: Optional[Path] = None


class TeamConfigLoader:
    """Loads and parses team configuration files."""

    def __init__(self, search_paths: Optional[List[Path]] = None):
        """Initialize the config loader with search paths.

        Args:
            search_paths: List of paths to search for config files.
                         Defaults to ['teams/', 'examples/teams/']
        """
        self.logger = logging.getLogger(__name__)

        if search_paths is None:
            self.search_paths = [Path("teams"), Path("examples/teams")]
        else:
            self.search_paths = search_paths

        # Default settings
        self.default_settings = {
            "default_context_name": "team-session",
            "default_model": "sonnet",
            "orchestrator_type": "enhanced",
        }

    def find_config_file(self, config_name: str) -> Optional[Path]:
        """Find a configuration file by name in search paths.

        Searches for files with .yaml, .yml, or .json extensions.

        Args:
            config_name: Name of the config file (with or without extension)

        Returns:
            Path to the config file if found, None otherwise
        """
        # Remove extension if present
        base_name = config_name
        for ext in [".yaml", ".yml", ".json"]:
            if config_name.endswith(ext):
                base_name = config_name[: -len(ext)]
                break

        # Search for file with supported extensions
        for search_path in self.search_paths:
            for ext in [".yaml", ".yml", ".json"]:
                config_path = search_path / f"{base_name}" / f"team{ext}"
                if config_path.exists():
                    self.logger.debug(f"Found config file: {config_path}")
                    return config_path

        return None

    def load_prompt_file(self, prompt_file: str, config_dir: Path) -> Optional[str]:
        """Load prompt content from a markdown file.

        Args:
            prompt_file: Name of the prompt file
            config_dir: Directory containing the config file

        Returns:
            Content of the prompt file if found, None otherwise
        """
        prompt_path = config_dir / prompt_file
        if prompt_path.exists():
            try:
                content = prompt_path.read_text()
                self.logger.debug(f"Loaded prompt file: {prompt_path}")
                return content
            except Exception as e:
                self.logger.error(f"Error reading prompt file {prompt_path}: {e}")
                return None
        else:
            self.logger.debug(f"Prompt file not found: {prompt_path}")
            return None

    def parse_config_data(self, config_data: str, file_path: Path) -> TeamConfigData:
        """Parse configuration data based on file extension.

        Supports YAML and JSON formats. YAML support requires PyYAML.

        Args:
            config_data: Configuration string
            file_path: Path to the config file (for extension detection)

        Returns:
            Parsed configuration data

        Raises:
            ValueError: If configuration format is invalid
        """
        ext = file_path.suffix.lower()

        if ext == ".json":
            try:
                data = json.loads(config_data)
                return cast(TeamConfigData, data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {e}")

        elif ext in [".yaml", ".yml"]:
            try:
                import yaml

                data = yaml.safe_load(config_data)
                return cast(TeamConfigData, data)
            except ImportError:
                # Fallback: try to parse as JSON
                self.logger.warning("PyYAML not installed, attempting JSON parse")
                try:
                    data = json.loads(config_data)
                    return cast(TeamConfigData, data)
                except json.JSONDecodeError:
                    raise ValueError(
                        "PyYAML is required for YAML files. Install with: pip install pyyaml"
                    )
            except Exception as e:
                raise ValueError(f"Invalid YAML format: {e}")

        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def load_config(self, config_name: str) -> TeamConfig:
        """Load a team configuration by name.

        Args:
            config_name: Name of the configuration file

        Returns:
            TeamConfig object with loaded configuration

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config file is invalid
        """
        # Find the config file
        config_path = self.find_config_file(config_name)
        if not config_path:
            searched_paths = ", ".join(str(p) for p in self.search_paths)
            raise FileNotFoundError(
                f"Configuration file '{config_name}' not found in: {searched_paths}"
            )

        # Load and parse the config file
        try:
            config_content = config_path.read_text()
            config_data = self.parse_config_data(config_content, config_path)
        except Exception as e:
            raise ValueError(f"Error loading config file {config_path}: {e}")

        # Extract team information
        team_info = config_data.get("team", {})
        if not team_info:
            raise ValueError("Configuration must have a 'team' section")

        team_config = TeamConfig(
            name=team_info.get("name", "Unnamed Team"),
            description=team_info.get("description", ""),
            config_path=config_path,
        )

        # Process agents
        config_dir = config_path.parent
        agents_data = config_data.get("agents", [])
        if not agents_data:
            raise ValueError("Configuration must have at least one agent")

        for agent_data in agents_data:
            if not isinstance(agent_data, dict):
                raise ValueError(f"Invalid agent configuration: {agent_data}")

            agent = AgentConfig(
                name=agent_data.get("name", "Unknown"),
                role=agent_data.get("role", "Agent"),
                model=agent_data.get("model"),
            )

            # Load prompt file if specified or use default naming
            prompt_file = agent_data.get("prompt_file")
            if not prompt_file:
                # Try default naming convention
                prompt_file = f"{agent.name.lower().replace(' ', '_')}.md"

            agent.prompt_file = prompt_file
            agent.prompt = self.load_prompt_file(prompt_file, config_dir)

            team_config.agents.append(agent)

        # Process settings with defaults
        settings = config_data.get("settings", {})
        team_config.settings = {**self.default_settings, **settings}

        self.logger.info(
            f"Loaded team configuration: {team_config.name} "
            f"with {len(team_config.agents)} agents"
        )

        return team_config

    def validate_config(self, config: TeamConfig) -> List[str]:
        """Validate a team configuration.

        Args:
            config: TeamConfig to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not config.name:
            errors.append("Team name is required")

        if not config.agents:
            errors.append("At least one agent is required")

        # Check for duplicate agent names
        agent_names = [agent.name for agent in config.agents]
        if len(agent_names) != len(set(agent_names)):
            errors.append("Duplicate agent names found")

        for i, agent in enumerate(config.agents):
            if not agent.name:
                errors.append(f"Agent {i+1}: name is required")
            if not agent.role:
                errors.append(f"Agent {agent.name or i+1}: role is required")

        # Validate settings
        orchestrator_type = config.settings.get("orchestrator_type", "")
        if orchestrator_type not in ("base", "enhanced"):
            errors.append(
                f"Invalid orchestrator_type: '{orchestrator_type}'. " "Must be 'base' or 'enhanced'"
            )

        return errors

    def get_agent_by_name(self, config: TeamConfig, name: str) -> Optional[AgentConfig]:
        """Get an agent by name from the configuration.

        Args:
            config: TeamConfig to search
            name: Name of the agent

        Returns:
            Agent if found, None otherwise
        """
        for agent in config.agents:
            if agent.name.lower() == name.lower():
                return agent
        return None
