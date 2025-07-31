"""Test helper utilities for creating proper test fixtures"""

import os
import json
import tempfile
import shutil
from typing import Optional, Dict, Any
from datetime import datetime


class SessionTestHelper:
    """Helper for creating real session files for tests"""
    
    def __init__(self):
        self.temp_dirs = []
        
    def create_session_dir(self) -> str:
        """Create a temporary session directory"""
        temp_dir = tempfile.mkdtemp(prefix="claude_test_sessions_")
        self.temp_dirs.append(temp_dir)
        return temp_dir
        
    def create_session_file(self, session_dir: str, session_id: str, 
                          initial_messages: Optional[list] = None) -> str:
        """Create a real session file with optional initial messages"""
        session_file = os.path.join(session_dir, f"{session_id}.jsonl")
        
        if initial_messages is None:
            initial_messages = [
                {
                    "uuid": "init-1",
                    "sessionId": session_id,
                    "type": "system",
                    "timestamp": datetime.now().timestamp(),
                    "message": {
                        "content": "System initialized"
                    }
                }
            ]
            
        with open(session_file, 'w') as f:
            for msg in initial_messages:
                f.write(json.dumps(msg) + '\n')
                
        return session_file
        
    def add_message_to_session(self, session_file: str, message_type: str,
                             content: str, uuid: Optional[str] = None) -> None:
        """Add a message to an existing session file"""
        if uuid is None:
            uuid = f"msg-{datetime.now().timestamp()}"
            
        message = {
            "uuid": uuid,
            "sessionId": os.path.basename(session_file).replace('.jsonl', ''),
            "type": message_type,
            "timestamp": datetime.now().timestamp(),
            "message": {
                "content": content if message_type == "user" else [{"type": "text", "text": content}]
            }
        }
        
        with open(session_file, 'a') as f:
            f.write(json.dumps(message) + '\n')
            
    def cleanup(self):
        """Clean up all temporary directories"""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
                
class MockTmuxHelper:
    """Helper for creating properly configured tmux mocks"""
    
    @staticmethod
    def create_mock_tmux(success=True, session_ids=None):
        """Create a mock tmux manager with proper behavior"""
        from unittest.mock import MagicMock
        
        mock_tmux = MagicMock()
        mock_tmux.create_session.return_value = success
        mock_tmux.set_pane_title.return_value = True
        mock_tmux.kill_session.return_value = True
        mock_tmux.send_to_pane.return_value = True
        
        # If session_ids provided, return them in order
        if session_ids:
            mock_tmux.launch_claude_in_pane.side_effect = session_ids
        else:
            # Generate unique session IDs
            import uuid
            mock_tmux.launch_claude_in_pane.side_effect = lambda *args, **kwargs: str(uuid.uuid4())
            
        return mock_tmux