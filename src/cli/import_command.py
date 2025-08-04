"""
Import Command

Imports context configuration from a file.
"""
from argparse import ArgumentParser, Namespace

from .base_command import BaseCommand


class ImportCommand(BaseCommand):
    """Command to import context configuration"""
    
    @property
    def name(self) -> str:
        return "import"
    
    @property
    def help(self) -> str:
        return "Import context configuration"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "config_file",
            help="Configuration file path"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        success = manager.import_session_config(args.config_file)
        return 0 if success else 1