"""
Agent State Monitor - Tracks agent busy/idle states and handles message delivery
"""

import re
import time
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class AgentState(Enum):
    """Agent states"""
    IDLE = "idle"
    BUSY = "busy"
    WRITING = "writing"  # Has typed text but not sent
    ERROR = "error"
    QUIT = "quit"
    UNKNOWN = "unknown"


@dataclass
class AgentStatus:
    """Status of an agent"""
    state: AgentState
    last_update: float
    last_activity: Optional[str] = None
    pending_messages: deque = field(default_factory=deque)
    messages_sent_while_busy: int = 0
    

class AgentStateMonitor:
    """Monitors agent states in tmux panes"""
    
    # Patterns to detect agent state
    BUSY_PATTERNS = [
        r"^.\s+(Accomplishing|Actioning|Actualizing|Baking|Booping|Brewing|Calculating|Cerebrating|Channelling|Churning|Clauding|Coalescing|Cogitating|Combobulating|Computing|Concocting|Conjuring|Considering|Contemplating|Cooking|Crafting|Creating|Crunching|Deciphering|Deliberating|Determining|Discombobulating|Divining|Doing|Effecting|Elucidating|Enchanting|Envisioning|Finagling|Flibbertigibbeting|Forging|Forming|Frolicking|Generating|Germinating|Hatching|Herding|Honking|Hustling|Ideating|Imagining|Incubating|Inferring|Jiving|Manifesting|Marinating|Meandering|Moseying|Mulling|Mustering|Musing|Noodling|Percolating|Perusing|Philosophising|Pondering|Pontificating|Processing|Puttering|Puzzling|Reticulating|Ruminating|Scheming|Schlepping|Shimmying|Shucking|Simmering|Smooshing|Spelunking|Spinning|Stewing|Sussing|Synthesizing|Thinking|Tinkering|Transmuting|Unfurling|Unravelling|Vibing|Wandering|Whirring|Wibbling|Wizarding|Working|Wrangling)…",  # Without timer (simpler format)
    ]
    
    IDLE_PATTERNS = [
        r"╭─+╮\s*\n\s*│\s*>\s*",  # Claude prompt box pattern
        r"│\s*>",  # Simplified prompt pattern (just needs the prompt indicator)
        r"\? for shortcuts",  # Claude is waiting at bottom
        r"Press Enter to continue",  # Waiting for input
    ]
    
    ERROR_PATTERNS = [
        r"Error:",
        r"Failed:",
        r"Exception:",
        r"Traceback",
        r"MCP error",
        r"Cannot connect",
    ]
    
    QUIT_PATTERNS = [
        r"Goodbye!",
        r"Session ended",
        r"Claude exited",
        r"Process.*terminated",
    ]
    
    def __init__(self, tmux_manager):
        self.tmux = tmux_manager
        self.logger = logging.getLogger(__name__)
        self.agent_states: Dict[str, AgentStatus] = {}
        
    def detect_agent_state(self, pane_content: str) -> AgentState:
        """Detect agent state from pane content"""
        if not pane_content:
            return AgentState.UNKNOWN
            
        # Get last 20 lines for analysis
        lines = pane_content.strip().split('\n')
        recent_content = '\n'.join(lines[-20:])
        
        # Check for errors first (highest priority)
        # Only consider it an error if the error is in the last 5 lines (recent/active)
        last_few_lines = '\n'.join(lines[-5:])
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, last_few_lines, re.IGNORECASE):
                # But not if there's a prompt box after the error (agent recovered)
                if not re.search(r'│\s*>', last_few_lines):
                    return AgentState.ERROR
                
        # Check if quit
        for pattern in self.QUIT_PATTERNS:
            if re.search(pattern, recent_content, re.IGNORECASE):
                return AgentState.QUIT
                
        # Check if busy FIRST - if we see processing indicator, Claude is busy
        # even if the prompt box is still visible below it
        for pattern in self.BUSY_PATTERNS:
            if re.search(pattern, recent_content, re.IGNORECASE | re.MULTILINE):
                return AgentState.BUSY
                
        # Check if idle (looking for prompt box)
        for pattern in self.IDLE_PATTERNS:
            if re.search(pattern, recent_content, re.MULTILINE | re.DOTALL):
                # Check if there's text after the prompt (WRITING state)
                # Look for prompt box with content after '>'
                prompt_match = re.search(r'│\s*>\s*(.+?)\s*│', recent_content)
                if prompt_match and prompt_match.group(1).strip():
                    return AgentState.WRITING
                return AgentState.IDLE
                
        # Default to idle if we see the prompt character in Claude's prompt box
        # But not if it's just a shell prompt with '>'
        last_few_lines = '\n'.join(lines[-3:])
        if '│' in last_few_lines and '>' in last_few_lines:  # Claude's box prompt
            # Check for content after prompt
            prompt_match = re.search(r'│\s*>\s*(.+?)\s*│', last_few_lines)
            if prompt_match and prompt_match.group(1).strip():
                return AgentState.WRITING
            return AgentState.IDLE
            
        return AgentState.UNKNOWN
        
    def update_agent_state(self, agent_name: str, pane_index: int) -> AgentState:
        """Update and return agent state"""
        # Capture pane content
        content = self.tmux.capture_pane(pane_index, history_limit=-50)
        if not content:
            self.logger.warning(f"Could not capture pane for {agent_name}")
            return AgentState.UNKNOWN
            
        # Detect state
        state = self.detect_agent_state(content)
        
        # Update or create agent status
        if agent_name not in self.agent_states:
            self.agent_states[agent_name] = AgentStatus(
                state=state,
                last_update=time.time()
            )
        else:
            old_state = self.agent_states[agent_name].state
            self.agent_states[agent_name].state = state
            self.agent_states[agent_name].last_update = time.time()
            
            # Log state changes
            if old_state != state:
                self.logger.info(f"Agent {agent_name} state changed: {old_state.value} -> {state.value}")
                
                # If agent became idle and has pending messages
                if state == AgentState.IDLE and self.agent_states[agent_name].pending_messages:
                    self.logger.info(f"Agent {agent_name} is now idle with {len(self.agent_states[agent_name].pending_messages)} pending messages")
                    
        return state
        
    def is_agent_busy(self, agent_name: str) -> bool:
        """Check if agent is busy"""
        if agent_name not in self.agent_states:
            return False
        return self.agent_states[agent_name].state == AgentState.BUSY
        
    def is_agent_idle(self, agent_name: str) -> bool:
        """Check if agent is idle"""
        if agent_name not in self.agent_states:
            return False
        return self.agent_states[agent_name].state == AgentState.IDLE
        
    def queue_message_for_agent(self, agent_name: str, message: Dict) -> None:
        """Queue a message for a busy agent"""
        if agent_name not in self.agent_states:
            self.agent_states[agent_name] = AgentStatus(
                state=AgentState.UNKNOWN,
                last_update=time.time()
            )
            
        self.agent_states[agent_name].pending_messages.append(message)
        self.agent_states[agent_name].messages_sent_while_busy += 1
        self.logger.info(f"Queued message for {agent_name} (total: {len(self.agent_states[agent_name].pending_messages)})")
        
    def get_pending_messages(self, agent_name: str) -> List[Dict]:
        """Get and clear pending messages for an agent"""
        if agent_name not in self.agent_states:
            return []
            
        messages = list(self.agent_states[agent_name].pending_messages)
        self.agent_states[agent_name].pending_messages.clear()
        self.agent_states[agent_name].messages_sent_while_busy = 0
        return messages
        
    def has_pending_messages(self, agent_name: str) -> bool:
        """Check if agent has pending messages"""
        if agent_name not in self.agent_states:
            return False
        return len(self.agent_states[agent_name].pending_messages) > 0
        
    def get_agent_summary(self) -> Dict[str, Dict]:
        """Get summary of all agent states"""
        summary = {}
        for agent_name, status in self.agent_states.items():
            summary[agent_name] = {
                'state': status.state.value,
                'last_update': status.last_update,
                'pending_messages': len(status.pending_messages),
                'messages_while_busy': status.messages_sent_while_busy
            }
        return summary