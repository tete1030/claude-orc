"""
Shared configuration for Claude launcher
"""

import os
import shlex
from typing import List, Optional


class ClaudeLauncherConfig:
    """Centralized configuration for Claude launching"""
    
    # Base Docker script path
    DOCKER_SCRIPT = "../scripts/docker-claude-code.sh"
    
    @classmethod
    def build_command(cls, agent_name: str, session_id: str, system_prompt: str, 
                     mcp_config_path: Optional[str] = None) -> List[str]:
        """Build the Claude launch command as a list of arguments"""
        cmd = [
            "env",
            f"CLAUDE_INSTANCE={agent_name}",
            "CLAUDE_CONTAINER_MODE=isolated",
            cls.DOCKER_SCRIPT,
            "run",
            "--session-id", session_id,
            "--append-system-prompt", system_prompt
        ]
        
        if mcp_config_path:
            cmd.extend(["--mcp-config", mcp_config_path, "--debug"])
            
        return cmd
    
    @classmethod
    def build_command_string(cls, agent_name: str, session_id: str, system_prompt: str,
                           mcp_config_path: Optional[str] = None) -> str:
        """Build the command as a shell-ready string"""
        # Build the base command
        cmd_parts = [
            "env",
            f"CLAUDE_INSTANCE={agent_name}",
            "CLAUDE_CONTAINER_MODE=isolated",
            cls.DOCKER_SCRIPT,
            "run",
            "--session-id", session_id,
            "--append-system-prompt", shlex.quote(system_prompt)
        ]
        
        if mcp_config_path:
            cmd_parts.extend(["--mcp-config", mcp_config_path, "--debug"])
            
        return " ".join(cmd_parts)
    
    @classmethod
    def verify_script_exists(cls) -> bool:
        """Verify the Docker script exists"""
        if os.path.exists(cls.DOCKER_SCRIPT):
            return True
            
        # Try from orchestrator directory
        orchestrator_script = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "..", 
            cls.DOCKER_SCRIPT
        )
        return os.path.exists(orchestrator_script)