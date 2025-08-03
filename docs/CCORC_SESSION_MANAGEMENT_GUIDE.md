# CCORC Session Management Guide

## Overview

The Claude Multi-Agent Orchestrator supports persistent **team sessions** that survive container restarts and system reboots. This feature allows you to:

- Create long-running team sessions with preserved Claude Code state
- Resume work exactly where you left off after interruptions
- Manage multiple concurrent team sessions
- Clean up resources when sessions are no longer needed

**Key Concept**: Session persistence is achieved through persistent Docker containers that maintain their internal Claude Code state (stored in `~/.claude` within each container).

## Team Sessions vs Individual Containers

### Team Sessions
- **Managed by**: `ccorc` and orchestrator `--session-name/--resume` flags
- **Scope**: Complete team setups (leader, researcher, writer agents)
- **Purpose**: Orchestrated multi-agent work sessions
- **Lifecycle**: Created/resumed as coordinated units

### Individual Containers  
- **Managed by**: `ccdk` commands
- **Scope**: Single Claude Code instances
- **Purpose**: Standalone development work
- **Lifecycle**: Independent container management

**Example Distinction**:
```bash
# Team session management (coordinates multiple agents)
ccorc list                    # Shows team sessions only
python examples/team_mcp_demo_enhanced.py --session-name project-alpha

# Individual container management (single agents)
ccdk list                          # Shows all containers
ccdk start -i my-dev-container     # Single container
```

## Quick Start

### Creating a New Team Session
```bash
# Create a new team session
python examples/team_mcp_demo_enhanced.py --session-name my-project

# This creates:
# - Tmux session: my-project
# - Team containers: my-project-leader, my-project-researcher, my-project-writer
# - Session registry entry tracking all components
```

### Resuming an Existing Team Session
```bash
# Resume a previous team session
python examples/team_mcp_demo_enhanced.py --resume my-project

# This:
# - Starts stopped team containers (if needed)
# - Reconnects to existing tmux session
# - Restores all agent states and message history
```

### Listing Available Team Sessions
```bash
# Show all registered team sessions
ccorc list

# Show detailed information
ccorc list --verbose

# Output shows:
# - Team session names and creation dates
# - Container status for each agent (running/stopped)
# - Tmux session status
# - Total and running container counts
```

**Note**: `ccorc list` shows only orchestrated team sessions. To see all containers (including individual ones), use `ccdk list`.

## Container Lifecycle and Persistence

### How Team Session Persistence Works

1. **Team Container Creation**: Each agent gets a persistent container with its own `~/.claude` directory
2. **State Storage**: Claude Code stores session data, conversation history, and settings in `~/.claude`
3. **Container Persistence**: Team containers are stopped (not removed) when sessions end
4. **State Restoration**: Restarting team containers restores all Claude Code state automatically

### Container States in Team Sessions

- **Running**: Container is active, agent is available for orchestrated work
- **Stopped**: Container exists but is not running (team state preserved)
- **Missing**: Container was manually removed (team session broken)

### Example Team Session Workflow
```bash
# Day 1: Start team session
python examples/team_mcp_demo_enhanced.py --session-name data-analysis
# ... work with coordinated agents, team containers created and running

# End of day: Stop session (team containers persist)
# Team containers are stopped but not removed

# Day 2: Resume team session  
python examples/team_mcp_demo_enhanced.py --resume data-analysis
# Team containers restart, all previous team context restored
```

## Troubleshooting Common Issues

### Team Session Won't Resume
**Problem**: `--resume` fails with "session not found"
**Solution**: 
```bash
# Check if team session exists
ccorc list

# If session exists but containers are missing:
ccorc cleanup --fix-broken
```

### Team Containers Not Starting
**Problem**: Resume fails because team containers won't start
**Solution**:
```bash
# Check team container status
ccorc list --verbose

# Manually start team containers
ccdk start -i my-project-leader
ccdk start -i my-project-researcher  
ccdk start -i my-project-writer

# Then resume team session
python examples/team_mcp_demo_enhanced.py --resume my-project
```

### Tmux Session Conflicts
**Problem**: "session already exists" error
**Solution**:
```bash
# Check existing tmux sessions
tmux ls

# Attach to existing team session instead of creating new
tmux attach -t my-project

# Or force kill existing and recreate
python examples/team_mcp_demo_enhanced.py --session-name my-project --force
```

### Out of Disk Space
**Problem**: Many persistent team containers consuming disk space
**Solution**:
```bash
# List all team sessions and their container counts
ccorc list --verbose

# Clean up old unused team sessions
ccorc cleanup --interactive

# Remove specific team session completely
ccorc cleanup --remove my-old-project
```

