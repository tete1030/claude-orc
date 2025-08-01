"""
Main Orchestrator Module
Central service for coordinating multi-agent communication
"""

import os
import sys
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty

from .tmux_manager import TmuxManager
from .session_monitor import SessionMonitor, Command


@dataclass
class Agent:
    """Represents an agent in the system"""
    name: str
    session_id: str
    pane_index: int
    session_file: str
    system_prompt: str
    working_dir: Optional[str] = None
    monitor: Optional[SessionMonitor] = None
    last_active: float = field(default_factory=time.time)


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator"""
    session_name: str = "claude-agents"
    claude_bin: str = ""  # Will be auto-detected if not specified
    session_dir: str = ""  # Will be set dynamically based on working directory
    poll_interval: float = 0.5
    interrupt_cooldown: float = 2.0  # Seconds between interrupts to same agent
    context_threshold: int = 10000  # Lines before suggesting context management
    
    def __post_init__(self):
        """Set session_dir based on current working directory and auto-detect Claude binary"""
        if not self.session_dir:
            # Claude stores sessions in ~/.claude/projects/<escaped-cwd>/
            cwd = os.getcwd()
            escaped_cwd = cwd.replace('/', '-')
            self.session_dir = os.path.expanduser(f"~/.claude/projects/{escaped_cwd}")
        
        # Auto-detect Claude binary if not specified
        if not self.claude_bin:
            import subprocess
            try:
                result = subprocess.run(["which", "claude"], capture_output=True, text=True)
                if result.returncode == 0:
                    self.claude_bin = result.stdout.strip()
            except Exception:
                pass
            
            # If which didn't work, try common locations
            if not self.claude_bin:
                for path in ["/usr/local/bin/claude", "/usr/bin/claude",
                             os.path.expanduser("~/.local/bin/claude"),
                             os.path.expanduser("~/.claude/local/claude")]:
                    if os.path.exists(path):
                        self.claude_bin = path
                        break
            
            if not self.claude_bin:
                raise ValueError("Could not find Claude binary. Please specify claude_bin in config.")


class Orchestrator:
    """Main orchestrator for multi-agent coordination"""
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self.tmux = TmuxManager(self.config.session_name)
        self.agents: Dict[str, Agent] = {}
        self.running = False
        self.monitors_thread: Optional[threading.Thread] = None
        self.command_queue: Queue[Command] = Queue()
        self.interrupt_history: Dict[str, float] = {}  # agent_name -> last_interrupt_time
        self.mailbox: Dict[str, List[Dict[str, Any]]] = {}  # agent_name -> messages
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Thread synchronization
        self._agents_lock = threading.RLock()  # For agents dict
        self._mailbox_lock = threading.RLock()  # For mailbox dict
        self._interrupt_lock = threading.Lock()  # For interrupt history
        
        # Command handlers
        self.command_handlers: Dict[str, Callable] = {
            "send_message": self._handle_send_message,
            "list_agents": self._handle_list_agents,
            "mailbox_check": self._handle_mailbox_check,
            "context_status": self._handle_context_status,
        }
        
    def register_agent(self, name: str, session_id: str, system_prompt: str,
                      working_dir: Optional[str] = None) -> None:
        """Register a new agent"""
        with self._agents_lock:
            if name in self.agents:
                raise ValueError(f"Agent {name} already registered - duplicate names not allowed")
            
            # Determine pane index
            pane_index = len(self.agents)
            
            # Note: session_id is now just a placeholder - actual session ID 
            # will be determined after Claude starts
            session_file = None  # Will be set after we get actual session ID
            
            # Create agent
            agent = Agent(
                name=name,
                session_id=session_id,  # Placeholder for now
                pane_index=pane_index,
                session_file="",  # Will be updated after launch
                system_prompt=system_prompt,
                working_dir=working_dir
            )
            
            self.agents[name] = agent
        
        # Initialize mailbox
        with self._mailbox_lock:
            self.mailbox[name] = []
        
        self.logger.info(f"Registered agent {name}")
        
    def start(self, mcp_port: Optional[int] = None) -> bool:
        """Start the orchestrator and all agents
        
        Args:
            mcp_port: Port for MCP server. If provided, agents will be configured to use MCP.
        """
        if self.running:
            self.logger.warning("Orchestrator already running")
            return False
            
        if not self.agents:
            self.logger.error("No agents registered")
            return False
            
        # Create session-specific directory with bin and mcp_configs subdirectories
        import random
        session_id = f"orc-{random.randint(100000, 999999)}"
        
        # Use /tmp/claude-orc/{session-id}
        self.shared_dir = f"/tmp/claude-orc/{session_id}"
        self.shared_bin_dir = os.path.join(self.shared_dir, "bin")
        self.shared_mcp_dir = os.path.join(self.shared_dir, "mcp_configs")
        
        # Create directories
        os.makedirs(self.shared_bin_dir, exist_ok=True)
        os.makedirs(self.shared_mcp_dir, exist_ok=True)
        self.logger.info(f"Created session directories at {self.shared_dir}")
            
        # Create tmux session
        num_panes = len(self.agents)
        if not self.tmux.create_session(num_panes, force=False):
            self.logger.error("Failed to create tmux session")
            return False
            
        # Set shared directory for launcher
        self.tmux.simple_launcher.shared_mcp_dir = self.shared_mcp_dir
        
        # Launch agents in their panes
        for agent in self.agents.values():
            # Set pane title
            self.tmux.set_pane_title(agent.pane_index, f"Agent: {agent.name}")
            
            # Create MCP config if port provided
            mcp_config = None
            if mcp_port:
                # Use stdio transport with thin proxy
                proxy_path = os.path.join(os.path.dirname(__file__), "mcp_thin_proxy.py")
                
                # Get current Python executable
                python_executable = sys.executable
                
                # Copy thin proxy to shared location
                shared_proxy_path = os.path.join(self.shared_bin_dir, "mcp_thin_proxy.py")
                try:
                    import shutil
                    shutil.copy2(proxy_path, shared_proxy_path)
                    # Make the script executable
                    os.chmod(shared_proxy_path, 0o755)
                    proxy_path = shared_proxy_path
                    self.logger.info(f"Copied thin proxy to shared location: {shared_proxy_path}")
                except Exception as e:
                    self.logger.warning(f"Could not copy to shared location, using original: {e}")
                
                mcp_config = {
                    "mcpServers": {
                        "orchestrator": {
                            "command": "python3",
                            "args": [proxy_path],
                            "env": {
                                "AGENT_NAME": agent.name,
                                "ORCHESTRATOR_URL": f"http://localhost:{mcp_port}"
                            }
                        }
                    }
                }
            
            # Launch Claude - this now returns the session ID
            session_id = self.tmux.launch_claude_in_pane(
                agent.pane_index,
                agent.name,  # Now passing agent name instead of session_id
                agent.system_prompt,
                agent.working_dir,
                self.config.claude_bin,
                mcp_config=mcp_config
            )
            
            if session_id:
                # Update agent with actual session ID
                agent.session_id = session_id
                agent.session_file = os.path.join(self.config.session_dir, f"{session_id}.jsonl")
                self.logger.info(f"Agent {agent.name} launched with session ID: {session_id}")
                
                # Set agent name as a pane variable
                # This will be displayed in the pane border along with whatever title Claude sets
                self.tmux.set_pane_agent_name(agent.pane_index, agent.name)
            else:
                self.logger.error(f"Failed to launch agent {agent.name}")
                self.stop()
                return False
            
        # All agents now have their session IDs from the two-stage launch
        self.logger.info("All agents launched with session IDs")
        
        # Send initial messages to create session files
        self.logger.info("Creating session files...")
        for agent in self.agents.values():
            if agent.session_id and agent.session_id != "placeholder":
                # Send initial message directly
                if mcp_port:
                    message = f"System initialized. You are {agent.name} agent with MCP tools available. Use 'list_agents' to see other agents."
                else:
                    message = f"System initialized. You are {agent.name} agent. Ready to receive commands."
                    
                if self.tmux.send_to_pane(agent.pane_index, message):
                    self.logger.info(f"Sent initial message to {agent.name}")
                else:
                    self.logger.error(f"Failed to send initial message to {agent.name}")
                time.sleep(1)
        
        # Wait for session files to be created
        self.logger.info("Waiting for session files to be created...")
        time.sleep(5)
        
        # If MCP is enabled, add welcome messages to help agents start
        if mcp_port:
            self.logger.info("Adding welcome messages for MCP agents...")
            with self._mailbox_lock:
                for agent_name in self.agents:
                    welcome_msg = {
                        "from": "System",
                        "to": agent_name,
                        "message": f"Welcome {agent_name}! You have MCP tools available. Try 'list_agents' to see who else is online.",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.mailbox[agent_name].append(welcome_msg)
        
        # Set up monitors for agents with session files
        success_count = 0
        for agent in self.agents.values():
            if agent.session_file and agent.session_id != "placeholder":
                # Check multiple times for session file
                for attempt in range(3):
                    if os.path.exists(agent.session_file):
                        agent.monitor = SessionMonitor(agent.session_file, agent.name)
                        self.logger.info(f"Agent {agent.name} monitoring session file")
                        success_count += 1
                        break
                    self.logger.warning(f"Session file not found for {agent.name}, attempt {attempt + 1}")
                    time.sleep(2)
            else:
                self.logger.warning(f"No valid session ID for {agent.name}")
        
        if success_count == 0:
            self.logger.error("No agents have working session monitors!")
        else:
            self.logger.info(f"{success_count}/{len(self.agents)} agents have working monitors")
        
        # Start monitoring thread
        self.running = True
        self.monitors_thread = threading.Thread(target=self._monitor_loop)
        self.monitors_thread.daemon = True
        self.monitors_thread.start()
        
        self.logger.info("Orchestrator started successfully")
        return True
        
    def stop(self) -> None:
        """Stop the orchestrator"""
        self.running = False
        
        if self.monitors_thread:
            self.monitors_thread.join(timeout=5.0)
            
        self.tmux.kill_session()
        
        with self._agents_lock:
            self.agents.clear()
        with self._mailbox_lock:
            self.mailbox.clear()
        with self._interrupt_lock:
            self.interrupt_history.clear()
        
        self.logger.info("Orchestrator stopped")
        
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                # Check each agent for new messages
                with self._agents_lock:
                    agents_copy = list(self.agents.items())
                
                for name, agent in agents_copy:
                    if agent.monitor:
                        # Get new messages
                        messages = agent.monitor.get_new_messages()
                        
                        # Extract commands
                        if messages:
                            self.logger.debug(f"Agent {name} has {len(messages)} new messages")
                            commands = agent.monitor.extract_commands(messages)
                            if commands:
                                self.logger.info(f"Agent {name} extracted {len(commands)} commands")
                            for cmd in commands:
                                self.command_queue.put(cmd)
                                with self._agents_lock:
                                    agent.last_active = time.time()
                
                # Process commands
                while not self.command_queue.empty():
                    try:
                        cmd = self.command_queue.get_nowait()
                        self._process_command(cmd)
                    except Empty:
                        break
                        
                # Sleep before next check
                time.sleep(self.config.poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                
    def _process_command(self, cmd: Command) -> None:
        """Process a command from an agent"""
        self.logger.info(f"Processing {cmd.command_type} from {cmd.agent_name}")
        
        handler = self.command_handlers.get(cmd.command_type)
        if handler:
            try:
                handler(cmd)
            except Exception as e:
                self.logger.error(f"Error handling {cmd.command_type}: {e}")
                raise
        else:
            self.logger.warning(f"Unknown command type: {cmd.command_type}")
            
    def _handle_send_message(self, cmd: Command) -> None:
        """Handle send_message command"""
        self.logger.info(f"Handling send_message: from={cmd.from_agent}, to={cmd.to_agent}, title={cmd.title}")
        
        if not cmd.to_agent:
            raise ValueError("send_message command missing required to_agent field")
        
        with self._agents_lock:
            target_agent = self.agents.get(cmd.to_agent)
        if not target_agent:
            # Try case-insensitive lookup
            with self._agents_lock:
                agents_items = list(self.agents.items())
            
            for agent_name, agent in agents_items:
                if agent_name.lower() == cmd.to_agent.lower():
                    target_agent = agent
                    self.logger.debug(f"Found agent {agent_name} via case-insensitive match for {cmd.to_agent}")
                    break
        
        if not target_agent:
            raise ValueError(f"Unknown target agent: {cmd.to_agent}")
            
        # Prepare message
        message = {
            "from": cmd.from_agent or cmd.agent_name,
            "to": cmd.to_agent,
            "title": cmd.title or "Message",
            "content": cmd.content or "",
            "timestamp": datetime.now().isoformat(),
            "priority": cmd.priority or "normal"
        }
        
        self.logger.info(f"Message prepared: {message['from']} -> {message['to']}: {message['title']}")
        
        # Check priority for interrupt
        if cmd.priority == "high":
            # Check interrupt cooldown
            with self._interrupt_lock:
                last_interrupt = self.interrupt_history.get(cmd.to_agent, 0)
                if time.time() - last_interrupt > self.config.interrupt_cooldown:
                    # Send interrupt
                    interrupt_msg = f"[INTERRUPT FROM: {message['from']}] {message['title']}"
                    if message['content']:
                        interrupt_msg += f"\n{message['content']}"
                        
                    self.tmux.send_to_pane(target_agent.pane_index, interrupt_msg)
                    self.interrupt_history[cmd.to_agent] = time.time()
                    self.logger.info(f"Sent interrupt to {cmd.to_agent}")
                else:
                    # Add to mailbox instead - use actual agent name
                    actual_agent_name = target_agent.name
                    with self._mailbox_lock:
                        self.mailbox[actual_agent_name].append(message)
                    self.logger.info(f"Interrupt on cooldown, added to {actual_agent_name} mailbox")
        else:
            # Add to mailbox - use the actual agent name, not the potentially lowercase version
            actual_agent_name = target_agent.name
            with self._mailbox_lock:
                self.mailbox[actual_agent_name].append(message)
            self.logger.info(f"Added message to {actual_agent_name} mailbox")
            
            # Notify the agent about new message
            notification = f"\n[MAILBOX NOTIFICATION] You have a new message from {message['from']} - Title: {message['title']}\nUse <orc-command name=\"mailbox_check\"></orc-command> to retrieve your messages.\n"
            self.tmux.send_to_pane(target_agent.pane_index, notification)
            
    def _handle_list_agents(self, cmd: Command) -> None:
        """Handle list_agents command"""
        # Create response
        agent_list = []
        with self._agents_lock:
            agents_copy = list(self.agents.items())
        
        for name, agent in agents_copy:
            with self._mailbox_lock:
                mailbox_count = len(self.mailbox.get(name, []))
            
            agent_info = {
                "name": name,
                "session_id": agent.session_id,
                "pane_index": agent.pane_index,
                "last_active": datetime.fromtimestamp(agent.last_active).isoformat(),
                "mailbox_count": mailbox_count
            }
            agent_list.append(agent_info)
            
        response = f"[ORC RESPONSE: list_agents]\n"
        response += json.dumps(agent_list, indent=2)
        
        # Send to requesting agent
        with self._agents_lock:
            requesting_agent = self.agents.get(cmd.agent_name)
        if requesting_agent:
            self.tmux.send_to_pane(requesting_agent.pane_index, response)
        else:
            raise ValueError(f"Requesting agent {cmd.agent_name} not found")
            
    def _handle_mailbox_check(self, cmd: Command) -> None:
        """Handle mailbox_check command"""
        # Get messages for requesting agent
        with self._mailbox_lock:
            messages = self.mailbox.get(cmd.agent_name, [])
            
            if messages:
                response = f"[ORC RESPONSE: mailbox]\n"
                response += f"You have {len(messages)} messages:\n"
                for i, msg in enumerate(messages):
                    response += f"\n--- Message {i+1} ---\n"
                    response += f"From: {msg['from']}\n"
                    response += f"Title: {msg.get('title', 'No title')}\n"
                    response += f"Time: {msg.get('timestamp', 'Unknown')}\n"
                    response += f"Priority: {msg.get('priority', 'normal')}\n"
                    content = msg.get('content') or msg.get('message', '')
                    if content:
                        response += f"Content:\n{content}\n"
                        
                # Clear mailbox after retrieval
                self.mailbox[cmd.agent_name] = []
            else:
                response = "[ORC RESPONSE: mailbox]\nNo new messages."
            
        # Send to requesting agent
        with self._agents_lock:
            requesting_agent = self.agents.get(cmd.agent_name)
        if requesting_agent:
            self.tmux.send_to_pane(requesting_agent.pane_index, response)
        else:
            raise ValueError(f"Requesting agent {cmd.agent_name} not found")
            
    def _handle_context_status(self, cmd: Command) -> None:
        """Handle context_status command"""
        # Get session file size for requesting agent
        with self._agents_lock:
            agent = self.agents.get(cmd.agent_name)
        if not agent or not agent.monitor:
            raise ValueError(f"Agent {cmd.agent_name} not found or has no monitor")
            
        file_size = agent.monitor.get_file_size()
        
        # Estimate lines (rough approximation)
        estimated_lines = file_size // 100  # Assume ~100 bytes per line average
        
        response = f"[ORC RESPONSE: context_status]\n"
        response += f"Session file size: {file_size:,} bytes\n"
        response += f"Estimated context usage: {estimated_lines:,} lines\n"
        
        if estimated_lines > self.config.context_threshold:
            response += f"\nWARNING: Approaching context limit.\n"
            response += f"Consider starting a new session with --resume flag.\n"
            
        self.tmux.send_to_pane(agent.pane_index, response)
        
    def send_to_agent(self, agent_name: str, message: str) -> bool:
        """Send a direct message to an agent (used by external controllers)"""
        with self._agents_lock:
            agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_name}")
            
        return self.tmux.send_to_pane(agent.pane_index, message)
        
    def get_agent_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent"""
        with self._agents_lock:
            agent = self.agents.get(agent_name)
        if not agent:
            return None
        
        with self._mailbox_lock:
            mailbox_count = len(self.mailbox.get(agent_name, []))
            
        return {
            "name": agent.name,
            "session_id": agent.session_id,
            "pane_index": agent.pane_index,
            "last_active": datetime.fromtimestamp(agent.last_active).isoformat(),
            "mailbox_count": mailbox_count,
            "session_file_size": agent.monitor.get_file_size() if agent.monitor else 0
        }
        
    def get_all_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents"""
        with self._agents_lock:
            agent_names = list(self.agents.keys())
        
        return {name: status for name in agent_names 
                if (status := self.get_agent_status(name)) is not None}
    
    def get_mailbox_count(self, agent_name: str) -> int:
        """Get the number of messages in an agent's mailbox"""
        with self._mailbox_lock:
            return len(self.mailbox.get(agent_name, []))
    
    # Removed get_session_id_from_agent - no longer needed with two-stage launcher
    
