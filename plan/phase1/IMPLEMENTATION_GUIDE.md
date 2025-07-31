# Phase 1 Implementation Guide

## Quick Start Checklist

### Prerequisites
- [ ] Python 3.8+ installed
- [ ] tmux installed
- [ ] Claude CLI installed and configured
- [ ] Identify Claude session file location

### Implementation Order

1. **Create Project Structure** (15 min)
   ```bash
   mkdir -p multi-agent-system/{prompts,scripts,logs}
   touch orchestrator.py session_monitor.py tmux_manager.py config.yaml
   ```

2. **Start with Tmux Manager** (1 hour)
   - Basic pane creation
   - Send-keys functionality
   - Pane listing

3. **Build Session Monitor** (2 hours)
   - File watching logic
   - Command extraction regex
   - Incremental reading

4. **Implement Orchestrator** (2 hours)
   - Command processing
   - Message routing
   - Main loop

5. **Create Setup Scripts** (30 min)
   - Agent initialization
   - Prompt injection

6. **Test End-to-End** (1 hour)
   - Manual testing first
   - Automated test cases

## Code Templates

### 1. Tmux Manager Starter

```python
# tmux_manager.py
import subprocess
import logging

class TmuxManager:
    def __init__(self):
        self.session_name = "multi-agent"
        
    def create_session(self):
        """Create tmux session with two panes"""
        # tmux new-session -d -s multi-agent
        # tmux split-window -h
        pass
        
    def send_to_pane(self, pane_index, text):
        """Send text to specific pane"""
        # tmux send-keys -t multi-agent:0.{pane_index} "{text}" Enter
        pass
```

### 2. Session Monitor Starter

```python
# session_monitor.py
import re
import os
import time

class SessionMonitor:
    def __init__(self, session_file, agent_name):
        self.session_file = session_file
        self.agent_name = agent_name
        self.last_position = 0
        self.command_pattern = re.compile(
            r'<orc-command.*?>(.*?)</orc-command>',
            re.DOTALL
        )
    
    def get_new_content(self):
        """Read only new content since last check"""
        if not os.path.exists(self.session_file):
            return ""
            
        with open(self.session_file, 'r') as f:
            f.seek(self.last_position)
            content = f.read()
            self.last_position = f.tell()
            
        return content
```

### 3. Message Formatting

```python
def format_message_for_agent(from_agent, content):
    """Format message with identity prefix"""
    return f"[FROM: {from_agent}] {content}"
```

## Configuration File

```yaml
# config.yaml
orchestrator:
  poll_interval: 1  # seconds
  log_level: INFO

agents:
  master_agent:
    session_file: "~/.claude/sessions/master/conversation.json"
    tmux_pane: 0
    
  worker_agent:
    session_file: "~/.claude/sessions/worker/conversation.json"
    tmux_pane: 1

tmux:
  session_name: "multi-agent"
  window_name: "agents"
```

## Testing Scenarios

### Scenario 1: Basic Message Exchange

```
1. Master Agent: "Worker, please list all Python files in the project"
   <orc-command type="send_message">
     <from>master_agent</from>
     <to>worker_agent</to>
     <title>List Python files</title>
     <content>Please list all Python files in the project</content>
   </orc-command>

2. Orchestrator detects command
3. Orchestrator sends to Worker: "[FROM: Master Agent] Please list all Python files in the project"
4. Worker responds with file list
5. Worker Agent: "Master, I found 15 Python files..."
   <orc-command type="send_message">
     <from>worker_agent</from>
     <to>master_agent</to>
     <title>Python files list</title>
     <content>I found 15 Python files...</content>
   </orc-command>
```

## Common Issues & Solutions

### Issue 1: Can't find Claude session files
**Solution**: 
- Check `~/.config/claude/` or `~/.claude/`
- Look for `.jsonl` or `.json` files
- May need to start Claude once to create session

### Issue 2: Tmux commands not working
**Solution**:
```bash
# Test tmux manually first
tmux new-session -d -s test
tmux send-keys -t test "echo hello" Enter
tmux capture-pane -t test -p
```

### Issue 3: Commands not detected
**Solution**:
- Add debug logging to see raw content
- Check regex pattern matches
- Ensure session file is being updated

## Debug Mode

Add verbose logging to track issues:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# In your code
logger.debug(f"Detected command: {command}")
logger.debug(f"Sending to pane {pane_id}: {message}")
```

## Validation Checklist

Before considering Phase 1 complete:

- [ ] Master can send message to Worker
- [ ] Worker can send message to Master
- [ ] Identity prefixes appear correctly
- [ ] Commands detected within 2 seconds
- [ ] No manual tmux commands needed
- [ ] Clean orchestrator logs
- [ ] Graceful error handling
- [ ] Setup script works reliably

## Phase 2 Preparation

Start thinking about:
- How to add third agent
- Mailbox data structure
- Communication rules format
- State persistence approach
- Context monitoring strategy