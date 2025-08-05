# Team Context and Session Management Guide

This guide explains the architecture and concepts behind team contexts and session persistence in the Claude Multi-Agent Orchestrator.

> **For CLI commands and syntax, see the [CLI Reference Guide](CLI_REFERENCE.md)**

## Overview

The Claude Multi-Agent Orchestrator supports persistent **team contexts** that survive container restarts and system reboots. This enables:

- Long-running team sessions with preserved state
- Resuming work exactly where you left off
- Managing multiple concurrent team contexts
- Clean resource management

## Core Concepts

### Team Contexts
A team context is a complete orchestrated environment that includes:
- **Team Configuration**: The YAML/JSON definition of agents and settings
- **Docker Containers**: One container per agent, named `<context>-<agent>`
- **tmux Session**: Terminal multiplexer session for agent interaction
- **Session IDs**: Unique identifiers for each agent's conversation history
- **Metadata**: Creation time, configuration overrides, task assignments

### Contexts vs Individual Containers

**Team Contexts** (Managed by `ccorc`):
- Coordinate multiple agents as a unit
- Provide orchestrated communication via MCP
- Maintain team-level state and configuration
- Launch/stop all agents together

**Individual Containers** (Managed by `ccdk`):
- Single Claude instances for standalone work
- No orchestration or inter-agent communication
- Independent lifecycle management
- Useful for solo development tasks

## Session Persistence Architecture

### How It Works

1. **Session ID Generation**: Each agent gets a UUID when first launched
2. **Conversation Storage**: Claude saves conversations in `~/.claude/projects/<workspace>/<session-id>.jsonl`
3. **Context Registry**: Team contexts store session IDs in `~/.claude-orc/team_contexts.json`
4. **Auto-Resume**: When relaunching, agents use `claude --resume <session-id>`

### Session Lifecycle

```
First Launch:
├── Generate new session IDs
├── Launch agents with fresh sessions
├── Store IDs in context registry
└── Conversations saved automatically

Subsequent Launches:
├── Load session IDs from registry
├── Check if --fresh flag is set
├── If not fresh: Resume with existing IDs
└── If fresh: Generate new IDs
```

### Important Notes
- Session files are NOT validated before resume attempts
- Claude handles missing/corrupted session files gracefully
- The `--fresh` flag forces new sessions regardless of existing IDs

## Context Persistence

### Registry Structure
Team contexts are stored in `~/.claude-orc/team_contexts.json`:

```json
{
  "contexts": {
    "my-project": {
      "name": "my-project",
      "team_name": "devops-team",
      "agents": [
        {
          "name": "Architect",
          "role": "System Architect",
          "model": "sonnet",
          "session_id": "abc123-def456-..."
        }
      ],
      "tmux_session": "my-project",
      "created_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "task": "Build authentication system"
      }
    }
  }
}
```

### Container Naming Convention
Containers follow the pattern: `ccbox-<context>-<agent>`
- Example: `ccbox-my-project-architect`
- This enables Docker-based discovery of team members

## Working with Team Contexts

### Typical Workflow

1. **Initial Setup**: Launch team with specific task
2. **Active Development**: Agents collaborate via MCP
3. **Interruption**: Stop work (containers persist)
4. **Resume**: Relaunch team (conversations continue)
5. **Completion**: Clean up resources

### Best Practices

**Context Naming**:
- Use descriptive names: `auth-feature`, `q4-analysis`
- Avoid generic names: `test`, `temp`
- Include project/feature identifiers

**Session Management**:
- Use `--fresh` for new features/tasks
- Let sessions resume for ongoing work
- Export contexts before major changes

**Resource Cleanup**:
- Remove contexts when work is complete
- Check for orphaned containers with `ccdk ps`
- Use `ccorc rm -f` for force cleanup

## Advanced Topics

### Multi-Context Management
Run multiple teams concurrently:
- Each context has isolated containers
- Separate tmux sessions per team
- No cross-context communication

### Context Recovery
If containers are manually stopped:
1. Context metadata remains intact
2. Relaunch recreates containers
3. Sessions resume from last state

### Background Operations
For long-running teams:
- Use `claude-bg` to run in background
- Contexts persist across daemon restarts
- Logs available via `claude-bg logs`

## Troubleshooting

### Common Issues

**"Context already exists" error**:
- Use `-f` flag to force cleanup
- Or choose a different context name

**Containers not starting**:
- Check if containers already exist: `docker ps -a`
- Verify Docker daemon is running
- Check for port conflicts

**Sessions not resuming**:
- Verify session files exist in `~/.claude/`
- Check if `--fresh` flag was used
- Ensure same working directory

### Diagnostic Commands
```bash
# Check context details
ccorc info <context>

# Verify container health
ccorc health <context>

# View Docker containers
docker ps -a | grep ccbox

# Check tmux sessions
tmux ls
```

## Architecture Details

### Component Interaction
```
User → ccorc launch
      ├→ TeamLaunchService
      │  ├→ Load team config
      │  ├→ Create/resume context
      │  └→ Launch orchestrator
      ├→ OrchestratorFactory
      │  └→ Create enhanced orchestrator
      ├→ Docker containers
      │  └→ One per agent
      └→ tmux session
         └→ Panes for each agent
```

### State Management
- **Persistent**: Context registry, session IDs
- **Ephemeral**: tmux sessions, container state
- **Recoverable**: Agent conversations, team configuration