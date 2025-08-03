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

Create a `.ccbox/mounts` file in your workspace to define custom mounts:

```bash
# .ccbox/mounts
MOUNT_DATA="/mnt/data:/mnt/data:ro"
MOUNT_CACHE="/home/user/.cache:/workspace/.cache:cached"
MOUNT_MODELS="/path/to/models:/models:ro"
```

#### .ccbox/mounts Configuration

The `.ccbox/mounts` file allows you to configure additional volume mounts for your containers. This file is automatically loaded when you start containers and supports the following format:

```bash
# Format: MOUNT_<NAME>="/host/path:/container/path:options"
```

**Mount Options**:
- `ro` - Read-only mount (recommended for data directories)
- `rw` - Read-write mount (default if no option specified)
- `cached` - Better performance for code directories on macOS

#### Setup Instructions

1. **Create the .ccbox directory**:
   ```bash
   mkdir -p .ccbox
   ```

2. **Copy the example file**:
   ```bash
   cp .ccbox/mounts.example .ccbox/mounts
   ```

3. **Edit the mounts file**:
   ```bash
   # Edit .ccbox/mounts to add your custom mounts
   nano .ccbox/mounts
   ```

4. **Example configurations**:
   ```bash
   # Mount data directories (read-only)
   MOUNT_DATA="/mnt/external/data:/mnt/data:ro"
   MOUNT_DATASETS="/home/user/datasets:/workspace/datasets:ro"
   
   # Mount code repositories (with caching for performance)
   MOUNT_PROJECTS="/home/user/projects:/workspace/projects:cached"
   MOUNT_LIBS="/home/user/libraries:/workspace/libs:ro"
   
   # Mount configuration files (read-only for security)
   MOUNT_CONFIG="/home/user/.myapp:/workspace/.myapp:ro"
   
   # Mount shared caches (for faster builds)
   MOUNT_NPM_CACHE="/home/user/.npm:/home/user/.npm:cached"
   MOUNT_PIP_CACHE="/home/user/.cache/pip:/home/user/.cache/pip:cached"
   MOUNT_CARGO_CACHE="/home/user/.cargo:/home/user/.cargo:cached"
   
   # Mount external drives or network shares
   MOUNT_EXTERNAL="/media/external:/mnt/external:ro"
   MOUNT_NFS="/mnt/nfs/share:/workspace/share:ro"
   
   # Mount specific tools or binaries
   MOUNT_TOOLS="/opt/custom-tools:/opt/custom-tools:ro"
   ```

#### Important Notes

- **Git Ignored**: Add `.ccbox/` to your `.gitignore` to avoid committing environment-specific configurations
- **Security**: Never mount sensitive directories with write access unless absolutely necessary
- **Performance**: Use `:cached` option for frequently accessed code directories on macOS
- **Paths**: Use absolute paths for both host and container paths
- **Conflicts**: Avoid mounting over existing system directories in the container
- **Permissions**: The container runs as your host user, so mounted files will have correct permissions

#### Common Use Cases

**Development Environment**:
```bash
# Mount shared development tools
MOUNT_TOOLS="/opt/dev-tools:/opt/dev-tools:ro"
MOUNT_SCRIPTS="/home/user/scripts:/workspace/scripts:cached"

# Mount shared libraries and dependencies
MOUNT_SHARED_LIBS="/opt/shared-libs:/opt/shared-libs:ro"
```

**Data Science Projects**:
```bash
# Mount large datasets (read-only)
MOUNT_DATASETS="/mnt/datasets:/data/datasets:ro"
MOUNT_MODELS="/mnt/models:/data/models:ro"

# Mount model outputs (read-write)
MOUNT_OUTPUTS="/mnt/outputs:/data/outputs:rw"

# Mount Jupyter notebooks (cached for performance)
MOUNT_NOTEBOOKS="/home/user/notebooks:/workspace/notebooks:cached"
```

**Multi-Project Development**:
```bash
# Mount related projects for cross-project development
MOUNT_PROJECT_A="/home/user/project-a:/workspace/project-a:cached"
MOUNT_PROJECT_B="/home/user/project-b:/workspace/project-b:cached"
MOUNT_SHARED="/home/user/shared:/workspace/shared:cached"
```

#### Troubleshooting Mounts

**Mount not appearing**:
```bash
# Check if the .ccbox/mounts file exists and has correct format
cat .ccbox/mounts

# Verify host path exists
ls -la /host/path/to/mount

# Check container mounts
ccdk shell mount | grep workspace
```

**Permission issues**:
```bash
# Check file ownership on host
ls -la /host/path/to/mount

# Check user ID in container matches host
ccdk shell id
```

**Performance issues**:
```bash
# For macOS, add :cached option for better performance
MOUNT_CODE="/home/user/code:/workspace/code:cached"

# For large datasets, consider read-only mounts
MOUNT_DATA="/mnt/data:/data:ro"
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
- Custom mounts from `.ccbox/mounts`

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
- [.ccbox/mounts.example](../.ccbox/mounts.example) - Example custom mounts configuration
