# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Note for AI agents**: This is your primary reference. Project documentation in `docs/` contains critical implementation details - you MUST read relevant docs before implementing features.

**Important**: After completing significant development work, update CLAUDE.md and TROUBLESHOOTING.md to reflect new patterns and lessons learned.

## Recent Debug Session Learnings (2025-08-01)

### Critical Timing Issue Fixed
- **Problem**: State monitoring started 30+ seconds late
- **Solution**: Rewrote EnhancedOrchestrator to avoid parent's sleep() calls
- **Key Insight**: When inheriting, understand parent's implementation deeply

### UI/Terminal Best Practices
- **Emojis**: Can break terminal layouts - use colors or ASCII instead
- **Updates**: Only update UI when state changes to avoid flashing
- **Active Pane**: Use multiple indicators (arrows + reverse video + white border)

### Debug Methodology That Works
1. Write single comprehensive test script (see examples in .temp/)
2. Capture everything in parallel (subprocess output + tmux content + timestamps)
3. Test terminal features in isolation before implementing
4. Always track previous state to avoid redundant updates

**See TROUBLESHOOTING.md for detailed debug patterns and solutions**

### CRITICAL: Development Discipline
1. **NEVER do things other than what has been discussed**. If you want to make additional changes, ALWAYS discuss with the user first. Only implement exactly what was requested.
2. **CRITICAL**: Remember things the user tells you to remember by updating CLAUDE.md immediately. When user says "remember" or "remember for future usage", update this file right away.

**Documentation Creation Rule**: Only create documentation files when explicitly requested by the user. Module-specific READMEs are acceptable for explaining how to use specific modules. However, do NOT create task-specific documents in the main `docs/` folder - these clutter the general documentation and duplicate information already provided in conversation.

## 🚀 Production Readiness Status

**This is a mature, production-ready system** - not a development prototype. All core components have been thoroughly tested and are ready for real-world deployment.

### ✅ Production-Ready Features
- **Robust Multi-Agent Orchestration**: Complete MCP integration with intelligent message routing
- **Real-Time State Monitoring**: Advanced tmux-based agent state detection with 4-state classification
- **Enterprise Docker Support**: Full containerization with isolation and shared communication channels  
- **Background Process Management**: Production-grade process management with `claude-bg`
- **Comprehensive Tooling**: Complete CLI toolchain (`dkcc` for Docker, diagnostic scripts, monitoring tools)
- **Modern Python Stack**: Migrated to Poetry for dependency management and packaging

### 🎯 Deployment-Ready Components
- **Core Orchestrator** (`orchestrator.py`) - Battle-tested message routing and agent coordination
- **Enhanced Orchestrator** (`orchestrator_enhanced.py`) - Advanced state monitoring and intelligent delivery
- **MCP Central Server** (`mcp_central_server.py`) - Production MCP server implementation
- **Agent State Monitor** (`agent_state_monitor.py`) - Real-time state detection system
- **Tmux Manager** (`tmux_manager.py`) - Robust session and pane management

### 📊 System Capabilities
- **Multi-Agent Coordination**: Seamlessly orchestrate multiple Claude Code agents
- **Intelligent Message Delivery**: Context-aware routing based on agent availability and state
- **Real-Time Monitoring**: Live agent state tracking with diagnostic tools
- **Docker Isolation**: Complete containerized environments for secure agent separation
- **Background Operations**: Non-blocking orchestrator operations with full process management
- **Extensible Architecture**: Modular design supporting custom agent roles and workflows

### 🔧 Recent Modernization Achievements
- **Poetry Migration**: Modern Python packaging and dependency management
- **Enhanced Docker Integration**: Improved containerization with advanced CLI tooling
- **Expanded Monitoring**: Comprehensive diagnostic and monitoring capabilities
- **Production Toolchain**: Complete set of production-ready utilities and scripts

## Project Overview

**Claude Code Multi-Agent Orchestrator** - A framework for orchestrating multiple Claude Code agents with:
- MCP (Model Context Protocol) integration for inter-agent communication
- Intelligent message delivery based on agent states (IDLE, BUSY, WRITING, ERROR)
- Real-time agent state monitoring via tmux pane content analysis
- Docker-based isolated agent environments
- Background monitoring and automatic message queueing

