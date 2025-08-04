"""
Team Launch Service

Handles the complex process of launching team configurations.
"""
import time
from typing import Dict, List, Optional, Any, Callable

from src.team_config_loader import TeamConfigLoader
from src.team_context_manager import TeamContextAgentInfo
from src.mcp_central_server import CentralMCPServer
from .port_discovery_service import PortDiscoveryService
from .orchestrator_factory import OrchestratorFactory, OrchestratorOptions
from .mcp_server_manager import MCPServerManager
from .signal_handler_service import SignalHandlerService
from .context_persistence_service import ContextPersistenceService


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
    
    def launch_team(
        self,
        team_name: str,
        context_name: Optional[str] = None,
        model_override: Optional[str] = None,
        agent_model_overrides: Optional[Dict[str, str]] = None,
        force: bool = False,
        debug: bool = False,
        task: Optional[str] = None,
        auto_cleanup: bool = True,
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
            context_name = team_config.settings.get("default_context_name", "team-context")
        
        # Check for existing context
        if context_name and self.context_persistence.get_context(context_name) is not None:
            if not force:
                raise ValueError(f"Context '{context_name}' already exists")
            else:
                print(f"Forcing launch of team '{team_name}' to existing context '{context_name}'")
                # Cleanup will be handled elsewhere
        
        print(f"Launching team: {team_config.name}")
        print(f"Context: {context_name}")
        print(f"Agents: {len(team_config.agents)}")
        
        # Prepare agent configurations
        agent_configs = self._prepare_agent_configs(
            team_config, 
            context_name, 
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
        if context_name:
            self._register_team_context(
                context_name, 
                team_config, 
                agent_configs, 
                orchestrator
            )
        
        # Start the orchestrator
        print(f"\nStarting orchestrator with {len(team_config.agents)} agents...")
        orchestrator.start(mcp_port=mcp_port)
        
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
        model_override: Optional[str],
        agent_model_overrides: Optional[Dict[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Prepare agent configurations"""
        agent_configs = {}
        
        for agent_config in team_config.agents:
            # Determine model to use
            model = agent_config.model
            if model_override:
                model = model_override
            elif agent_model_overrides and agent_config.name in agent_model_overrides:
                model = agent_model_overrides[agent_config.name]
            elif not model:
                # Use intelligent model assignment if no explicit model
                model = self._get_intelligent_model(agent_config.name, agent_config.role)
            
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
            }
        
        return agent_configs
    
    def _get_intelligent_model(self, agent_name: str, agent_role: str) -> str:
        """Get default model assignment when none specified"""
        # Return a sensible default without hardcoded role assumptions
        # This should ideally come from configuration
        return "sonnet"  # Default model for all roles
    
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
            prompt = agent_config.prompt or f"You are {agent_config.name}, with role: {agent_config.role}"
            if task and agent_config.name.lower() == "architect":
                task_context = f"\n\nInitial task from user: {task}"
                prompt += task_context
                print(f"Task injected into Architect prompt: {task}")
            
            print(f"Registering agent: {agent_config.name} ({agent_config.role}) - Model: {prepared_config['model']}")
            
            # Register agent with orchestrator
            session_id = f"session_{i}"
            agent = orchestrator.register_agent(agent_config.name, session_id, prompt)
            
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
                pane_index=agent_cfg["pane_index"]
            ))
        
        # Create team context using persistence service
        self.context_persistence.create_context(
            context_name=context_name,
            agents=agents,
            tmux_session=tmux_session,
            metadata={"team_name": team_config.name}
        )
        
        print(f"Team context '{context_name}' registered for persistence")
    
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