# Current Research Status

## ✅ Completed Research

### 1. Session File Structure
- **Location**: `~/.claude/projects/{project-name}/*.jsonl`
- **Format**: JSONL (JSON Lines)
- **Structure**: Well-documented in SESSION_FILE_ANALYSIS.md
- **Key finding**: Can detect `<orc-command>` in messages
- **Incremental reading**: Feasible with seek/tell

### 2. File Monitoring Strategy
- Use file position tracking for incremental reads
- Track processed UUIDs to avoid duplicates
- Poll interval: 1-2 seconds should suffice

## 🔄 In Progress Research

### 1. Claude CLI Options (Need Help)
- Location: `~/.claude/local/claude`
- Need to identify prompt injection method
- Testing various options like --prompt, --system-prompt, etc.

### 2. Tmux-Claude Integration
- Need to test send-keys reliability
- Special character handling
- Timing between messages

## 📋 Remaining Research Items

### 1. Agent Session Identification
- How to map session files to specific agents
- Possible approaches:
  - Use working directory in session data
  - Use specific project paths
  - Track session start times

### 2. Edge Cases
- Claude's behavior while "thinking"
- Message delivery during tool use
- Session file rotation

## 🚀 Ready to Implement

Based on current knowledge, we can start implementing:

1. **Session File Monitor** - Structure is clear
2. **Basic Tmux Manager** - Standard tmux commands
3. **Command Parser** - Simple XML extraction
4. **Message Router** - Basic routing logic

## 🤔 Workarounds for Unknowns

### If CLI Prompts Don't Work:
- Send role instructions as first message after launch
- Use a standardized greeting that establishes role

### If Session Identification is Unclear:
- Use tmux pane title to track which agent is where
- Monitor file creation times
- Use unique working directories per agent

## Next Steps

1. Get Claude CLI help output (need user assistance)
2. Create basic tmux test with Claude
3. Start implementing core components
4. Test with real Claude sessions