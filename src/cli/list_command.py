"""
List Command

Lists all registered team contexts.
"""
from argparse import ArgumentParser, Namespace
from typing import Dict

from .base_command import BaseCommand


class ListCommand(BaseCommand):
    """Command to list all team contexts"""
    
    @property
    def name(self) -> str:
        return "list"
    
    @property
    def help(self) -> str:
        return "List all team contexts"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--detailed", "-d",
            action="store_true",
            help="Show detailed information"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        contexts = manager.list_contexts()
        
        if args.detailed:
            for context in contexts.values():
                self._print_context_details(context)
                print()
        else:
            self._print_sessions_table(contexts)
        
        return 0
    
    def _print_sessions_table(self, contexts: Dict[str, any]) -> None:
        """Print sessions in a formatted table"""
        if not contexts:
            print("No team contexts found")
            return

        print(
            f"\n{'Session Name':<25} {'Containers':<12} "
            f"{'Running':<8} {'Tmux':<15} {'Created':<20}"
        )
        print("-" * 85)

        for context_name, context in sorted(contexts.items()):
            tmux_status = "✓" if context.tmux_session else "-"
            created = context.created[:19] if context.created else "Unknown"

            print(
                f"{context_name:<25} {context.total_containers:<12} "
                f"{context.running_containers:<8} {tmux_status:<15} {created:<20}"
            )
    
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