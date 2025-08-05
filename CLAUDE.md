# CLAUDE.md - Developer Guide for AI Agents

This file provides guidance specifically for AI agents (like Claude Code) working on the Claude Multi-Agent Orchestrator codebase. This is your primary reference for development patterns, architecture decisions, and common pitfalls.

**Critical**: This is developer documentation for agents building this system. For end-user documentation, see `docs/USAGE_GUIDE.md`.

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

## System Architecture Overview

**This is a mature, production-ready system** designed for orchestrating multiple Claude Code agents with sophisticated state management and communication protocols.

### Core Architecture Components

#### Message Communication Layer
- **MCP (Model Context Protocol)**: Inter-agent communication backbone
- **Central Server** (`mcp_central_server.py`): Message routing hub with mailbox system
- **Enhanced Delivery** (`message_delivery.py`): State-aware message routing logic

#### Agent State Management
- **State Monitor** (`agent_state_monitor.py`): Real-time detection via tmux content analysis
- **4-State Classification**: IDLE, BUSY, WRITING, ERROR/QUIT with priority-based detection
- **Intelligent Routing**: Messages delivered based on recipient state

#### Session Orchestration
- **Base Orchestrator** (`orchestrator.py`): Core agent lifecycle and session management
- **Enhanced Orchestrator** (`orchestrator_enhanced.py`): Adds state monitoring and intelligent delivery
- **Team Context Manager** (`team_context_manager.py`): Persistent team context registry and metadata
- **Tmux Manager** (`tmux_manager.py`): Terminal session and pane coordination

#### Team Configuration System
- **Team Config Loader** (`team_config_loader.py`): YAML/JSON team configuration parser
- **Pre-built Teams** (`examples/teams/`): Ready-to-use team configurations
- **Team Launch System** (`ccorc`): CLI for launching and managing teams

#### Containerization Layer
- **Docker Integration**: Full containerization with ccbox (Claude Code Box)
- **Workspace Configuration**: `.ccbox/` directory for environment customization
- **Background Processing**: `claude-bg` for non-blocking operations

### Key Architectural Decisions

1. **Team-Based Configuration**: YAML/JSON team configs replace manual Python scripting for better user experience
2. **Tmux-Based State Detection**: Instead of complex agent APIs, we parse tmux pane content to detect Claude's actual state
3. **MCP Communication**: Standardized protocol for agent-to-agent messaging
4. **Enhanced vs Base Orchestrator**: Composition pattern where enhanced adds monitoring without modifying base
5. **Container Isolation**: Docker provides clean separation while shared mounts enable communication
6. **CLI-First Experience**: `ccorc` provides user-friendly team management without requiring Python knowledge

## Codebase Navigation for Developers

### Core Components Location Map

#### Primary Source Code (`src/`)
- **`orchestrator.py`**: Base orchestrator class - start here for understanding core agent lifecycle
- **`orchestrator_enhanced.py`**: Enhanced orchestrator with state monitoring - most production deployments use this
- **`agent_state_monitor.py`**: State detection logic - critical for understanding how agent states are determined
- **`message_delivery.py`**: Intelligent message routing - handles state-aware delivery decisions
- **`mcp_central_server.py`**: MCP server implementation - handles all inter-agent communication
- **`tmux_manager.py`**: Terminal session management - abstracts tmux operations
- **`team_context_manager.py`**: Persistent team context registry - handles team context metadata and recovery

#### Team Configurations (`examples/teams/`)
- **`devops-team/`**: Complete DevOps team configuration - good starting point for understanding team structure
- **`security-team/`**: Cybersecurity team example - demonstrates specialized team workflows
- **`data-team/`**: Data engineering team example - shows multi-role team coordination

#### Docker Environment (`docker/claude-code/`)
- **`Dockerfile`**: Container definition with all dependencies
- **`run-command-with-env.sh`**: Environment loading script that sources `.ccbox/init.sh`
- **`session-monitor-daemon.sh`**: Background session monitoring

#### CLI Tools (`bin/`)
- **`ccdk`**: Docker container management - handles ccbox lifecycle
- **`ccorc`**: Team context management - handles persistent team contexts
- **`claude-bg`**: Background process manager - essential for non-blocking operations

#### Diagnostic Tools (`scripts/`)
- **`diagnose_agent_states.py`**: Debug agent state detection issues
- **`monitor_live_states.py`**: Real-time state monitoring for development
- **`capture-state-snapshot.sh`**: Quick debugging utility

