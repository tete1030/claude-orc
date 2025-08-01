#!/usr/bin/env python3
"""
Enhanced orchestrator with state monitoring and intelligent message delivery
"""
import os
import sys
import time
import threading
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from .orchestrator import Orchestrator, OrchestratorConfig
from .agent_state_monitor import AgentStateMonitor, AgentState
from .message_delivery import MessageDeliverySystem


class EnhancedOrchestrator(Orchestrator):
    """Enhanced orchestrator with state monitoring and intelligent message delivery"""
    
    def __init__(self, config: OrchestratorConfig):
        super().__init__(config)
        self.state_monitor: Optional[AgentStateMonitor] = None
        self.message_delivery: Optional[MessageDeliverySystem] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_interval = 0.5  # Check agent states every 0.5 seconds for faster updates
        self.initialization_start_time = None  # Track when we started
        
    def start(self, mcp_port: Optional[int] = None) -> bool:
        """Start orchestrator with enhanced features"""
        # Check if already running
        if self.running:
            self.logger.warning("Orchestrator already running")
            return False
            
        if not self.agents:
            self.logger.error("No agents registered")
            return False
            
        # Create session directories (copied from parent)
        import random
        session_id = f"orc-{random.randint(100000, 999999)}"
        self.shared_dir = f"/tmp/claude-orc/{session_id}"
        self.shared_bin_dir = os.path.join(self.shared_dir, "bin")
        self.shared_mcp_dir = os.path.join(self.shared_dir, "mcp_configs")
        os.makedirs(self.shared_bin_dir, exist_ok=True)
        os.makedirs(self.shared_mcp_dir, exist_ok=True)
        
        # Create tmux session
        num_panes = len(self.agents)
        if not self.tmux.create_session(num_panes, force=False):
            self.logger.error("Failed to create tmux session")
            return False
            
        # Set shared directory for launcher
        self.tmux.simple_launcher.shared_mcp_dir = self.shared_mcp_dir
        
        # Initialize monitoring IMMEDIATELY after session creation
        self.state_monitor = AgentStateMonitor(self.tmux)
        self.message_delivery = MessageDeliverySystem(self, self.tmux, self.state_monitor)
        
        # Initialize UI elements
        initial_states = {}
        for i, (agent_name, agent) in enumerate(self.agents.items()):
            agent.pane_index = i  # Set pane index
            initial_states[agent_name] = "initializing"
            self.tmux.set_pane_title(i, f"Agent: {agent_name}")
            self.tmux.set_pane_agent_name(i, agent_name)
            # Don't set per-pane border colors anymore
            self.tmux.update_pane_message_count(i, 0)
            self.tmux.set_pane_activity_indicator(i, False)
        
        # Set initial window-level border color once
        initial_agent_states = {name: (i, "initializing") for i, name in enumerate(self.agents.keys())}
        self.tmux.update_border_colors_for_states(initial_agent_states)
        
        # Set initial status bar
        self.tmux.update_status_bar(initial_states)
        
        # Start monitoring thread BEFORE launching agents
        self.running = True
        self.initialization_start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._state_monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("State monitor loop started early")
        
        # Now launch agents (this is the slow part)
        if not self._launch_agents_quickly(mcp_port):
            self.stop()
            return False
            
        self.logger.info("Enhanced orchestrator started with state monitoring")
        
        # Print usage instructions
        print("\n" + "="*60)
        print("Orchestrator Started Successfully!")
        print("="*60)
        print("\nTo interact with the agents:")
        print("1. Open a new terminal")
        print("2. Attach to tmux session: tmux attach -t team-mcp-demo")
        print("3. Switch between agents:")
        print("   Fast switching (no prefix):")
        print("   - F1 or Alt+1 → Leader")
        print("   - F2 or Alt+2 → Researcher")
        print("   - F3 or Alt+3 → Writer")
        print("   - Click pane with mouse")
        print("   Standard tmux navigation:")
        print("   - Ctrl+b, 1 → Leader")
        print("   - Ctrl+b, 2 → Researcher")
        print("   - Ctrl+b, 3 → Writer")
        print("4. Mouse support enabled - click to switch, scroll to navigate")
        print("5. Use '?' in any pane to see Claude shortcuts")
        print("6. Detach with Ctrl+b, d")
        print("="*60 + "\n")
        
        return True
        
    def _launch_agents_quickly(self, mcp_port: Optional[int] = None) -> bool:
        """Launch agents without unnecessary delays"""
        # Copy MCP proxy if needed
        if mcp_port:
            proxy_path = os.path.join(os.path.dirname(__file__), "mcp_thin_proxy.py")
            shared_proxy_path = os.path.join(self.shared_bin_dir, "mcp_thin_proxy.py")
            try:
                import shutil
                shutil.copy2(proxy_path, shared_proxy_path)
                os.chmod(shared_proxy_path, 0o755)
                proxy_path = shared_proxy_path
            except Exception as e:
                self.logger.warning(f"Could not copy to shared location: {e}")
        
        # Launch all agents
        for agent in self.agents.values():
            # Create MCP config if needed
            mcp_config = None
            if mcp_port:
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
            
            # Launch Claude
            session_id = self.tmux.launch_claude_in_pane(
                agent.pane_index,
                agent.name,
                agent.system_prompt,
                agent.working_dir,
                self.config.claude_bin,
                mcp_config=mcp_config
            )
            
            if session_id:
                agent.session_id = session_id
                agent.session_file = os.path.join(self.config.session_dir, f"{session_id}.jsonl")
                self.logger.info(f"Agent {agent.name} launched with session ID: {session_id}")
            else:
                self.logger.error(f"Failed to launch agent {agent.name}")
                return False
                
        self.logger.info("All agents launched")
        
        # Send initial messages without delays
        for agent in self.agents.values():
            if mcp_port:
                message = f"System initialized. You are {agent.name} agent with MCP tools available. Use 'list_agents' to see other agents."
            else:
                message = f"System initialized. You are {agent.name} agent. Ready to receive commands."
            self.tmux.send_to_pane(agent.pane_index, message)
            
        # Add welcome messages for MCP
        if mcp_port:
            with self._mailbox_lock:
                for agent_name in self.agents:
                    welcome_msg = {
                        "from": "System",
                        "to": agent_name,
                        "message": f"Welcome {agent_name}! You have MCP tools available. Try 'list_agents' to see who else is online.",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.mailbox[agent_name].append(welcome_msg)
                    
        return True
        
    def _state_monitor_loop(self) -> None:
        """Monitor agent states in background"""
        # Start monitoring immediately
        self.logger.info("State monitor loop started")
        iteration = 0
        
        # Track previous states to avoid unnecessary updates
        previous_states = {}
        previous_msg_counts = {}
        
        # Set border colors once at startup
        initial_states = {name: (agent.pane_index, "initializing") 
                         for name, agent in self.agents.items()}
        self.tmux.update_border_colors_for_states(initial_states)
        
        while self.running:
            try:
                iteration += 1
                if iteration % 20 == 1:  # Log every 20 iterations
                    self.logger.debug(f"Monitor loop iteration {iteration}")
                    
                # Update all agent states
                for agent_name, agent in self.agents.items():
                    state = self.state_monitor.update_agent_state(agent_name, agent.pane_index)
                    
                    # Track state changes and update pane indicators
                    if state and previous_states.get(agent_name) != state.value:
                        previous_states[agent_name] = state.value
                        
                        # Update pane state indicator (title and icon)
                        self.tmux.set_pane_border_color(agent.pane_index, state.value)
                        
                        # Set activity indicator based on state
                        is_busy = state.value in ["busy", "writing"]
                        self.tmux.set_pane_activity_indicator(agent.pane_index, is_busy)
                    
                    # Only update message count if it changed
                    msg_count = self.get_mailbox_count(agent_name)
                    if previous_msg_counts.get(agent_name) != msg_count:
                        self.tmux.update_pane_message_count(agent.pane_index, msg_count)
                        previous_msg_counts[agent_name] = msg_count
                    
                # Check and deliver pending messages
                if self.message_delivery:
                    self.message_delivery.check_and_deliver_pending_messages()
                
                # Update status bar with current states
                states = self.get_all_agent_states()
                if states:
                    self.tmux.update_status_bar(states)
                    
                    # Update border colors for all panes
                    agent_state_info = {}
                    
                    # Collect current states
                    for agent_name, agent in self.agents.items():
                        agent_status = self.state_monitor.agent_states.get(agent_name)
                        if agent_status and agent_status.state:
                            agent_state_info[agent_name] = (agent.pane_index, agent_status.state.value)
                    
                    # No need to update border colors anymore - they stay blue
                
                # Log summary periodically
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    summary = self.state_monitor.get_agent_summary()
                    self.logger.debug(f"Agent states: {json.dumps(summary, indent=2)}")
                    
            except Exception as e:
                self.logger.error(f"Error in state monitor loop: {e}")
                
            time.sleep(self.monitor_interval)
            
    def send_message_to_agent(self, to_agent: str, from_agent: str, 
                            message_content: str, priority: str = "normal") -> bool:
        """Send a message to another agent"""
        if not self.message_delivery:
            # Fallback to direct mailbox delivery
            return super().send_message_to_agent(to_agent, from_agent, message_content, priority)
            
        return self.message_delivery.send_message_to_agent(to_agent, from_agent, message_content, priority)
        
    def get_agent_state(self, agent_name: str) -> Optional[str]:
        """Get current state of an agent"""
        if not self.state_monitor or agent_name not in self.agents:
            return None
        
        agent = self.agents[agent_name]
        state = self.state_monitor.update_agent_state(agent_name, agent.pane_index)
        return state.value
        
    def get_all_agent_states(self) -> Dict[str, str]:
        """Get states of all agents"""
        states = {}
        for agent_name in self.agents:
            state = self.get_agent_state(agent_name)
            if state:
                states[agent_name] = state
        return states
        
    def wait_for_agent_idle(self, agent_name: str, timeout: int = 30) -> bool:
        """Wait for an agent to become idle"""
        if not self.state_monitor or agent_name not in self.agents:
            return False
            
        start_time = time.time()
        while time.time() - start_time < timeout:
            state = self.get_agent_state(agent_name)
            if state == AgentState.IDLE.value:
                return True
            time.sleep(0.5)
            
        return False
        
    def send_direct_input(self, agent_name: str, text: str) -> bool:
        """Send text directly to agent's input field"""
        if not self.message_delivery:
            return False
        return self.message_delivery.send_text_to_agent_input(agent_name, text)
        
    def send_command(self, agent_name: str, command: str) -> bool:
        """Send a command to agent"""
        if not self.message_delivery:
            return False
        return self.message_delivery.send_command_to_agent(agent_name, command)