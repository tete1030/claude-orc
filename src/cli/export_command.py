"""
Export Command

Exports context configuration to a file.
"""
from argparse import ArgumentParser, Namespace

from .base_command import BaseCommand


class ExportCommand(BaseCommand):
    """Command to export context configuration"""
    
    @property
    def name(self) -> str:
        return "export"
    
    @property
    def help(self) -> str:
        return "Export context configuration"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "context_name",
            help="Name of the context"
        )
        parser.add_argument(
            "output_file",
            help="Output file path"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        success = manager.export_session_config(args.context_name, args.output_file)
        return 0 if success else 1