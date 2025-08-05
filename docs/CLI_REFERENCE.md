# CLI Reference Guide

This document provides a complete reference for all CLI commands and options in the Claude Multi-Agent Orchestrator.

## CCORC (Claude Code Orchestrator)

### Command Structure
```
ccorc <command> [target] [options]
```

### Commands

#### `launch` - Launch a team configuration
```bash
ccorc launch <team> [context-name] [options]

Positional Arguments:
  team              Team configuration name (required)
  context-name      Context name (optional, defaults to team name)

Options:
  -m, --model       Override all agents' models
  -f, --force       Force kill existing session if it exists
  -d, --debug       Enable debug mode
  -t, --task        Initial task for the team
  --rm              Automatic context cleanup on exit
  -F, --fresh       Force new sessions, ignore existing session IDs
  --agent-model     Override specific agent model (format: Agent=model)

Examples:
  ccorc launch devops-team
  ccorc launch devops-team my-project --rm
  ccorc launch security-team -t "Audit the codebase"
  ccorc launch data-team -m opus -d -F
  ccorc launch devops-team prod -f -t "Deploy v2.0"
```

#### `ls` / `list` - List all team contexts
```bash
ccorc ls [-d]
ccorc list [--detailed]

Options:
  -d, --detailed    Show detailed information

Examples:
  ccorc ls
  ccorc list -d
```

#### `info` - Show detailed context information
```bash
ccorc info <context-name>

Examples:
  ccorc info devops-team
  ccorc info my-project
```

#### `health` - Check context health
```bash
ccorc health <context-name>

Examples:
  ccorc health devops-team
```

#### `rm` / `clean` - Clean up a context
```bash
ccorc rm <context-name> [-f]
ccorc clean <context-name> [--force]

Options:
  -f, --force       Skip confirmation prompt

Examples:
  ccorc rm old-project
  ccorc clean devops-team -f
```

#### `export` - Export context configuration
```bash
ccorc export <context-name> <output-file>

Examples:
  ccorc export devops-team team-backup.json
```

#### `import` - Import context configuration
```bash
ccorc import <input-file>

Examples:
  ccorc import team-backup.json
```

#### `teams` - Team configuration management
```bash
ccorc teams list                    # List available teams
ccorc teams show <team-name>        # Show team details

Examples:
  ccorc teams list
  ccorc teams show devops-team
```

## CCDK (Claude Code Docker Kit)

### Command Structure
```
ccdk [global-options] <command> [instance] [command-options]
```

### Global Options (before command)
- `-m, --model <model>` - Set Claude model (e.g., sonnet, opus)
- `-q, --quiet` - Quiet mode
- `-v, --verbose` - Verbose mode

### Commands

#### `run` - Run Claude Code in temporary container
```bash
ccdk run [instance] [options]

Options:
  -i, --isolated    Use isolated container mode
  -s, --shared      Use shared container mode
  -r, --random      Add random suffix to container name

Examples:
  ccdk run                    # Default instance
  ccdk run dev                # Named instance
  ccdk run -i                 # Isolated mode
  ccdk -m opus run prod -i    # With model override
  ccdk run test -s -r         # Shared mode with random suffix
```

#### `start` - Start a persistent container
```bash
ccdk start [instance] [options]

Options:
  -i, --isolated    Use isolated container mode
  -s, --shared      Use shared container mode
  -r, --random      Add random suffix to container name

Examples:
  ccdk start
  ccdk start frontend -i
  ccdk start backend -s -r
```

#### `stop` - Stop a running container
```bash
ccdk stop [instance]

Examples:
  ccdk stop
  ccdk stop frontend
```

#### `restart` - Restart a container
```bash
ccdk restart [instance]

Examples:
  ccdk restart
  ccdk restart backend
```

#### `sh` / `shell` - Open bash shell in container
```bash
ccdk sh [instance] [command]
ccdk shell [instance] [command]

Examples:
  ccdk sh                     # Shell into default instance
  ccdk sh frontend            # Shell into specific instance
  ccdk sh backend ls -la      # Run command in container
  ccdk shell dev python app.py
```

#### `rm` / `clean` - Remove container and volumes
```bash
ccdk rm [instance|pattern]
ccdk clean [instance|pattern]

Examples:
  ccdk rm                     # Remove default instance
  ccdk rm frontend            # Remove specific instance
  ccdk clean test-*           # Remove matching containers
```

#### `ps` / `list` - List all Claude Code containers
```bash
ccdk ps
ccdk list

Examples:
  ccdk ps
  ccdk list
```

#### `logs` - View container logs
```bash
ccdk logs [instance]

Examples:
  ccdk logs
  ccdk logs frontend
```

#### `status` - Show container status
```bash
ccdk status [instance]

Examples:
  ccdk status
  ccdk status backend
```

#### `build` - Build the Docker image
```bash
ccdk build

Note: Must be run from the orchestrator repository directory

Examples:
  ccdk build
```

