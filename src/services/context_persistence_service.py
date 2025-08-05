"""
Context Persistence Service

Handles all context persistence operations including creation, retrieval,
deletion, and export/import of team contexts.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from src.team_context_manager import TeamContextManager, TeamContextAgentInfo


@dataclass
class ContextDetails:
    """Detailed information about a team context"""
    name: str
    agents: List[TeamContextAgentInfo]
    tmux_session: Optional[str]
    created_at: Optional[str]
    metadata: Dict[str, Any]


class ContextPersistenceService:
    """Service for managing team context persistence"""
    
    def __init__(self, context_manager: Optional[TeamContextManager] = None):
        self.logger = logging.getLogger(__name__)
        self.context_manager = context_manager or TeamContextManager()
    
    def create_context(
        self, 
        context_name: str,
        agents: List[TeamContextAgentInfo],
        tmux_session: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new team context.
        
        Args:
            context_name: Name for the context
            agents: List of agents in the team
            tmux_session: Associated tmux session name
            metadata: Additional metadata to store
            
        Returns:
            True if created successfully
        """
        try:
            self.context_manager.create_context(
                context_name=context_name,
                agents=agents,
                tmux_session=tmux_session
            )
            
            # Store additional metadata if provided
            if metadata:
                # Update context metadata through manager's methods
                self.update_context_metadata(context_name, metadata)
            
            self.logger.info(f"Created context '{context_name}' with {len(agents)} agents")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create context '{context_name}': {e}")
            raise
    
    def get_context(self, context_name: str) -> Optional[ContextDetails]:
        """
        Get detailed information about a context.
        
        Args:
            context_name: Name of the context
            
        Returns:
            ContextDetails if found, None otherwise
        """
        team_context = self.context_manager.get_context(context_name)
        if not team_context:
            return None
        
        # Handle both dict and TeamContext object
        if isinstance(team_context, dict):
            # Legacy dict format
            agents_data = team_context.get('agents', [])
            # Convert agent dicts to TeamContextAgentInfo objects
            agents = []
            for agent in agents_data:
                if isinstance(agent, dict):
                    agents.append(TeamContextAgentInfo(**agent))
                else:
                    agents.append(agent)
            tmux_session = team_context.get('tmux_session')
            created_at = team_context.get('created_at', '')
            # Extract metadata
            metadata = {k: v for k, v in team_context.items() 
                       if k not in ["context_name", "agents", "containers", "tmux_session", "created_at"]}
        else:
            # TeamContext object has attributes
            agents = team_context.agents if hasattr(team_context, 'agents') else []
            tmux_session = team_context.tmux_session if hasattr(team_context, 'tmux_session') else None
            created_at = team_context.created_at if hasattr(team_context, 'created_at') else ''
            
            # Extract metadata from extra attributes
            metadata = {}
            if hasattr(team_context, '__dict__'):
                for attr, value in team_context.__dict__.items():
                    if attr not in ["context_name", "agents", "containers", "tmux_session", "created_at", "updated_at", "orchestrator_config"]:
                        metadata[attr] = value
        
        return ContextDetails(
            name=context_name,
            agents=agents,
            tmux_session=tmux_session,
            created_at=created_at,
            metadata=metadata
        )
    
    def list_contexts(self) -> Dict[str, ContextDetails]:
        """
        List all registered contexts.
        
        Returns:
            Dictionary mapping context names to their details
        """
        contexts = {}
        
        # list_contexts returns a dict of context names
        for name in self.context_manager.list_contexts().keys():
            context = self.get_context(name)
            if context:
                contexts[name] = context
        
        return contexts
    
    def delete_context(self, context_name: str) -> bool:
        """
        Delete a context from the registry.
        
        Args:
            context_name: Name of the context to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            self.context_manager.delete_context(context_name)
            self.logger.info(f"Deleted context '{context_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete context '{context_name}': {e}")
            return False
    
    def export_context(self, context_name: str) -> Optional[Dict[str, Any]]:
        """
        Export context configuration for backup or sharing.
        
        Args:
            context_name: Name of the context to export
            
        Returns:
            Exportable dictionary representation
        """
        context = self.get_context(context_name)
        if not context:
            return None
        
        export_data = {
            "context_name": context.name,
            "export_date": datetime.now().isoformat(),
            "tmux_session": context.tmux_session,
            "created_at": context.created_at,
            "agents": [asdict(agent) if hasattr(agent, '__dataclass_fields__') else agent for agent in context.agents],
            "metadata": context.metadata
        }
        
        return export_data
    
    def import_context(
        self, 
        import_data: Dict[str, Any],
        new_name: Optional[str] = None,
        skip_existing: bool = True
    ) -> bool:
        """
        Import a context from exported data.
        
        Args:
            import_data: Exported context data
            new_name: Optional new name for the context
            skip_existing: Skip if context already exists
            
        Returns:
            True if imported successfully
        """
        context_name = new_name or import_data.get("context_name")
        if not context_name:
            raise ValueError("Context name not provided")
        
        # Check if already exists
        if self.get_context(context_name):
            if skip_existing:
                self.logger.info(f"Context '{context_name}' already exists, skipping")
                return False
            else:
                self.delete_context(context_name)
        
        # Recreate agents
        agents = []
        for agent_data in import_data.get("agents", []):
            agents.append(TeamContextAgentInfo(
                name=agent_data.get("name"),
                container=agent_data.get("container"),
                model=agent_data.get("model", "sonnet"),
                pane_index=agent_data.get("pane_index", 0)
            ))
        
        # Create context
        metadata = import_data.get("metadata", {})
        metadata["imported_from"] = import_data.get("context_name")
        metadata["imported_at"] = datetime.now().isoformat()
        
        return self.create_context(
            context_name=context_name,
            agents=agents,
            tmux_session=import_data.get("tmux_session"),
            metadata=metadata
        )
    
    def save_to_file(self, context_name: str, file_path: str) -> bool:
        """
        Save context to a JSON file.
        
        Args:
            context_name: Name of the context to save
            file_path: Path to save the file
            
        Returns:
            True if saved successfully
        """
        export_data = self.export_context(context_name)
        if not export_data:
            return False
        
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Saved context '{context_name}' to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save context to file: {e}")
            return False
    
    def load_from_file(self, file_path: str, new_name: Optional[str] = None) -> bool:
        """
        Load context from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            new_name: Optional new name for the context
            
        Returns:
            True if loaded successfully
        """
        try:
            with open(file_path, 'r') as f:
                import_data = json.load(f)
            
            return self.import_context(import_data, new_name)
            
        except Exception as e:
            self.logger.error(f"Failed to load context from file: {e}")
            return False
    
    def update_context(
        self,
        context_name: str,
        agents: Optional[List[TeamContextAgentInfo]] = None,
        tmux_session: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing team context.
        
        Args:
            context_name: Name of the context to update
            agents: Updated list of agents (optional)
            tmux_session: Updated tmux session name (optional)
            metadata: Updated metadata (optional)
            
        Returns:
            True if updated successfully
        """
        try:
            # Prepare kwargs for update
            update_kwargs = {}
            
            if agents is not None:
                update_kwargs['agents'] = agents
            
            if tmux_session is not None:
                update_kwargs['tmux_session'] = tmux_session
            
            # Add metadata fields directly to kwargs
            if metadata is not None:
                update_kwargs.update(metadata)
            
            # Use the existing update_context method from TeamContextManager
            updated_context = self.context_manager.update_context(context_name, **update_kwargs)
            
            if updated_context:
                self.logger.info(f"Updated context '{context_name}'")
                return True
            else:
                self.logger.error(f"Context '{context_name}' not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update context '{context_name}': {e}")
            return False
    
    def update_context_metadata(
        self, 
        context_name: str, 
        metadata: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        Update metadata for a context.
        
        Args:
            context_name: Name of the context
            metadata: New metadata
            merge: If True, merge with existing; if False, replace
            
        Returns:
            True if updated successfully
        """
        try:
            # Use the update_context method with metadata
            updated_context = self.context_manager.update_context(context_name, **metadata)
            
            if updated_context:
                self.logger.info(f"Updated metadata for context '{context_name}'")
                return True
            else:
                self.logger.error(f"Context '{context_name}' not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update context metadata: {e}")
            return False