# CCORC Team Context Management Guide

## Overview

The Claude Multi-Agent Orchestrator supports persistent **team contexts** that survive container restarts and system reboots. This feature allows you to:

- Create long-running team contexts with preserved Claude Code state
- Resume work exactly where you left off after interruptions
- Manage multiple concurrent team contexts
- Clean up resources when contexts are no longer needed

**Key Concept**: Team context persistence is achieved through persistent Docker containers that maintain their internal Claude Code state (stored in `~/.claude` within each container).

## Team Contexts vs Individual Containers

### Team Contexts
- **Managed by**: `ccorc` and orchestrator `--context-name/--resume` flags
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
# Team context management (coordinates multiple agents)
ccorc list                    # Shows team contexts only
ccorc launch --team devops-team --session project-alpha

# Individual container management (single agents)
ccdk list                          # Shows all containers
ccdk start -i my-dev-container     # Single container
```

## Quick Start

### Creating a New Team Context
```bash
# Create a new team context using a pre-configured team
ccorc launch --team devops-team --session my-project

# This creates:
# - Tmux session: my-project
# - Team containers: my-project-architect, my-project-developer, etc.
# - Session registry entry tracking all components
```

### Resuming an Existing Team Context
```bash
# Resume a previous team context (containers restart automatically)
ccorc launch --team devops-team --session my-project

# Or use team context management commands
ccorc info my-project     # Check status first
ccorc health my-project   # Verify team health

# This:
# - Starts stopped team containers (if needed)
# - Reconnects to existing tmux session
# - Restores all agent states and message history
```

### Listing Available Team Contexts
```bash
# Show all registered team contexts
ccorc list

# Show detailed information
ccorc list --verbose

# Output shows:
# - Team session names and creation dates
# - Container status for each agent (running/stopped)
# - Tmux session status
# - Total and running container counts
```

**Note**: `ccorc list` shows only orchestrated team contexts. To see all containers (including individual ones), use `ccdk list`.

## Container Lifecycle and Persistence

### How Team Context Persistence Works

1. **Team Container Creation**: Each agent gets a persistent container with its own `~/.claude` directory
2. **State Storage**: Claude Code stores session data, conversation history, and settings in `~/.claude`
3. **Container Persistence**: Team containers are stopped (not removed) when sessions end
4. **State Restoration**: Restarting team containers restores all Claude Code state automatically

### Container States in Team Contexts

- **Running**: Container is active, agent is available for orchestrated work
- **Stopped**: Container exists but is not running (team state preserved)
- **Missing**: Container was manually removed (team context broken)

### Example Team Context Workflow
```bash
# Day 1: Start team context
ccorc launch --team data-team --session data-analysis
# ... work with coordinated agents, team containers created and running

# End of day: Stop session (team containers persist)
# Team containers are stopped but not removed

# Day 2: Resume team context  
ccorc launch --team data-team --session data-analysis
# Team containers restart, all previous team context restored
```

## Troubleshooting Common Issues

### Team Context Won't Resume
**Problem**: `--resume` fails with "session not found"
**Solution**: 
```bash
# Check if team context exists
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

# Then resume team context
ccorc launch --team devops-team --session my-project
```

### Tmux Session Conflicts
**Problem**: "session already exists" error
**Solution**:
```bash
# Check existing tmux sessions
tmux ls

# Attach to existing team context instead of creating new
tmux attach -t my-project

# Or force kill existing and recreate
ccorc launch --team devops-team --session my-project --force
```

### Out of Disk Space
**Problem**: Many persistent team containers consuming disk space
**Solution**:
```bash
# List all team contexts and their container counts
ccorc list --verbose

# Clean up old unused team contexts
ccorc cleanup --interactive

