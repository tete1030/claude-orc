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
            "team",
            help="Team configuration name"
        )
        parser.add_argument(
            "name",
            nargs="?",
            help="Context name (defaults to team name)"
        )
        parser.add_argument(
            "-m", "--model",
            help="Override all agents' models"
        )
        parser.add_argument(
            "--agent-model",
            action="append",
            default=[],
            help="Override specific agent model (format: Agent=model)"
        )
        parser.add_argument(
            "-f", "--force",
            action="store_true",
            help="Force kill existing session if it exists"
        )
        parser.add_argument(
            "-d", "--debug",
            action="store_true",
            help="Enable debug mode"
        )
        parser.add_argument(
            "-t", "--task",
            help="Initial task for the team (will be added to Architect prompt)"
        )
        parser.add_argument(
            "--rm",
            action="store_true",
            dest="auto_cleanup",
            default=False,
            help="Disable automatic context cleanup on exit"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        # Parse agent model overrides
        agent_model_overrides = self._parse_agent_model_overrides(args.agent_model)
        
        # Launch the team
        success = manager.launch_team(
            team_name=args.team,
            context_name=args.name,  # Will be None if not provided, handled by launch_team
            model_override=args.model,
            agent_model_overrides=agent_model_overrides,
            force=args.force,
            debug=args.debug,
            task=args.task,
            auto_cleanup=args.auto_cleanup,
            fresh=True,  # Launch always creates new sessions
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