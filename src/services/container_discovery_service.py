"""
Container Discovery Service

Handles discovery and parsing of Docker containers for team contexts.
Uses Docker inspect for proper JSON-based label reading.
"""
import subprocess
import json
import logging
import re
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
        self.logger = logging.getLogger(__name__)
        # Container name validation pattern (alphanumeric, dash, underscore)
        self._container_name_pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')
    
    def discover_all_containers(self) -> Dict[str, ContextInfo]:
        """Discover all team contexts from running containers using docker inspect"""
        contexts = {}
        
        try:
            # Phase 1: Get container names
            ps_result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={self.container_prefix}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            
            container_names = [name.strip() for name in ps_result.stdout.strip().split("\n") if name.strip()]
            
            if not container_names:
                return contexts
            
            # Phase 2: Batch inspect all containers at once
            # Note: Some containers might disappear between ps and inspect (--rm containers)
            # So we need to handle this gracefully
            inspect_result = subprocess.run(
                ["docker", "inspect"] + container_names,
                capture_output=True,
                text=True,
                check=False,  # Don't fail if some containers are gone
            )
            
            # If all containers are gone, return empty
            if inspect_result.returncode != 0:
                # Check if it's because containers don't exist
                if "No such object" in inspect_result.stderr:
                    self.logger.info("Some containers disappeared during discovery (likely --rm containers)")
                    # Try to inspect containers one by one to get what we can
                    containers_data = []
                    for container_name in container_names:
                        single_inspect = subprocess.run(
                            ["docker", "inspect", container_name],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if single_inspect.returncode == 0:
                            try:
                                data = json.loads(single_inspect.stdout)
                                if data:
                                    containers_data.extend(data)
                            except json.JSONDecodeError:
                                pass
                    if not containers_data:
                        return contexts
                else:
                    # Some other error
                    raise subprocess.CalledProcessError(
                        inspect_result.returncode, 
                        inspect_result.args,
                        output=inspect_result.stdout,
                        stderr=inspect_result.stderr
                    )
            else:
                containers_data = json.loads(inspect_result.stdout)
            
            # Process each container's data
            for container_data in containers_data:
                # Extract relevant fields
                container_name = container_data["Name"].lstrip("/")  # Docker adds leading slash
                labels = container_data["Config"]["Labels"] or {}
                state = container_data["State"]
                created = container_data["Created"]
                
                # Check for our label schema
                if "xyz.texot.ccbox.schema_version" not in labels:
                    self.logger.debug(f"Container '{container_name}' missing schema version label. Skipping.")
                    continue
                
                context_name = labels.get("xyz.texot.ccbox.context")
                agent_role = labels.get("xyz.texot.ccbox.role")
                
                if not context_name or not agent_role:
                    self.logger.debug(f"Container '{container_name}' missing required labels (context/role). Skipping.")
                    continue
                
                # Create container info
                # Build status string from running state
                status = "running" if state["Running"] else f"exited ({state.get('ExitCode', 'unknown')})"
                
                container_info = ContainerInfo(
                    name=container_name,
                    status=status,
                    created=created,
                    agent_role=agent_role,
                    running=state["Running"],
                )
                
                # Add to context
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
                if state["Running"]:
                    contexts[context_name].running_containers += 1
                
                # Set session creation time to earliest container
                if not contexts[context_name].created or created < contexts[context_name].created:
                    contexts[context_name].created = created
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Docker command failed during discovery: {e}")
            raise RuntimeError(f"Failed to discover containers: {e}") from e
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from docker inspect: {e}")
            raise RuntimeError(f"Failed to parse docker output: {e}") from e
        
        return contexts
    
    # Container identification relies solely on Docker labels
    # No parsing or guessing - containers without proper labels are rejected
    
    def get_container_status(self, container_names: List[str]) -> List[ContainerInfo]:
        """Get status information for specific containers using docker inspect"""
        containers = []
        
        if not container_names:
            return containers
        
        # Validate container names for security
        validated_names = []
        for name in container_names:
            if not self._container_name_pattern.match(name):
                self.logger.warning(f"Invalid container name format: {name}")
                continue
            validated_names.append(name)
        
        if not validated_names:
            return containers
        
        try:
            # Batch inspect all validated containers
            inspect_result = subprocess.run(
                ["docker", "inspect"] + validated_names,
                capture_output=True,
                text=True,
                check=False,  # Don't fail if some containers don't exist
            )
            
            if inspect_result.returncode != 0:
                # Some containers might not exist, that's ok
                return containers
            
            containers_data = json.loads(inspect_result.stdout)
            
            # Process each container's data
            for container_data in containers_data:
                # Extract relevant fields
                container_name = container_data["Name"].lstrip("/")
                labels = container_data["Config"]["Labels"] or {}
                state = container_data["State"]
                created = container_data["Created"]
                
                # Check for required labels
                if "xyz.texot.ccbox.schema_version" not in labels:
                    self.logger.debug(f"Container '{container_name}' missing schema version label. Skipping.")
                    continue
                
                agent_role = labels.get("xyz.texot.ccbox.role")
                if not agent_role:
                    self.logger.debug(f"Container '{container_name}' missing required 'xyz.texot.ccbox.role' label.")
                    continue
                
                # Create container info
                # Build status string from running state
                status = "running" if state["Running"] else f"exited ({state.get('ExitCode', 'unknown')})"
                
                containers.append(ContainerInfo(
                    name=container_name,
                    status=status,
                    created=created,
                    agent_role=agent_role,
                    running=state["Running"],
                ))
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from docker inspect: {e}")
            # Return empty list instead of raising - some containers might not exist
            return []
        
        return containers
    
    def check_container_running(self, container_name: str) -> bool:
        """Check if a container exists and is running - exact name match only"""
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