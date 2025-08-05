"""
Simple Claude launcher with explicit session ID
"""

import subprocess
import time
import os
import logging
import uuid
import json
import shlex
from typing import Optional, Dict, Any
from .claude_launcher_config import ClaudeLauncherConfig


class SimpleLauncher:
    """Launches Claude with a pre-generated session ID"""
    
    def __init__(self, tmux_manager):
        self.tmux = tmux_manager
        self.logger = logging.getLogger(__name__)
        self.shared_mcp_dir: Optional[str] = None  # Will be set by orchestrator
        
    def launch_agent(self,
                    pane_index: int,
                    agent_name: str,
                    system_prompt: str,
                    mcp_config: Optional[Dict[str, Any]] = None,
                    mcp_config_path: Optional[str] = None,
                    working_dir: Optional[str] = None,
                    session_id: Optional[str] = None
                    ) -> Optional[str]:
        """Launch agent with explicit session ID and return it
        
        Args:
            pane_index: Tmux pane index
            agent_name: Name of the agent
            system_prompt: System prompt to use
            mcp_config: MCP configuration dict
            mcp_config_path: Path to MCP config file
            working_dir: Working directory to change to
            session_id: Session ID to resume
            
        Returns:
            Session ID if successful, None otherwise
        """
        resume = False
        # Handle session ID logic
        if session_id:
            resume = True
            self.logger.info(f"Resuming {agent_name} with session ID: {session_id}")
        else:
            # Generate new session ID if not provided
            session_id = str(uuid.uuid4())
            self.logger.info(f"Launching {agent_name} with new session ID: {session_id}")
        
        # Verify Docker script exists
        if not ClaudeLauncherConfig.verify_script_exists():
            self.logger.error("Could not find Docker Claude script")
            return None
            
        # Create MCP config file if provided
        if mcp_config and not mcp_config_path:
            mcp_config_path = self._create_mcp_config_file(agent_name, mcp_config)
            
        # Change to working directory if specified
        if working_dir:
            self.tmux._run_command([
                "tmux", "send-keys", "-t",
                f"{self.tmux.session_name}:0.{pane_index}",
                f"cd {shlex.quote(working_dir)}", "Enter"
            ])
            time.sleep(0.1)
            
        # Build command based on resume vs new session
        cmd = ClaudeLauncherConfig.build_command_string(
            instance_name=agent_name,
            session_id=session_id,
            system_prompt=system_prompt,
            resume=resume,
            mcp_config_path=mcp_config_path
        )
        
        # Send command to pane
        self.logger.info(f"Sending command: {cmd}")
        
        # Send the command using literal mode to handle special characters
        self.tmux._run_command([
            "tmux", "send-keys", "-t",
            f"{self.tmux.session_name}:0.{pane_index}",
            "-l", cmd
        ])
        # Send Enter separately
        self.tmux._run_command([
            "tmux", "send-keys", "-t",
            f"{self.tmux.session_name}:0.{pane_index}",
            "Enter"
        ])
        
        # Wait for Claude to be ready
        # TODO: remove this stupidity
        if self._wait_for_claude_ready(pane_index, agent_name):
            self.logger.info(f"Successfully launched {agent_name} with session {session_id}")
            if mcp_config_path:
                self.logger.info(f"MCP config: {mcp_config_path}")
            return session_id
        else:
            self.logger.error(f"Failed to launch {agent_name}")
            return None
            
    def _wait_for_claude_ready(self, pane_index: int, agent_name: str, timeout: int = 15) -> bool:
        """Wait for Claude to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            content = self.tmux.capture_pane(pane_index, history_limit=-50)
            if not content:
                time.sleep(0.5)
                continue
                
            # Check for theme selection prompt
            if ("Dark mode" in content and "Light mode" in content and 
                ("Preview" in content or "To change this later" in content)):
                self.logger.info(f"Handling theme selection for {agent_name}")
                self.tmux.send_to_pane(pane_index, "1")  # Select dark mode
                time.sleep(1)
                continue
                
            # Check for trust prompt
            if "Do you trust the files in this folder?" in content:
                self.logger.info(f"Handling trust prompt for {agent_name}")
                self.tmux.send_to_pane(pane_index, "1")
                time.sleep(1)
                continue
                
            # Check for authentication prompt
            if ("Browser didn't open?" in content or 
                "Paste code here if prompted" in content or
                "oauth/authorize" in content):
                self.logger.warning(f"Claude requires authentication for {agent_name}. May need to use a different approach.")
                # Continue waiting to see if it resolves
                
            # Check if Claude is ready
            if any(indicator in content for indicator in [
                "Welcome to Claude Code",  # Remove the ! to handle both versions
                "Tips for getting started:",
                "│ >",  # Box drawing character with prompt
                "claude-code-interactive",
                "Try \"",
                "System Diagnostics"
            ]):
                self.logger.info(f"Claude ready for {agent_name}")
                return True
            
            # Also check for simple prompt without requiring other indicators
            if "│ >" in content or "| >" in content:
                self.logger.info(f"Claude ready for {agent_name} (prompt detected)")
                return True
            
            # Check for MCP errors
            if "Invalid MCP configuration" in content:
                self.logger.error(f"MCP configuration error for {agent_name}")
                # Log the actual error
                lines = content.strip().split('\n')
                for i, line in enumerate(lines):
                    if "Invalid MCP" in line:
                        # Show this line and next few
                        for j in range(i, min(i+5, len(lines))):
                            self.logger.error(f"  {lines[j]}")
                        break
                return False
                    
            time.sleep(0.5)
            
        self.logger.error(f"Timeout waiting for Claude to start for {agent_name}")
        return False
        
    
    def _create_mcp_config_file(self, agent_name: str, config: Dict[str, Any]) -> str:
        """Create temporary MCP config file for agent"""
        # Use shared directory for cross-container access
        if not self.shared_mcp_dir:
            raise ValueError("shared_mcp_dir is not set")
        
        # Ensure directory exists
        os.makedirs(self.shared_mcp_dir, exist_ok=True)
        
        # Write config to file
        config_path = os.path.join(self.shared_mcp_dir, f"mcp_{agent_name}_{uuid.uuid4().hex[:8]}.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_path