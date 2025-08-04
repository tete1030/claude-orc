"""
Container Discovery Service

Handles discovery and parsing of Docker containers for team contexts.
"""
import subprocess
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ContainerInfo:
    """Information about a container"""
    name: str
    status: str
    created: str
    agent_role: str
    running: bool


@dataclass
class ContextInfo:
    """Information about a team context"""
    name: str
    containers: List[ContainerInfo]
    tmux_session: Optional[str]
    created: Optional[str]
    total_containers: int
    running_containers: int


class ContainerDiscoveryService:
    """Service for discovering and managing Docker containers"""
    
    def __init__(self, container_prefix: str = "ccbox-"):
        self.container_prefix = container_prefix
    
    def discover_all_containers(self) -> Dict[str, ContextInfo]:
        """Discover all team contexts from running containers"""
        contexts = {}
        
        try:
            # Get all ccbox containers
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={self.container_prefix}",
                    "--format",
                    "{{.Names}}\t{{.Status}}\t{{.CreatedAt}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                
                container_name, status, created = parts[0], parts[1], parts[2]
                
                # Parse container name to extract session and role
                context_name, agent_role = self.parse_container_name(container_name)
                if not context_name:
                    continue
                
                # Determine if container is running
                running = "Up" in status
                
                container_info = ContainerInfo(
                    name=container_name,
                    status=status,
                    created=created,
                    agent_role=agent_role,
                    running=running,
                )
                
                # Add to session
                if context_name not in contexts:
                    contexts[context_name] = ContextInfo(
                        name=context_name,
                        containers=[],
                        tmux_session=None,
                        created=None,
                        total_containers=0,
                        running_containers=0,
                    )
                
                contexts[context_name].containers.append(container_info)
                contexts[context_name].total_containers += 1
                if running:
                    contexts[context_name].running_containers += 1
                
                # Set session creation time to earliest container
                if not contexts[context_name].created or created < contexts[context_name].created:
                    contexts[context_name].created = created
        
        except subprocess.CalledProcessError as e:
            print(f"Error discovering contexts: {e}")
        
        return contexts
    
    def parse_container_name(self, container_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse container name to extract session name and agent role"""
        if not container_name.startswith(self.container_prefix):
            return None, None
        
        # Remove prefix: ccbox-session-role or ccbox-session-sub-role
        name_part = container_name[len(self.container_prefix):]
        
        # Find last dash to separate role from session name
        parts = name_part.split("-")
        if len(parts) < 2:
            return None, None
        
        # Agent role is the last part
        agent_role = parts[-1]
        # Session name is everything before the last dash
        context_name = "-".join(parts[:-1])
        
        return context_name, agent_role
    
    def get_container_status(self, container_names: List[str]) -> List[ContainerInfo]:
        """Get status information for specific containers"""
        containers = []
        
        for container_name in container_names:
            try:
                # Get container status
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "-a",
                        "--filter",
                        f"name=^{container_name}$",
                        "--format",
                        "{{.Names}}\t{{.Status}}\t{{.CreatedAt}}",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                
                if result.stdout.strip():
                    parts = result.stdout.strip().split("\t")
                    if len(parts) >= 3:
                        status = parts[1]
                        created = parts[2]
                        running = "Up" in status
                        
                        # Extract agent role from container name
                        agent_role = container_name.split("-")[-1]
                        
                        container_info = ContainerInfo(
                            name=container_name,
                            status=status,
                            created=created,
                            agent_role=agent_role,
                            running=running,
                        )
                        
                        containers.append(container_info)
            
            except subprocess.CalledProcessError:
                pass
        
        return containers
    
    def check_container_running(self, container_name: str) -> bool:
        """Quick check if a container exists and is running"""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception:
            return False