### Project Structure Patterns
```
orchestrator/
├── .temp/                    # ALWAYS use for experiments and temporary files
├── src/                      # Production code only after thorough testing
├── examples/                 # Working examples for reference
├── docs/                     # End-user and technical documentation
├── tests/                    # Test suite (unit and integration)
├── scripts/                  # Utility and diagnostic scripts
└── docker/                   # Container environment definitions
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
- **Hardcoded keyword lists** (e.g., role_keywords = ['engineer', 'developer', ...])
- **Heuristic pattern matching** based on hardcoded assumptions

**EXAMPLES OF BAD PRACTICES TO AVOID**:
```python
# ❌ NEVER DO THIS:
KNOWN_ROLES = {'architect', 'developer', 'qa', ...}  # Hardcoded list
role_keywords = ['engineer', 'manager', ...]  # Brittle assumptions

# ❌ NEVER DO THIS:
if 'engineer' in text or 'developer' in text:  # Hardcoded checks
    return True
```

**REQUIRED APPROACH**:
- All configuration must come from config files or environment variables
- Use proper configuration management patterns
- Rely on explicit metadata (like Docker labels) instead of parsing/guessing
- **NO FALLBACKS** - If metadata is missing, fail with clear error message
- If temporary data is needed during development, mark with **FIXME**

**WHY THIS MATTERS**:
- Hardcoded lists are unmaintainable and will inevitably become outdated
- They make incorrect assumptions about data that will break with new inputs
- They create hidden dependencies that are hard to track and update

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
ccorc launch --team devops-team

# Force kill existing session
ccorc launch --team devops-team --force

# Use different session name
ccorc launch --team devops-team --session my-custom-session
```

## Session Persistence (Technical Details)

### Architecture Overview
The orchestrator supports automatic session persistence using Claude's built-in `--resume` functionality:

1. **Session ID Storage**: Each agent's session ID is stored in `TeamContextAgentInfo.session_id`
2. **Auto-Resume Logic**: `TeamLaunchService._launch_agent()` checks for existing session files before launching
3. **Session File Location**: `~/.claude/projects/<escaped-cwd>/<session-id>.jsonl`
4. **Fresh Sessions**: `--fresh` flag bypasses session checking and forces new UUIDs

### Implementation Details

#### Auto-Resume Decision Flow
1. Check if agent has existing `session_id` in context
2. If session ID exists and not `--fresh`: Use `--resume <session_id>`
3. Otherwise: Generate new session ID and start fresh

#### Key Components Modified
- `TeamContextAgentInfo`: Added `session_id` field
- `TeamLaunchService`: Added session resume logic

**Note**: Session file validation is NOT performed. The system trusts Claude's built-in session management and does not verify session file existence before attempting resume.

### Testing Session Persistence
```bash
# Launch team and create sessions
ccorc launch --team devops-team

# Verify session IDs are stored
ccorc info devops-team  # Shows session IDs

# Stop and restart - should auto-resume
ccorc launch --team devops-team

# Force fresh sessions
ccorc launch --team devops-team --fresh
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
# Start team in background
claude-bg start 'ccorc launch --team devops-team --session bg-demo' team-demo

# Check status
claude-bg status team-demo_[timestamp]

# View logs
claude-bg logs team-demo_[timestamp]

# Stop process
claude-bg stop team-demo_[timestamp]
```

## Development Patterns and Best Practices

### Backward Compatibility Policy

**IMPORTANT**: For this project, backward compatibility is generally NOT required. This allows for:
- Cleaner code without legacy support
- Faster development cycles
- Simpler data models
- Focus on current functionality over migration paths

When making changes:
- Feel free to modify data structures without migration code
- Don't add complexity to support old formats
- Focus on the best solution for current needs
- Document breaking changes clearly

## Development Patterns and Best Practices

### Team Configuration Development

#### Creating Custom Teams
1. **Start with Examples**: Use `examples/teams/devops-team/` as a template
2. **YAML Structure**: Follow the established team.yaml format with team, agents, and settings sections
3. **Agent Prompts**: Create `.md` files for agent-specific prompts (optional but recommended)
4. **Test Early**: Use `ccorc launch --team your-team` to test configurations immediately

#### Team Configuration Patterns
```yaml
# Standard team structure
team:
  name: "Team Name"
  description: "Clear team purpose"

agents:
  - name: "Lead"           # Coordinator role
    role: "Team Lead"
    model: "sonnet"
  - name: "Specialist"     # Domain expert
    role: "Domain Expert"
    model: "sonnet"

settings:
  orchestrator_type: "enhanced"  # Always use enhanced for production
  poll_interval: 0.5            # Adjust based on team responsiveness needs
```

### When to Use Enhanced vs Base Orchestrator
- **Base Orchestrator** (`orchestrator.py`): Use for simple coordination without state monitoring
- **Enhanced Orchestrator** (`orchestrator_enhanced.py`): Use for production - adds intelligent message delivery (default for team configs)

