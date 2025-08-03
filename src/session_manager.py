#!/usr/bin/env python3
"""
Session Manager for Orchestrator Team Sessions

Manages persistent container-based team sessions, tracking:
- Container names for each agent
- Tmux session names
- Session metadata
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
class AgentInfo:
    """Information about an agent in a session"""
    name: str
    container: str
    container_mode: str = "isolated"  # isolated or shared
    model: str = "sonnet"
    pane_index: Optional[int] = None
    
    
@dataclass 
class TeamSession:
    """Represents a team session with containers and tmux"""
    session_name: str
    containers: List[str]
    tmux_session: str
    created_at: str
    agents: List[AgentInfo]
    updated_at: Optional[str] = None
    orchestrator_config: Dict[str, Any] = field(default_factory=dict)
    

class SessionManager:
    """Manages team sessions and their persistent containers"""
    
    def __init__(self, registry_path: Optional[str] = None):
        """Initialize session manager
        
        Args:
            registry_path: Path to session registry JSON file.
                          Defaults to ~/.claude-orc/sessions.json
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up registry path
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            self.registry_path = Path.home() / ".claude-orc" / "sessions.json"
            
        # Create directory if needed
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing registry
        self.sessions = self._load_registry()
        
    def _load_registry(self) -> Dict[str, TeamSession]:
        """Load session registry from disk"""
        if not self.registry_path.exists():
            return {}
            
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                
            sessions = {}
            for name, session_data in data.items():
                # Convert agent dicts to AgentInfo objects
                agents = [AgentInfo(**agent) for agent in session_data.get('agents', [])]
                session_data['agents'] = agents
                
                sessions[name] = TeamSession(**session_data)
                
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
            return {}
            
    def _save_registry(self):
        """Save session registry to disk"""
        try:
            # Convert sessions to JSON-serializable format
            data = {}
            for name, session in self.sessions.items():
                session_dict = asdict(session)
                # Ensure agents are properly serialized
                session_dict['agents'] = [asdict(agent) for agent in session.agents]
                data[name] = session_dict
                
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
            
    def create_session(self, session_name: str, agents: List[AgentInfo], 
                      tmux_session: str, orchestrator_config: Optional[Dict] = None) -> TeamSession:
        """Create a new team session
        
        Args:
            session_name: Unique name for this team session
            agents: List of AgentInfo objects defining the agents
            tmux_session: Name of the tmux session
            orchestrator_config: Optional orchestrator configuration
            
        Returns:
            Created TeamSession object
            
        Raises:
            ValueError: If session already exists
        """
        if session_name in self.sessions:
            raise ValueError(f"Session '{session_name}' already exists")
            
        # Extract container names
        containers = [agent.container for agent in agents]
        
        # Create session object
        session = TeamSession(
            session_name=session_name,
            containers=containers,
            tmux_session=tmux_session,
            created_at=datetime.now().isoformat(),
            agents=agents,
            orchestrator_config=orchestrator_config or {}
        )
        
        # Save to registry
        self.sessions[session_name] = session
        self._save_registry()
        
        self.logger.info(f"Created session '{session_name}' with {len(agents)} agents")
        return session
        
    def resume_session(self, session_name: str) -> Optional[TeamSession]:
        """Resume an existing session
        
        Args:
            session_name: Name of session to resume
            
        Returns:
            TeamSession if found and containers exist
            
        Raises:
            ValueError: If session not found or containers missing
        """
        if session_name not in self.sessions:
            raise ValueError(f"Session '{session_name}' not found")
            
        session = self.sessions[session_name]
        
        # Verify all containers exist
        missing_containers = []
        for container in session.containers:
            if not self._check_container_exists(container):
                missing_containers.append(container)
                
        if missing_containers:
            raise ValueError(f"Missing containers for session '{session_name}': {missing_containers}")
            
        # Update last accessed time
        session.updated_at = datetime.now().isoformat()
        self._save_registry()
        
        self.logger.info(f"Resumed session '{session_name}'")
        return session
        
    def list_sessions(self) -> Dict[str, Dict]:
        """List all sessions
        
        Returns:
            Dictionary of session names to session data
        """
        return {name: asdict(session) for name, session in self.sessions.items()}
        
    def delete_session(self, session_name: str) -> bool:
        """Delete a session from registry (does not remove containers)
        
        Args:
            session_name: Name of session to delete
            
        Returns:
            True if deleted, False if not found
        """
        if session_name not in self.sessions:
            return False
            
        del self.sessions[session_name]
        self._save_registry()
        
        self.logger.info(f"Deleted session '{session_name}' from registry")
        return True
        
    def cleanup_session(self, session_name: str) -> bool:
        """Cleanup a session and its resources
        
        This method removes the session from registry and optionally
        cleans up associated resources like containers and tmux sessions.
        
        Args:
            session_name: Name of session to cleanup
            
        Returns:
            True if cleanup successful, False if session not found
        """
        if session_name not in self.sessions:
            return False
            
        session = self.sessions[session_name]
        
        # Log what would be cleaned up (actual cleanup not implemented)
        self.logger.info(f"Cleaning up session '{session_name}'")
        self.logger.info(f"Would remove containers: {session.containers}")
        self.logger.info(f"Would kill tmux session: {session.tmux_session}")
        
        # Remove from registry
        del self.sessions[session_name]
        self._save_registry()
        
        return True
        
    def get_session(self, session_name: str) -> Optional[TeamSession]:
        """Get a session by name
        
        Args:
            session_name: Name of session
            
        Returns:
            TeamSession if found, None otherwise
        """
        return self.sessions.get(session_name)
        
    def update_session(self, session_name: str, **kwargs) -> Optional[TeamSession]:
        """Update session metadata
        
        Args:
            session_name: Name of session to update
            **kwargs: Fields to update
            
        Returns:
            Updated TeamSession if found, None otherwise
        """
        if session_name not in self.sessions:
            return None
            
        session = self.sessions[session_name]
        
        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
                
        # Always update timestamp
        session.updated_at = datetime.now().isoformat()
        
        self._save_registry()
        return session