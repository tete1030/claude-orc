"""
Message Delivery System - Handles message delivery with agent state awareness
"""

import time
import logging
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass
from .agent_state_monitor import AgentState


@dataclass
class MessageNotification:
    """Message notification settings"""
    prefix: str = "[MESSAGE]"
    notification_format: str = "{prefix} You have a new message from {sender}. Check it when convenient using 'check_messages' - no need to interrupt your current task unless urgent."
    queue_notification_format: str = "{prefix} You received {count} messages while busy. Use 'check_messages' to read them."
    idle_reminder_format: str = "{prefix} Reminder: You have {count} unread message(s) in your mailbox. Use 'check_messages' to read them."
    

class MessageDeliverySystem:
    """Handles intelligent message delivery based on agent states"""
    
    def __init__(self, orchestrator, tmux_manager, state_monitor, notification_settings: Optional[MessageNotification] = None):
        self.orchestrator = orchestrator
        self.tmux = tmux_manager
        self.state_monitor = state_monitor
        self.logger = logging.getLogger(__name__)
        self.notification = notification_settings or MessageNotification()
        # Track which agents we've sent idle reminders to
        self.idle_reminder_sent = {}
        # Lock to ensure sequential message delivery
        self._delivery_lock = threading.Lock()
        # Track last notification time per agent
        self._last_notification_time = {}
        
    def send_message_to_agent(self, to_agent: str, from_agent: str, message_content: str, priority: str = "normal") -> bool:
        """Send message to agent - always delivers regardless of state"""
        # Check if recipient exists
        if to_agent not in self.orchestrator.agents:
            self.logger.error(f"Agent {to_agent} not found")
            return False
            
        # Use lock to ensure sequential delivery
        with self._delivery_lock:
            # Create message object (use 'message' field to match MCP server format)
            message = {
                'from': from_agent,
                'to': to_agent,
                'message': message_content,
                'priority': priority,
                'timestamp': time.time()
            }
            
            # Always deliver the message
            self.logger.info(f"Delivering message to {to_agent}")
            return self._deliver_message_now(to_agent, message)
            
    def _deliver_message_now(self, agent_name: str, message: Dict) -> bool:
        """Deliver message immediately to agent"""
        try:
            agent = self.orchestrator.agents[agent_name]
            
            # First, add to mailbox
            if agent_name not in self.orchestrator.mailbox:
                self.orchestrator.mailbox[agent_name] = []
            self.orchestrator.mailbox[agent_name].append(message)
            
            # Reset idle reminder flag since there's a new message
            self.idle_reminder_sent[agent_name] = False
            
            # Send notification to agent's pane
            notification = self.notification.notification_format.format(
                prefix=self.notification.prefix,
                sender=message['from']
            )
            
            # Ensure minimum delay between notifications to same agent
            last_time = self._last_notification_time.get(agent_name, 0)
            time_since_last = time.time() - last_time
            if time_since_last < 0.2:  # 200ms minimum between notifications
                time.sleep(0.2 - time_since_last)
            
            # Send notification
            self.tmux.send_to_pane(agent.pane_index, notification)
            self._last_notification_time[agent_name] = time.time()
            
            self.logger.info(f"Delivered message notification to {agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deliver message to {agent_name}: {e}")
            return False
            
    def check_and_deliver_pending_messages(self) -> None:
        """Check all agents and send idle reminders for unread messages
        
        Simplified version that only checks mailbox and sends reminders to IDLE agents
        """
        for agent_name, agent in self.orchestrator.agents.items():
            # Update state just for logging/reminder purposes
            state = self.state_monitor.update_agent_state(agent_name, agent.pane_index)
            
            # Only send reminders to idle agents
            if state == AgentState.IDLE:
                # Check if agent has unread messages in mailbox
                mailbox_count = len(self.orchestrator.mailbox.get(agent_name, []))
                
                # If they have messages and we haven't sent a reminder yet
                if mailbox_count > 0 and not self.idle_reminder_sent.get(agent_name, False):
                    # Send idle reminder
                    notification = self.notification.idle_reminder_format.format(
                        prefix=self.notification.prefix,
                        count=mailbox_count
                    )
                    
                    self.tmux.send_to_pane(agent.pane_index, notification)
                    self.idle_reminder_sent[agent_name] = True
                    
                    self.logger.info(f"Sent idle reminder to {agent_name} for {mailbox_count} unread messages")
                
                # If mailbox is empty, reset the reminder flag
                elif mailbox_count == 0:
                    self.idle_reminder_sent[agent_name] = False
                    
    def send_text_to_agent_input(self, agent_name: str, text: str) -> bool:
        """Send text directly to agent's input field (for non-vim mode)"""
        if agent_name not in self.orchestrator.agents:
            self.logger.error(f"Agent {agent_name} not found")
            return False
            
        agent = self.orchestrator.agents[agent_name]
        
        # Type the text without pressing Enter
        return self.tmux.type_in_pane(agent.pane_index, text)
        
    def send_command_to_agent(self, agent_name: str, command: str) -> bool:
        """Send a command to agent (with Enter)"""
        if agent_name not in self.orchestrator.agents:
            self.logger.error(f"Agent {agent_name} not found")
            return False
            
        agent = self.orchestrator.agents[agent_name]
        
        # Send the command
        return self.tmux.send_to_pane(agent.pane_index, command)