"""
Resume Command

Resumes an existing team context with proper session handling.
"""
from argparse import ArgumentParser, Namespace
from typing import Dict, List

from .base_command import BaseCommand


class ResumeCommand(BaseCommand):
    """Command to resume an existing team context"""
    
    @property
    def name(self) -> str:
        return "resume"
    
    @property
    def help(self) -> str:
        return "Resume an existing team context"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "context",
            help="Context name to resume"
        )
        parser.add_argument(
            "-f", "--force",
            action="store_true",
            help="Force kill existing tmux session if it exists"
        )
        parser.add_argument(
            "-m", "--model",
            help="Override all agents' models"
        )
        parser.add_argument(
            "--agent-model",
            action="append",
            default=[],
            help="Override specific agent model (format: Agent=model)"
        )
        parser.add_argument(
            "-d", "--debug",
            action="store_true",
            help="Enable debug mode"
        )
        parser.add_argument(
            "-t", "--task",
            help="New task for the team (will be added to Architect prompt)"
        )
    
    def execute(self, args: Namespace, manager) -> int:
        # Parse agent model overrides
        agent_model_overrides = self._parse_agent_model_overrides(args.agent_model)
        
        # Check if context exists
        context = manager.context_persistence.get_context(args.context)
        if not context:
            print(f"Error: Context '{args.context}' not found")
            print("\nAvailable contexts:")
            contexts = manager.list_contexts()
            if contexts:
                for ctx_name in contexts:
                    print(f"  - {ctx_name}")
            else:
                print("  No contexts found")
            print("\nUse 'ccorc launch <team>' to create a new context")
            return 1
        
        # Get team name from context
        team_name = context.metadata.get("team_name")
        if not team_name:
            print(f"Error: Context '{args.context}' does not have associated team configuration")
            return 1
        
        print(f"Resuming context '{args.context}' with team '{team_name}'")
        
        # Resume with fork checking always enabled
        try:
            success = manager.resume_team(
                context_name=args.context,
                force=args.force,
                check_forks=True,  # Always check for forks
                fresh_sessions=False,  # Never use fresh sessions for resume
                model_override=args.model,
                agent_model_overrides=agent_model_overrides,
                debug=args.debug,
                task=args.task,
                auto_cleanup=False,  # No auto cleanup for resume
            )
            
            return 0 if success else 1
        except Exception as e:
            print(f"Error resuming context: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
    
    def _parse_agent_model_overrides(self, overrides_list: List[str]) -> Dict[str, str]:
        """Parse agent model override arguments"""
        overrides = {}
        for override in overrides_list:
            if "=" not in override:
                print(f"Warning: Invalid override format '{override}', expected Agent=model")
                continue
            agent, model = override.split("=", 1)
            overrides[agent.strip()] = model.strip()
        return overrides