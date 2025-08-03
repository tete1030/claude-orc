# Troubleshooting Guide

## Agent State Monitoring Issues

### Continuous Anomaly Recording Problems

#### High Memory Usage During Monitoring
**Symptoms:**
- System memory consumption increases significantly during monitoring
- Out of memory errors during extended monitoring sessions
- Slow system performance while monitoring runs

**Diagnostic Steps:**
```bash
# Check current memory usage
ps aux | grep monitor_live_states
free -h

# Monitor memory growth during session
top -p $(pgrep -f monitor_live_states)
```

**Solutions:**
1. **Reduce record limits:**
```python
# Configure lower limits
anomaly_config = AnomalyHistoryConfig(
    max_records_per_agent=1000,    # Default: 5000
    max_total_records=5000,        # Default: 20000
    retention_hours=6.0            # Default: 12.0
)
```

2. **Use shorter monitoring duration:**
```bash
# Reduce session length
python scripts/monitor_live_states.py session --continuous-anomaly-recording --duration 1800  # 30 min instead of longer
```

3. **Enable simple mode:**
```bash
# Lower overhead with simple mode
python scripts/monitor_live_states.py session --continuous-anomaly-recording --simple
```

#### Anomaly Reports Not Generated
**Symptoms:**
- Monitoring completes but no report file created
- Empty or incomplete anomaly reports
- Report files created but contain no data

**Diagnostic Steps:**
```bash
# Check .temp directory permissions
ls -la .temp/
touch .temp/test_file

# Verify anomaly detection is working
python scripts/diagnose_agent_states.py session-name --single

# Check for Python exceptions during monitoring
python scripts/monitor_live_states.py session-name --continuous-anomaly-recording 2>&1 | tee monitor.log
```

**Solutions:**
1. **Ensure .temp directory exists:**
```bash
mkdir -p .temp
chmod 755 .temp
```

2. **Force report generation:**
```bash
# Try different format that might work
python scripts/monitor_live_states.py session --continuous-anomaly-recording --anomaly-report-format json
```

3. **Check for anomalies manually:**
```bash
# Verify agents are actually producing anomalies
python scripts/diagnose_agent_states.py session-name --duration 60
```

#### Text Format Display Issues
**Symptoms:**
- Garbled text in anomaly reports
- Missing line breaks or formatting problems
- Special characters not displaying correctly

**Known Issue:** Text format has minor display formatting problems

**Solutions:**
1. **Use JSON format instead:**
```bash
python scripts/monitor_live_states.py session --continuous-anomaly-recording --anomaly-report-format json
```

2. **Use CSV format for analysis:**
```bash
python scripts/monitor_live_states.py session --continuous-anomaly-recording --anomaly-report-format csv
```

3. **Manual formatting cleanup:**
```bash
# Post-process text reports if needed
sed 's/\r//g' .temp/anomaly_report_*.txt > cleaned_report.txt
```

#### Missing Anomalies in Reports
**Symptoms:**
- Agents showing anomalies in UI but not captured in reports
- Inconsistent anomaly detection between sessions
- Expected anomalies not appearing in final report

**Diagnostic Steps:**
```bash
# Increase monitoring frequency
python scripts/monitor_live_states.py session --continuous-anomaly-recording --interval 0.2

# Check agent state detection manually
python scripts/diagnose_agent_states.py session-name --single --verbose

# Verify tmux session health
tmux list-sessions
tmux capture-pane -t session-name:0 -p
```

**Solutions:**
1. **Increase monitoring frequency:**
```bash
# Check more frequently for brief anomalies
--interval 0.2  # Instead of default 0.5
```

2. **Verify UI patterns:**
```bash
# Check if agent UI matches expected patterns
python scripts/diagnose_agent_states.py session-name --duration 60
```

3. **Check tmux configuration:**
```bash
# Ensure tmux scrollback is sufficient
tmux show-options -g history-limit
# Should be at least 2000
```

