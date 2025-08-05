"""
Tmux Manager Module
Handles all tmux operations for the orchestrator
"""

import subprocess
import logging
import time
import shlex
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from .simple_launcher import SimpleLauncher
from .layout_manager import LayoutConfig, TmuxLayoutManager, create_layout, get_layout_for_agent_count


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
        self.layout_manager = TmuxLayoutManager()
        self.current_layout = None
        
    def session_exists(self) -> bool:
        """Check if tmux session exists"""
        try:
            result = self._run_command(["tmux", "has-session", "-t", self.session_name], 
                                     check=False, capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
            
    def create_session(self, num_panes: int = 2, force: bool = False, 
                      layout: Optional[Union[str, Dict, LayoutConfig]] = None) -> bool:
        """Create tmux session with specified number of panes and layout
        
        Args:
            num_panes: Number of panes to create
            force: If True, kill existing session. If False, fail if session exists.
            layout: Layout configuration (string name, dict, or LayoutConfig object).
                   Defaults to horizontal layout if not specified.
        """
        try:
            # Check for existing session
            session_exists = self.session_exists()
            if session_exists:
                if not force:
                    self.logger.error(f"Tmux session '{self.session_name}' already exists!")
                    self.logger.info("Options:")
                    self.logger.info(f"  1. Attach to existing: tmux attach -t {self.session_name}")
                    self.logger.info(f"  2. Kill existing: tmux kill-session -t {self.session_name}")
                    self.logger.info(f"  3. Use --force flag to auto-kill existing session")
                    self.logger.info(f"  4. Use a different session name")
                    return False
                else:
                    self.logger.warning(f"Force mode: Killing existing session '{self.session_name}'")
                    self.kill_session()
                    time.sleep(0.5)
            
            # In force mode, always try to kill any lingering session
            # This is more aggressive and handles edge cases
            if force:
                self.logger.debug(f"Force mode: Ensuring clean state by killing session '{self.session_name}'")
                try:
                    # Kill session
                    self._run_command(["tmux", "kill-session", "-t", self.session_name], check=False)
                    # Also try to kill any windows that might be lingering
                    self._run_command(["tmux", "kill-window", "-t", f"{self.session_name}:"], check=False)
                    time.sleep(0.3)
                except:
                    pass
                    
                # Double-check it's really gone
                if self.session_exists():
                    self.logger.error(f"Session '{self.session_name}' still exists after force kill!")
                    # Try one more time with server kill
                    try:
                        self._run_command(["tmux", "kill-server"], check=False)
                        time.sleep(0.5)
                    except:
                        pass
            
            # Create new session (detached) with a shell
            # Set a larger default window size if creating many panes
            if num_panes >= 5:
                # For 5+ panes, we need a larger window
                self._run_command(["tmux", "new-session", "-d", "-s", self.session_name, "-x", "120", "-y", "40", "bash"])
                self.logger.info(f"Created session with larger window size (120x40) for {num_panes} panes")
            else:
                self._run_command(["tmux", "new-session", "-d", "-s", self.session_name, "bash"])
            
            # Small delay to ensure session is fully initialized
            time.sleep(0.1)
            
            # Verify session was created
            if not self.session_exists():
                self.logger.error(f"Failed to create tmux session '{self.session_name}'")
                return False
                
            # Check initial pane count
            try:
                result = self._run_command(
                    ["tmux", "list-panes", "-t", self.session_name, "-F", "#{pane_index}"],
                    capture_output=True, text=True
                )
                initial_panes = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                if initial_panes != 1:
                    self.logger.warning(f"Session created with {initial_panes} panes instead of 1!")
            except:
                pass
            
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
            
            # Create layout configuration
            if layout is None:
                # Default to horizontal layout
                layout_config = create_layout("horizontal", num_panes)
            else:
                layout_config = create_layout(layout, num_panes)
                
            # Store current layout
            self.current_layout = layout_config
            
            # Apply layout if more than one pane
            if num_panes > 1:
                # Check current pane count before applying layout
                try:
                    result = self._run_command(
                        ["tmux", "list-panes", "-t", self.session_name, "-F", "#{pane_index}"],
                        capture_output=True, text=True
                    )
                    current_panes = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                    self.logger.info(f"Before layout: session has {current_panes} panes, expecting to create {num_panes}")
                except:
                    pass
                    
                layout_commands = self.layout_manager.generate_layout_commands(
                    layout_config, self.session_name
                )
                
                self.logger.info(f"Layout commands to execute: {len(layout_commands)}")
                for i, cmd in enumerate(layout_commands):
                    # Execute layout commands in the session context
                    cmd_parts = ["tmux"] + cmd.split()
                    try:
                        self.logger.debug(f"Executing layout command: {' '.join(cmd_parts)}")
                        # Capture output for better error reporting
                        result = self._run_command(cmd_parts, capture_output=True, text=True)
                    except subprocess.CalledProcessError as e:
                        self.logger.error(f"Failed to execute layout command: {' '.join(cmd_parts)}")
                        self.logger.error(f"Error: {e}")
                        if hasattr(e, 'stderr') and e.stderr:
                            self.logger.error(f"stderr: {e.stderr}")
                            # Check for specific errors
                            if "no space for new pane" in e.stderr:
                                self.logger.error("Terminal too small or too many panes for available space!")
                                # Get terminal dimensions
                                try:
                                    dims = self._run_command(
                                        ["tmux", "display-message", "-p", "#{window_width}x#{window_height}"],
                                        capture_output=True, text=True, check=False
                                    )
                                    self.logger.error(f"Terminal dimensions: {dims.stdout.strip()}")
                                except:
                                    pass
                        if hasattr(e, 'stdout') and e.stdout:
                            self.logger.error(f"stdout: {e.stdout}")
                        # Check if session still exists
                        if not self.session_exists():
                            self.logger.error(f"Session '{self.session_name}' no longer exists!")
                        else:
                            # List current state for debugging
                            try:
                                windows = self._run_command(
                                    ["tmux", "list-windows", "-t", self.session_name],
                                    capture_output=True, text=True, check=False
                                )
                                self.logger.error(f"Current windows: {windows.stdout}")
                                panes = self._run_command(
                                    ["tmux", "list-panes", "-t", self.session_name],
                                    capture_output=True, text=True, check=False
                                )
                                self.logger.error(f"Current panes: {panes.stdout}")
                            except:
                                pass
                        raise
            
            layout_info = f" using {layout_config.type.value} layout"
            if layout_config.type.value == "grid" and layout_config.grid_rows:
                layout_info += f" ({layout_config.grid_rows}x{layout_config.grid_cols})"
            self.logger.info(f"Created tmux session '{self.session_name}' with {num_panes} panes{layout_info}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create tmux session: {e}")
            return False
            
    def send_to_pane(self, pane_index: int, command: str) -> bool:
        """Send command to specific pane
        
        Note: This sends the text and Enter as separate commands, which can
        cause issues if the target is processing. For critical messages,
        consider using send-keys with -l flag for literal text.
        """
        try:
            target = f"{self.session_name}:0.{pane_index}"
            
            # Send command followed by Enter key
            # Using literal mode (-l) to ensure special characters are handled correctly
            self._run_command(["tmux", "send-keys", "-t", target, "-l", command])
            
            # Small delay to ensure text is processed before Enter
            # This helps prevent race conditions when sending multiple messages rapidly
            time.sleep(0.05)  # 50ms delay
            
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
                            mcp_config: Optional[Dict[str, Any]] = None,
                            session_id: Optional[str] = None) -> Optional[str]:
        """Launch Claude in specific pane with given configuration
        
        Args:
            pane_index: Tmux pane index
            agent_name: Name of the agent
            agent_prompt: System prompt for the agent
            working_dir: Optional working directory
            mcp_config: Optional MCP configuration
            session_id: Session ID to resume
        
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            # Change directory if specified
            if working_dir:
                self.send_to_pane(pane_index, f"cd {shlex.quote(working_dir)}")
                time.sleep(0.5)
            
            # Use simple launcher to get session ID
            launched_session_id = self.simple_launcher.launch_agent(
                pane_index=pane_index, 
                agent_name=agent_name, 
                system_prompt=agent_prompt, 
                mcp_config=mcp_config,
                session_id=session_id
            )
            
            if launched_session_id:
                if session_id is not None and launched_session_id != session_id:
                    self.logger.error(f"Agent {agent_name} launched with different session ID: {launched_session_id} (expected {session_id})")
                self.logger.info(f"Successfully launched Claude in pane {pane_index} with session {launched_session_id}")
            else:
                self.logger.error(f"Failed to launch Claude in pane {pane_index}")
                
            return launched_session_id
            
        except Exception as e:
            self.logger.error(f"Failed to launch Claude in pane {pane_index}: {e}")
            return None
    
    def get_layout_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current layout"""
        if not self.current_layout:
            return None
            
        return {
            "type": self.current_layout.type.value,
            "agent_count": self.current_layout.agent_count,
            "keyboard_shortcuts": self.layout_manager.get_keyboard_shortcuts(self.current_layout),
            "panes": self.list_panes()
        }
    
    def _run_command(self, cmd: List[str], check: bool = True, 
                    capture_output: bool = False, text: bool = False) -> subprocess.CompletedProcess:
        """Run command with error handling"""
        self.logger.debug(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=text)
        if result.returncode != 0 and capture_output:
            self.logger.debug(f"Command failed with stdout: {result.stdout}")
            self.logger.debug(f"Command failed with stderr: {result.stderr}")
        return result