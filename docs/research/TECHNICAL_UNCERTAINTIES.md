# Technical Uncertainties & Research Needs

## Critical Uncertainties (Must Research Before Implementation)

### 1. Claude Session File Format & Location
**Uncertainty**: Where exactly are Claude session files stored and what format?
**Why Critical**: Core dependency - we need to monitor these files
**Research Needed**:
- [ ] Find exact session file path on different OS (Linux/Mac)
- [ ] Determine file format (JSON, JSONL, or other)
- [ ] Check if sessions persist across Claude restarts
- [ ] Verify file update frequency (real-time or batched)
- [ ] Test if multiple Claude instances create separate session files

**Research Method**:
```bash
# Search for Claude session files
find ~ -name "*claude*" -type f 2>/dev/null | grep -E "(session|conversation|chat)"
# Check Claude config directory
ls -la ~/.config/claude/ ~/.claude/ ~/Library/Application\ Support/claude/
# Start Claude and monitor file system changes
fswatch -r ~ | grep claude  # on macOS
inotifywait -mr ~ | grep claude  # on Linux
```

### 2. Claude CLI Prompt Injection Options
**Uncertainty**: Exact syntax for adding custom prompts via CLI
**Why Critical**: Need this for agent role specialization
**Research Needed**:
- [ ] Verify if `--prompt` or similar option exists
- [ ] Test how custom prompts interact with base Claude prompt
- [ ] Check character limits for CLI prompts
- [ ] Determine if prompts can be loaded from files

**Research Method**:
```bash
# Check Claude CLI help
claude --help
claude chat --help
# Try various prompt injection methods
claude --system-prompt "You are a test agent"
claude --prompt "Additional instructions"
claude chat --context "Role definition"
```

### 3. Session File Update Behavior
**Uncertainty**: How/when Claude writes to session files
**Why Critical**: Affects our monitoring strategy
**Research Needed**:
- [ ] Is content written incrementally or in chunks?
- [ ] Are there file locks during writes?
- [ ] How to detect only new content efficiently?
- [ ] What happens to session files on Claude exit?

**Research Method**:
```python
# Monitor file changes in real-time
import time
import os

session_file = "/path/to/session"
last_size = 0

while True:
    current_size = os.path.getsize(session_file)
    if current_size > last_size:
        print(f"File grew by {current_size - last_size} bytes")
        # Read new content
    last_size = current_size
    time.sleep(0.1)
```

### 4. Tmux Input Handling for Claude TUI
**Uncertainty**: How Claude's TUI handles tmux send-keys input
**Why Critical**: Our primary communication method
**Research Needed**:
- [ ] Does Claude's TUI properly receive multi-line input via send-keys?
- [ ] Are there timing issues between rapid send-keys commands?
- [ ] How to handle special characters in messages?
- [ ] What happens if we send input while Claude is "thinking"?

**Research Method**:
```bash
# Test various input patterns
tmux send-keys -t session:pane "Simple message" Enter
tmux send-keys -t session:pane "Multi" Enter "Line" Enter "Message" Enter
tmux send-keys -t session:pane 'Message with "quotes" and $special chars' Enter
```

### 5. Claude Context Window Behavior
**Uncertainty**: How to detect when context is getting full
**Why Critical**: Need to know when to trigger compaction (Phase 2)
**Research Needed**:
- [ ] Can we extract token count from session files?
- [ ] Are there warning messages we can detect?
- [ ] What's the actual context limit for different models?
- [ ] How does Claude handle context overflow?

### 6. Process Management & Recovery
**Uncertainty**: How to handle Claude process crashes/restarts
**Why Critical**: System reliability
**Research Needed**:
- [ ] How to detect if Claude process died in tmux pane?
- [ ] Can we auto-restart Claude with same session?
- [ ] How to preserve agent state across restarts?
- [ ] What happens to session files on crash?

## Medium Priority Uncertainties

### 7. Performance & Scalability
**Uncertainty**: Resource usage with multiple agents
**Research Needed**:
- [ ] Memory usage per Claude instance
- [ ] CPU usage during active conversations
- [ ] File I/O patterns of session monitoring
- [ ] Optimal polling intervals

### 8. Command Detection Edge Cases
**Uncertainty**: Reliability of XML-style command detection
**Research Needed**:
- [ ] What if agent outputs partial command?
- [ ] How to handle malformed XML?
- [ ] Could commands appear in code blocks?
- [ ] Prevention of command injection

### 9. Identity Prefix Reliability
**Uncertainty**: Will agents consistently use identity prefixes?
**Research Needed**:
- [ ] How well do agents follow formatting instructions?
- [ ] Fallback strategies if prefix is missing
- [ ] Handling of messages from non-agent sources

## Research Action Plan

### Immediate (Before Any Coding):
1. **Session File Investigation** (2 hours)
   - Start Claude and find session files
   - Analyze file format and structure
   - Test update patterns

2. **CLI Options Testing** (1 hour)
   - Document all Claude CLI options
   - Test prompt injection methods
   - Verify persistence of CLI settings

3. **Tmux-Claude Integration Test** (1 hour)
   - Create simple tmux test with Claude
   - Test send-keys reliability
   - Check special character handling

### During Phase 1 Development:
4. **Build Monitoring Diagnostics**
   - Add extensive logging
   - Create debug mode
   - Build test harness

5. **Document Findings**
   - Update this file with discoveries
   - Create troubleshooting guide
   - Note platform differences

## Fallback Strategies

### If Session Files Are Problematic:
- **Plan B**: Use tmux capture-pane to read agent output
- **Plan C**: Inject periodic status commands for agents to report

### If CLI Prompts Don't Work:
- **Plan B**: Send role instructions as first message
- **Plan C**: Use environment variables or config files

### If Send-Keys Is Unreliable:
- **Plan B**: Use named pipes (FIFOs)
- **Plan C**: Use expect/pexpect for PTY control

## Test Environment Setup

Before full implementation, create isolated tests:

```bash
# Test 1: Session file monitoring
./test_session_monitoring.py

# Test 2: Tmux control
./test_tmux_integration.py

# Test 3: Claude CLI options
./test_claude_cli.sh

# Test 4: Full integration
./test_minimal_integration.py
```

## Success Criteria for Research

We can proceed with confidence when:
1. ✅ Located and understood session file format
2. ✅ Confirmed reliable tmux-Claude communication
3. ✅ Tested prompt injection method
4. ✅ Built working prototype of core loop
5. ✅ Documented platform-specific differences

## Risk Mitigation

**Highest Risk**: Session file format is undocumented/unstable
**Mitigation**: Build abstraction layer that can switch between:
- Session file monitoring (preferred)
- Tmux pane capture (fallback)
- Direct pipe communication (emergency)

**Second Risk**: Claude TUI doesn't play well with automation
**Mitigation**: 
- Test thoroughly before committing to approach
- Consider using Claude API mode if available
- Build in manual intervention capabilities