## Best Practices for Long-Running Team Sessions

### Session Naming
- Use descriptive names: `customer-support-team`, `data-pipeline-debug`
- Include dates for temporary work: `hotfix-team-2025-08-01`
- Avoid spaces and special characters

### Resource Management
- **Monitor Team Sessions**: Check team session status regularly
- **Clean Up Completed Work**: Remove team sessions when projects finish
- **Limit Concurrent Team Sessions**: Don't run too many team sessions simultaneously

### Backup Important Work
```bash
# Export team session information and metadata
ccorc export my-project --output ./backups/

# Monitor team session health before major changes  
ccorc health my-project
```

### Development Workflow
```bash
# 1. Start team session for new feature
python examples/team_mcp_demo_enhanced.py --session-name feature-auth

# 2. Work with coordinated agents throughout development
# (team containers automatically save state)

# 3. Stop when switching contexts
# (team containers stop but preserve coordinated state)

# 4. Resume when returning to feature
python examples/team_mcp_demo_enhanced.py --resume feature-auth

# 5. Clean up when feature is complete
ccorc cleanup --remove feature-auth
```

### Team Collaboration
- **Session Sharing**: Share team session names for coordinated handoffs
- **State Documentation**: Use Claude's memory features to document team session context
- **Clean Handoffs**: Document current team state before passing sessions to teammates

## Advanced Usage

### Custom Team Container Configuration
```bash
# Start team session with custom container settings
python examples/team_mcp_demo_enhanced.py \
  --session-name my-project \
  --container-memory 4g \
  --container-cpus 2
```

### Team Session Monitoring
```bash
# Monitor team session health
ccorc health my-project

# List all team sessions with detailed status
ccorc list --verbose
```

### Bulk Team Session Operations
```bash
# Clean up multiple team sessions interactively
ccorc cleanup --interactive

# Remove team sessions by pattern
ccorc cleanup --pattern "feature-*"

# Remove all stopped team sessions
ccorc cleanup --stopped-only
```

## Integration with Existing Tools

### With ccdk (Individual Container Management)
Team session management works alongside individual container management:
```bash
# View team containers created by sessions
ccdk list | grep my-project

# Access individual agent containers directly
ccdk shell -i my-project-leader

# Check logs for specific team agent
ccdk logs -i my-project-researcher

# Create individual containers (not part of team sessions)
ccdk run -i standalone-dev
```

### With tmux
Team sessions create standard tmux sessions that work with all tmux commands:
```bash
# Attach to team session
tmux attach -t my-project

# Create additional windows in team session
tmux new-window -t my-project -n "monitoring"

# Use all standard tmux features with team sessions
```

### With Background Processes
```bash
# Run team session in background
claude-bg start 'python examples/team_mcp_demo_enhanced.py --session-name bg-task' session-runner

# Resume team session in background
claude-bg start 'python examples/team_mcp_demo_enhanced.py --resume bg-task' session-resumer
```

## Session CLI Reference

### Complete Command Reference

```bash
# List all team sessions (NOT individual containers)
ccorc list [--verbose]

# Check team session health  
ccorc health <session-name>

# Export team session metadata
ccorc export <session-name> [--output <path>]

# Clean up team sessions
ccorc cleanup [options]
  --interactive          # Interactive team session selection
  --remove <name>        # Remove specific team session
  --pattern <pattern>    # Remove team sessions matching pattern
  --stopped-only         # Remove only stopped team sessions
  --fix-broken          # Fix team sessions with missing containers
```

### Key Differences from ccdk

| Command | Scope | Purpose |
|---------|-------|---------|
| `ccorc list` | Team sessions only | Show orchestrated multi-agent sessions |
| `ccdk list` | All containers | Show individual containers (team + standalone) |
| `ccorc cleanup` | Team sessions | Remove coordinated agent groups |
| `ccdk stop/start` | Individual containers | Manage single containers |

### Integration with Core Components

- **SessionManager**: Core team session persistence and registry management
- **Orchestrator Integration**: Automatic team session creation and management via `--session-name` and `--resume` flags
- **Container Discovery**: Hybrid approach using both registry and live container inspection for team containers
- **Registry Synchronization**: CLI operations update shared team session registry

---

For more detailed information, see:
- `src/session_manager.py` - Core team session management implementation
- `bin/ccorc` - Command-line interface source
- `tests/unit/test_session_persistence.py` - Test suite and examples
- `examples/` - Example team session configurations