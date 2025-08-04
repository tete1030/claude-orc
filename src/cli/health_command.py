"""
Health Command

Performs health checks on team contexts.
"""
import json
from argparse import ArgumentParser, Namespace

from .base_command import BaseCommand


class HealthCommand(BaseCommand):
    """Command to check context health"""
    
    @property
    def name(self) -> str:
        return "health"
    
    @property
    def help(self) -> str:
        return "Check context health"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "context_name",
            help="Name of the context"
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        health = manager.health_check_context(args.context_name)
        
        if args.json:
            print(json.dumps(health, indent=2))
        else:
            if "error" in health:
                print(health["error"])
                return 1
            else:
                print(f"Context: {health['context_name']}")
                print(f"Overall health: {health['overall_health']}")

                if health["issues"]:
                    print("\nIssues:")
                    for issue in health["issues"]:
                        print(f"  - {issue}")

                print(f"\nContainers: {len(health['containers'])}")
                for name, container_health in health["containers"].items():
                    status_icon = "🟢" if container_health["status"] == "healthy" else "🔴"
                    print(f"  {status_icon} {name}: {container_health['status']}")
        
        return 0 if health.get("overall_health") == "healthy" else 1