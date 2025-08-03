# Session Management

## Understanding Claude Sessions

### What is a Session?

A Claude session represents a conversation with specific context and history. Each session:
- Has a unique UUID identifier
- Stores conversation history in a JSONL file
- Maintains context across multiple interactions
- Can be resumed later with `--resume`

### Session File Structure

#### Location
```
~/.claude/projects/<escaped-cwd>/<session-id>.jsonl
```

Where:
- `<escaped-cwd>`: Current working directory with `/` replaced by `-`
- `<session-id>`: UUID like `d4f3a2b1-c3d2-4e5f-a6b7-8c9d0e1f2a3b`

#### JSONL Format
Each line is a JSON object representing an event:

```json
{"id": "msg_123", "type": "user", "timestamp": 1234567890, "message": {"content": "Hello"}}
{"id": "msg_124", "type": "assistant", "timestamp": 1234567891, "message": {"content": "Hi there!"}}
{"id": "msg_125", "type": "system", "timestamp": 1234567892, "message": {"content": "Session saved"}}
```

## Session ID Strategy

### The Challenge

Originally, we tried various approaches:
1. **Letting Claude auto-generate IDs**: Unpredictable file locations
2. **Using `/status` command**: Autocomplete UI interference
3. **Two-stage launch**: Overly complex

### The Solution: Pre-generated UUIDs

```python
# SimpleLauncher approach
session_id = str(uuid.uuid4())
cmd = f"claude --session-id {session_id} --append-system-prompt '{prompt}'"
```

Benefits:
- Predictable session file location
- No need to query Claude for ID
- Stable across restarts
- Simple implementation

## Session Lifecycle

### 1. Creation
```python
def launch_agent(self, pane_index: int, agent_name: str, system_prompt: str):
    # Generate session ID upfront
    session_id = str(uuid.uuid4())
    
    # Build command with explicit session ID
    cmd = f"{claude_bin} --session-id {session_id} --append-system-prompt '{system_prompt}'"
    
    # Send to tmux pane
    self.tmux.send_to_pane(pane_index, cmd)
```

### 2. Monitoring
```python
# SessionMonitor watches the file
monitor = SessionMonitor(session_file_path, agent_name)

# Continuously check for new messages
while running:
    messages = monitor.get_new_messages()
    commands = monitor.extract_commands(messages)
```

### 3. Resumption
To resume a session later:
```bash
claude --resume <session-id>
```

### 4. Cleanup
Sessions persist until manually deleted:
```bash
rm ~/.claude/projects/*/<session-id>.jsonl
```

## Implementation Details

### File Watching Strategy

The `SessionMonitor` uses an efficient approach:

```python
class SessionMonitor:
    def __init__(self, session_file: str, agent_name: str):
        self.session_file = session_file
        self.agent_name = agent_name
        self.last_position = 0
    
    def get_new_messages(self):
        # Only read from last position
        with open(self.session_file, 'r') as f:
            f.seek(self.last_position)
            new_lines = f.readlines()
            self.last_position = f.tell()
```

Benefits:
- Incremental reading (no re-reading old messages)
- Low memory usage
- Efficient for long sessions

### Handling Missing Files

Session files don't exist immediately:

```python
def get_new_messages(self):
    if not os.path.exists(self.session_file):
        return []  # File not created yet
    
    try:
        # Read file
    except FileNotFoundError:
        return []  # Handle race condition
```

### Thread Safety

Each agent has its own monitor thread:

```python
def _monitor_agent(self, agent: Agent):
    """Monitoring thread for single agent"""
    monitor = SessionMonitor(agent.session_file, agent.name)
    agent.monitor = monitor
    
    while self.is_running and agent.name in self.agents:
        # Thread-safe message processing
        messages = monitor.get_new_messages()
        commands = monitor.extract_commands(messages)
        
        for command in commands:
            self.command_queue.put((agent.name, command))
```

## Session File Examples

### Basic Conversation
```json
{"id": "1", "type": "system", "timestamp": 1700000000, "message": {"content": "Session started"}}
{"id": "2", "type": "user", "timestamp": 1700000001, "message": {"content": "Send a message to Worker"}}
{"id": "3", "type": "assistant", "timestamp": 1700000002, "message": {"content": "I'll send a message to Worker.\n\n<orc-command name=\"send_message\" from=\"Master\" to=\"Worker\">Please calculate 5 + 3</orc-command>"}}
```

### Command Extraction
From the above, `SessionMonitor` extracts:
```python
Command(
    command_type="send_message",
    from_agent="Master",
    to_agent="Worker",
    content="Please calculate 5 + 3",
    priority="normal"
)
```

## Best Practices

### 1. Session ID Management
- Always use pre-generated UUIDs
- Store session IDs if you need to resume later
- Don't rely on parsing them from Claude output

### 2. File Monitoring
- Use incremental reading
- Handle missing files gracefully
- Reset position periodically for long sessions

### 3. Error Handling
```python
try:
    messages = monitor.get_new_messages()
except (FileNotFoundError, IOError) as e:
    logger.warning(f"Session file issue: {e}")
    continue  # Try again next iteration
```

### 4. Performance
- Adjust `poll_interval` based on needs
- Consider file size limits for very long sessions
- Implement log rotation if needed

## Advanced Topics

### Custom Session Directories

```python
# Override default location
class CustomConfig(OrchestratorConfig):
    def __post_init__(self):
        self.session_dir = "/custom/path/to/sessions"
```

### Session Persistence

To save and restore orchestrator state:

```python
def save_state(self):
    state = {
        "agents": {
            name: {
                "session_id": agent.session_id,
                "system_prompt": agent.system_prompt,
                "working_dir": agent.working_dir
            }
            for name, agent in self.agents.items()
        },
        "mailboxes": dict(self.mailbox)
    }
    with open("orchestrator_state.json", "w") as f:
        json.dump(state, f)

def restore_state(self):
    with open("orchestrator_state.json", "r") as f:
        state = json.load(f)
    
    # Re-register agents and restore mailboxes
    for name, config in state["agents"].items():
        self.register_agent(name, **config)
```

### Session Analytics

```python
def analyze_session(session_file: str):
    """Extract metrics from session file"""
    metrics = {
        "message_count": 0,
        "command_count": 0,
        "duration": 0,
        "agents_involved": set()
    }
    
    with open(session_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            metrics["message_count"] += 1
            
            if "<orc-command" in data.get("message", {}).get("content", ""):
                metrics["command_count"] += 1
    
    return metrics
```

## Troubleshooting Session Issues

### Session File Not Found
1. Check Claude started successfully
2. Verify correct working directory
3. Wait a few seconds for file creation

### Session File Not Updating
1. Check Claude is responding
2. Verify not in hung state
3. Try sending a message manually

### Can't Resume Session
1. Verify session ID is correct
2. Check file still exists
3. Ensure same working directory