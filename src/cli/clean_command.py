"""
Clean Command

Cleans up team contexts and their resources.
"""
from argparse import ArgumentParser, Namespace

from .base_command import BaseCommand


class CleanCommand(BaseCommand):
    """Command to clean up a context"""
    
    @property
    def name(self) -> str:
        return "clean"
    
    @property
    def help(self) -> str:
        return "Clean up a context"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "context_name",
            help="Name of the context"
        )
        parser.add_argument(
            "--force", "-f",
            action="store_true",
            help="Skip confirmation prompt"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        success = manager.cleanup_context(args.context_name, args.force)
        return 0 if success else 1