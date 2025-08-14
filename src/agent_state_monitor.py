"""
Agent State Monitor - Tracks agent busy/idle states and handles message delivery
"""

import re
import time
import logging
import json
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any
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


@dataclass
class AnomalyRecord:
    """Individual anomaly record with metadata"""
    timestamp: float
    agent_name: str
    anomaly_type: str
    line_num: int
    content: str
    context: List[str]
    pane_state: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'agent_name': self.agent_name,
            'anomaly_type': self.anomaly_type,
            'line_num': self.line_num,
            'content': self.content,
            'context': self.context,
            'pane_state': self.pane_state
        }


@dataclass 
class AnomalyHistoryConfig:
    """Configuration for anomaly history tracking"""
    max_records_per_agent: int = 1000
    max_total_records: int = 5000
    retention_hours: float = 24.0
    enable_persistence: bool = False
    persistence_path: Optional[str] = None


class AnomalyHistory:
    """Manages historical anomaly records"""
    
    def __init__(self, config: AnomalyHistoryConfig = None):
        self.config = config or AnomalyHistoryConfig()
        self.history: Dict[str, deque] = {}
        self._total_records = 0
        
    def record_anomalies(self, agent_name: str, anomalies: List[dict], 
                        pane_state: Optional[str] = None) -> None:
        """Record new anomalies for an agent"""
        if agent_name not in self.history:
            self.history[agent_name] = deque(maxlen=self.config.max_records_per_agent)
            
        timestamp = time.time()
        
        for anomaly in anomalies:
            anomaly_type = self._classify_anomaly_type(anomaly['content'])
            
            record = AnomalyRecord(
                timestamp=timestamp,
                agent_name=agent_name,
                anomaly_type=anomaly_type,
                line_num=anomaly['line_num'],
                content=anomaly['content'],
                context=anomaly.get('context', []),
                pane_state=pane_state
            )
            
            self.history[agent_name].append(record)
            self._total_records += 1
            
        self._apply_retention()
        
    def _classify_anomaly_type(self, content: str) -> str:
        """Classify anomaly type based on content"""
        if "Multiple input boxes" in content:
            return "multiple_input_boxes"
        elif "Incomplete prompt box" in content:
            return "incomplete_box"
        elif "Unrecognized box type" in content:
            return "unknown_box_type"
        elif "Too many prompt boxes" in content:
            return "too_many_boxes"
        else:
            return "other"
            
    def _apply_retention(self) -> None:
        """Apply retention policies to limit history size"""
        current_time = time.time()
        cutoff_time = current_time - (self.config.retention_hours * 3600)
        
        # Remove old records
        for agent_name, records in self.history.items():
            while records and records[0].timestamp < cutoff_time:
                records.popleft()
                self._total_records -= 1
                
        # Apply total size limit
        if self._total_records > self.config.max_total_records:
            all_records = []
            for agent_name, records in self.history.items():
                all_records.extend([(r.timestamp, agent_name) for r in records])
            
            all_records.sort()
            to_remove = self._total_records - self.config.max_total_records
            
            for _, agent_name in all_records[:to_remove]:
                if self.history[agent_name]:
                    self.history[agent_name].popleft()
                    self._total_records -= 1
                    
    def query_history(self, agent_name: Optional[str] = None,
                     anomaly_type: Optional[str] = None,
                     start_time: Optional[float] = None,
                     end_time: Optional[float] = None,
                     limit: int = 100) -> List[AnomalyRecord]:
        """Query anomaly history with filters"""
        results = []
        
        if agent_name:
            agents = [agent_name] if agent_name in self.history else []
        else:
            agents = list(self.history.keys())
            
        for agent in agents:
            for record in self.history[agent]:
                if anomaly_type and record.anomaly_type != anomaly_type:
                    continue
                if start_time and record.timestamp < start_time:
                    continue
                if end_time and record.timestamp > end_time:
                    continue
                    
                results.append(record)
                
                if len(results) >= limit:
                    return results
                    
        return results
        
    def get_summary(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics of anomalies"""
        summary = {
            'total_records': 0,
            'by_type': {},
            'by_agent': {},
            'oldest_record': None,
            'newest_record': None
        }
        
        agents = [agent_name] if agent_name else list(self.history.keys())
        
        for agent in agents:
            if agent not in self.history:
                continue
                
            agent_records = list(self.history[agent])
            if not agent_records:
                continue
                
            summary['by_agent'][agent] = len(agent_records)
            summary['total_records'] += len(agent_records)
            
            for record in agent_records:
                anomaly_type = record.anomaly_type
                summary['by_type'][anomaly_type] = summary['by_type'].get(anomaly_type, 0) + 1
                
                if not summary['oldest_record'] or record.timestamp < summary['oldest_record']:
                    summary['oldest_record'] = record.timestamp
                if not summary['newest_record'] or record.timestamp > summary['newest_record']:
                    summary['newest_record'] = record.timestamp
                    
        return summary
        
    def export_report(self, output_format: str = 'json',
                     agent_name: Optional[str] = None,
                     start_time: Optional[float] = None,
                     end_time: Optional[float] = None) -> str:
        """Export anomaly report in specified format"""
        records = self.query_history(
            agent_name=agent_name,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        if output_format == 'json':
            return json.dumps({
                'summary': self.get_summary(agent_name),
                'records': [r.to_dict() for r in records]
            }, indent=2)
        elif output_format == 'csv':
            lines = ['timestamp,datetime,agent_name,anomaly_type,line_num,content']
            for record in records:
                lines.append(f"{record.timestamp},{datetime.fromtimestamp(record.timestamp).isoformat()},"
                           f"{record.agent_name},{record.anomaly_type},{record.line_num},"
                           f'"{record.content}"')
            return '\n'.join(lines)
        elif output_format == 'text':
            lines = [f"Anomaly Report - Generated at {datetime.now().isoformat()}"]
            lines.append("=" * 60)
            
            summary = self.get_summary(agent_name)
            lines.append(f"Total Records: {summary['total_records']}")
            lines.append(f"Date Range: {datetime.fromtimestamp(summary['oldest_record']).isoformat() if summary['oldest_record'] else 'N/A'} to "
                        f"{datetime.fromtimestamp(summary['newest_record']).isoformat() if summary['newest_record'] else 'N/A'}")
            lines.append("\nAnomalies by Type:")
            for atype, count in summary['by_type'].items():
                lines.append(f"  {atype}: {count}")
            lines.append("\nAnomalies by Agent:")
            for agent, count in summary['by_agent'].items():
                lines.append(f"  {agent}: {count}")
                
            lines.append("\n" + "=" * 60)
            lines.append("Detailed Records:")
            lines.append("=" * 60)
            
            for record in records:
                lines.append(f"\n[{datetime.fromtimestamp(record.timestamp).isoformat()}] "
                           f"{record.agent_name} - {record.anomaly_type}")
                lines.append(f"  Line {record.line_num}: {record.content}")
                if record.context:
                    lines.append("  Context:")
                    for ctx_line in record.context[:3]:
                        lines.append(f"    {ctx_line}")
                        
            return '\n'.join(lines)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
    

class AgentStateMonitor:
    """Monitors agent states in tmux panes"""
    
    # Patterns to detect agent state
    # IMPORTANT: DO NOT CHANGE THIS PATTERN! It works correctly as is.
    # The pattern ^. matches any character at the start, which includes all spinner characters
    BUSY_PATTERNS = [
        # IMPORTANT: DO NOT CHANGE THIS PATTERN! It works correctly as is.
        # The pattern ^. matches any character at the start, which includes all spinner characters
        r"^.\s+(Accomplishing|Actioning|Actualizing|Analyzing|Baking|Booping|Brewing|Calculating|Cerebrating|Channelling|Churning|Clauding|Coalescing|Cogitating|Combobulating|Computing|Concocting|Conjuring|Considering|Contemplating|Cooking|Crafting|Creating|Crunching|Deciphering|Deliberating|Determining|Discombobulating|Divining|Doing|Effecting|Elucidating|Enchanting|Envisioning|Finagling|Flibbertigibbeting|Forging|Forming|Frolicking|Generating|Germinating|Hatching|Herding|Honking|Hustling|Ideating|Imagining|Incubating|Inferring|Jiving|Manifesting|Marinating|Meandering|Moseying|Mulling|Mustering|Musing|Noodling|Percolating|Perusing|Philosophising|Polishing|Pondering|Pontificating|Processing|Puttering|Puzzling|Reticulating|Reviewing|Ruminating|Scheming|Schlepping|Shimmying|Shucking|Simmering|Smooshing|Spelunking|Spinning|Stewing|Sussing|Synthesizing|Thinking|Tinkering|Transmuting|Unfurling|Unravelling|Vibing|Wandering|Whirring|Wibbling|Wizarding|Working|Wrangling)…",  # Processing indicator
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
        r"^\[Process.*terminated\]$",  # More specific - must be on its own line with brackets
        r"^Process exited with",  # More specific - at start of line
    ]
    
    FEEDBACK_UI_PATTERNS = [
        r"How is Claude doing this session\?",  # Feedback prompt
        r"1:\s*Bad\s+2:\s*Fine\s+3:\s*Good\s+0:\s*Dismiss",  # Feedback options
        r"✓ Thanks for helping make Claude better!",  # Feedback confirmation
        r"Thanks for helping make Claude better",  # Alternate confirmation
    ]
    
    INITIALIZING_PATTERNS = [
        r"Starting Claude",
        r"Initializing",
        r"Loading",
        r"Connecting",
        r"Welcome to Claude",
        r"Claude Code v\d+\.\d+",
    ]
    
    def __init__(self, tmux_manager, anomaly_history_config: Optional[AnomalyHistoryConfig] = None):
        self.tmux = tmux_manager
        self.logger = logging.getLogger(__name__)
        self.agent_states: Dict[str, AgentStatus] = {}
        
        # Initialize anomaly history
        self.anomaly_history = AnomalyHistory(anomaly_history_config)
        self.anomaly_monitoring_enabled = True
        
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
        
        # Filter out feedback UI elements before processing
        filtered_recent = recent_content
        filtered_last_few = last_few_lines
        for pattern in self.FEEDBACK_UI_PATTERNS:
            filtered_recent = re.sub(pattern, '', filtered_recent, flags=re.IGNORECASE)
            filtered_last_few = re.sub(pattern, '', filtered_last_few, flags=re.IGNORECASE)
        
        # 1. Check for QUIT first (highest priority) with context checking
        for pattern in self.QUIT_PATTERNS:
            match = re.search(pattern, recent_content, re.IGNORECASE | re.MULTILINE)
            if match:
                # Check if there's an active prompt box AFTER the quit pattern
                match_pos = match.start()
                after_match = recent_content[match_pos:]
                
                # If we see an active prompt box after, agent hasn't quit
                if re.search(r'╭.*╮.*\n.*│.*>.*│.*\n.*╰.*╯', after_match, re.DOTALL):
                    continue
                    
                # If we see processing indicators after, agent hasn't quit
                if any(re.search(f'{word}…', after_match) for word in [
                    'Accomplishing', 'Working', 'Processing', 'Thinking', 'Analyzing'
                ]):
                    continue
                    
                return AgentState.QUIT
        
        # 2. Check for ERROR (but not if there's a prompt after)
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, filtered_last_few, re.IGNORECASE):
                # If there's a prompt box after error, agent recovered
                if not re.search(r'│\s*>', filtered_last_few):
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
        
        lines = filtered_recent.split('\n')
        
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
                        # Strip line before checking to handle leading spaces from snapshot formatting
                        line_to_check = lines[check_idx].strip()
                        for pattern in self.BUSY_PATTERNS:
                            if re.search(pattern, line_to_check, re.IGNORECASE):
                                found_indicator = True
                                indicator_line = check_idx
                                break
                        if found_indicator:
                            break
                    
                    if found_indicator:
                        # Verify no unrelated content between indicator and empty line
                        # Allow only token count, interrupt messages, and message notifications
                        valid_busy = True
                        for check_idx in range(indicator_line + 1, prompt_box_top - 1):
                            line = lines[check_idx].strip()
                            # Allow expected lines between indicator and prompt box
                            allowed_patterns = [
                                'tokens',      # Token count
                                'interrupt',   # Interrupt message
                                '↓',          # Token arrow
                                'esc',        # Escape message
                                '[MESSAGE]',  # Message notifications
                                'check_messages',  # Part of message notification
                                'You have a new message',  # Message notification text
                                'Reminder:',   # Idle reminder messages
                                '⎿',          # Continuation character
                                'Tip:',       # Tip messages that appear after processing
                                '/statusline' # Part of tip messages
                            ]
                            if line and not any(x in line for x in allowed_patterns):
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
        if '│' in filtered_last_few and '>' in filtered_last_few:
            # Check for text after prompt
            prompt_match = re.search(r'│\s*>\s*(.+)', filtered_last_few)
            if prompt_match and prompt_match.group(1).strip():
                text = prompt_match.group(1).strip()
                # TODO: Same temporary fix as above - skip Claude's suggestions
                if not text.startswith('Try "'):
                    return AgentState.WRITING
            # Only return IDLE if we clearly see an empty prompt box
            # Otherwise return UNKNOWN
            if re.search(r'│\s*>\s*│', filtered_last_few):
                return AgentState.IDLE
        
        # 7. If we can't determine the state clearly, return UNKNOWN
        # Don't make assumptions during initialization
        return AgentState.UNKNOWN
    
    def _classify_box_type(self, lines: List[str], box: dict) -> str:
        """
        Classify a box based on its content.
        Returns: 'welcome', 'input', 'message', 'unknown'
        """
        # Extract box content
        box_content = []
        for idx in box['middle']:
            if idx < len(lines):
                # Remove box borders
                content = lines[idx].strip()
                if content.startswith('│') and content.endswith('│'):
                    content = content[1:-1].strip()
                box_content.append(content)
        
        # Join all content
        full_content = ' '.join(box_content)
        
        # Classification rules
        if 'Welcome to Claude Code' in full_content:
            return 'welcome'
        elif re.search(r'^\s*>\s*', full_content):
            # Any input box with > prompt (includes empty prompt, commands, and typing)
            return 'input'
        elif 'MESSAGE' in full_content or 'message' in full_content:
            return 'message'
        elif any(keyword in full_content for keyword in ['Tip:', 'Note:', 'Warning:', 'Error:']):
            return 'info'
        elif 'Permissions:' in full_content and ('Allow' in full_content or 'Deny' in full_content):
            return 'dialog'  # Permissions dialog
        elif any(keyword in full_content for keyword in [
            'Settings', 'Configure Claude Code',
            'Agents', 'Create new agent', 
            'Hook Configuration', 'Select Model'
        ]):
            return 'dialog'  # Other dialog types
        elif len(full_content.strip()) == 0:
            return 'empty'
        else:
            return 'unknown'
    
    def detect_ui_anomalies(self, pane_content: str) -> list:
        """
        Detect structural anomalies in UI layout.
        Focuses on UI structure, not content.
        Returns list of anomalies found.
        """
        anomalies = []
        lines = pane_content.split('\n')
        
        # Structural patterns
        PROMPT_BOX_TOP = r'╭[─]+╮'
        PROMPT_BOX_MIDDLE = r'│.*│'
        PROMPT_BOX_BOTTOM = r'╰[─]+╯'
        SHORTCUTS_LINE = r'\? for shortcuts'
        PERMISSIONS_LINE = r'Bypassing Permissions'
        
        # Find all prompt boxes
        prompt_boxes = []
        i = 0
        while i < len(lines):
            if re.match(PROMPT_BOX_TOP, lines[i]):
                box = {'top': i, 'middle': [], 'bottom': None, 'type': None}
                i += 1
                
                # Find middle and bottom
                while i < len(lines) and i < box['top'] + 10:  # Reasonable box size limit
                    if re.match(PROMPT_BOX_MIDDLE, lines[i]):
                        box['middle'].append(i)
                        i += 1
                    elif re.match(PROMPT_BOX_BOTTOM, lines[i]):
                        box['bottom'] = i
                        break
                    else:
                        break
                
                if box['bottom'] is not None:
                    # Classify the box type
                    box['type'] = self._classify_box_type(lines, box)
                    prompt_boxes.append(box)
                else:
                    # Check if this is a dialog/menu box (which often don't have bottom borders)
                    # Extract content to check if it's a dialog
                    box_content = []
                    for idx in box['middle']:
                        if idx < len(lines):
                            content = lines[idx].strip()
                            if content.startswith('│') and content.endswith('│'):
                                content = content[1:-1].strip()
                            box_content.append(content)
                    
                    full_content = ' '.join(box_content)
                    
                    # Check if it's a known dialog type (these normally don't have bottom borders)
                    dialog_keywords = [
                        'Settings', 'Configure Claude Code',
                        'Agents', 'Create new agent',
                        'Hook Configuration', 'Hooks are shell commands',
                        'Select Model', 'Switch between Claude models'
                    ]
                    
                    is_dialog = any(keyword in full_content for keyword in dialog_keywords)
                    
                    if not is_dialog:
                        # Only flag as anomaly if it's not a known dialog type
                        anomalies.append({
                            'line_num': box['top'],
                            'content': f"Incomplete prompt box starting at line {box['top']}",
                            'context': lines[box['top']:min(len(lines), box['top']+5)]
                        })
            i += 1
        
        # Check for structural anomalies based on box types
        
        # Count boxes by type
        box_types = {}
        for box in prompt_boxes:
            box_type = box.get('type', 'unknown')
            box_types[box_type] = box_types.get(box_type, 0) + 1
        
        # Anomaly rules based on box types
        # 1. Multiple input boxes (should only have one)
        if box_types.get('input', 0) > 1:
            # Find the second input box
            input_count = 0
            for box in prompt_boxes:
                if box['type'] == 'input':
                    input_count += 1
                    if input_count == 2:
                        anomalies.append({
                            'line_num': box['top'],
                            'content': f"Multiple input boxes detected ({box_types['input']} found)",
                            'context': []
                        })
                        break
        
        # 2. Unknown box types might indicate UI issues
        if box_types.get('unknown', 0) > 0:
            for box in prompt_boxes:
                if box['type'] == 'unknown':
                    anomalies.append({
                        'line_num': box['top'],
                        'content': f"Unrecognized box type",
                        'context': lines[box['top']:box['bottom']+1] if box['bottom'] else []
                    })
                    break  # Only report first unknown
        
        # Normal scenarios (not anomalies):
        # - One welcome box + one input box
        # - Message boxes (any number)
        # - Info boxes (any number)
        
        # 2. No prompt box (might be initializing or error state)
        # Don't flag as anomaly since this is common during initialization
        
        # 3. Check for unexpected structural elements
        # Check ALL lines, not just above prompt boxes
        for i in range(len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            
            # Skip lines that are part of valid prompt boxes
            skip_line = False
            for box in prompt_boxes:
                if box['top'] <= i <= box['bottom']:
                    skip_line = True
                    break
            
            if skip_line:
                continue
            
            # Check for unusual separators
            if re.match(r'^[═━┃┏┓┗┛]+$', line) and len(line) > 10:
                anomalies.append({
                    'line_num': i,
                    'content': line,
                    'context': lines[max(0, i-2):min(len(lines), i+3)]
                })
            
            # Check for box chars outside expected areas
            unexpected_box_chars = ['┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼']
            if any(char in line for char in unexpected_box_chars):
                anomalies.append({
                    'line_num': i,
                    'content': line,
                    'context': lines[max(0, i-2):min(len(lines), i+3)]
                })
        
        # 4. Footer elements are OPTIONAL - do not check for them
        # "? for shortcuts" only appears when input box is empty
        # "Bypassing Permissions" can be hidden by startup parameters
        # These are not structural requirements
        
        return anomalies
    
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
        
        # Detect UI anomalies first
        anomalies = self.detect_ui_anomalies(content)
        if anomalies:
            self.logger.debug(f"UI anomalies detected for {agent_name}: {len(anomalies)} anomaly(ies)")
            # Log first few anomalies for debugging
            for i, anomaly in enumerate(anomalies[:3]):
                self.logger.debug(
                    f"UI Anomaly {i+1} at line {anomaly['line_num']}: {anomaly['content'][:60]}..."
                )
        
        # Detect state
        state = self.detect_agent_state(content, agent_name)
        
        # Extra warning if state is UNKNOWN with anomalies
        if anomalies and state == AgentState.UNKNOWN:
            self.logger.debug(
                f"Agent {agent_name} has UNKNOWN state with UI anomalies. "
                "Claude UI may have changed. Review anomalies for detection updates."
            )
        
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