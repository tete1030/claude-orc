# Claude Session File Analysis Results

## Session File Location & Structure

### Location
- Session files are in: `~/.claude/projects/{project-name}/`
- Format: JSONL (JSON Lines - one JSON object per line)
- File naming: UUID format (e.g., `ae881004-5054-42d8-ad1d-48e1dc3ac4ec.jsonl`)

### File Structure Analysis

**File Stats:**
- Size: ~692KB for a moderately active session
- Lines: 253 (each line is a separate JSON message)
- Message types distribution:
  - `assistant`: 99 messages
  - `system`: 84 messages  
  - `user`: 70 messages

### Message Structure

#### Common Fields (all messages):
```json
{
  "uuid": "unique-message-id",
  "parentUuid": "parent-message-id",
  "sessionId": "session-id",
  "timestamp": "ISO-8601-timestamp",
  "type": "user|assistant|system",
  "message": {...},
  "cwd": "/current/working/directory",
  "gitBranch": "current-git-branch",
  "userType": "user-type",
  "version": "version-number",
  "isSidechain": false
}
```

#### User Message Structure:
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "user's message text"
  }
}
```

#### Assistant Message Structure:
```json
{
  "type": "assistant", 
  "message": {
    "id": "msg-id",
    "type": "message",
    "role": "assistant",
    "model": "claude-3-5-sonnet-20241022",
    "content": [
      {
        "type": "text|tool_use|thinking",
        "text": "response text (for text type)",
        "id": "tool-use-id (for tool_use)",
        "name": "tool-name (for tool_use)",
        "input": {tool-input-object},
        "thinking": "thinking text (for thinking type)",
        "signature": "signature (for thinking type)"
      }
    ],
    "stop_reason": "end_turn|max_tokens",
    "stop_sequence": null,
    "usage": {
      "input_tokens": 12345,
      "output_tokens": 678
    }
  }
}
```

### Key Findings for Our System

1. **Command Detection is Feasible**
   - Found 5 instances of `<orc-command` in user messages
   - Found 2 instances in assistant messages
   - Commands will appear in message content field

2. **Message Tracking**
   - Each message has unique UUID
   - Parent UUID links conversations
   - Timestamps for ordering

3. **Content Structure**
   - User messages: Simple string in `message.content`
   - Assistant messages: Array of content blocks in `message.content`
   - Assistant can have multiple content types (text, tool_use, thinking)

## Parsing Strategy for Phase 1

### Session Monitor Implementation

```python
import json
import os
from datetime import datetime

class SessionFileMonitor:
    def __init__(self, session_file_path):
        self.session_file = session_file_path
        self.last_position = 0
        self.processed_uuids = set()
        
    def get_new_messages(self):
        """Read only new messages since last check"""
        if not os.path.exists(self.session_file):
            return []
            
        new_messages = []
        
        with open(self.session_file, 'r') as f:
            # Seek to last read position
            f.seek(self.last_position)
            
            for line in f:
                try:
                    msg = json.loads(line.strip())
                    
                    # Skip if we've already processed this message
                    if msg['uuid'] in self.processed_uuids:
                        continue
                        
                    self.processed_uuids.add(msg['uuid'])
                    new_messages.append(msg)
                    
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
                    
            # Update position for next read
            self.last_position = f.tell()
            
        return new_messages
    
    def extract_commands(self, messages):
        """Extract orc-commands from messages"""
        commands = []
        
        for msg in messages:
            if msg['type'] == 'user':
                # User messages have simple content
                content = msg['message']['content']
                if '<orc-command' in content:
                    commands.append({
                        'from': 'user',
                        'uuid': msg['uuid'],
                        'timestamp': msg['timestamp'],
                        'content': content
                    })
                    
            elif msg['type'] == 'assistant':
                # Assistant messages have content array
                for content_block in msg['message']['content']:
                    if content_block.get('type') == 'text':
                        text = content_block.get('text', '')
                        if '<orc-command' in text:
                            commands.append({
                                'from': 'assistant',
                                'uuid': msg['uuid'],
                                'timestamp': msg['timestamp'],
                                'content': text
                            })
                            
        return commands
```

## Important Considerations

1. **File Size Management**
   - Sessions can grow large (692KB+)
   - Use incremental reading (seek/tell)
   - Track processed UUIDs to avoid duplicates

2. **Real-time Monitoring**
   - File is appended to, not rewritten
   - Poll interval of 1-2 seconds should be sufficient
   - Watch for file rotation (new session = new file)

3. **Message Parsing**
   - User messages: Direct string content
   - Assistant messages: Array of content blocks
   - System messages: May contain important state info

4. **Error Handling**
   - Handle incomplete JSON lines (being written)
   - Skip malformed entries
   - Handle file not found (session not started)

## Next Steps

1. Implement basic session monitor with command extraction
2. Test with real Claude sessions
3. Add robust error handling
4. Optimize for performance with large files