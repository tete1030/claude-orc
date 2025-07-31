"""
Tmux Manager Module
Handles all tmux operations for the orchestrator
"""

import subprocess
import logging
import time
import shlex
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .simple_launcher import SimpleLauncher


@dataclass
class TmuxPane:
    """Represents a tmux pane"""
    index: int
    width: int
    height: int
    active: bool
    title: Optional[str] = None


class TmuxManager:
    """Manages tmux sessions and panes for agents"""
    
    def __init__(self, session_name: str = "claude-agents"):
        self.session_name = session_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.simple_launcher = SimpleLauncher(self)
        
    def session_exists(self) -> bool:
        """Check if tmux session exists"""
        try:
            result = self._run_command(["tmux", "has-session", "-t", self.session_name], 
                                     check=False, capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
            
    def create_session(self, num_panes: int = 2) -> bool:
        """Create tmux session with specified number of panes"""
        try:
            # Kill existing session if any
            if self.session_exists():
                self.kill_session()
                time.sleep(0.5)
            
            # Create new session (detached) with a shell
            self._run_command(["tmux", "new-session", "-d", "-s", self.session_name, "bash"])
            
            # Create additional panes with shells
            for _ in range(1, num_panes):
                self._run_command(["tmux", "split-window", "-h", "-t", f"{self.session_name}:0", "bash"])
                
            # Even out pane sizes
            if num_panes > 1:
                self._run_command(["tmux", "select-layout", "-t", f"{self.session_name}:0", 
                                 "even-horizontal"])
            
            self.logger.info(f"Created tmux session '{self.session_name}' with {num_panes} panes")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create tmux session: {e}")
            return False
            
    def send_to_pane(self, pane_index: int, command: str) -> bool:
        """Send command to specific pane"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Send command followed by Enter key
            self._run_command(["tmux", "send-keys", "-t", target, command])
            self._run_command(["tmux", "send-keys", "-t", target, "Enter"])
            
            self.logger.debug(f"Sent to pane {pane_index}: {command[:50]}...")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to send to pane {pane_index}: {e}")
            return False
            
    def type_in_pane(self, pane_index: int, text: str) -> bool:
        """Type text in pane without pressing Enter"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Send text without Enter
            self._run_command(["tmux", "send-keys", "-t", target, text])
            
            self.logger.debug(f"Typed in pane {pane_index}: {text[:50]}...")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to type in pane {pane_index}: {e}")
            return False
            
    def send_command(self, pane_index: int, command: str) -> bool:
        """Send a command to pane and execute it with proper timing
        
        Args:
            pane_index: Index of the pane
            command: Command to send
        """
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # First send the command text
            self._run_command(["tmux", "send-keys", "-t", target, command])
            # Then send Enter
            self._run_command(["tmux", "send-keys", "-t", target, "Enter"])
            
            self.logger.debug(f"Sent command to pane {pane_index}: {command[:50]}...")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to send command to pane {pane_index}: {e}")
            return False
            
    def capture_pane(self, pane_index: int, history_limit: int = 0) -> Optional[str]:
        """Capture current content of pane
        
        Args:
            pane_index: Index of the pane to capture
            history_limit: Number of lines to capture from history (0 = visible only, -1 = all)
        """
        try:
            target = f"{self.session_name}:0.{pane_index}"
            cmd = ["tmux", "capture-pane", "-t", target, "-p"]
            
            if history_limit != 0:
                cmd.extend(["-S", str(history_limit)])
                
            result = self._run_command(cmd, capture_output=True, text=True)
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to capture pane {pane_index}: {e}")
            return None
            
    def list_panes(self) -> List[TmuxPane]:
        """List all panes in session"""
        try:
            result = self._run_command([
                "tmux", "list-panes", "-t", self.session_name, 
                "-F", "#{pane_index}:#{pane_width}:#{pane_height}:#{pane_active}"
            ], capture_output=True, text=True)
            
            panes = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        panes.append(TmuxPane(
                            index=int(parts[0]),
                            width=int(parts[1]),
                            height=int(parts[2]),
                            active=parts[3] == '1'
                        ))
                    
            return panes
            
        except subprocess.CalledProcessError:
            return []
            
    def set_pane_title(self, pane_index: int, title: str) -> bool:
        """Set pane title for identification"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Enable pane border status for the whole window
            self._run_command(["tmux", "set-option", "-t", f"{self.session_name}:0", 
                             "pane-border-status", "top"])
            
            # Use select-pane to set the actual pane title
            self._run_command(["tmux", "select-pane", "-t", target, 
                             "-T", title])
            
            return True
            
        except subprocess.CalledProcessError:
            return False
            
    def kill_session(self) -> bool:
        """Kill the tmux session"""
        try:
            self._run_command(["tmux", "kill-session", "-t", self.session_name])
            self.logger.info(f"Killed tmux session '{self.session_name}'")
            return True
            
        except subprocess.CalledProcessError:
            return False
            
    def launch_claude_in_pane(self, pane_index: int, agent_name: str,
                            agent_prompt: str, working_dir: Optional[str] = None,
                            claude_bin: Optional[str] = None, mcp_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Launch Claude in specific pane with given configuration
        
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            # Change directory if specified
            if working_dir:
                self.send_to_pane(pane_index, f"cd {shlex.quote(working_dir)}")
                time.sleep(0.5)
            
            # Use simple launcher to get session ID
            session_id = self.simple_launcher.launch_agent(
                pane_index=pane_index, 
                agent_name=agent_name, 
                system_prompt=agent_prompt, 
                mcp_config=mcp_config
            )
            
            if session_id:
                self.logger.info(f"Successfully launched Claude in pane {pane_index} with session {session_id}")
            else:
                self.logger.error(f"Failed to launch Claude in pane {pane_index}")
                
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to launch Claude in pane {pane_index}: {e}")
            return None
    
    def _run_command(self, cmd: List[str], check: bool = True, 
                    capture_output: bool = False, text: bool = False) -> subprocess.CompletedProcess:
        """Run command with error handling"""
        return subprocess.run(cmd, check=check, capture_output=capture_output, text=text)