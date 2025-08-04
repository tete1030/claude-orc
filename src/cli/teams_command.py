"""
Teams Command

Manages team configurations.
"""
from argparse import ArgumentParser, Namespace
from typing import Dict, List, Any

from .base_command import BaseCommand


class TeamsListSubcommand(BaseCommand):
    """Subcommand to list available teams"""
    
    @property
    def name(self) -> str:
        return "list"
    
    @property
    def help(self) -> str:
        return "List available team configurations"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        # No additional arguments
        pass
    
    def execute(self, args: Namespace, manager) -> int:
        teams = manager.list_teams()
        self._print_teams_table(teams)
        return 0
    
    def _print_teams_table(self, teams: List[Dict[str, Any]]) -> None:
        """Print teams in a formatted table"""
        if not teams:
            print("No team configurations found")
            return

        print(f"\n{'Team Name':<20} {'Config Name':<25} {'Agents':<8} {'Directory':<15}")
        print("-" * 75)

        for team in sorted(teams, key=lambda t: t["name"]):
            print(
                f"{team['team_name']:<20} {team['name']:<25} "
                f"{team['agents']:<8} {team['directory']:<15}"
            )


class TeamsCommand(BaseCommand):
    """Command for team configuration management"""
    
    def __init__(self):
        self.subcommands = {
            "list": TeamsListSubcommand()
        }
    
    @property
    def name(self) -> str:
        return "teams"
    
    @property
    def help(self) -> str:
        return "Team configuration management"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        subparsers = parser.add_subparsers(
            dest="teams_command",
            help="Teams commands"
        )
        
        for cmd in self.subcommands.values():
            subparser = subparsers.add_parser(cmd.name, help=cmd.help)
            cmd.add_arguments(subparser)
    
    def execute(self, args: Namespace, manager) -> int:
        if args.teams_command in self.subcommands:
            return self.subcommands[args.teams_command].execute(args, manager)
        else:
            # Print help if no subcommand
            return 1
    
    def get_subcommands(self) -> Dict[str, BaseCommand]:
        return self.subcommands