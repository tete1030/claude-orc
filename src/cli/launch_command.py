"""
Launch Command

Launches a team configuration.
"""
from argparse import ArgumentParser, Namespace
from typing import Dict, List

from .base_command import BaseCommand


class LaunchCommand(BaseCommand):
    """Command to launch a team configuration"""
    
    @property
    def name(self) -> str:
        return "launch"
    
    @property
    def help(self) -> str:
        return "Launch a team configuration"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--team",
            required=True,
            help="Team configuration name"
        )
        parser.add_argument(
            "--name",
            help="Override context name"
        )
        parser.add_argument(
            "--model",
            help="Override all agents' models"
        )
        parser.add_argument(
            "--agent-model",
            action="append",
            default=[],
            help="Override specific agent model (format: Agent=model)"
        )
        parser.add_argument(
            "--force", "-f",
            action="store_true",
            help="Force kill existing session if it exists"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode"
        )
        parser.add_argument(
            "--task",
            help="Initial task for the team (will be added to Architect prompt)"
        )
        parser.add_argument(
            "--no-auto-cleanup",
            action="store_true",
            help="Disable automatic context cleanup on exit"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        # Parse agent model overrides
        agent_model_overrides = self._parse_agent_model_overrides(args.agent_model)
        
        # Launch the team
        success = manager.launch_team(
            team_name=args.team,
            context_name=args.name,
            model_override=args.model,
            agent_model_overrides=agent_model_overrides,
            force=args.force,
            debug=args.debug,
            task=args.task,
            auto_cleanup=not args.no_auto_cleanup,
        )
        
        return 0 if success else 1
    
    def _parse_agent_model_overrides(self, overrides_list: List[str]) -> Dict[str, str]:
        """Parse agent model override arguments"""
        overrides = {}
        for override in overrides_list:
            if "=" not in override:
                print(f"Warning: Invalid override format '{override}', expected Agent=model")
                continue
            agent, model = override.split("=", 1)
            overrides[agent.strip()] = model.strip()
        return overrides