### State Detection Implementation Details
The system uses tmux pane content analysis with specific detection priority:

**Critical Pattern Recognition**:
1. **ERROR** (highest priority): Recent error messages in last 5 lines
2. **QUIT**: Agent has exited (no active process)
3. **BUSY**: Processing indicator visible (matches Claude's format: `^.\s+(ProcessingWord)…`)
4. **IDLE/WRITING**: Prompt box visible

**Key Implementation Notes**:
- Claude's processing indicator starts with rotating spinner + space + processing word
- Detection order matters - check ERROR before BUSY before IDLE
- State transitions trigger message delivery decisions

### Message Delivery Strategy
**Design Decision**: Claude Code handles input organization, so we deliver all messages but with contextual notifications:

- **IDLE**: Standard delivery
- **BUSY/WRITING**: Delivered with "check when convenient" note
- **ERROR/QUIT**: Not delivered (filtered out)

### Background Process Architecture
**Critical for Bash Tool Limitations**: The Bash tool cannot run processes in background with `&`, so:

1. **ALWAYS use `claude-bg`** for background processes
2. **NEVER use `&` operator** in Bash tool commands
3. **Sequential Operations**: Cannot run server + test simultaneously without background manager

### Container Environment Loading
The `.ccbox/` system enables workspace-specific configuration:

**Loading Sequence**:
1. Container starts with `run-command-with-env.sh`
2. Script sources `${WORKSPACE_PATH}/.ccbox/init.sh` if exists
3. Environment customization applied before command execution

**Developer Guidelines**:
- Use `${WORKSPACE_PATH}` for relative paths in init scripts
- Conditional setup based on project file detection
- Separate docker-specific environments (`.venv-docker/` not `.venv/`)

### Testing and Validation Patterns

#### State Detection Testing
```bash
# Use diagnostic tools to validate state detection
python scripts/diagnose_agent_states.py <session> --single
python scripts/monitor_live_states.py <session>  # Real-time validation
```

#### Component Testing Approach
1. **Start in `.temp/`**: All experiments and tests go here first
2. **Single Test Scripts**: Comprehensive tests that capture everything in parallel
3. **Terminal Feature Isolation**: Test tmux features separately before implementing
4. **State Tracking**: Always track previous state to avoid redundant updates

#### Integration Testing Strategy
- Test with real tmux sessions and Claude instances
- Validate state transitions under load
- Test message delivery across different states
- Verify team context persistence across container restarts

## Common Development Pitfalls and Solutions

### State Detection Issues

**Problem**: False state detection or missed transitions
**Root Causes**:
- Processing indicators appear/disappear quickly
- Multiple state indicators present simultaneously
- Race conditions in tmux content capture

**Solutions**:
- Increased polling frequency for BUSY detection
- Priority-based detection (ERROR > QUIT > BUSY > IDLE)
- Buffer analysis for consistent state determination

**Debug Approach**:
```bash
# Capture state snapshots during issues
python scripts/diagnose_agent_states.py <session> --duration 60
# Check for pattern matching issues in logs
```

### Message Delivery Race Conditions

**Problem**: Duplicate notifications or missed messages
**Root Causes**:
- Agent state changes during message delivery
- Reminder system triggering inappropriately
- Base vs Enhanced orchestrator compatibility issues

**Solutions**:
- Single notification format with convenience messaging
- State-aware delivery decisions
- Reminder reset logic when mailbox cleared

### Container Communication Issues

**Problem**: Agents cannot communicate via MCP
**Root Causes**:
- Missing shared directory mount (`/tmp/claude-orc`)
- Permission issues with socket files
- Container isolation blocking communication

**Solutions**:
- Ensure `/tmp/claude-orc` mounted in all containers
- Use consistent user ID mapping across containers
- Verify MCP server accessibility from all agents

### Background Process Management

**Problem**: Background processes don't start or terminate unexpectedly
**Root Causes**:
- Using `&` operator with Bash tool (doesn't work)
- Process not properly managed by `claude-bg`
- Log output not captured

**Solutions**:
- ALWAYS use `claude-bg` for background processes
- Check process status with `claude-bg status`
- Monitor logs with `claude-bg logs`

### Development Workflow Issues

**Problem**: Code scattered across multiple files or cluttered project structure
**Root Causes**:
- Creating files outside `.temp/` during development
- Multiple experimental versions in production directories
- Not cleaning up after experiments

**Solutions**:
- Start ALL experiments in `.temp/`
- Move only ONE clean version to production after testing
- Regular cleanup of temporary files
- Use proper file organization patterns

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