## Common Issues and Solutions

### 1. Claude Not Starting

#### Symptoms
- Tmux panes created but remain empty
- No session files created in `~/.claude/projects/`
- Commands appear in pane but nothing happens

#### Diagnostic Steps
```bash
# Check if Claude CLI is installed
which claude

# Test Claude can start manually
claude chat --help

# Verify Claude binary path
ls -la ~/.claude/local/claude
```

#### Solutions

**Claude CLI not installed:**
1. Visit https://claude.ai/cli for installation instructions
2. Ensure claude is in your PATH or update `claude_bin` in config

**Wrong binary path:**
```python
config = OrchestratorConfig(
    claude_bin="/correct/path/to/claude"  # Update this
)
```

**Permission issues:**
```bash
chmod +x ~/.claude/local/claude
```

### 2. Messages Not Being Delivered

#### Symptoms
- Agent sends XML command but recipient doesn't receive it
- Mailbox check returns empty
- Commands visible in session file but not processed

#### Diagnostic Steps
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check mailbox state
print(f"Mailboxes: {orc.mailbox}")

# Verify agent names
print(f"Registered agents: {list(orc.agents.keys())}")
```

#### Common Causes

**Case sensitivity in agent names:**
- Agent registered as "Worker" but command uses "worker"
- Solution: Orchestrator handles this, but check for typos

**Malformed XML:**
```xml
<!-- Wrong - missing closing tag -->
<orc-command name="send_message" from="Master" to="Worker">Message

<!-- Correct -->
<orc-command name="send_message" from="Master" to="Worker">Message</orc-command>
```

**Agent not outputting commands:**
- Ensure system prompt includes clear examples
- Commands must be in assistant's response, not in code blocks

### 3. Session File Issues

#### Symptoms
- "Session file not found" errors
- Can't find session files for agents
- SessionMonitor not detecting new messages

#### Understanding Session Files
```
Location: ~/.claude/projects/<escaped-cwd>/<session-id>.jsonl
Example:  ~/.claude/projects/-home-user-project/d4f3a2b1-c3d2-4e5f-a6b7-8c9d0e1f2a3b.jsonl
```

#### Solutions

**Verify session directory:**
```python
# Check where files should be
import os
cwd = os.getcwd()
escaped_cwd = cwd.replace('/', '-')
session_dir = os.path.expanduser(f"~/.claude/projects/{escaped_cwd}")
print(f"Session dir: {session_dir}")
print(f"Files: {os.listdir(session_dir) if os.path.exists(session_dir) else 'Not found'}")
```

**Wait for file creation:**
```python
# Session files may take a moment to appear
time.sleep(2)  # After starting agents
```

### 4. Tmux Issues

#### Symptoms
- "No such session" errors
- Can't attach to tmux session
- Panes not created properly

#### Diagnostic Commands
```bash
# List all tmux sessions
tmux ls

# Check specific session
tmux has-session -t claude-agents

# Force kill stuck session
tmux kill-session -t claude-agents
```

#### Solutions

**Session name conflicts:**
```python
# Use unique session name
config = OrchestratorConfig(
    session_name=f"agents-{int(time.time())}"
)
```

**Tmux not installed:**
```bash
# Ubuntu/Debian
sudo apt-get install tmux

# macOS
brew install tmux
```

### 5. Command Not Processing

#### Symptoms
- XML commands visible but not extracted
- SessionMonitor not finding commands
- Regex not matching

#### Debug Command Extraction
```python
# Test regex manually
import re

content = '<orc-command name="mailbox_check"></orc-command>'
pattern = re.compile(
    r'<orc-command\s+(?:name|type)=["\']([^"\']+)["\'](?:\s+[^>]+)?>(.*?)</orc-command>',
    re.DOTALL | re.IGNORECASE
)

