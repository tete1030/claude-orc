"""
Enhanced Orchestrator with agent state monitoring and intelligent message delivery
"""

import os
import sys
import time
import json
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .orchestrator import Orchestrator, OrchestratorConfig, Agent
from .agent_state_monitor import AgentStateMonitor, AgentState
from .message_delivery import MessageDeliverySystem


class EnhancedOrchestrator(Orchestrator):
    """Enhanced orchestrator with state monitoring and intelligent message delivery"""
    
    def __init__(self, config: OrchestratorConfig):
        super().__init__(config)
        self.state_monitor: Optional[AgentStateMonitor] = None
        self.message_delivery: Optional[MessageDeliverySystem] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_interval = 2.0  # Check agent states every 2 seconds
        
    def start(self, mcp_port: Optional[int] = None) -> bool:
        """Start orchestrator with enhanced features"""
        # Start base orchestrator
        if not super().start(mcp_port):
            return False
            
        # Initialize state monitor and message delivery
        self.state_monitor = AgentStateMonitor(self.tmux)
        self.message_delivery = MessageDeliverySystem(self, self.tmux, self.state_monitor)
        
        # Start state monitoring thread
        self.monitor_thread = threading.Thread(target=self._state_monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Enhanced orchestrator started with state monitoring")
        return True
        
    def _state_monitor_loop(self) -> None:
        """Monitor agent states in background"""
        while self.running:
            try:
                # Update all agent states
                for agent_name, agent in self.agents.items():
                    self.state_monitor.update_agent_state(agent_name, agent.pane_index)
                    
                # Check and deliver pending messages
                self.message_delivery.check_and_deliver_pending_messages()
                
                # Log summary periodically
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    summary = self.state_monitor.get_agent_summary()
                    self.logger.debug(f"Agent states: {json.dumps(summary, indent=2)}")
                    
            except Exception as e:
                self.logger.error(f"Error in state monitor loop: {e}")
                
            time.sleep(self.monitor_interval)
            
    def send_message_to_agent(self, to_agent: str, from_agent: str, 
                            message_content: str, priority: str = "normal") -> bool:
        """Send message with state awareness"""
        if not self.message_delivery:
            # Fallback to original method if enhanced features not initialized
            return self.send_to_agent(to_agent, f"[FROM: {from_agent}] {message_content}")
            
        return self.message_delivery.send_message_to_agent(
            to_agent, from_agent, message_content, priority
        )
        
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