# Remove specific team context completely
ccorc cleanup --remove my-old-project
```

## Best Practices for Long-Running Team Contexts

### Session Naming
- Use descriptive names: `customer-support-team`, `data-pipeline-debug`
- Include dates for temporary work: `hotfix-team-2025-08-01`
- Avoid spaces and special characters

### Resource Management
- **Monitor Team Contexts**: Check team context status regularly
- **Clean Up Completed Work**: Remove team contexts when projects finish
- **Limit Concurrent Team Contexts**: Don't run too many team contexts simultaneously

### Backup Important Work
```bash
# Export team context information and metadata
ccorc export my-project --output ./backups/

# Monitor team context health before major changes  
ccorc health my-project
```

### Development Workflow
```bash
# 1. Start team context for new feature
ccorc launch --team devops-team --session feature-auth

# 2. Work with coordinated agents throughout development
# (team containers automatically save state)

# 3. Stop when switching contexts
# (team containers stop but preserve coordinated state)

# 4. Resume when returning to feature
ccorc launch --team devops-team --session feature-auth

# 5. Clean up when feature is complete
ccorc clean feature-auth
```

### Team Collaboration
- **Session Sharing**: Share team context names for coordinated handoffs
- **State Documentation**: Use Claude's memory features to document team context context
- **Clean Handoffs**: Document current team state before passing sessions to teammates

## Advanced Usage

### Custom Team Container Configuration
```bash
# Start team context with custom settings
ccorc launch --team devops-team --session my-project --debug

# Override specific agent models
ccorc launch --team devops-team --session my-project \
  --agent-model "Architect=opus" \
  --agent-model "Developer=sonnet"
```

### Team Context Monitoring
```bash
# Monitor team context health
ccorc health my-project

# List all team contexts with detailed status
ccorc list --verbose
```

### Bulk Team Context Operations
```bash
# Clean up multiple team contexts interactively
ccorc cleanup --interactive

# Remove team contexts by pattern
ccorc cleanup --pattern "feature-*"

# Remove all stopped team contexts
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

# Create individual containers (not part of team contexts)
ccdk run -i standalone-dev
```

### With tmux
Team sessions create standard tmux sessions that work with all tmux commands:
```bash
# Attach to team context
tmux attach -t my-project

# Create additional windows in team context
tmux new-window -t my-project -n "monitoring"

# Use all standard tmux features with team contexts
```

### With Background Processes
```bash
# Run team context in background
claude-bg start 'ccorc launch --team devops-team --session bg-task' session-runner

# Run different team in background
claude-bg start 'ccorc launch --team security-team --session security-review' security-runner
```

## Session CLI Reference

### Complete Command Reference

```bash
# List all team contexts (NOT individual containers)
ccorc list [--verbose]

# Check team context health  
ccorc health <session-name>

# Export team context metadata
ccorc export <session-name> [--output <path>]

# Clean up team contexts
ccorc cleanup [options]
  --interactive          # Interactive team context selection
  --remove <name>        # Remove specific team context
  --pattern <pattern>    # Remove team contexts matching pattern
  --stopped-only         # Remove only stopped team contexts
  --fix-broken          # Fix team contexts with missing containers
```

### Key Differences from ccdk

| Command | Scope | Purpose |
|---------|-------|---------|
| `ccorc list` | Team sessions only | Show orchestrated multi-agent sessions |
| `ccdk list` | All containers | Show individual containers (team + standalone) |
| `ccorc cleanup` | Team sessions | Remove coordinated agent groups |
| `ccdk stop/start` | Individual containers | Manage single containers |

### Integration with Core Components

- **TeamContextManager**: Core team context persistence and registry management
- **Orchestrator Integration**: Automatic team context creation and management via `--context-name` and `--resume` flags
- **Container Discovery**: Hybrid approach using both registry and live container inspection for team containers
- **Registry Synchronization**: CLI operations update shared team context registry

---

For more detailed information, see:
- `src/team_context_manager.py` - Core team context management implementation
- `bin/ccorc` - Command-line interface source
- `tests/unit/test_session_persistence.py` - Test suite and examples
- `examples/` - Example team context configurations