"""
Test helpers for creating proper mock objects
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.team_context_manager import TeamContext, TeamContextAgentInfo


def create_mock_team_context(
    context_name: str,
    agents: List[Dict[str, Any]],
    tmux_session: str = "test-session",
    created_at: Optional[str] = None,
    working_dir: Optional[str] = None,
    orchestrator_config: Optional[Dict[str, Any]] = None,
    **extra_fields
) -> TeamContext:
    """
    Create a proper TeamContext object for testing.
    
    This helper ensures tests use real TeamContext objects instead of dicts,
    avoiding the need for isinstance checks in production code.
    """
    # Convert agent dicts to TeamContextAgentInfo objects
    agent_objects = []
    for agent_data in agents:
        agent_objects.append(TeamContextAgentInfo(
            name=agent_data.get("name", "Agent"),
            role=agent_data.get("role", "Role"),
            model=agent_data.get("model", "sonnet"),
            pane_index=agent_data.get("pane_index"),
            session_id=agent_data.get("session_id"),
            fork_history=agent_data.get("fork_history", [])
        ))
    
    # Create the TeamContext
    context = TeamContext(
        context_name=context_name,
        tmux_session=tmux_session,
        created_at=created_at or datetime.now().isoformat(),
        agents=agent_objects,
        working_dir=working_dir,
        orchestrator_config=orchestrator_config or {}
    )
    
    # Handle any extra fields that tests might expect in metadata
    # by adding them to orchestrator_config
    if extra_fields:
        context.orchestrator_config.update(extra_fields)
    
    return context