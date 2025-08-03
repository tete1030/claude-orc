# ccdk - Docker Claude Code Manager

`ccdk` is a command-line tool for managing Claude Code Docker containers (CCBox - Claude Code Box).

## Installation

```bash
# From the orchestrator directory
./scripts/install-ccdk.sh
```

This installs `ccdk` to:
- `/usr/local/bin/ccdk` (if run as root)
- `~/.local/bin/ccdk` (if run as regular user)

Make sure `~/.local/bin` is in your PATH if installing as a regular user.

## Important: Building the Image

The `ccdk build` command must be run from the orchestrator repository directory where the Dockerfile exists. After installation, the build command will only work when executed from the source repository.

```bash
# From the orchestrator repository
./bin/ccdk build

# Or if installed globally, from the orchestrator directory
ccdk build
```

Once built, all other commands can be run from any directory.

## Basic Usage

### Building the Docker Image

```bash
# Build the CCBox image
ccdk build
```

### Running Containers

#### Temporary Container (Recommended for quick tasks)
```bash
# Run Claude Code in a temporary container
ccdk run

# Run with interactive shell instead of Claude
ccdk run-shell
```

#### Persistent Container (For long-running work)
```bash
# Start a persistent container
ccdk start

# Check container status
ccdk status

# Stop the container
ccdk stop

# Restart the container
ccdk restart

# Remove the container
ccdk rm
```

### Working with Running Containers

```bash
# View container logs
ccdk logs

# Run Claude Code in existing container
ccdk cc                  # Start Claude
ccdk cc --help          # Pass arguments to Claude

# Open bash shell in container
ccdk shell

# Execute other commands in container
ccdk shell ls -la        # Run commands via shell
ccdk shell python app.py # Run Python scripts
```

## Advanced Usage

### Command-Line Options

Use convenient options instead of environment variables:

```bash
# Set instance name
ccdk run -i dev
ccdk start -i frontend

# Set model
ccdk run -m sonnet
ccdk run -m opus  # Pass model name directly

# Set container mode
ccdk run --isolated   # Isolated container mode
ccdk run --shared     # Shared container mode

# Combine options
ccdk run -i dev -m sonnet --isolated
```

### Multiple Instances

You can run multiple Claude Code containers:

```bash
# Using options
ccdk start -i dev
ccdk start -i test
ccdk start -i prod

# Work with specific instance
ccdk cc -i dev
ccdk logs -i test
ccdk stop -i prod

# Using environment variables (legacy)
CLAUDE_INSTANCE=dev ccdk start
CLAUDE_INSTANCE=test ccdk logs
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
If you get "Dockerfile not found" error when running `ccdk build`:
- The build command must be run from the orchestrator repository directory
- Ensure you're in the directory containing `docker/claude-code/Dockerfile`
- After installation, `ccdk` cannot build from other directories

### Container won't start
```bash
# Check if container already exists
ccdk status

# Check if image exists
docker images | grep ccbox

# If image missing, build from orchestrator repo
cd /path/to/orchestrator
ccdk build

# Then start from anywhere
ccdk start
```

### Permission issues
```bash
# Container runs as your user ID/GID
# Check current user
ccdk exec whoami
ccdk exec id
```

### Can't find ccdk after installation
```bash
# Check installation location
which ccdk

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
| `ccdk build` | Build the Docker image |
| `ccdk run` | Run Claude in temporary container |
| `ccdk run-shell` | Run shell in temporary container |
| `ccdk start` | Start persistent container |
| `ccdk stop` | Stop running container |
| `ccdk restart` | Restart container |
| `ccdk clean` | Remove container and volumes |
| `ccdk status` | Show container status |
| `ccdk logs` | View container logs |
| `ccdk cc [args]` | Run Claude Code in container |
| `ccdk shell [cmd]` | Open shell or execute command |
| `ccdk list` | List all Claude Code containers |
| `ccdk --help` | Show help message |

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
