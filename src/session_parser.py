#!/usr/bin/env python3
"""Parse Claude session files to detect forks and lineage"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

class SessionParser:
    """Parse and analyze Claude session files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_session_file(self, session_file: Path) -> Dict:
        """Parse session file to extract metadata
        
        Claude session files are JSONL with each line containing:
        - sessionId: The session UUID (may change within file for forks)
        - parentUuid: Parent message UUID (for message chaining)
        - uuid: Message UUID
        
        Args:
            session_file: Path to the session JSONL file
            
        Returns:
            Dictionary containing session metadata
            
        Raises:
            FileNotFoundError: If session file doesn't exist
            ValueError: If file cannot be parsed
        """
        if not session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")
            
        session_info = {
            'session_id': session_file.stem,  # Filename is the active session
            'session_changed': False,
            'message_count': 0,
            'all_session_ids': set()  # All sessionIds found in file
        }
        
        try:
            with open(session_file, 'r') as f:
                lines = f.readlines()
                
            if not lines:
                return session_info
                
            session_info['message_count'] = len(lines)
            
            # Check first few messages for session ID changes (fork indicator)
            prev_session_id = None
            for i, line in enumerate(lines[:min(10, len(lines))]):
                try:
                    msg = json.loads(line)
                    current_session_id = msg.get('sessionId')
                    
                    if current_session_id:
                        session_info['all_session_ids'].add(current_session_id)
                        
                        # If sessionId changes, this is a fork
                        if prev_session_id and current_session_id != prev_session_id:
                            session_info['session_changed'] = True
                            self.logger.debug(
                                f"Fork detected in {session_file.name}: "
                                f"{prev_session_id} -> {current_session_id}"
                            )
                            break
                            
                        prev_session_id = current_session_id
                        
                except json.JSONDecodeError:
                    continue
                    
            # Convert set to list for JSON serialization
            session_info['all_session_ids'] = list(session_info['all_session_ids'])
                    
        except Exception as e:
            self.logger.error(f"Failed to parse {session_file}: {e}")
            raise ValueError(f"Cannot parse session file: {e}")
            
        return session_info
    
    def verify_descendant(self, parent_session_id: str, session_file: Path) -> bool:
        """Check if session file is descendant of parent session
        
        A session is a descendant if:
        1. It has the parent_session_id in its sessionId history (fork)
        2. The parent_session field matches
        
        Args:
            parent_session_id: UUID of the parent session
            session_file: Path to the potential descendant session file
            
        Returns:
            True if session_file is a descendant of parent_session_id
            
        Raises:
            ValueError: If file cannot be read or parsed
        """
        if not session_file.exists():
            raise ValueError(f"Session file not found: {session_file}")
            
        try:
            # Parse the file to check for parent relationship
            session_info = self.parse_session_file(session_file)
            
            # Direct parent relationship (fork detected)
            if session_info['session_changed']:
                self.logger.debug(f"Found direct fork: {session_file.stem} forked from {parent_session_id}")
                return True
            
            # Check if parent is in the session ID history
            if parent_session_id in session_info.get('all_session_ids', []):
                self.logger.debug(f"Found parent {parent_session_id} in session history")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to verify descendant relationship: {e}")
            raise ValueError(f"Cannot verify descendant: {e}")