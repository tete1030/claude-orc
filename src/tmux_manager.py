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
            
            # Configure tmux to show pane titles with agent names
            self._run_command(["tmux", "set-option", "-t", self.session_name, "pane-border-status", "top"])
            
            # Use a format that shows agent name with color based on state
            # The color is stored in @pane_color_code variable
            self._run_command(["tmux", "set-option", "-w", "-t", self.session_name, "pane-border-format", 
                             "#{?@agent_name,#{?pane_active,#[reverse],}#{@pane_color_code}[#{@agent_name}#{?@state_dot,#{@state_dot},}]#[default]#{?@msg_count, (#{@msg_count} msgs),} ,}#{pane_title}"])
            
            # Set pane border colors: blue for all panes
            self._run_command(["tmux", "set-option", "-w", "-t", self.session_name, 
                             "pane-border-style", "fg=blue"])
            self._run_command(["tmux", "set-option", "-w", "-t", self.session_name, 
                             "pane-active-border-style", "fg=blue"])  # Same blue for active
            
            # Enable mouse mode for easy pane switching and scrolling
            self._run_command(["tmux", "set-option", "-g", "mouse", "on"])
            
            # Add keyboard shortcuts for quick pane switching
            # Use Alt+1/2/3 (less likely to conflict)
            for i in range(min(num_panes, 9)):  # Support up to 9 panes
                # Alt+number for quick switching
                self._run_command(["tmux", "bind-key", "-n", f"M-{i+1}", 
                                 f"select-pane -t {self.session_name}:0.{i}"])
                # With prefix (Ctrl+b,1 Ctrl+b,2, etc.) as backup
                self._run_command(["tmux", "bind-key", str(i+1), 
                                 f"select-pane -t {self.session_name}:0.{i}"])
                
            # Add F1/F2/F3 shortcuts for the first 3 panes
            if num_panes >= 1:
                self._run_command(["tmux", "bind-key", "-n", "F1", 
                                 f"select-pane -t {self.session_name}:0.0"])
            if num_panes >= 2:
                self._run_command(["tmux", "bind-key", "-n", "F2", 
                                 f"select-pane -t {self.session_name}:0.1"])
            if num_panes >= 3:
                self._run_command(["tmux", "bind-key", "-n", "F3", 
                                 f"select-pane -t {self.session_name}:0.2"])
            
            # Configure status bar to show agent states
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status", "on"])
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status-interval", "2"])
            
            # We'll update this dynamically, but set initial format
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status-left", 
                             "[Orchestrator] "])
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status-left-length", "20"])
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status-right", 
                             "Agents: Initializing..."])
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status-right-length", "80"])
            
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
            
    def set_pane_title(self, pane_index: int, title: str) -> bool:
        """Set the title of a specific pane"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Set pane title using select-pane -T
            self._run_command(["tmux", "select-pane", "-t", target, "-T", title])
            
            self.logger.info(f"Set pane {pane_index} title to: {title}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to set pane title: {e}")
            return False
            
    def set_pane_agent_name(self, pane_index: int, agent_name: str) -> bool:
        """Store agent name as a custom pane variable"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Set a custom user option to store the agent name
            # This will be used by our hook to prepend to titles
            self._run_command(["tmux", "set-option", "-p", "-t", target, "@agent_name", agent_name])
            
            self.logger.info(f"Set pane {pane_index} agent name to: {agent_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to set pane agent name: {e}")
            return False
    
    def update_status_bar(self, agent_states: Dict[str, str]) -> bool:
        """Update the status bar with agent states"""
        try:
            # Format: Colored single letters to show state visually without emojis
            status_parts = []
            for agent_name, state in agent_states.items():
                # Use tmux color codes for visual indication
                color = {
                    "idle": "#[fg=white]",  # White for better visibility
                    "busy": "#[fg=yellow]", 
                    "writing": "#[fg=cyan]",
                    "error": "#[fg=red,bold]",
                    "quit": "#[fg=colour237]",  # dark gray
                    "unknown": "#[fg=colour245]",  # medium gray
                    "initializing": "#[fg=blue]"
                }.get(state, "#[fg=default]")
                
                # Use first letter of agent name
                short_name = agent_name[0].upper()
                
                # Add colored letter with reset
                status_parts.append(f"{color}{short_name}#[default]")
            
            # Join with spaces and add a label
            status_text = "Agents: " + " ".join(status_parts) if status_parts else "No agents"
            
            # Update the right side of status bar with length limit
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status-right", 
                             status_text])
            # Set reasonable length limit to prevent wrapping
            self._run_command(["tmux", "set-option", "-t", self.session_name, "status-right-length", "30"])
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update status bar: {e}")
            return False
    
    def set_pane_border_color(self, pane_index: int, state: str) -> bool:
        """Set pane state indicator based on agent state"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Define colors for each state (states come in lowercase)
            color_map = {
                "idle": "green",
                "busy": "yellow", 
                "writing": "cyan",
                "error": "red",
                "quit": "colour237",  # dark gray
                "initializing": "blue",  # blue for startup
                "unknown": "colour245"  # medium gray
            }
            
            color = color_map.get(state, "default")
            
            # Store the color code for header text (e.g., "#[fg=green]")
            color_code = f"#[fg={color}]" if color != "default" else "#[default]"
            self._run_command(["tmux", "set-option", "-p", "-t", target, "@pane_color_code", color_code])
            
            # Define state indicator dots (using unicode dots)
            state_dots = {
                "idle": " ✓",        # Check mark (idle/ready)
                "busy": " ●",        # Filled circle (busy)
                "writing": " ✎",     # Pencil (writing)
                "error": " ⚠",       # Warning sign (error)
                "quit": " ✕",        # X mark (quit)
                "initializing": " ◌", # Dotted circle (initializing)
                "unknown": " ?"      # Question mark
            }
            
            dot = state_dots.get(state, " ?")
            
            # Store the state dot indicator
            self._run_command(["tmux", "set-option", "-p", "-t", target, "@state_dot", dot])
            
            # Update pane title to show state
            # Get agent name from pane variable
            try:
                result = self._run_command(["tmux", "show-options", "-p", "-t", target, "@agent_name"])
                if result and "=" in result.stdout:
                    agent_name = result.stdout.strip().split("=", 1)[1]
                    state_label = state.upper()
                    self._run_command(["tmux", "set-option", "-p", "-t", target, 
                                     "@pane_title", f"{agent_name} [{state_label}]"])
            except:
                pass  # Ignore errors in getting agent name
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to set pane state indicator: {e}")
            return False
    
    def get_active_pane_index(self) -> Optional[int]:
        """Get the index of the currently active pane"""
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "-t", self.session_name, "#{pane_index}"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
            return None
        except (subprocess.CalledProcessError, ValueError):
            return None
    
    def update_border_colors_for_states(self, agent_states: Dict[str, tuple]) -> bool:
        """Update border colors to always be blue
        
        Since tmux doesn't support per-pane border colors, we keep borders blue
        and use pane headers to show individual states.
        
        Args:
            agent_states: Dict of agent_name -> (pane_index, state)
        """
        try:
            # Always use blue for borders
            border_color = "blue"
            
            # Set window-level border colors to blue
            self._run_command(["tmux", "set-option", "-w", "-t", self.session_name, 
                             "pane-border-style", f"fg={border_color}"])
            self._run_command(["tmux", "set-option", "-w", "-t", self.session_name, 
                             "pane-active-border-style", f"fg={border_color},bold"])
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update border colors: {e}")
            return False
    
    def update_pane_message_count(self, pane_index: int, msg_count: int) -> bool:
        """Update the message count for a pane"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Set the message count as a pane variable
            self._run_command(["tmux", "set-option", "-p", "-t", target, "@msg_count", str(msg_count)])
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update message count: {e}")
            return False
    
    def set_pane_activity_indicator(self, pane_index: int, is_busy: bool) -> bool:
        """Set activity indicator for a pane"""
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Set the busy indicator as a pane variable (1 for busy, 0 for not)
            self._run_command(["tmux", "set-option", "-p", "-t", target, "@is_busy", "1" if is_busy else "0"])
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to set activity indicator: {e}")
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