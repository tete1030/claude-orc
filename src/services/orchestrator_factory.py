"""
Orchestrator Factory - Create properly configured orchestrators without monkey-patching
"""
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from src.orchestrator import Orchestrator, OrchestratorConfig
from src.orchestrator_enhanced import EnhancedOrchestrator
import shlex

@dataclass
class OrchestratorOptions:
    """Options for creating an orchestrator"""
    context_name: str
    orchestrator_type: str = "enhanced"
    poll_interval: float = 0.5
    force: bool = False
    layout_config: Optional[Dict[str, Any]] = None
    debug: bool = False


class ConfigurableTmuxManager:
    """Wrapper for TmuxManager that accepts configuration without monkey-patching"""
    
    def __init__(self, tmux_manager, force: bool = False, layout_config: Optional[Dict[str, Any]] = None):
        self._tmux = tmux_manager
        self._force = force
        self._layout_config = layout_config
        
        # Copy all attributes from the original tmux manager
        for attr in dir(tmux_manager):
            if not attr.startswith('_') and attr != 'create_session':
                setattr(self, attr, getattr(tmux_manager, attr))
    
    def create_session(self, num_panes: int, force: Optional[bool] = None, layout: Optional[Dict[str, Any]] = None):
        """Create session with configured defaults"""
        if force is None:
            force = self._force
        if layout is None:
            layout = self._layout_config
            
        return self._tmux.create_session(num_panes, force=force, layout=layout)


class ConfigurableClaudeLauncher:
    """Wrapper for ClaudeLauncherConfig that handles model configuration"""
    
    def __init__(self, launcher_config_class, agent_configs: Dict[str, Dict[str, Any]], context_name: str = None, debug: bool = False):
        self._launcher_class = launcher_config_class
        self._agent_configs = agent_configs
        self._context_name = context_name or "default"
        self._debug = debug
        self._original_build = launcher_config_class.build_command_string
    
    def build_command_string(self, instance_name: str, session_id: str, system_prompt: str, resume: bool, mcp_config_path: Optional[str] = None) -> str:
        """Build command with proper configuration"""
        # Find the agent config
        agent_config = None
        agent_name = None
        for name, config in self._agent_configs.items():
            if config.get("name", name) == instance_name:
                agent_config = config
                agent_name = name
                break

        if not agent_config:
            # No special config, just use default
            return self._original_build(instance_name, session_id, system_prompt, resume, mcp_config_path)
        
        # Build base command
        base_cmd = self._original_build(instance_name, session_id, system_prompt, resume, mcp_config_path)
        
        # Build ccdk parameters that need to go BEFORE "run"
        ccdk_params = []

        # Add model if specified
        model = agent_config.get("model")
        if model:
            ccdk_params.extend(["-m", shlex.quote(model)])
        
        # Add context (ccdk accepts this)
        ccdk_params.extend(["--context", shlex.quote(self._context_name)])
        
        # Add role (ccdk accepts this)
        agent_role = agent_config.get("role", agent_name or "agent")
        ccdk_params.extend(["--role", shlex.quote(agent_role)])

        # Insert ccdk parameters before "run"
        if ccdk_params:
            params_str = " ".join(ccdk_params)
            base_cmd = base_cmd.replace("ccdk run", f"ccdk run {params_str}", 1)
        
        return base_cmd


class OrchestratorFactory:
    """Factory for creating configured orchestrators without monkey-patching"""
    
    def __init__(self, layout_service=None):
        self.logger = logging.getLogger(__name__)
        self.layout_service = layout_service
    
    def create_orchestrator(
        self,
        options: OrchestratorOptions,
        team_config: Optional[Any] = None
    ) -> Orchestrator:
        """
        Create a properly configured orchestrator.
        
        Args:
            options: Configuration options
            team_config: Optional team configuration for advanced setup
            
        Returns:
            Configured orchestrator instance
        """
        # Create base configuration
        config = OrchestratorConfig(
            context_name=options.context_name,
            poll_interval=options.poll_interval
        )
        
        # Create appropriate orchestrator type
        if options.orchestrator_type == "enhanced":
            orchestrator = EnhancedOrchestrator(config)
        else:
            orchestrator = Orchestrator(config)
        
        # Configure tmux manager if layout is specified
        if options.layout_config or options.force:
            orchestrator.tmux = ConfigurableTmuxManager(
                orchestrator.tmux,
                force=options.force,
                layout_config=options.layout_config
            )
        
        self.logger.info(
            f"Created {options.orchestrator_type} orchestrator for context '{options.context_name}'"
        )
        
        return orchestrator
    
    def configure_launcher(
        self,
        orchestrator: Orchestrator,
        agent_configs: Dict[str, Dict[str, Any]],
        debug: bool = False
    ):
        """
        Configure the launcher for model and debug settings.
        
        Args:
            orchestrator: The orchestrator to configure
            agent_configs: Agent configuration mapping
            debug: Whether to enable debug mode
        """
        # Import here to avoid circular dependency
        from src.claude_launcher_config import ClaudeLauncherConfig
        
        # Replace the class method with our configurable version
        configurable_launcher = ConfigurableClaudeLauncher(
            ClaudeLauncherConfig,
            agent_configs,
            context_name=orchestrator.config.context_name,
            debug=debug
        )
        
        # Replace the class method to add agent-specific configuration
        # This allows per-agent model and debug settings without modifying the base class
        ClaudeLauncherConfig.build_command_string = configurable_launcher.build_command_string
        
        self.logger.info("Configured launcher for model assignments")
    
    def create_configured_orchestrator(
        self,
        options: OrchestratorOptions,
        team_config: Any,
        agent_configs: Dict[str, Dict[str, Any]]
    ) -> Orchestrator:
        """
        Create a fully configured orchestrator with all settings.
        
        This is the main entry point that combines all configuration.
        
        Args:
            options: Orchestrator options
            team_config: Team configuration
            agent_configs: Agent configurations with models
            
        Returns:
            Fully configured orchestrator
        """
        # Detect layout if service available and not specified
        if self.layout_service and not options.layout_config:
            num_agents = len(agent_configs)
            options.layout_config = self.layout_service.detect_smart_layout(num_agents)
        
        # Create orchestrator
        orchestrator = self.create_orchestrator(options, team_config)
        
        # Configure launcher if needed
        if agent_configs:
            self.configure_launcher(orchestrator, agent_configs, options.debug)
        
        return orchestrator