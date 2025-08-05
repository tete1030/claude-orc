"""
Team Launch Service

Handles the complex process of launching team configurations.
"""
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from src.team_config_loader import TeamConfigLoader
from src.team_context_manager import TeamContextAgentInfo
from src.mcp_central_server import CentralMCPServer
from .port_discovery_service import PortDiscoveryService
from .orchestrator_factory import OrchestratorFactory, OrchestratorOptions
from .mcp_server_manager import MCPServerManager
from .signal_handler_service import SignalHandlerService
from .context_persistence_service import ContextDetails, ContextPersistenceService


class TeamLaunchService:
    """Service for launching team configurations"""
    
    def __init__(
        self,
        port_service: PortDiscoveryService,
        orchestrator_factory: OrchestratorFactory,
        mcp_server_manager: MCPServerManager,
        signal_handler: SignalHandlerService,
        context_persistence: ContextPersistenceService,
        cleanup_callback: Optional[Callable[[str, bool], bool]] = None,
    ):
        self.port_service = port_service
        self.orchestrator_factory = orchestrator_factory
        self.mcp_server_manager = mcp_server_manager
        self.signal_handler = signal_handler
        self.context_persistence = context_persistence
        self.team_loader = TeamConfigLoader()
        self.cleanup_callback = cleanup_callback
        self.logger = logging.getLogger(__name__)
    
    def launch_team(
        self,
        team_name: str,
        context_name: Optional[str] = None,
        model_override: Optional[str] = None,
        agent_model_overrides: Optional[Dict[str, str]] = None,
        force: bool = False,
        debug: bool = False,
        task: Optional[str] = None,
        auto_cleanup: bool = False,
        fresh: bool = False,
    ) -> bool:
        """Launch a team configuration"""
        # Load and validate team configuration
        team_config = self.team_loader.load_config(team_name)
        errors = self.team_loader.validate_config(team_config)
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        # Apply context name override
        if context_name:
            team_config.settings["default_context_name"] = context_name
        else:
            context_name = team_config.settings.get("default_context_name", f"{team_name}")
        
        # Check for existing context and load session IDs if resuming
        existing_context = None
        if context_name:
            existing_context = self.context_persistence.get_context(context_name)
            if existing_context is not None:
                print(f"Found existing context '{context_name}'")
        
        print(f"Launching team: {team_config.name}")
        print(f"Context: {context_name}")
        print(f"Agents: {len(team_config.agents)}")
        if existing_context and not fresh:
            print(f"Resume mode: Will attempt to resume existing sessions")
        elif fresh:
            print(f"Fresh mode: Creating new sessions")
        
        # Prepare agent configurations
        agent_configs = self._prepare_agent_configs(
            team_config, 
            context_name, 
            existing_context if not fresh else None,
            model_override, 
            agent_model_overrides
        )
        
        # Create orchestrator
        orchestrator_type = team_config.settings.get("orchestrator_type", "enhanced")
        options = OrchestratorOptions(
            context_name=context_name,
            orchestrator_type=orchestrator_type,
            poll_interval=0.5,
            force=force,
            debug=debug
        )
        
        orchestrator = self.orchestrator_factory.create_configured_orchestrator(
            options, team_config, agent_configs
        )
        
        # Find available MCP port
        desired_port = team_config.settings.get("mcp_port", 8765)
        mcp_port = self.port_service.find_available_port(desired_port)
        
        # Create and start MCP server
        mcp_server = CentralMCPServer(orchestrator, port=mcp_port)
        self.mcp_server_manager.start_server(mcp_server, startup_delay=2.0)
        
        # Register agents with orchestrator
        self._register_agents(team_config, agent_configs, orchestrator, task)
        
        # Setup shutdown handling
        self._setup_shutdown_handling(
            orchestrator, 
            context_name, 
            auto_cleanup
        )
        
        # Register team context for persistence
        # Only create new context if we're not resuming an existing one
        if context_name:
            if not existing_context:
                self._register_team_context(
                    context_name, 
                    team_config, 
                    agent_configs, 
                    orchestrator
                )
            else:
                self._update_team_context(
                    context_name, 
                    team_config, 
                    agent_configs, 
                    orchestrator
                )
        
        # Start the orchestrator
        print(f"\nStarting orchestrator with {len(team_config.agents)} agents...")
        orchestrator.start(mcp_port=mcp_port)
        
        # Update context with actual session IDs after launch
        if context_name:
            self._update_team_context_session_ids(context_name, orchestrator)
        
        # Display launch status
        self._display_launch_status(team_config, agent_configs, mcp_port, debug, task, orchestrator)
        
        # Wait for interrupt
        try:
            while orchestrator.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            # Cleanup
            self.signal_handler.trigger_shutdown()
            self.signal_handler.restore_signal_handlers()
        
        return True
    
    def _prepare_agent_configs(
        self,
        team_config: Any,
        context_name: str,
        context_details: Optional[ContextDetails] = None,
        model_override: Optional[str] = None,
        agent_model_overrides: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Prepare agent configurations"""
        agent_configs = {}

        context_agent_infos = {}
        if context_details and context_details.agents:
            for context_agent_info in context_details.agents:
                context_agent_infos[context_agent_info.name] = context_agent_info

        for agent_config in team_config.agents:
            session_id = None
            if agent_config.name in context_agent_infos:
                session_id = context_agent_infos[agent_config.name].session_id

            # Determine model to use
            model = None
            if agent_model_overrides and agent_config.name in agent_model_overrides:
                model = agent_model_overrides[agent_config.name]
            elif model_override:
                model = model_override
            elif agent_config.model:
                model = agent_config.model
            elif team_config.settings.get("default_model"):
                model = team_config.settings.get("default_model")
            elif context_agent_infos.get(agent_config.name) and context_agent_infos[agent_config.name].model:
                model = context_agent_infos[agent_config.name].model
            elif not model:
                model = None
            
            agent_name_sanitized = agent_config.name.lower().replace(" ", "-")
            if context_name:
                claude_instance = f"{context_name}-{agent_name_sanitized}"
            else:
                claude_instance = agent_name_sanitized
            
            agent_configs[agent_config.name] = {
                "name": agent_config.name,
                "instance_name": claude_instance,
                "role": agent_config.role,
                "model": model,
                "prompt": agent_config.prompt,
                "prompt_file": agent_config.prompt_file,
                "session_id": session_id,
            }

        return agent_configs
    
    def _register_agents(
        self,
        team_config: Any,
        agent_configs: Dict[str, Dict[str, Any]],
        orchestrator: Any,
        task: Optional[str]
    ) -> None:
        """Register agents with the orchestrator"""
        for i, agent_config in enumerate(team_config.agents):
            # Get prepared config
            prepared_config = agent_configs[agent_config.name]
            
            # Create agent prompt with task injection for Architect
            # FIXME: specify coordinator
            prompt = agent_config.prompt
            if task and agent_config.name.lower() == "architect":
                task_context = f"\n\nInitial task from user: {task}"
                prompt += task_context
                print(f"Task injected into Architect prompt: {task}")
            
            # Check if we have session info for resume
            session_id = prepared_config.get("session_id", None)
            
            agent = orchestrator.register_agent(
                name=agent_config.name, 
                session_id=session_id,
                system_prompt=prompt,
                working_dir=None
            )
            
            # Update agent config with pane index for team context
            agent_configs[agent_config.name]["pane_index"] = agent.pane_index
    
    def _setup_shutdown_handling(
        self,
        orchestrator: Any,
        context_name: Optional[str],
        auto_cleanup: bool
    ) -> None:
        """Setup graceful shutdown handling"""
        self.signal_handler.clear_tasks()
        
        # Register shutdown tasks
        self.signal_handler.register_shutdown_task(
            "stop_orchestrator",
            lambda: orchestrator.stop() if orchestrator and orchestrator.running else None,
            critical=False
        )
        
        self.signal_handler.register_shutdown_task(
            "stop_mcp_server",
            lambda: self.mcp_server_manager.stop_server(timeout=1.0)
        )
        
        if auto_cleanup and context_name and self.cleanup_callback:
            def cleanup_context_task():
                print(f"Auto-cleaning context '{context_name}'...")
                try:
                    self.cleanup_callback(context_name, True)
                except Exception as e:
                    print(f"Warning: Failed to auto-cleanup context: {e}")
            
            self.signal_handler.register_shutdown_task(
                "cleanup_context",
                cleanup_context_task,
                critical=False
            )
        
        # Set up signal handlers
        self.signal_handler.setup_signal_handlers()
    
    def _register_team_context(
        self,
        context_name: str,
        team_config: Any,
        agent_configs: Dict[str, Dict[str, Any]],
        orchestrator: Any
    ) -> None:
        """Register team context for persistence"""
        agents = []
        tmux_session = orchestrator.tmux.session_name
        
        # Store agent metadata only (no container names)
        for agent_cfg in agent_configs.values():
            agents.append(TeamContextAgentInfo(
                name=agent_cfg["name"],
                role=agent_cfg["role"],
                model=agent_cfg["model"],
                pane_index=agent_cfg["pane_index"],
                session_id=orchestrator.agents[agent_cfg["name"]].session_id
            ))
        
        # Create team context using persistence service
        self.context_persistence.create_context(
            context_name=context_name,
            agents=agents,
            tmux_session=tmux_session,
            metadata={"team_name": team_config.name}
        )
        
        self.logger.info(f"Team context '{context_name}' registered for persistence")

    def _update_team_context(
        self,
        context_name: str,
        team_config: Any,
        agent_configs: Dict[str, Dict[str, Any]],
        orchestrator: Any
    ) -> None:
        """Update team context with actual session IDs after launch"""
        # Get current context
        context = self.context_persistence.get_context(context_name)
        if not context:
            self.logger.error(f"Could not find context '{context_name}' to update")
            return

        agents = []
        for agent_cfg in agent_configs.values():
            agents.append(TeamContextAgentInfo(
                name=agent_cfg["name"],
                role=agent_cfg["role"],
                model=agent_cfg["model"],
                pane_index=agent_cfg["pane_index"],
                session_id=orchestrator.agents[agent_cfg["name"]].session_id
            ))

        self.context_persistence.update_context(
            context_name=context_name,
            agents=agents,
            tmux_session=orchestrator.tmux.session_name,
            metadata={"team_name": team_config.name}
        )

        self.logger.info(f"Team context '{context_name}' updated")
        
    def _update_team_context_session_ids(
        self,
        context_name: str,
        orchestrator: Any
    ) -> None:
        """Update team context with actual session IDs after launch"""
        # Get current context
        context = self.context_persistence.get_context(context_name)
        if not context:
            self.logger.error(f"Could not find context '{context_name}' to update")
            return
            
        # Update session IDs from orchestrator agents
        updated = False
        for agent_info in context.agents:
            if agent_info.name in orchestrator.agents:
                agent = orchestrator.agents[agent_info.name]
                if agent.session_id:
                    agent_info.session_id = agent.session_id
                    updated = True
                    print(f"  Updated {agent_info.name} with session ID: {agent.session_id}")
        
        # Save updated context
        if updated:
            self.context_persistence.update_context(
                context_name,
                agents=context.agents
            )
            self.logger.info(f"Team context '{context_name}' updated with session IDs")
    
    def _display_launch_status(
        self,
        team_config: Any,
        agent_configs: Dict[str, Dict[str, Any]],
        mcp_port: int,
        debug: bool,
        task: Optional[str],
        orchestrator: Any
    ) -> None:
        """Display rich status output after launch"""
        print(f"""
============================================================
Enhanced Team Launch - {team_config.name}
============================================================

✓ Team launched successfully!
✓ MCP server running on port {mcp_port}
✓ Debug mode: {'enabled' if debug else 'disabled'}

Team Layout: {'Auto-selected based on terminal size' if len(team_config.agents) == 5 else 'Default layout'}
  • Smart layout detection for 5-agent teams
  • Adaptive layout based on terminal dimensions

Team Members & Models:
""")
        for agent_cfg in agent_configs.values():
            print(f"  • {agent_cfg['name']} ({agent_cfg['role']}) - Model: {agent_cfg['model']}")
        
        print(f"""
Capabilities:
  • Read: Full codebase access (src/, tests/, docs/)
  • Write: Limited to .temp/ directory for experiments
  • Execute: Tests and development commands
  • MCP Communication: Inter-agent messaging

{f"Initial Task: {task}" if task else "The team will self-organize and identify improvements."}

Tmux session: {orchestrator.tmux.session_name}
Attach with: tmux attach -t {orchestrator.tmux.session_name}

Press Ctrl+C to stop
""")