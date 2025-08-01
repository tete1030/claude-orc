"""
Message Delivery System - Handles message delivery with agent state awareness
"""

import time
import logging
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
        
    def send_message_to_agent(self, to_agent: str, from_agent: str, message_content: str, priority: str = "normal") -> bool:
        """Send message to agent with state awareness"""
        # Check if recipient exists
        if to_agent not in self.orchestrator.agents:
            self.logger.error(f"Agent {to_agent} not found")
            return False
            
        recipient = self.orchestrator.agents[to_agent]
        
        # Update agent state
        state = self.state_monitor.update_agent_state(to_agent, recipient.pane_index)
        
        # Create message object (use 'message' field to match MCP server format)
        message = {
            'from': from_agent,
            'to': to_agent,
            'message': message_content,
            'priority': priority,
            'timestamp': time.time()
        }
        
        # Handle based on agent state
        if state == AgentState.IDLE:
            # Agent is idle, deliver immediately
            self.logger.info(f"Agent {to_agent} is idle, delivering message immediately")
            return self._deliver_message_now(to_agent, message)
            
        elif state in (AgentState.BUSY, AgentState.WRITING):
            # Agent is busy or writing
            state_desc = "busy" if state == AgentState.BUSY else "writing"
            self.logger.info(f"Agent {to_agent} is {state_desc}, delivering notification anyway")
            
            # Add to orchestrator mailbox for persistence
            if to_agent not in self.orchestrator.mailbox:
                self.orchestrator.mailbox[to_agent] = []
            self.orchestrator.mailbox[to_agent].append(message)
            
            # Reset idle reminder flag since there's a new message
            self.idle_reminder_sent[to_agent] = False
            
            # Send notification even though agent is busy
            # Claude Code will handle organizing the inputs
            agent = self.orchestrator.agents[to_agent]
            notification = self.notification.notification_format.format(
                prefix=self.notification.prefix,
                sender=message['from']
            )
            self.tmux.send_to_pane(agent.pane_index, notification)
            
            self.logger.info(f"Sent notification to {to_agent} despite {state_desc} state")
            return True
            
        elif state == AgentState.ERROR:
            self.logger.error(f"Agent {to_agent} is in error state, cannot deliver message")
            return False
            
        elif state == AgentState.QUIT:
            self.logger.error(f"Agent {to_agent} has quit, cannot deliver message")
            return False
            
        else:
            # Unknown state, try to deliver anyway
            self.logger.warning(f"Agent {to_agent} in unknown state, attempting delivery")
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
            
            # Send notification
            self.tmux.send_to_pane(agent.pane_index, notification)
            
            self.logger.info(f"Delivered message notification to {agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deliver message to {agent_name}: {e}")
            return False
            
    def check_and_deliver_pending_messages(self) -> None:
        """Check all agents and send idle reminders for unread messages
        
        This method now:
        1. Clears any legacy queued messages
        2. Sends reminders to idle agents who have unread messages
        """
        for agent_name, agent in self.orchestrator.agents.items():
            # Update state
            state = self.state_monitor.update_agent_state(agent_name, agent.pane_index)
            
            # First, handle any legacy pending messages (from before the change)
            if self.state_monitor.has_pending_messages(agent_name):
                pending_messages = self.state_monitor.get_pending_messages(agent_name)
                
                if pending_messages:
                    self.logger.info(f"Clearing {len(pending_messages)} legacy pending messages for {agent_name}")
                    
                    # Add all pending messages to mailbox
                    if agent_name not in self.orchestrator.mailbox:
                        self.orchestrator.mailbox[agent_name] = []
                    self.orchestrator.mailbox[agent_name].extend(pending_messages)
            
            # Now check for idle reminders
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
        
        # Check if agent is idle before sending
        state = self.state_monitor.update_agent_state(agent_name, agent.pane_index)
        if state != AgentState.IDLE:
            self.logger.warning(f"Agent {agent_name} is not idle (state: {state.value}), may not accept input")
            
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