# Implementation Notes

## Claude Launch Process

This document explains how the orchestrator launches Claude instances and the evolution of our approach.

## Current Implementation

### Launch Sequence

1. **Orchestrator.start()** initiates the process
2. **TmuxManager.create_session()** creates tmux panes with bash shells
3. **SimpleLauncher.launch_agent()** generates session ID and builds command
4. **TmuxManager.send_to_pane()** executes the Claude command

### Key Components

```python
# SimpleLauncher: Generates session ID upfront
session_id = str(uuid.uuid4())
cmd = f"{claude_bin} --session-id {session_id} --append-system-prompt '{system_prompt}'"

# TmuxManager: Sends command to pane
self._run_command(["tmux", "send-keys", "-t", target, command])
self._run_command(["tmux", "send-keys", "-t", target, "Enter"])
```

## Evolution of Approaches

### 1. Initial Approach: Auto-generated Session IDs
- Let Claude generate its own session ID
- Problem: Couldn't predict session file location

### 2. Second Approach: /status Command
- Use `/status` to query session ID after launch
- Problem: Autocomplete UI interference made it unreliable

### 3. Third Approach: Two-Stage Launch
- Stage 1: Launch with debug flag to get session ID
- Stage 2: Kill and resume with normal mode
- Problem: Overly complex for simple need

### 4. Final Solution: Pre-generated UUIDs
- Generate UUID before launching Claude
- Use `--session-id` flag to specify it
- Result: Simple, predictable, reliable

## Critical Discoveries

### The --session-id Flag
We discovered Claude CLI accepts `--session-id` to specify a session ID:
```bash
claude --session-id <uuid> --append-system-prompt "You are an agent..."
```

This eliminated the need for complex workarounds.

### Enter Key Handling
Initial implementation sent "Enter" as literal text:
```python
# Wrong
self._run_command(["tmux", "send-keys", "-t", target, command, "Enter"])

# Correct  
self._run_command(["tmux", "send-keys", "-t", target, command])
self._run_command(["tmux", "send-keys", "-t", target, "Enter"])
```

### XML Command Format Compatibility
The system supports both modern and legacy XML formats:
```xml
<!-- Modern (recommended) -->
<orc-command name="send_message" from="A" to="B">Message</orc-command>

<!-- Legacy (still supported) -->
<orc-command type="send_message">
  <from>A</from>
  <to>B</to>
  <content>Message</content>
</orc-command>
```

## Debugging Claude Launch Issues

### Common Problems

1. **Claude not installed**: Check with `which claude`
2. **Wrong binary path**: Update `claude_bin` in config
3. **Permission issues**: Ensure claude is executable
4. **System prompt syntax**: Verify `--append-system-prompt` is supported

### Debug Steps

1. **Manual test in tmux:**
   ```bash
   tmux new -s test
   claude --help  # Check available options
   ```

2. **Verify command building:**
   ```python
   # Log the exact command being sent
   print(f"Command: {cmd}")
   ```

3. **Check tmux pane content:**
   ```bash
   tmux capture-pane -t session:0.0 -p
   ```

## Lessons Learned

1. **Simplicity wins**: Pre-generated UUIDs are simpler than complex discovery
2. **Test assumptions**: The --session-id flag wasn't documented but works
3. **Handle edge cases**: Support multiple XML formats for robustness
4. **Debug systematically**: Start with basic tmux tests, then add complexity

## Future Improvements

1. **Auto-detect Claude path**: Search common locations
2. **Validate Claude installation**: Pre-flight check before starting
3. **Support different Claude versions**: Handle CLI variations
4. **Better error messages**: Detect and report specific failure modes