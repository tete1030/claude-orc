"""
Session Monitor Module
Monitors Claude session files for commands and messages
"""

import json
import os
import re
import logging
import time
from typing import List, Dict, Optional, Set, Any, Pattern
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a message from session file"""
    uuid: str
    session_id: str
    type: str  # user, assistant, system
    timestamp: float
    content: str
    raw_data: Dict[str, Any]


@dataclass
class Command:
    """Represents an extracted command"""
    uuid: str
    timestamp: float
    sender_type: str  # user or assistant
    agent_name: str
    command_type: str
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[str] = None
    raw_content: str = ""


class SessionMonitor:
    """Monitor Claude session files for orchestrator commands"""
    
    def __init__(self, session_file: str, agent_name: str):
        self.session_file = session_file
        self.agent_name = agent_name
        self.last_position = 0
        self.processed_uuids: Set[str] = set()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Compile regex patterns for efficiency
        # Support both name= and type= for backward compatibility
        self.command_pattern: Pattern = re.compile(
            r'<orc-command\s+(?:name|type)=["\']([^"\']+)["\'](?:\s+[^>]+)?>(.*?)</orc-command>',
            re.DOTALL | re.IGNORECASE
        )
        
        self.field_patterns = {
            'from': re.compile(r'<from>(.*?)</from>', re.DOTALL),
            'to': re.compile(r'<to>(.*?)</to>', re.DOTALL),
            'title': re.compile(r'<title>(.*?)</title>', re.DOTALL),
            'content': re.compile(r'<content>(.*?)</content>', re.DOTALL),
            'priority': re.compile(r'<priority>(.*?)</priority>', re.DOTALL)
        }
        
    def get_new_messages(self) -> List[Message]:
        """Read new messages since last check"""
        if not os.path.exists(self.session_file):
            self.logger.debug(f"Session file not found: {self.session_file}")
            return []
            
        new_messages = []
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                # Seek to last read position
                f.seek(self.last_position)
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line)
                        msg_uuid = data.get('uuid')
                        
                        # Skip if already processed
                        if msg_uuid and msg_uuid in self.processed_uuids:
                            continue
                            
                        if msg_uuid:
                            self.processed_uuids.add(msg_uuid)
                            
                        # Extract message content
                        message = self._parse_message(data)
                        if message:
                            new_messages.append(message)
                            
                    except json.JSONDecodeError as e:
                        self.logger.debug(f"Failed to parse JSON line: {e}")
                        continue
                        
                # Update position for next read
                self.last_position = f.tell()
                
        except Exception as e:
            self.logger.error(f"Error reading session file: {e}")
            
        return new_messages
    
    def _parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse message from session data"""
        msg_type = data.get('type')
        if msg_type not in ['user', 'assistant', 'system']:
            return None
            
        msg_data = data.get('message', {})
        content = ""
        
        if msg_type == 'user':
            # User messages have simple content
            msg_content = msg_data.get('content', '')
            # Handle list content (like tool results)
            if isinstance(msg_content, list):
                # Convert tool results to string representation
                for item in msg_content:
                    if isinstance(item, dict) and item.get('type') == 'tool_result':
                        content += f"[Tool Result: {item.get('content', '')}]\n"
                    else:
                        content += str(item) + '\n'
            else:
                content = msg_content
        elif msg_type == 'assistant':
            # Assistant messages have content array
            content_blocks = msg_data.get('content', [])
            for block in content_blocks:
                if isinstance(block, dict) and block.get('type') == 'text':
                    content += block.get('text', '')
        elif msg_type == 'system':
            # System messages might have content
            content = msg_data.get('content', '')
            
        if not content:
            return None
            
        return Message(
            uuid=data.get('uuid', ''),
            session_id=data.get('sessionId', ''),
            type=msg_type,
            timestamp=data.get('timestamp', time.time()),
            content=content,
            raw_data=data
        )
    
    def extract_commands(self, messages: List[Message]) -> List[Command]:
        """Extract orc-commands from messages"""
        commands = []
        
        for msg in messages:
            # Skip if content is not a string
            if not isinstance(msg.content, str):
                continue
                
            # Find all commands in the message content
            for match in self.command_pattern.finditer(msg.content):
                command_type = match.group(1)
                command_content = match.group(2).strip()
                
                # Create command object
                cmd = Command(
                    uuid=msg.uuid,
                    timestamp=msg.timestamp,
                    sender_type=msg.type,
                    agent_name=self.agent_name,
                    command_type=command_type,
                    raw_content=command_content
                )
                
                # Extract fields based on command type
                if command_type == 'send_message':
                    # Pass the full match to parse attributes from the tag
                    self._parse_send_message_fields(cmd, match.group(0))
                    
                commands.append(cmd)
                
                self.logger.debug(f"Extracted command: {command_type} from {cmd.from_agent}")
                
        return commands
    
    def _parse_send_message_fields(self, cmd: Command, full_match: str) -> None:
        """Parse send_message command fields from XML attributes and content"""
        # First try to extract attributes from the opening tag
        import re
        tag_match = re.match(r'<orc-command\s+([^>]+)>', full_match)
        
        if tag_match:
            attributes_str = tag_match.group(1)
            # Parse each attribute
            attr_pattern = re.compile(r'(\w+)=["\']([^"\']+)["\']')
            
            # Map XML attribute names to Command attribute names
            field_mapping = {
                'from': 'from_agent',
                'to': 'to_agent',
                'title': 'title',
                'priority': 'priority'
            }
            
            for attr_match in attr_pattern.finditer(attributes_str):
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2)
                
                # Skip 'name' and 'type' attributes as they're the command type
                if attr_name in ['name', 'type']:
                    continue
                    
                # Use the mapped attribute name
                cmd_attr = field_mapping.get(attr_name, attr_name)
                setattr(cmd, cmd_attr, attr_value)
        
        # If we didn't get fields from attributes, try nested XML format
        if not cmd.from_agent:
            # Use the field patterns to extract from nested tags
            for field_name, pattern in self.field_patterns.items():
                match = pattern.search(cmd.raw_content)
                if match:
                    value = match.group(1).strip()
                    if field_name == 'from':
                        cmd.from_agent = value
                    elif field_name == 'to':
                        cmd.to_agent = value
                    elif field_name == 'title':
                        cmd.title = value
                    elif field_name == 'priority':
                        cmd.priority = value
                    elif field_name == 'content':
                        cmd.content = value
        
        # If content wasn't in a nested tag, use the raw content
        if not cmd.content and cmd.raw_content:
            # Remove any nested XML tags from raw content
            content = cmd.raw_content
            for pattern in self.field_patterns.values():
                content = pattern.sub('', content)
            cmd.content = content.strip()
    
    def reset(self) -> None:
        """Reset monitor state"""
        self.last_position = 0
        self.processed_uuids.clear()
        self.logger.info(f"Reset monitor for {self.agent_name}")
    
    def get_file_size(self) -> int:
        """Get current session file size"""
        try:
            return os.path.getsize(self.session_file)
        except OSError:
            return 0