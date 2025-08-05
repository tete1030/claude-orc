"""
Test fixtures for team configurations
"""
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
import yaml


class TeamConfigFixtures:
    """Provides test fixtures for team configurations"""
    
    @staticmethod
    def minimal_team_config() -> Dict[str, Any]:
        """Minimal valid team configuration"""
        return {
            "team": {
                "name": "Test Team",
                "description": "A test team for unit testing"
            },
            "agents": [
                {
                    "name": "TestAgent",
                    "role": "Test Role"
                }
            ],
            "settings": {
                "default_context_name": "test-context",
                "orchestrator_type": "enhanced",
                "poll_interval": 0.5,
                "mcp_port": 8765
            }
        }
    
    @staticmethod
    def devops_team_config() -> Dict[str, Any]:
        """DevOps team configuration similar to the real one"""
        return {
            "team": {
                "name": "DevOps Team",
                "description": "Complete DevOps team for software development lifecycle"
            },
            "agents": [
                {
                    "name": "Architect",
                    "role": "Team Lead and System Architect"
                },
                {
                    "name": "Developer", 
                    "role": "Implementation and Coding Engineer"
                },
                {
                    "name": "QA",
                    "role": "Quality Assurance Engineer"
                },
                {
                    "name": "DevOps",
                    "role": "Infrastructure and Deployment Engineer"  
                },
                {
                    "name": "Docs",
                    "role": "Documentation Specialist"
                }
            ],
            "settings": {
                "default_context_name": "devops-team",
                "orchestrator_type": "enhanced",
                "poll_interval": 0.5,
                "mcp_port": 8766
            }
        }
    
    @staticmethod
    def team_with_explicit_models() -> Dict[str, Any]:
        """Team configuration with explicit model assignments"""
        return {
            "team": {
                "name": "Model Test Team",
                "description": "Team for testing model assignments"
            },
            "agents": [
                {
                    "name": "LeadArchitect",
                    "role": "Lead System Architect",
                    "model": "opus"
                },
                {
                    "name": "SeniorDeveloper",
                    "role": "Senior Software Developer", 
                    "model": "opus"
                },
                {
                    "name": "QATester",
                    "role": "Quality Assurance Tester",
                    "model": "sonnet"
                }
            ],
            "settings": {
                "default_context_name": "model-test",
                "default_model": "sonnet"
            }
        }
    
    @staticmethod
    def invalid_team_config() -> Dict[str, Any]:
        """Invalid team configuration for testing validation"""
        return {
            "team": {
                "name": "",  # Invalid: empty name
                "description": "Invalid config"
            },
            "agents": [],  # Invalid: no agents
            "settings": {}
        }
    
    @staticmethod
    def create_temp_team_dir(config: Dict[str, Any], team_name: str = "test-team") -> Path:
        """Create a temporary team directory with config files"""
        temp_dir = Path(tempfile.mkdtemp())
        team_dir = temp_dir / team_name
        team_dir.mkdir()
        
        # Write team.yaml
        with open(team_dir / "team.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        # Create agent prompt files if they don't exist
        for agent in config.get("agents", []):
            agent_name = agent["name"].lower().replace(" ", "-")
            prompt_file = team_dir / f"{agent_name}.md"
            if not prompt_file.exists():
                prompt_file.write_text(f"# {agent['name']} Agent Prompt\n\nTest prompt for {agent['name']}")
        
        return team_dir
    
    @staticmethod
    def cleanup_temp_dir(temp_dir: Path):
        """Clean up temporary directory"""
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


class LaunchConfigFixtures:
    """Fixtures for launch configurations"""
    
    @staticmethod
    def minimal_launch_config():
        """Minimal launch configuration"""
        return {
            "team_name": "test-team",
            "context_name": None,
            "model_override": None,
            "agent_model_overrides": {},
            "force": False,
            "debug": False,
            "task": None
        }
    
    @staticmethod
    def full_launch_config():
        """Complete launch configuration with all options"""
        return {
            "team_name": "devops-team",
            "context_name": "custom-context",
            "model_override": "opus",
            "agent_model_overrides": {
                "Developer": "opus",
                "QA": "sonnet"
            },
            "force": True,
            "debug": True,
            "task": "Implement new feature"
        }
    
    @staticmethod
    def launch_config_with_task():
        """Launch config with task injection"""
        return {
            "team_name": "devops-team",
            "context_name": "task-test",
            "model_override": None,
            "agent_model_overrides": {},
            "force": False,
            "debug": False,
            "task": "Analyze the message delivery system and suggest improvements"
        }


class MockFixtures:
    """Mock objects for testing"""
    
    @staticmethod
    def mock_orchestrator():
        """Mock orchestrator for testing"""
        class MockOrchestrator:
            def __init__(self):
                self.running = False
                self.agents = {}
                self.tmux = MockTmux()
            
            def register_agent(self, name, session_id, prompt):
                agent = MockAgent(name, session_id, prompt)
                self.agents[name] = agent
                return agent
            
            def start(self, mcp_port=None):
                self.running = True
                return True
            
            def stop(self):
                self.running = False
        
        return MockOrchestrator()
    
    @staticmethod
    def mock_tmux():
        """Mock tmux manager"""
        class MockTmux:
            def __init__(self):
                self.session_name = "mock-session"
            
            def create_session(self, num_panes, force=False, layout=None):
                return True
        
        return MockTmux()
    
    @staticmethod  
    def mock_agent(name="TestAgent", session_id="test-session", prompt="Test prompt"):
        """Mock agent"""
        class MockAgent:
            def __init__(self, name, session_id, prompt):
                self.name = name
                self.session_id = session_id
                self.prompt = prompt
                self.pane_index = 0
        
        return MockAgent(name, session_id, prompt)


class NetworkFixtures:
    """Network-related test fixtures"""
    
    @staticmethod
    def get_available_port() -> int:
        """Get an actually available port for testing"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('', 0))
            port = sock.getsockname()[1]
            return port
        finally:
            sock.close()
    
    @staticmethod
    def get_busy_port() -> int:
        """Get a port that's actually in use"""
        import socket
        # Try common ports that are likely to be busy
        busy_ports = [22, 80, 443, 8080]
        for port in busy_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(('localhost', port))
                if result == 0:  # Port is open/busy
                    return port
            except:
                continue
            finally:
                sock.close()
        
        # Fallback: create our own busy port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        port = sock.getsockname()[1]
        # Don't close the socket, keep it busy
        return port