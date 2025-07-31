# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Note for AI agents**: This is your primary reference. Project documentation in `docs/` contains critical implementation details - you MUST read relevant docs before implementing features.

**Important**: After completing significant development work, update CLAUDE.md and TROUBLESHOOTING.md to reflect new patterns and lessons learned.

**Documentation Creation Rule**: Only create documentation files when explicitly requested by the user. Module-specific READMEs are acceptable for explaining how to use specific modules. However, do NOT create task-specific documents in the main `docs/` folder - these clutter the general documentation and duplicate information already provided in conversation.

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
├── scripts/                  # Utility scripts
│   ├── claude-bg             # Background process manager (install into user or system path)
│   ├── docker-claude-code.sh # Docker management script
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

### Message Delivery
Messages are delivered based on agent state:
- **IDLE**: Delivered immediately with notification
- **BUSY/WRITING**: Queued for later delivery
- **ERROR/QUIT**: Not delivered

**Notification Format**: 
- Single notification per message: `[MESSAGE] You have a new message from Sender. Use 'check_messages' to read it.`
- No duplicate prompts

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

## Background Process Management

### CRITICAL: Use claude-bg for Background Processes
- **NEVER** use `&` to run background processes - it doesn't work properly in the Bash tool
- **ALWAYS** use the background process manager: `claude-bg`

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

### Diagnostic Tools
```bash
# Monitor agent states in real-time
python scripts/monitor_live_states.py <session-name>

# Capture detailed state data for analysis
python scripts/diagnose_agent_states.py <session-name> --duration 120
```

### Docker Management
```bash
# Build image
./scripts/docker-claude-code.sh build

# Start container
./scripts/docker-claude-code.sh start

# Run Claude in container
./scripts/docker-claude-code.sh run

# Multiple instances
CLAUDE_INSTANCE=test1 ./scripts/docker-claude-code.sh start
```

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