#### `cc` - Run Claude Code in existing container
```bash
ccdk cc [instance] [claude-args]

Examples:
  ccdk cc                     # Run in default instance
  ccdk cc frontend            # Run in specific instance
  ccdk cc backend --help      # Pass args to Claude
```

## Common Usage Patterns

### Quick Team Launch
```bash
# Simple launch
ccorc launch devops-team

# With task and debug
ccorc launch devops-team -t "Build auth system" -d

# Fresh start with model override
ccorc launch security-team -m opus -F

# Full options (with auto-cleanup)
ccorc launch data-team analytics -m sonnet -f -d -t "Process Q4 data" --rm -F
```

### Container Management
```bash
# Quick development container
ccdk run dev -i

# Persistent containers for services
ccdk start api -s
ccdk start worker -s
ccdk start db -i

# Access containers
ccdk sh api
ccdk logs worker
ccdk ps
```

### Team Context Management
```bash
# View all contexts
ccorc ls

# Check specific context
ccorc info my-project
ccorc health my-project

# Cleanup
ccorc rm my-project -f
```

## Tips and Best Practices

1. **Use short forms for common operations**:
   - `ccorc ls` instead of `ccorc list`
   - `ccorc rm` instead of `ccorc clean`
   - `ccdk sh` instead of `ccdk shell`
   - `ccdk ps` instead of `ccdk list`

2. **Combine options efficiently**:
   - `ccorc launch team -d -F --rm` for debug fresh sessions with auto-cleanup
   - `ccdk run dev -i -r` for isolated container with random suffix

3. **Use positional arguments**:
   - Team name and context name don't need flags
   - Instance names for ccdk are positional

4. **Model selection**:
   - Use `-m` globally for ccdk: `ccdk -m opus run`
   - Use `-m` as option for ccorc: `ccorc launch team -m opus`

5. **Background operations**:
   - Use `claude-bg` for long-running teams
   - Example: `claude-bg start 'ccorc launch devops-team' team-bg`

## Docker Environment Configuration

### Custom Volume Mounts (.ccbox/mounts)

Configure additional volume mounts for your containers by creating a `.ccbox/mounts` file in your workspace:

```bash
# Format: MOUNT_<NAME>="/host/path:/container/path:options"
```

#### Mount Options
- `ro` - Read-only mount (recommended for data directories)
- `rw` - Read-write mount (default if no option specified)
- `cached` - Better performance for code directories on macOS

#### Setup
1. Create directory: `mkdir -p .ccbox`
2. Create mounts file: `touch .ccbox/mounts`
3. Add mount configurations (see examples below)

#### Example Configurations

**Development Environment**:
```bash
# Mount shared development tools
MOUNT_TOOLS="/opt/dev-tools:/opt/dev-tools:ro"
MOUNT_SCRIPTS="/home/user/scripts:/workspace/scripts:cached"
MOUNT_SHARED_LIBS="/opt/shared-libs:/opt/shared-libs:ro"
```

**Data Science Projects**:
```bash
# Mount large datasets (read-only)
MOUNT_DATASETS="/mnt/datasets:/data/datasets:ro"
MOUNT_MODELS="/mnt/models:/data/models:ro"

# Mount model outputs (read-write)
MOUNT_OUTPUTS="/mnt/outputs:/data/outputs:rw"

# Mount Jupyter notebooks
MOUNT_NOTEBOOKS="/home/user/notebooks:/workspace/notebooks:cached"
```

**Multi-Project Development**:
```bash
# Mount related projects
MOUNT_PROJECT_A="/home/user/project-a:/workspace/project-a:cached"
MOUNT_PROJECT_B="/home/user/project-b:/workspace/project-b:cached"
MOUNT_SHARED="/home/user/shared:/workspace/shared:cached"
```

**Build Caches**:
```bash
# Mount shared caches for faster builds
MOUNT_NPM_CACHE="/home/user/.npm:/home/user/.npm:cached"
MOUNT_PIP_CACHE="/home/user/.cache/pip:/home/user/.cache/pip:cached"
MOUNT_CARGO_CACHE="/home/user/.cargo:/home/user/.cargo:cached"
```

#### Important Notes
- **Security**: Never mount sensitive directories with write access
- **Git**: Add `.ccbox/` to `.gitignore`
- **Paths**: Use absolute paths only
- **Performance**: Use `:cached` for frequently accessed directories on macOS
- **Permissions**: Container runs as your host user

### Workspace Initialization (.ccbox/init.sh)

Customize the container environment with an initialization script:

```bash
#!/bin/bash
# Example .ccbox/init.sh

# Configure Poetry for Docker
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"

# Set project environment
export DATABASE_URL="sqlite:///dev.db"
export DEBUG=true

# Auto-activate virtual environment
if [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
    source "$(find .venv-docker -name activate | head -1)" 2>/dev/null
fi
```