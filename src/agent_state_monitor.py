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
    INITIALIZING = "initializing"  # Agent is starting up
    UNKNOWN = "unknown"


@dataclass
class AgentStatus:
    """Status of an agent"""
    state: AgentState
    last_update: float
    initialization_time: float = field(default_factory=time.time)
    last_activity: Optional[str] = None
    pending_messages: deque = field(default_factory=deque)
    messages_sent_while_busy: int = 0
    

class AgentStateMonitor:
    """Monitors agent states in tmux panes"""
    
    # Patterns to detect agent state
    # IMPORTANT: DO NOT CHANGE THIS PATTERN! It works correctly as is.
    # The pattern ^. matches any character at the start, which includes all spinner characters
    BUSY_PATTERNS = [
        r"^.\s+(Accomplishing|Actioning|Actualizing|Baking|Booping|Brewing|Calculating|Cerebrating|Channelling|Churning|Clauding|Coalescing|Cogitating|Combobulating|Computing|Concocting|Conjuring|Considering|Contemplating|Cooking|Crafting|Creating|Crunching|Deciphering|Deliberating|Determining|Discombobulating|Divining|Doing|Effecting|Elucidating|Enchanting|Envisioning|Finagling|Flibbertigibbeting|Forging|Forming|Frolicking|Generating|Germinating|Hatching|Herding|Honking|Hustling|Ideating|Imagining|Incubating|Inferring|Jiving|Manifesting|Marinating|Meandering|Moseying|Mulling|Mustering|Musing|Noodling|Percolating|Perusing|Philosophising|Pondering|Pontificating|Processing|Puttering|Puzzling|Reticulating|Ruminating|Scheming|Schlepping|Shimmying|Shucking|Simmering|Smooshing|Spelunking|Spinning|Stewing|Sussing|Synthesizing|Thinking|Tinkering|Transmuting|Unfurling|Unravelling|Vibing|Wandering|Whirring|Wibbling|Wizarding|Working|Wrangling)…",  # Processing indicator
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
    
    INITIALIZING_PATTERNS = [
        r"Starting Claude",
        r"Initializing",
        r"Loading",
        r"Connecting",
        r"Welcome to Claude",
        r"Claude Code v\d+\.\d+",
    ]
    
    def __init__(self, tmux_manager):
        self.tmux = tmux_manager
        self.logger = logging.getLogger(__name__)
        self.agent_states: Dict[str, AgentStatus] = {}
        
    def detect_agent_state(self, pane_content: str, agent_name: str = None) -> AgentState:
        """Detect agent state from pane content with initialization handling"""
        if not pane_content:
            return AgentState.UNKNOWN
            
        # Get lines for analysis
        lines = pane_content.strip().split('\n')
        recent_content = '\n'.join(lines[-20:])
        last_few_lines = '\n'.join(lines[-5:])
        
        # Check agent age for initialization detection
        agent_age = None
        if agent_name and agent_name in self.agent_states:
            agent_age = time.time() - self.agent_states[agent_name].initialization_time
        
        # 1. Check for QUIT first (highest priority)
        for pattern in self.QUIT_PATTERNS:
            if re.search(pattern, recent_content, re.IGNORECASE):
                return AgentState.QUIT
        
        # 2. Check for ERROR (but not if there's a prompt after)
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, last_few_lines, re.IGNORECASE):
                # If there's a prompt box after error, agent recovered
                if not re.search(r'│\s*>', last_few_lines):
                    return AgentState.ERROR
        
        # 3. Check for INITIALIZING (during first 3 seconds or if we see init patterns)
        if agent_age is not None and agent_age < 3:
            # Only consider initializing if we see actual init patterns or just bash prompts
            for pattern in self.INITIALIZING_PATTERNS:
                if re.search(pattern, recent_content, re.IGNORECASE):
                    # But if we see a prompt box, agent has initialized
                    if not re.search(r'╭.*╮.*\n.*│.*>.*│.*\n.*╰.*╯', recent_content, re.DOTALL):
                        return AgentState.INITIALIZING
            
            # If agent is young and we only see bash prompts, it's probably initializing
            if self._contains_only_bash_prompts(recent_content):
                return AgentState.INITIALIZING
        
        # 4. Check for BUSY state by looking for processing indicator
        # The processing indicator appears above the prompt box with specific structure:
        # - Processing line (e.g., "✻ Germinating… (0s ·")
        # - Additional info lines
        # - Empty line
        # - Prompt box (╭─...─╮, │ > ... │, ╰─...─╯)
        
        lines = recent_content.split('\n')
        
        # Find the prompt box top line (╭────────────────────────╮)
        # We need to find the LAST prompt box, as there might be welcome boxes above
        prompt_box_top = -1
        for i, line in enumerate(lines):
            if '╭' in line and '╮' in line and '─' in line:
                # Check if this is likely an input prompt box by looking for '>' in next few lines
                is_input_box = False
                for j in range(i + 1, min(i + 4, len(lines))):
                    if '│' in lines[j] and '>' in lines[j]:
                        is_input_box = True
                        break
                if is_input_box:
                    prompt_box_top = i
        
        if prompt_box_top >= 0:
            # We found the prompt box
            # Check for processing indicator above it 
            # Valid BUSY state structure:
            # - Processing indicator (e.g., "✻ Germinating… (2s")
            # - Optional: token count line (e.g., "↓ 145 tokens")
            # - Optional: interrupt line (e.g., "esc to interrupt)")
            # - REQUIRED: Exactly one empty line
            # - Prompt box
            if prompt_box_top >= 2:  # Need at least 2 lines above for empty line + indicator
                # The line right above prompt box should be empty
                if lines[prompt_box_top - 1].strip() == '':
                    # Check if there's a processing indicator within the 4 lines above the empty line
                    found_indicator = False
                    indicator_line = -1
                    
                    for check_idx in range(max(0, prompt_box_top - 5), prompt_box_top - 1):
                        for pattern in self.BUSY_PATTERNS:
                            if re.search(pattern, lines[check_idx], re.IGNORECASE):
                                found_indicator = True
                                indicator_line = check_idx
                                break
                        if found_indicator:
                            break
                    
                    if found_indicator:
                        # Verify no unrelated content between indicator and empty line
                        # Allow only token count and interrupt messages
                        valid_busy = True
                        for check_idx in range(indicator_line + 1, prompt_box_top - 1):
                            line = lines[check_idx].strip()
                            if line and not any(x in line for x in ['tokens', 'interrupt', '↓', 'esc']):
                                valid_busy = False
                                break
                        
                        if valid_busy:
                            return AgentState.BUSY
            
            # No processing indicator found, check if IDLE or WRITING
            # Need to check ALL lines within the prompt box for content
            prompt_box_bottom = -1
            for i in range(prompt_box_top + 1, len(lines)):
                if '╰' in lines[i] and '╯' in lines[i]:
                    prompt_box_bottom = i
                    break
            
            if prompt_box_bottom > prompt_box_top:
                # Check all lines between top and bottom of box
                has_text = False
                for i in range(prompt_box_top + 1, prompt_box_bottom):
                    if '│' in lines[i] and '>' in lines[i]:
                        # This is the prompt line, check for text after >
                        match = re.search(r'>\s*(.*)(?=\s*│)', lines[i])
                        if match and match.group(1).strip():
                            text = match.group(1).strip()
                            # TODO: This is a temporary fix. Better solution would be to detect cursor position
                            # or text color to distinguish Claude's grayed-out suggestions from actual user input
                            # Skip Claude's startup suggestions
                            if text.startswith('Try "'):
                                continue
                            has_text = True
                            break
                    elif '│' in lines[i]:
                        # Continuation line, check if it has content
                        match = re.search(r'│\s*([^│]+)\s*│', lines[i])
                        if match and match.group(1).strip():
                            has_text = True
                            break
                
                return AgentState.WRITING if has_text else AgentState.IDLE
        
        # 6. Fallback: look for any prompt indicator
        if '│' in last_few_lines and '>' in last_few_lines:
            # Check for text after prompt
            prompt_match = re.search(r'│\s*>\s*(.+)', last_few_lines)
            if prompt_match and prompt_match.group(1).strip():
                text = prompt_match.group(1).strip()
                # TODO: Same temporary fix as above - skip Claude's suggestions
                if not text.startswith('Try "'):
                    return AgentState.WRITING
            # Only return IDLE if we clearly see an empty prompt box
            # Otherwise return UNKNOWN
            if re.search(r'│\s*>\s*│', last_few_lines):
                return AgentState.IDLE
        
        # 7. If we can't determine the state clearly, return UNKNOWN
        # Don't make assumptions during initialization
        return AgentState.UNKNOWN
    
    def _contains_only_bash_prompts(self, content: str) -> bool:
        """Check if content contains only bash prompts (no Claude UI)"""
        lines = content.strip().split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if not non_empty_lines:
            return True
            
        # Look for typical bash prompt patterns
        bash_patterns = [
            r'^\w+@\w+:.*\$$',  # user@host:path$
            r'^\$$',             # simple $
            r'^\#$',             # root #
        ]
        
        bash_line_count = 0
        for line in non_empty_lines[-3:]:  # Check last 3 non-empty lines
            for pattern in bash_patterns:
                if re.match(pattern, line.strip()):
                    bash_line_count += 1
                    break
        
        # If most recent lines are bash prompts, assume bash-only
        return bash_line_count >= min(2, len(non_empty_lines[-3:]))
        
    def update_agent_state(self, agent_name: str, pane_index: int) -> AgentState:
        """Update and return agent state"""
        # Capture pane content
        content = self.tmux.capture_pane(pane_index, history_limit=-50)
        if not content:
            self.logger.warning(f"Could not capture pane for {agent_name}")
            return AgentState.UNKNOWN
            
        # Debug: log content length
        self.logger.debug(f"Captured {len(content)} chars from {agent_name} pane")
        
        # Detect state
        state = self.detect_agent_state(content, agent_name)
        
        # Apply state stability during initialization
        current_time = time.time()
        
        # If agent is new or very young, keep it in initializing state
        if agent_name not in self.agent_states:
            self.agent_states[agent_name] = AgentStatus(
                state=AgentState.INITIALIZING,  # Always start as initializing
                last_update=current_time,
                initialization_time=current_time
            )
        else:
            old_state = self.agent_states[agent_name].state
            agent_age = current_time - self.agent_states[agent_name].initialization_time
            
            self.agent_states[agent_name].state = state
            self.agent_states[agent_name].last_update = current_time
            
            # Log state changes
            if old_state != state:
                self.logger.info(f"Agent {agent_name} state changed: {old_state.value} -> {state.value}")
                
                # If agent became idle and has pending messages
                if state == AgentState.IDLE and self.agent_states[agent_name].pending_messages:
                    self.logger.info(f"Agent {agent_name} is now idle with {len(self.agent_states[agent_name].pending_messages)} pending messages")
                    
        return self.agent_states[agent_name].state
        
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