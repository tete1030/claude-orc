"""
Info Command

Shows detailed information about a specific context.
"""
from argparse import ArgumentParser, Namespace

from .base_command import BaseCommand


class InfoCommand(BaseCommand):
    """Command to show detailed context information"""
    
    @property
    def name(self) -> str:
        return "info"
    
    @property
    def help(self) -> str:
        return "Show detailed context information"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "context_name",
            help="Name of the context"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        context = manager.get_context_details(args.context_name)
        if context:
            self._print_context_details(context)
            return 0
        else:
            print(f"Context '{args.context_name}' not found")
            return 1
    
    def _print_context_details(self, context) -> None:
        """Print detailed session information"""
        print(f"\nSession: {context.name}")
        print(f"Created: {context.created}")
        print(f"Containers: {context.total_containers} total, {context.running_containers} running")

        if context.tmux_session:
            print(f"Tmux session: {context.tmux_session}")
        else:
            print("Tmux session: None")

        print("\nContainers:")
        for container in context.containers:
            status_icon = "🟢" if container.running else "🔴"
            print(f"  {status_icon} {container.name}")
            print(f"    Role: {container.agent_role}")
            print(f"    Status: {container.status}")
            print(f"    Created: {container.created}")