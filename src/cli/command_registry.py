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
        self.aliases: Dict[str, str] = {}
        self._register_commands()
        self._register_aliases()
    
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
    
    def _register_aliases(self) -> None:
        """Register command aliases"""
        # Short aliases for common commands
        self.aliases["ls"] = "list"
        self.aliases["rm"] = "clean"
    
    def setup_parser(self, parser: ArgumentParser) -> None:
        """Set up argument parser with all commands"""
        subparsers = parser.add_subparsers(
            dest="command",
            help="Available commands"
        )
        
        # Register main commands
        for cmd in self.commands.values():
            subparser = subparsers.add_parser(
                cmd.name,
                help=cmd.help
            )
            cmd.add_arguments(subparser)
        
        # Register aliases
        for alias, target in self.aliases.items():
            if target in self.commands:
                cmd = self.commands[target]
                subparser = subparsers.add_parser(
                    alias,
                    help=f"{cmd.help} (alias for {target})"
                )
                cmd.add_arguments(subparser)
    
    def execute_command(self, args, manager) -> int:
        """Execute the specified command"""
        # Resolve alias to actual command
        command_name = args.command
        if command_name in self.aliases:
            command_name = self.aliases[command_name]
        
        if command_name in self.commands:
            cmd = self.commands[command_name]
            
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