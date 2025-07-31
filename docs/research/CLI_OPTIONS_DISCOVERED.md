# Claude CLI Options Discovery

## Key Findings

### Agent Role Injection
The option we need is:
```
--append-system-prompt <prompt>
```

This appends our agent-specific instructions to Claude's default system prompt.

### Example Usage for Agents

**Master Agent:**
```bash
claude chat --append-system-prompt "You are the Master Agent in a multi-agent system. Your role is to coordinate tasks and communicate with other agents. Use <orc-command> directives to send messages."
```

**Worker Agent:**
```bash
claude chat --append-system-prompt "You are the Worker Agent in a multi-agent system. Your role is to execute tasks assigned by the Master Agent. Use <orc-command> directives to respond."
```

### Other Useful Options

1. **Session Management:**
   - `-c, --continue` - Continue most recent conversation
   - `-r, --resume [sessionId]` - Resume specific conversation
   - `--session-id <uuid>` - Use specific session ID

2. **Directory Access:**
   - `--add-dir <directories...>` - Allow tool access to additional directories
   
3. **Model Selection:**
   - `--model <model>` - Specify model (e.g., 'sonnet', 'opus')

4. **Debug Mode:**
   - `-d, --debug` - Enable debug mode

### Session File Identification Strategy

Since we can use `--session-id`, we can:
1. Generate a UUID for each agent
2. Launch Claude with that session ID
3. Know exactly which session file belongs to which agent

Example:
```python
import uuid

# Generate UUIDs for agents
master_session_id = str(uuid.uuid4())
worker_session_id = str(uuid.uuid4())

# Launch agents with specific session IDs
claude_cmd_master = f"claude chat --session-id {master_session_id} --append-system-prompt 'You are the Master Agent...'"
claude_cmd_worker = f"claude chat --session-id {worker_session_id} --append-system-prompt 'You are the Worker Agent...'"
```

### Working Directory Strategy

Each agent can have its own working directory:
```bash
# Master agent
cd /tmp/claude-agents/master
claude chat --add-dir /tmp/claude-agents/shared --append-system-prompt "..."

# Worker agent  
cd /tmp/claude-agents/worker
claude chat --add-dir /tmp/claude-agents/shared --append-system-prompt "..."
```

This helps identify agents by their `cwd` field in session files.