match = pattern.search(content)
print(f"Match: {match.groups() if match else 'No match'}")
```

#### Common Issues

**Commands in code blocks:**
```markdown
<!-- This won't work - it's in a code block -->
```xml
<orc-command name="send_message">Message</orc-command>
```

<!-- This works - it's in the response -->
<orc-command name="send_message">Message</orc-command>
```

**Extra whitespace:**
```xml
<!-- May not work -->
<orc-command   name="send_message"   >Message</orc-command>

<!-- Better -->
<orc-command name="send_message">Message</orc-command>
```

### 6. Performance Issues

#### Symptoms
- High CPU usage
- Slow message delivery
- System becoming unresponsive

#### Solutions

**Increase poll interval:**
```python
config = OrchestratorConfig(
    poll_interval=2.0  # Check less frequently
)
```

**Limit session history:**
```python
# In SessionMonitor, limit how far back we read
monitor.reset()  # Periodically reset to avoid reading entire history
```

**Check for infinite loops:**
- Agents sending messages back and forth
- Add cooldowns or message limits

### 7. Agent Not Responding

#### Symptoms
- Agent receives message but doesn't act on it
- Mailbox check works but agent ignores messages
- Agent seems stuck

#### Solutions

**Clear instructions in prompts:**
```python
system_prompt = """When you receive a mailbox notification, immediately check your mailbox using:
<orc-command name="mailbox_check"></orc-command>

After checking messages, respond to each one appropriately."""
```

**Send explicit instructions:**
```python
# Instead of just notifying
orc.send_to_agent("Worker", "You have messages. Check your mailbox now using the mailbox_check command.")
```

### 8. Debugging Workflow

#### Enable Comprehensive Logging
```python
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orchestrator.log')
    ]
)
```

#### Monitor in Real-Time
```bash
# Watch session files
watch -n 1 'ls -la ~/.claude/projects/*/`'

# Tail orchestrator logs
tail -f orchestrator.log

# Monitor tmux session
tmux attach -t claude-agents
```

#### Test Components Individually
```python
# Test tmux manager
from src.tmux_manager import TmuxManager
tmux = TmuxManager("test-session")
tmux.create_session(2)
tmux.send_to_pane(0, "echo 'Hello from pane 0'")

# Test session monitor
from src.session_monitor import SessionMonitor
monitor = SessionMonitor("/path/to/session.jsonl", "TestAgent")
messages = monitor.get_new_messages()
```

### 9. Emergency Recovery

#### Complete Reset
```bash
# Kill all tmux sessions
tmux kill-server

# Clear session files (careful!)
rm -rf ~/.claude/projects/<escaped-cwd>/*.jsonl

# Restart orchestrator
python your_script.py
```

#### Partial Recovery
```python
# Restart specific agent
orc.stop_agent("Worker")  # If implemented
orc.start_agent("Worker")  # If implemented

# Clear specific mailbox
orc.mailbox["Worker"].clear()
```

## Getting Help

### Diagnostic Information to Collect

When reporting issues, include:

1. **System info:**
   ```bash
   python --version
   tmux -V
   which claude
   ```

2. **Orchestrator logs** (with DEBUG level)

3. **Session file samples** (first few lines)

4. **Agent system prompts**

5. **Minimal reproduction code**

### Debug Mode Example

```python
import logging
from src.orchestrator import Orchestrator, OrchestratorConfig

# Maximum debugging
logging.basicConfig(level=logging.DEBUG)

config = OrchestratorConfig(
    session_name="debug-test",
    poll_interval=1.0
)

orc = Orchestrator(config)

# Minimal test case
orc.register_agent(
    name="TestAgent",
    session_id="test-123",
    system_prompt="You are a test agent. When asked, output: <orc-command name='mailbox_check'></orc-command>"
)

if orc.start():
    import time
    time.sleep(5)
    
    # Test command
    orc.send_to_agent("TestAgent", "Please check your mailbox")
    
    time.sleep(5)
    print(f"Final state: {orc.mailbox}")
    
    orc.stop()
```