#!/usr/bin/env python3
"""
Team Context Manager for Orchestrator Team Contexts

Manages persistent container-based team contexts, tracking:
- Container names for each agent
- Tmux session names  
- Context metadata
"""

import json
import os
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class TeamContextAgentInfo:
    """Information about an agent in a context"""
    name: str
    container: str
    container_mode: str = "isolated"  # isolated or shared
    model: str = "sonnet"
    pane_index: Optional[int] = None
    
    
@dataclass 
class TeamContext:
    """Represents a team context with containers and tmux"""
    context_name: str
    containers: List[str]
    tmux_session: str  # Note: keeping tmux_session as it refers to actual tmux session
    created_at: str
    agents: List[TeamContextAgentInfo]
    updated_at: Optional[str] = None
    orchestrator_config: Dict[str, Any] = field(default_factory=dict)
    

class TeamContextManager:
    """Manages team contexts and their persistent containers"""
    
    def __init__(self, registry_path: Optional[str] = None):
        """Initialize team context manager
        
        Args:
            registry_path: Path to context registry JSON file.
                          Defaults to ~/.claude-orc/team_contexts.json
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up registry path
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            self.registry_path = Path.home() / ".claude-orc" / "team_contexts.json"
            
        # Create directory if needed
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing registry
        self.contexts = self._load_registry()
        
    def _load_registry(self) -> Dict[str, TeamContext]:
        """Load context registry from disk"""
        if not self.registry_path.exists():
            return {}
            
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                
            contexts = {}
            for name, context_data in data.items():
                # Convert agent dicts to TeamContextAgentInfo objects
                agents = [TeamContextAgentInfo(**agent) for agent in context_data.get('agents', [])]
                context_data['agents'] = agents
                
                contexts[name] = TeamContext(**context_data)
                
            return contexts
            
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
            return {}
            
    def _save_registry(self):
        """Save context registry to disk"""
        try:
            # Convert contexts to JSON-serializable format
            data = {}
            for name, context in self.contexts.items():
                context_dict = asdict(context)
                # Ensure agents are properly serialized
                context_dict['agents'] = [asdict(agent) for agent in context.agents]
                data[name] = context_dict
                
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
            raise
            
    def _check_container_exists(self, container_name: str) -> bool:
        """Check if a Docker container exists"""
        try:
            result = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to check container {container_name}: {e}")
            return False
            
    def _check_container_running(self, container_name: str) -> bool:
        """Check if a Docker container is running"""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception as e:
            self.logger.error(f"Failed to check container status {container_name}: {e}")
            return False
            
    def _check_tmux_session_exists(self, session_name: str) -> bool:
        """Check if a tmux session exists"""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
            
    def create_context(self, context_name: str, agents: List[TeamContextAgentInfo], 
                      tmux_session: str, orchestrator_config: Optional[Dict] = None) -> TeamContext:
        """Create a new team context
        
        Args:
            context_name: Unique name for this team context
            agents: List of TeamContextAgentInfo objects defining the agents
            tmux_session: Name of the tmux session
            orchestrator_config: Optional orchestrator configuration
            
        Returns:
            Created TeamContext object
            
        Raises:
            ValueError: If context already exists
        """
        if context_name in self.contexts:
            raise ValueError(f"Context '{context_name}' already exists")
            
        # Extract container names
        containers = [agent.container for agent in agents]
        
        # Create context object
        context = TeamContext(
            context_name=context_name,
            containers=containers,
            tmux_session=tmux_session,
            created_at=datetime.now().isoformat(),
            agents=agents,
            orchestrator_config=orchestrator_config or {}
        )
        
        # Save to registry
        self.contexts[context_name] = context
        self._save_registry()
        
        self.logger.info(f"Created context '{context_name}' with {len(agents)} agents")
        return context
        
    def resume_context(self, context_name: str) -> Optional[TeamContext]:
        """Resume an existing context
        
        Args:
            context_name: Name of context to resume
            
        Returns:
            TeamContext if found and containers exist
            
        Raises:
            ValueError: If context not found or containers missing
        """
        if context_name not in self.contexts:
            raise ValueError(f"Context '{context_name}' not found")
            
        context = self.contexts[context_name]
        
        # Verify all containers exist
        missing_containers = []
        for container in context.containers:
            if not self._check_container_exists(container):
                missing_containers.append(container)
                
        if missing_containers:
            raise ValueError(f"Missing containers for context '{context_name}': {missing_containers}")
            
        # Update last accessed time
        context.updated_at = datetime.now().isoformat()
        self._save_registry()
        
        self.logger.info(f"Resumed context '{context_name}'")
        return context
        
    def list_contexts(self) -> Dict[str, Dict]:
        """List all contexts
        
        Returns:
            Dictionary of context names to context data
        """
        return {name: asdict(context) for name, context in self.contexts.items()}
        
    def delete_context(self, context_name: str) -> bool:
        """Delete a context from registry (does not remove containers)
        
        Args:
            context_name: Name of context to delete
            
        Returns:
            True if deleted, False if not found
        """
        if context_name not in self.contexts:
            return False
            
        del self.contexts[context_name]
        self._save_registry()
        
        self.logger.info(f"Deleted context '{context_name}' from registry")
        return True
        
    def cleanup_context(self, context_name: str) -> bool:
        """Cleanup a context and its resources
        
        This method removes the context from registry and optionally
        cleans up associated resources like containers and tmux sessions.
        
        Args:
            context_name: Name of context to cleanup
            
        Returns:
            True if cleanup successful, False if context not found
        """
        if context_name not in self.contexts:
            return False
            
        context = self.contexts[context_name]
        
        # Log what would be cleaned up (actual cleanup not implemented)
        self.logger.info(f"Cleaning up context '{context_name}'")
        self.logger.info(f"Would remove containers: {context.containers}")
        self.logger.info(f"Would kill tmux session: {context.tmux_session}")
        
        # Remove from registry
        del self.contexts[context_name]
        self._save_registry()
        
        return True
        
    def get_context(self, context_name: str) -> Optional[TeamContext]:
        """Get a context by name
        
        Args:
            context_name: Name of context
            
        Returns:
            TeamContext if found, None otherwise
        """
        return self.contexts.get(context_name)
        
    def update_context(self, context_name: str, **kwargs) -> Optional[TeamContext]:
        """Update context metadata
        
        Args:
            context_name: Name of context to update
            **kwargs: Fields to update
            
        Returns:
            Updated TeamContext if found, None otherwise
        """
        if context_name not in self.contexts:
            return None
            
        context = self.contexts[context_name]
        
        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
                
        # Always update timestamp
        context.updated_at = datetime.now().isoformat()
        
        self._save_registry()
        return context