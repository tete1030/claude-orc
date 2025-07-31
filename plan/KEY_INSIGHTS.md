# Key Insights and Design Notes

## Critical Observations

### 1. The TUI Overwrite Problem
- Claude's interactive interface uses terminal control sequences
- Content is constantly overwritten, not appended
- Direct tmux pane capture would miss crucial information
- Session files preserve the complete interaction history

### 2. Input Stream Lifecycle
```
Launch: claude --chat "prompt" < input_pipe
   ↓
Initial prompt processed
   ↓
Claude switches to TTY mode (closes stdin pipe)
   ↓
Must use tmux send-keys for further input
```

### 3. Why Not Use SDK/Pipe Mode?
- User preference: Keep it simple for a small project
- Avoid building another TUI monitoring system
- Claude's TUI is already polished and feature-rich
- Session files give us everything we need for monitoring

### 4. Long-Lived Sessions vs Current System
Current Claude sub-agent system:
- One-shot execution
- No intermediate progress visibility
- No intervention capability
- No session management

Our improved system:
- Persistent sessions
- Real-time progress monitoring
- Context compaction when needed
- Session reset capabilities
- State preservation

## Design Advantages

### 1. Session File Monitoring Benefits
- Complete message history
- All tool invocations and results
- System messages and warnings
- Thinking process preservation
- No visual parsing needed

### 2. Coordination Patterns

**Sequential (Most Common)**
- Master spawns agent for task
- Monitors progress continuously
- Can intervene if needed
- Collects results when done

**Parallel (When Safe)**
- Check for resource conflicts first
- Spawn multiple agents
- Monitor for file conflicts
- Coordinate shared resources

### 3. Context Management Strategy
- Monitor token usage from session data
- Trigger compaction before limits
- Preserve critical information in summaries
- Reset with context when needed

## Technical Considerations

### 1. Session File Location
Need to verify:
- Exact path structure
- File format (JSON structure)
- Update frequency
- File locking behavior

### 2. Tmux Control
- Use `tmux send-keys` for normal input
- ESC interrupt: `tmux send-keys -t pane C-[`
- Escape special characters properly
- Handle multi-line input
- Consider timing between commands

### 3. File Watching
- Use watchdog or inotify
- Handle file rotation
- Incremental parsing important
- Don't re-parse entire file

### 4. Message Filtering
Categories to track:
- Tool calls (Read, Write, Edit, etc.)
- Errors and warnings
- Progress markers
- File modifications
- System messages

### 5. Multi-Channel Communication
- **Interrupts**: Reserved for true emergencies only
- **Mailbox**: File-based queues with JSON messages
- **Hooks**: Claude-code pre-prompt hooks for status display
- **Global Bulletin**: Shared state file for system-wide awareness

## Implementation Strategy

### Start Simple
1. Basic tmux pane creation
2. Agent launching with initial prompt
3. Simple session file monitoring
4. Basic message extraction

### Then Add Intelligence
1. Message categorization
2. Progress tracking
3. Error detection
4. Intervention logic

### Finally Optimize
1. Context compaction
2. Multi-agent coordination
3. Performance tuning
4. Advanced filtering

## Risks and Mitigations

### Risk: Session File Format Changes
- Mitigation: Abstract parsing logic
- Make parser configurable
- Version detection

### Risk: Tmux Timing Issues
- Mitigation: Add appropriate delays
- Verify command receipt
- Implement retry logic

### Risk: Context Loss During Reset
- Mitigation: Always generate summaries
- Save session state before reset
- Implement recovery procedures

### Risk: File Conflicts in Parallel Work
- Mitigation: Track file modifications
- Implement locking mechanism
- Coordinate through master