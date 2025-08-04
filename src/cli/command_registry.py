"""
Command Registry

Central registry for all CLI commands.
"""
from typing import Dict, Type
from argparse import ArgumentParser

from .base_command import BaseCommand
from .list_command import ListCommand
from .info_command import InfoCommand
from .health_command import HealthCommand
from .clean_command import CleanCommand
from .export_command import ExportCommand
from .import_command import ImportCommand
from .teams_command import TeamsCommand
from .launch_command import LaunchCommand


class CommandRegistry:
    """Registry for all available commands"""
    
    def __init__(self):
        self.commands: Dict[str, BaseCommand] = {}
        self._register_commands()
    
    def _register_commands(self) -> None:
        """Register all available commands"""
        command_classes = [
            ListCommand,
            InfoCommand,
            HealthCommand,
            CleanCommand,
            ExportCommand,
            ImportCommand,
            TeamsCommand,
            LaunchCommand,
        ]
        
        for cmd_class in command_classes:
            cmd = cmd_class()
            self.commands[cmd.name] = cmd
    
    def setup_parser(self, parser: ArgumentParser) -> None:
        """Set up argument parser with all commands"""
        subparsers = parser.add_subparsers(
            dest="command",
            help="Available commands"
        )
        
        for cmd in self.commands.values():
            subparser = subparsers.add_parser(
                cmd.name,
                help=cmd.help
            )
            cmd.add_arguments(subparser)
    
    def execute_command(self, args, manager) -> int:
        """Execute the specified command"""
        if args.command in self.commands:
            cmd = self.commands[args.command]
            
            # Validate arguments
            error = cmd.validate_args(args)
            if error:
                print(f"Error: {error}")
                return 1
            
            # Execute command
            return cmd.execute(args, manager)
        else:
            return 1
    
    def get_command(self, name: str) -> BaseCommand:
        """Get a command by name"""
        return self.commands.get(name)