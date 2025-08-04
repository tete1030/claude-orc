"""
Base Command Class

Provides the foundation for all CLI commands in the orchestrator system.
"""
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Optional, Dict, Any


class BaseCommand(ABC):
    """Abstract base class for CLI commands"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name used in CLI"""
        pass
    
    @property
    @abstractmethod
    def help(self) -> str:
        """Help text for the command"""
        pass
    
    @abstractmethod
    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Add command-specific arguments to the parser.
        
        Args:
            parser: ArgumentParser instance to add arguments to
        """
        pass
    
    @abstractmethod
    def execute(self, args: Namespace, manager: Any) -> int:
        """
        Execute the command.
        
        Args:
            args: Parsed command line arguments
            manager: SessionCLIManager instance
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass
    
    def validate_args(self, args: Namespace) -> Optional[str]:
        """
        Validate command arguments.
        
        Args:
            args: Parsed arguments
            
        Returns:
            Error message if validation fails, None if valid
        """
        return None
    
    def get_subcommands(self) -> Optional[Dict[str, 'BaseCommand']]:
        """
        Get subcommands for this command.
        
        Returns:
            Dictionary mapping subcommand names to command instances,
            or None if no subcommands
        """
        return None