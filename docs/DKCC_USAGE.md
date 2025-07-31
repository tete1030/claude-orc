# dkcc - Docker Claude Code Manager

`dkcc` is a command-line tool for managing Claude Code Docker containers (CCBox - Claude Code Box).

## Installation

```bash
# From the orchestrator directory
./scripts/install-dkcc.sh
```

This installs `dkcc` to:
- `/usr/local/bin/dkcc` (if run as root)
- `~/.local/bin/dkcc` (if run as regular user)

Make sure `~/.local/bin` is in your PATH if installing as a regular user.

## Important: Building the Image

The `dkcc build` command must be run from the orchestrator repository directory where the Dockerfile exists. After installation, the build command will only work when executed from the source repository.

```bash
# From the orchestrator repository
./bin/dkcc build

# Or if installed globally, from the orchestrator directory
dkcc build
```

Once built, all other commands can be run from any directory.

## Basic Usage

### Building the Docker Image

```bash
# Build the CCBox image
dkcc build
```

### Running Containers

#### Temporary Container (Recommended for quick tasks)
```bash
# Run Claude Code in a temporary container
dkcc run

# Run with interactive shell instead of Claude
dkcc run-shell
```

#### Persistent Container (For long-running work)
```bash
# Start a persistent container
dkcc start

# Check container status
dkcc status

# Stop the container
dkcc stop

# Restart the container
dkcc restart

# Remove the container
dkcc rm
```

### Working with Running Containers

```bash
# View container logs
dkcc logs

# Run Claude Code in existing container
dkcc cc                  # Start Claude
dkcc cc --help          # Pass arguments to Claude

# Open bash shell in container
dkcc shell

# Execute other commands in container
dkcc shell ls -la        # Run commands via shell
dkcc shell python app.py # Run Python scripts
```

## Advanced Usage

### Command-Line Options

Use convenient options instead of environment variables:

```bash
# Set instance name
dkcc run -i dev
dkcc start -i frontend

# Set model
dkcc run -m claude-3-5-sonnet-20241022
dkcc run -m sonnet  # Pass model name directly

# Set container mode
dkcc run --isolated   # Isolated container mode
dkcc run --shared     # Shared container mode

# Combine options
dkcc run -i dev -m sonnet --isolated
```

### Multiple Instances

You can run multiple Claude Code containers:

```bash
# Using options
dkcc start -i dev
dkcc start -i test
dkcc start -i prod

# Work with specific instance
dkcc cc -i dev
dkcc logs -i test
dkcc stop -i prod

# Using environment variables (legacy)
CLAUDE_INSTANCE=dev dkcc start
CLAUDE_INSTANCE=test dkcc logs
```

### Custom Volume Mounts

Create a `.ccbox.env` file in your workspace to define custom mounts:

```bash
# .ccbox.env
MOUNT_DATA="/mnt/data:/mnt/data:ro"
MOUNT_CACHE="/home/user/.cache:/workspace/.cache:cached"
MOUNT_MODELS="/path/to/models:/models:ro"
```

### Environment Variables

- `CLAUDE_INSTANCE`: Container instance name (default: empty)
- `CONTAINER_NAME`: Override container name (default: ccbox or ccbox-{instance})
- `ANTHROPIC_API_KEY`: API key for Claude (passed to container)

## Container Features

### Pre-installed Tools
- **Claude Code**: Latest version via npm
- **Python 3.12.11**: With pyenv and Poetry
- **Node.js 20.x LTS**: For Claude Code and React
- **claude-bg**: Background process manager
- **GitHub CLI**: For repository operations
- **Docker CLI**: Docker-in-Docker support
- **SQLite3**: Database operations

### Volume Mounts
- Your workspace directory (preserved path)
- Home directory (all configurations)
- Docker socket (for Docker operations)
- Shared orchestrator directory (`/tmp/claude-orc`)
- Custom mounts from `.ccbox.env`

## Troubleshooting

### Build command not found
If you get "Dockerfile not found" error when running `dkcc build`:
- The build command must be run from the orchestrator repository directory
- Ensure you're in the directory containing `docker/claude-code/Dockerfile`
- After installation, `dkcc` cannot build from other directories

### Container won't start
```bash
# Check if container already exists
dkcc status

# Check if image exists
docker images | grep ccbox

# If image missing, build from orchestrator repo
cd /path/to/orchestrator
dkcc build

# Then start from anywhere
dkcc start
```

### Permission issues
```bash
# Container runs as your user ID/GID
# Check current user
dkcc exec whoami
dkcc exec id
```

### Can't find dkcc after installation
```bash
# Check installation location
which dkcc

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

### Docker socket errors
```bash
# Ensure Docker daemon is running
sudo systemctl status docker

# Check Docker permissions
docker ps  # Should work without sudo
```

## Command Reference

| Command | Description |
|---------|-------------|
| `dkcc build` | Build the Docker image |
| `dkcc run` | Run Claude in temporary container |
| `dkcc run-shell` | Run shell in temporary container |
| `dkcc start` | Start persistent container |
| `dkcc stop` | Stop running container |
| `dkcc restart` | Restart container |
| `dkcc clean` | Remove container and volumes |
| `dkcc status` | Show container status |
| `dkcc logs` | View container logs |
| `dkcc cc [args]` | Run Claude Code in container |
| `dkcc shell [cmd]` | Open shell or execute command |
| `dkcc list` | List all Claude Code containers |
| `dkcc --help` | Show help message |

### Options

| Option | Description |
|--------|-------------|
| `-i, --instance <name>` | Set instance name |
| `-m, --model <model>` | Set Claude model |
| `--isolated` | Use isolated container mode |
| `--shared` | Use shared container mode |
| `--random` | Add random suffix to container |

## See Also

- [Docker Environment README](../docker/claude-code/README.md) - Detailed Docker setup documentation
- [CCBox Dockerfile](../docker/claude-code/Dockerfile) - Container configuration
- [.ccbox.env.example](../.ccbox.env.example) - Example custom mounts configuration
