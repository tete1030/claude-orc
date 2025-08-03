# Claude Multi-Agent Orchestrator Usage Guide

This guide covers how to use the Claude Multi-Agent Orchestrator system for end users and operators.

## Quick Start

### Installation

```bash
# Install system dependencies
./scripts/install-claude-bg.sh    # Background process manager
./scripts/install-ccdk.sh         # Docker management CLI
./scripts/install-ccorc.sh        # Team context manager

# Set up Python environment with Poetry
poetry install --no-dev           # Production dependencies only
poetry shell                      # Activate environment
```

## Getting Started with Teams

### List Available Teams
```bash
# See all pre-configured teams
ccorc teams list

# Shows teams like:
# - devops-team: Complete DevOps team (5 agents)
# - security-team: Cybersecurity team (4 agents)  
# - data-team: Data engineering team (4 agents)
```

### Launch a Team
```bash
# Launch the DevOps team
ccorc launch --team devops-team

# Launch with custom session name
ccorc launch --team devops-team --session my-project

# Launch with different model
ccorc launch --team devops-team --model sonnet

# Override individual agent models
ccorc launch --team devops-team --agent-model "Architect=opus" --agent-model "Developer=sonnet"

# Force kill existing session
ccorc launch --team devops-team --force

# Enable debug mode
ccorc launch --team devops-team --debug
```

### Team Configuration
Create custom teams using YAML files in the `teams/` directory:

```yaml
# teams/my-team.yaml
team:
  name: "My Custom Team"
  description: "Custom team for specific tasks"

agents:
  - name: "Lead"
    role: "Team Lead and Coordinator"
    model: "sonnet"
  - name: "Specialist"
    role: "Domain Expert"
    model: "sonnet"

settings:
  default_context_name: "my-team"
  orchestrator_type: "enhanced"
  poll_interval: 0.5
```

Launch your custom team:
```bash
ccorc launch --team my-team
```

## Interacting with Agents

The orchestrator runs agents in tmux with mouse support and keyboard shortcuts:

```bash
# Attach to the team session
tmux attach -t devops-team
# or
tmux attach -t my-project  # if you used --session my-project

# Navigate between agents:
# F1-F5 or Alt+1-5 - Switch to agent panes
# Mouse click - Switch to any pane
# Mouse scroll - Navigate history

# Standard tmux navigation also works:
# Ctrl+b, 1-5 - Switch to specific agent
# Ctrl+b, arrow keys - Navigate panes
# Ctrl+b, d - Detach from session

# Use Claude shortcuts (press '?' in any pane)
```

## Background Process Management

### Using claude-bg
```bash
# Start team in background
claude-bg start 'ccorc launch --team devops-team --session bg-team' team-demo

# Check status
claude-bg status team-demo_[timestamp]

# View logs
claude-bg logs team-demo_[timestamp]

# Stop process
claude-bg stop team-demo_[timestamp]
```

## Diagnostic Tools

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

## Team Context Management

Teams automatically create persistent contexts that survive restarts:

```bash
# List all active team contexts
ccorc list

# Get detailed information about a team
ccorc info my-project

# Check team health
ccorc health my-project

# Clean up team contexts
ccorc clean my-project
ccorc clean my-project --force

# Export team context metadata
ccorc export my-project my-project-backup.json
```

## Docker Management (ccdk)

```bash
# Build image
ccdk build

# Run Claude with options
ccdk run -i dev -m sonnet
ccdk run --isolated

# Start persistent container
ccdk start -i frontend

# Run Claude in existing container
ccdk cc -i frontend
ccdk cc -i frontend --help

# Open shell
ccdk shell -i frontend
ccdk shell -i frontend python app.py

# Other commands
ccdk stop -i frontend    # Stop container
ccdk logs -i frontend    # View logs
ccdk list                # List all containers
```

## Workspace Configuration (.ccbox/)

The `.ccbox/` directory provides workspace-specific configuration for Docker containers (CCBox - Claude Code Box). This directory enables custom environment setup and volume mounts for different project types.

### Directory Structure
```
.ccbox/
├── init.sh           # Workspace initialization script (optional)
├── mounts           # Custom volume mounts configuration (optional)
└── .gitignore       # Excludes configuration files from git
```

### Workspace Initialization (init.sh)
Create `.ccbox/init.sh` to customize the container environment for your specific project:

```bash
#!/bin/bash
# Example .ccbox/init.sh for a Python/Poetry project

# Configure Poetry for Docker environment
export POETRY_VIRTUALENVS_IN_PROJECT=false
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"

# Set up project-specific environment variables
export DATABASE_URL="sqlite:///dev.db"
export DEBUG=true

# Initialize or activate virtual environment
if command -v poetry &> /dev/null; then
    poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker"
    poetry env use python3.12 2>/dev/null || true
fi

# Auto-activate existing virtual environment
if [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
    DOCKER_VENV=$(find "${WORKSPACE_PATH}/.venv-docker" -maxdepth 1 -type d -name "*-py3.12" | head -1)
    if [ -n "$DOCKER_VENV" ] && [ -d "$DOCKER_VENV" ]; then
        export VIRTUAL_ENV="$DOCKER_VENV"
        export PATH="$VIRTUAL_ENV/bin:$PATH"
        source "$VIRTUAL_ENV/bin/activate" 2>/dev/null || true
    fi
fi
```

### Custom Volume Mounts
Configure additional volume mounts in `.ccbox/mounts`:

```bash
# Mount data directories
MOUNT_DATA="/mnt/data:/mnt/data:ro"
MOUNT_DATASETS="/home/user/datasets:/workspace/datasets:ro"

# Mount code repositories
MOUNT_PROJECTS="/home/user/projects:/workspace/projects:cached"

# Mount shared caches
MOUNT_NPM_CACHE="/home/user/.npm:/home/user/.npm:cached"
MOUNT_PIP_CACHE="/home/user/.cache/pip:/home/user/.cache/pip:cached"
```

### Language-Specific Examples

#### Python/Poetry Project
```bash
#!/bin/bash
# .ccbox/init.sh for Python project
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"
poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker"
poetry env use python3.12 2>/dev/null || true

# Auto-install dependencies if pyproject.toml exists
if [ -f "${WORKSPACE_PATH}/pyproject.toml" ] && ! [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
    echo "Installing Python dependencies with Poetry..."
    poetry install --no-root
fi
```

#### Node.js Project
```bash
#!/bin/bash
# .ccbox/init.sh for Node.js project
export NODE_ENV=development

# Auto-install dependencies if package.json exists
if [ -f "${WORKSPACE_PATH}/package.json" ] && ! [ -d "${WORKSPACE_PATH}/node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi
```

#### Multi-Language Project
```bash
#!/bin/bash
# .ccbox/init.sh for multi-language project
# Python setup
if [ -f "${WORKSPACE_PATH}/pyproject.toml" ]; then
    export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"
    poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker"
    poetry env use python3.12 2>/dev/null || true
fi

# Node.js setup
if [ -f "${WORKSPACE_PATH}/package.json" ]; then
    export NODE_ENV=development
fi

# Go setup
if [ -f "${WORKSPACE_PATH}/go.mod" ]; then
    export GOPATH="${WORKSPACE_PATH}/.go"
    export PATH="${GOPATH}/bin:$PATH"
fi
```

### Best Practices
- **Version Control**: Add `.ccbox/.gitignore` to exclude environment-specific files
- **Documentation**: Include setup instructions in your project README
- **Portability**: Use relative paths and environment variables in configuration
- **Security**: Never commit API keys or secrets in `.ccbox/` files
- **Performance**: Use `:cached` mount option for frequently accessed code directories

## Production Deployment Best Practices

### Environment Setup
```bash
# 1. Install system dependencies
./scripts/install-claude-bg.sh    # Background process manager
./scripts/install-ccdk.sh         # Docker management CLI

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
# Start team in background for production
claude-bg start 'ccorc launch --team devops-team --session production' production-team

# Monitor status
claude-bg status production-team_[timestamp]
claude-bg logs production-team_[timestamp]
```

#### Docker-Based Deployment
```bash
# Build production image
ccdk build

# Launch team with containerized agents
ccorc launch --team devops-team --session production
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

## See Also

- [CCDK Usage Guide](CCDK_USAGE.md) - Detailed Docker container management
- [Workspace Configuration Guide](WORKSPACE_CONFIGURATION.md) - Comprehensive .ccbox/ setup
- [Docker Environment README](../docker/claude-code/README.md) - Container setup details
- [Feature Matrix](FEATURE_MATRIX.md) - Feature comparison across components
- [Known Limitations](KNOWN_LIMITATIONS.md) - Current limitations and workarounds