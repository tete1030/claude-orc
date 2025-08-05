# Claude Multi-Agent Orchestrator Usage Guide

This guide covers how to use the Claude Multi-Agent Orchestrator system, focusing on workflows, concepts, and best practices.

> **For detailed CLI syntax and options, see the [CLI Reference Guide](CLI_REFERENCE.md)**

## Quick Start

### Installation

The Claude Multi-Agent Orchestrator can be installed in several ways depending on your needs:

#### Local Installation

There are multiple methods to install ccorc locally:

1. **Install from source with pip**:
   ```bash
   pip install /path/to/claude-orc
   ```

2. **Install in editable mode** (recommended for development):
   ```bash
   pip install -e /path/to/claude-orc
   ```

3. **Install with Poetry** (if working with the source code):
   ```bash
   cd /path/to/claude-orc
   poetry install
   ```

#### Docker Installation

When using the Docker environment, ccorc is pre-installed in the container image:

- No need to mount source code for ccorc to work
- The Docker image includes ccorc as a standalone package
- Simply use `ccdk run` or `ccdk start` to launch containers with ccorc available

#### Team Configuration Paths

The system searches for team configurations in these locations (in order):

1. Current directory: `teams/`
2. User home directory: `~/.ccorc/teams/`
3. Package data directory (for built-in teams)

You can also set custom paths using the `CCORC_TEAMS_PATH` environment variable:
```bash
export CCORC_TEAMS_PATH="/path/to/teams:/another/path/to/teams"
```

**Note**: The CCORC_TEAMS_PATH environment variable uses colon-separated paths (like PATH). There are ongoing investigations regarding YAML file handling with this variable - check the latest documentation for updates.

#### Development Usage

For backward compatibility, the original wrapper script still works:
```bash
# From the claude-orc directory
bin/ccorc [command]
```

This is useful when working directly with the source code without installing the package.

#### System Utilities

After installation, install the supporting utilities:

```bash
# Install background process manager
./scripts/install-claude-bg.sh

# Install Docker management CLI
./scripts/install-ccdk.sh

# Set up Python environment with Poetry (if needed)
poetry install --no-dev           # Production dependencies only
poetry shell                      # Activate environment
```

## Core Concepts

### Teams
Pre-configured groups of agents that work together with specific roles and workflows. Teams are defined in YAML configuration files and can be launched with a single command.

### Contexts
Persistent team sessions that maintain state across restarts. Each context includes:
- Team configuration and agent assignments
- Docker containers for each agent
- tmux session for interaction
- Session IDs for conversation persistence

### Agents
Individual Claude instances with specific roles, prompts, and models. Agents communicate via MCP (Model Context Protocol) tools.

## Working with Teams

### Available Teams
The system includes several pre-configured teams:
- **devops-team**: Complete DevOps workflow (5 agents)
- **security-team**: Cybersecurity analysis (4 agents)  
- **data-team**: Data engineering pipeline (4 agents)

### Team Workflow

1. **List available teams**:
   ```bash
   ccorc teams list
   ```

2. **Launch a team**:
   ```bash
   ccorc launch devops-team
   ```

3. **Interact with agents**:
   ```bash
   tmux attach -t devops-team
   ```

4. **Monitor team status**:
   ```bash
   ccorc info devops-team
   ```

See the [Team Configuration Guide](TEAM_CONFIGURATION.md) for creating custom teams.

## Interacting with Agents

### tmux Navigation
The orchestrator uses tmux with enhanced navigation:

- **F1-F5** or **Alt+1-5**: Switch to agent panes
- **Mouse click**: Switch to any pane
- **Mouse scroll**: Navigate history
- **Ctrl+b, d**: Detach from session

### Agent Communication
Agents communicate using MCP tools:
- `send_message`: Send to specific agent
- `check_messages`: Check inbox
- `broadcast_message`: Send to all agents
- `list_agents`: See available agents

## Session Persistence

### How It Works
- Each agent gets a unique session ID
- Conversations are saved automatically
- Sessions resume on team restart
- Use `-F` flag to force fresh sessions

### Session Management
1. **Normal launch** (resumes existing):
   ```bash
   ccorc launch devops-team
   ```

2. **Fresh start** (new sessions):
   ```bash
   ccorc launch devops-team -F
   ```

See the [Session Architecture Guide](SESSION_ARCHITECTURE.md) for details.

## Container Environment

### Workspace Configuration (.ccbox/)
Customize Docker environments per project:

```
.ccbox/
├── init.sh           # Environment setup script
├── mounts           # Custom volume mounts
└── .gitignore      # Exclude from version control
```

#### Example init.sh
```bash
#!/bin/bash
# Configure project environment
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"
export DATABASE_URL="sqlite:///dev.db"

# Auto-activate virtual environment
if [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
    source "$(find .venv-docker -name activate | head -1)" 2>/dev/null
fi
```

#### Example mounts
```bash
# Mount data directories
MOUNT_DATA="/mnt/data:/mnt/data:ro"
MOUNT_CACHE="/home/user/.cache:/workspace/.cache:cached"
```

## Background Operations

Use `claude-bg` for long-running teams:

```bash
# Start in background
claude-bg start 'ccorc launch devops-team' team-bg

# Check status
claude-bg status team-bg_[timestamp]

# View logs
claude-bg logs team-bg_[timestamp]
```

## Common Workflows

### Development Team Workflow
1. Launch team with task:
   ```bash
   ccorc launch devops-team -t "Build authentication system"
   ```

2. Monitor progress:
   ```bash
   tmux attach -t devops-team
   ```

3. Check team health:
   ```bash
   ccorc health devops-team
   ```

### Data Processing Workflow
1. Launch with specific model:
   ```bash
   ccorc launch data-team -m opus
   ```

2. Run in background:
   ```bash
   claude-bg start 'ccorc launch data-team -t "Process Q4 data"' data-job
   ```

### Security Audit Workflow
1. Fresh start for new audit:
   ```bash
   ccorc launch security-team -F -t "Audit codebase for vulnerabilities"
   ```

2. Enable debug mode:
   ```bash
   ccorc launch security-team -d
   ```

## Best Practices

### Team Management
- Use descriptive context names for different projects
- Clean up contexts when done: `ccorc rm old-project`
- Export important contexts: `ccorc export project backup.json`

### Performance Optimization
- Use appropriate models for each task
- Enable debug mode (`-d`) only when troubleshooting
- Monitor container resources with `docker stats`

### Troubleshooting
- Check agent states: `python scripts/monitor_live_states.py <session>`
- View container logs: `ccdk logs <instance>`
- Diagnose issues: `python scripts/diagnose_agent_states.py <session>`

## Advanced Topics

### Custom Team Creation
See [Team Configuration Guide](TEAM_CONFIGURATION.md)

### Session Architecture
See [Session Architecture Guide](SESSION_ARCHITECTURE.md)

### CLI Reference
See [CLI Reference Guide](CLI_REFERENCE.md)

### Docker Environment
See [Docker Setup Guide](../docker/claude-code/README.md)