## Project Structure
```
orchestrator/
├── .temp/                    # Temporary files and experiments (for AI agent use)
├── docker/                   # Docker configuration files
│   └── claude-code/         # Claude Code Docker environment
├── docs/                     # Project documentation
│   ├── FEATURE_MATRIX.md    # Feature comparison across phases
│   ├── KNOWN_LIMITATIONS.md # Current limitations and workarounds
│   └── research/            # Research findings and test results
├── examples/                 # Example orchestrator configurations
├── bin/                      # Executable scripts
│   ├── claude-bg             # Background process manager
│   └── dkcc                  # Docker management script
├── scripts/                  # Utility scripts
│   ├── install-claude-bg.sh  # Install claude-bg to PATH
│   ├── install-dkcc.sh       # Install dkcc to PATH
│   ├── diagnose_agent_states.py  # Agent state diagnostic tool
│   └── monitor_live_states.py    # Live state monitoring tool
├── src/                      # Main source code
│   ├── agent_state_monitor.py    # Agent state detection
│   ├── message_delivery.py       # Intelligent message routing
│   ├── mcp_central_server.py     # MCP server implementation
│   ├── orchestrator.py           # Base orchestrator
│   ├── orchestrator_enhanced.py  # Enhanced orchestrator with state monitoring
│   └── tmux_manager.py           # Tmux pane management
└── tests/                    # Test suite
    ├── integration/          # Integration tests
    └── unit/                 # Unit tests
```

## Core Development Principles

### 1. Fail-Fast Philosophy
**Clear errors > silent failures**

The codebase follows a strict "fail fast" philosophy:
- If something cannot work properly, throw an exception
- NEVER convert errors to warnings that get ignored
- Every error must clearly explain what failed and why
- Don't write code that "gracefully" handles broken states

**CRITICAL: Do not write error-tolerant code**
- NEVER use `if` conditions without proper `else` handling when the condition indicates a serious error
- NEVER use `try-except-pass` or silent error handling
- If data integrity is compromised (wrong types, missing required fields), raise exceptions immediately

### 2. Research-First Development
**Before writing code**:
- Check if the codebase has similar patterns
- Read relevant test files for usage examples
- Test assumptions with minimal examples first

### 3. Incremental Development
- Start with minimal working example
- Add features incrementally
- Test each addition thoroughly
- Document patterns that work

### 4. NO HARDCODED DATA IN PRODUCTION CODE
**ABSOLUTELY FORBIDDEN**:
- Hardcoded dates, paths, or configuration values
- Mock data in production components (only tests should have mocks)
- Static arrays/objects representing dynamic data

**REQUIRED APPROACH**:
- All configuration must come from config files or environment variables
- Use proper configuration management patterns
- If temporary data is needed during development, mark with **FIXME**

## Critical Implementation Rules

### Agent State Detection
The agent state monitor detects states by analyzing tmux pane content:

**State Detection Priority** (order matters!):
1. **ERROR** - Recent error messages (last 5 lines)
2. **QUIT** - Agent has exited
3. **BUSY** - Processing indicator visible (matches Claude's format: `^.\s+(ProcessingWord)…`)
4. **IDLE/WRITING** - Prompt box visible

**Key Pattern**: Claude's processing indicator starts with any character (rotating spinner) followed by space and a processing word.

### Message Delivery (Updated 2025-08-01)
Messages are now delivered with more flexible handling:
- **ALL STATES**: Notifications sent immediately (Claude Code handles input organization)
- **IDLE**: Message delivered with standard notification
- **BUSY/WRITING**: Message delivered with note to check "when convenient"
- **ERROR/QUIT**: Not delivered

**Broadcast Message Delivery**:
- **Intelligent Delivery System**: Broadcast messages use the enhanced delivery system with state-aware routing
- **BUSY/WRITING Agents**: Receive broadcast notifications with convenience notes
- **ERROR/QUIT Agents**: Do not receive broadcast messages (filtered out)
- **Base Orchestrator Compatibility**: Fallback behavior ensures compatibility with non-enhanced orchestrators

**Notification Formats**: 
- Standard: `[MESSAGE] You have a new message from Sender. Check it when convenient using 'check_messages' - no need to interrupt your current task unless urgent.`
- Idle reminder: `[MESSAGE] Reminder: You have X unread message(s) in your mailbox. Use 'check_messages' to read them.`

**Intelligent Reminders**:
- Agents are told they can check messages at their convenience
- When agents become IDLE with unread messages, a reminder is sent once
- Reminder resets when new messages arrive or mailbox is cleared

### Testing Discipline
- Use provided test scripts, don't bypass
- **NEVER delete or skip tests** - Always fix the underlying issue
- Match test complexity to need
- Use FIXME for complex issues that need investigation

### File System Discipline
- **Temporary files**: ALWAYS use `.temp/` directory
- **Code updates**: Modify files directly, never create new versions
- **Docker mounts**: Shared directory at `/tmp/claude-orc`

## CRITICAL: ASK BEFORE CREATING WORKAROUNDS

### When Encountering Obstacles
- **NEVER** create mock implementations to bypass requirements
- **NEVER** add files just to work around problems
- **ALWAYS** ask the user when facing large obstructions
- **ALWAYS** report blockers clearly and wait for guidance
- If something clearly goes against user instructions, STOP and ASK

### Example of What NOT to Do
- User wants feature X to work
- Feature X is blocked by authentication/permissions/etc
- ❌ WRONG: Create mock system to simulate feature X
- ✅ RIGHT: "I encountered an authentication requirement that blocks the implementation. How would you like me to proceed?"

## CRITICAL FILE ORGANIZATION RULES

### Where Files MUST Go:
- **Test files**: ALWAYS in `.temp/` directory (e.g., `.temp/test_mcp.py`)
- **Experiments**: ALWAYS in `.temp/` directory
- **Production code**: Only in `src/` after thorough testing
- **Examples**: Only finalized examples in `examples/`
- **Documentation**: In `docs/` directory

### NEVER Create Files:
- ❌ In project root (no `test_*.py` files cluttering root)
- ❌ Multiple experimental versions in `src/`
- ❌ Test files scattered everywhere
- ❌ Junk files outside project structure

### When Developing:
1. Start ALL experiments in `.temp/`
2. Test thoroughly in `.temp/`
3. Only move ONE clean version to `src/` when ready
4. Clean up `.temp/` experiments after finalizing
5. Don't create 10 different versions of the same thing

## Tmux Session Management

### CRITICAL: Be Careful with tmux
- **NEVER** kill all tmux sessions blindly
- **ALWAYS** list sessions first: `tmux ls`
- **ONLY** kill orchestrator-specific sessions
- User may have other important tmux sessions running
- Use pattern matching to find orchestrator sessions:
  ```bash
  # List orchestrator sessions only
  tmux ls | grep -E "(mcp-demo|claude-agents|orchestrator)"
  
  # Kill specific session
  tmux kill-session -t simple-mcp-demo
  ```

### Session Conflict Detection (2025-08-01)
The orchestrator now detects existing tmux sessions to prevent accidental overwrites:
- **Default behavior**: Fails with helpful error message if session exists
- **Options when session exists**:
  1. Attach to existing: `tmux attach -t <session-name>`
  2. Kill existing: `tmux kill-session -t <session-name>`
  3. Use `--force` flag to auto-kill existing session
  4. Use `--session <name>` to specify a different session name

Example usage:
```bash
# Will fail if session exists
python examples/team_mcp_demo.py

# Force kill existing session
python examples/team_mcp_demo.py --force

# Use different session name
python examples/team_mcp_demo.py --session my-custom-session
```

## Background Process Management

### CRITICAL: Use claude-bg for Background Processes
- **NEVER** use `&` to run background processes - it doesn't work properly in the Bash tool
- **ALWAYS** use the background process manager: `claude-bg`
- **REMEMBER**: User explicitly stated "told you to use claude-bg for background task" - this is mandatory
- **REMEMBER**: You cannot run a process and do something else at the same time. Whenever you need two actions together (like running a server and testing it), you MUST use background services like `claude-bg`

### Installation:
```bash
# Install claude-bg to your PATH
./scripts/install-claude-bg.sh
```

### Usage:
```bash
# Start orchestrator example in background
claude-bg start 'python examples/team_mcp_demo.py' team-demo

# Check status
claude-bg status team-demo_[timestamp]

# View logs
claude-bg logs team-demo_[timestamp]

# Stop process
claude-bg stop team-demo_[timestamp]
```

## Common Commands

### Running the Orchestrator
```bash
# Basic team demo
python examples/team_mcp_demo.py

# Enhanced demo with state monitoring
python examples/team_mcp_demo_enhanced.py

# With custom model
ANTHROPIC_MODEL=sonnet python examples/team_mcp_demo_enhanced.py
```

### Interacting with Agents
The orchestrator runs agents in tmux with mouse support and keyboard shortcuts:

```bash
# Attach to the session
./scripts/attach-orchestrator.sh
# or
tmux attach -t team-mcp-demo

# Navigate between agents:
# F1 or Alt+1 - Leader
# F2 or Alt+2 - Researcher  
# F3 or Alt+3 - Writer
# Mouse click - Switch to any pane
# Mouse scroll - Navigate history

# Standard tmux navigation also works:
# Ctrl+b, 1 - Leader
# Ctrl+b, 2 - Researcher
# Ctrl+b, 3 - Writer

# Use Claude shortcuts (press '?' in any pane)
# Detach with Ctrl+b, d
```

### Diagnostic Tools
```bash
# Monitor agent states in real-time
python scripts/monitor_live_states.py <session-name>

# Capture detailed state data for analysis
python scripts/diagnose_agent_states.py <session-name> --duration 120

# Quick state snapshot when you see an issue
python scripts/diagnose_agent_states.py <session-name> --single
# or use the shortcut:
./scripts/capture-state-snapshot.sh [session-name]
# Saves to .temp/state_snapshot_TIMESTAMP.txt
```

### Docker Management (dkcc)

#### Installation:
```bash
# Install dkcc to your PATH
./scripts/install-dkcc.sh
```

#### Usage:
```bash
# Build image
dkcc build

# Run Claude with options
dkcc run -i dev -m sonnet
dkcc run --isolated

# Start persistent container
dkcc start -i frontend

# Run Claude in existing container
dkcc cc -i frontend
dkcc cc -i frontend --help

# Open shell
dkcc shell -i frontend
dkcc shell -i frontend python app.py

# Other commands
dkcc stop -i frontend    # Stop container
dkcc logs -i frontend    # View logs
dkcc list                # List all containers
```

## Production Deployment Best Practices

### Environment Setup
```bash
# 1. Install system dependencies
./scripts/install-claude-bg.sh    # Background process manager
./scripts/install-dkcc.sh         # Docker management CLI

# 2. Set up Python environment with Poetry
poetry install --no-dev           # Production dependencies only
poetry shell                      # Activate environment
```

### Configuration Management
- **Environment Variables**: Use `.env` files for environment-specific configuration
- **Model Selection**: Set `ANTHROPIC_MODEL` environment variable (default: sonnet)
- **API Keys**: Ensure `ANTHROPIC_API_KEY` is properly configured
- **Docker Mounts**: Verify `/tmp/claude-orc` is accessible for MCP communication

### Deployment Patterns

#### Standard Deployment
```bash
# Start orchestrator in background
claude-bg start 'python examples/team_mcp_demo_enhanced.py' production-orchestrator

# Monitor status
claude-bg status production-orchestrator_[timestamp]
claude-bg logs production-orchestrator_[timestamp]
```

#### Docker-Based Deployment
```bash
# Build production image
dkcc build

# Deploy isolated agents
dkcc start -i leader
dkcc start -i researcher  
dkcc start -i writer

# Run orchestrator connecting to containerized agents
python examples/team_mcp_demo_enhanced.py
```

### Monitoring and Maintenance

#### Health Checks
```bash
# Monitor agent states in real-time
python scripts/monitor_live_states.py <session-name>

# Diagnostic state capture
python scripts/diagnose_agent_states.py <session-name> --duration 120
```

#### Session Management
- **Graceful Shutdown**: Always use `claude-bg stop` rather than killing processes directly
- **Session Cleanup**: Regular cleanup of orphaned tmux sessions using pattern matching
- **Log Rotation**: Monitor and rotate background process logs as needed

### Security Considerations
- **API Key Protection**: Never commit API keys to version control
- **Container Isolation**: Use Docker isolation for multi-tenant environments
- **Network Security**: Ensure MCP communication channels are properly secured
- **Process Permissions**: Run orchestrator with minimal required permissions

### Performance Optimization
- **State Monitoring Frequency**: Adjust polling intervals based on workload requirements
- **Message Queue Limits**: Configure appropriate queue sizes for high-throughput scenarios
- **Resource Allocation**: Monitor Docker container resource usage in production

## Known Issues and Solutions

### Agent State Detection
- **Issue**: Processing indicators appear briefly
- **Solution**: Increased polling frequency, check BUSY before IDLE

### Message Delivery
- **Issue**: Duplicate notifications when agent becomes idle
- **Solution**: Single notification format with check_messages reminder

### Docker Isolation
- **Issue**: Agents need shared directory for MCP communication
- **Solution**: Mount `/tmp/claude-orc` in all containers

## CLAUDE.md Maintenance Protocol

### Update Triggers
- After debugging sessions → Update TROUBLESHOOTING.md
- After implementing features → Update relevant docs
- After discovering gotchas → Add warning to CLAUDE.md
- When user says "remember this" → Update immediately

### The 3-Question Test
Before adding to CLAUDE.md:
1. Will this prevent an immediate mistake?
2. Will this be referenced weekly?
3. Is this a foundational principle?

If not 2/3 "yes" → goes in project docs

Remember: One hour reading docs saves ten hours debugging!