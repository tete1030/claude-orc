# Claude Code Docker Environment Setup

This Docker environment (CCBox - Claude Code Box) provides a complete development environment for running Claude Code with all necessary dependencies.

**Note**: The `ccdk` tool no longer uses docker-compose. All container management is done with pure Docker commands.

## Features

- **Claude Code**: Pre-installed globally via npm
- **Python 3.12.11**: With virtual environment support via pyenv and Poetry
- **Node.js 20.x LTS**: For Claude Code and React development
- **Project Dependencies**: All necessary system libraries for development
- **Dynamic User Mapping**: Container uses your host user ID/GID for perfect permission compatibility
- **Home Directory Preservation**: Your entire home directory is mounted, preserving all configurations
- **Development Tools**: git, vim, nano, build tools, sqlite3, GitHub CLI, Docker CLI, etc.
- **Docker Access**: Full Docker access from within the container via socket mounting
- **GitHub CLI**: Pre-installed for repository operations and GitHub integration
- **claude-bg**: Background process manager pre-installed for managing long-running tasks
- **ccdk**: Docker container manager pre-installed for Docker-in-Docker operations

## Quick Start

### Option 1: Temporary Container (Recommended for Quick Tasks)
```bash
# Run Claude Code directly in temporary container (with venv auto-sourced)
ccdk run
# This creates a temporary container that runs: claude --dangerously-skip-permissions

# Or run interactive bash shell
ccdk run-bash

# Or use Docker directly
docker run --rm -it \
    -e LOCAL_USER_ID=$(id -u) \
    -e LOCAL_GROUP_ID=$(id -g) \
    -e LOCAL_USER_NAME=$USER \
    -e LOCAL_USER_HOME=$HOME \
    -v "$PWD:$PWD:cached" \
    -w "$PWD" \
    ccbox:latest
# The container will keep running in the background
```

### Option 2: Persistent Container
```bash
# Build the Docker image (only needed once)
ccdk build

# Start a persistent container
ccdk start

# Access the container with shell
ccdk shell

# Or run Claude directly (default for exec)
ccdk exec
```

### Option 3: Multiple Named Instances
```bash
# Run multiple instances for different projects
CLAUDE_INSTANCE=project1 ccdk start
CLAUDE_INSTANCE=project2 ccdk start

# Access specific instance
CLAUDE_INSTANCE=project1 ccdk shell

# List all instances
ccdk list
```

### Option 4: Containers with Random Suffix
```bash
# Create container with random 8-character suffix
ccdk --random start
# Creates: ccbox-a1b2c3d4

# Named instance with random suffix
CLAUDE_INSTANCE=dev ccdk --random start
# Creates: ccbox-dev-x9y8z7w6

# Always use random suffix via environment variable
export CLAUDE_INSTANCE_RANDOM=true
ccdk start
# Creates: ccbox-m3n4o5p6

# Use with specific instance name
CLAUDE_INSTANCE=test CLAUDE_INSTANCE_RANDOM=true ccdk start
# Creates: ccbox-test-q1r2s3t4
```

## Key Features

- **Auto-build**: The image is automatically built on first use if it doesn't exist
- **Multiple instances**: Run multiple Claude Code containers simultaneously using `CLAUDE_INSTANCE`
- **Random suffix support**: Generate unique container names with `--random` flag or `CLAUDE_INSTANCE_RANDOM=true`
- **Temporary containers**: Use `run` command for one-off tasks (auto-cleanup)
- **Persistent containers**: Use `start/stop` for long-running work
- **Auto-start Claude Code**: When no command is specified, automatically runs `claude --dangerously-skip-permissions`
- **Auto-source venv**: Automatically sources Python virtual environment if it exists

## Volume Mounts

### Default Mounts
The following directories are mounted by default:

- **Project directory**: Mounted at the same path as on your host
- `~/.claude`: Your Claude configuration
- `~/.gitconfig` and `~/.ssh`: Git configuration (read-only)
- `/tmp/claude-orc`: Shared orchestrator directory
- `~/.cache/ms-playwright`: Playwright browser cache

### Custom Mounts via .ccbox.env
You can add custom volume mounts by creating a `.ccbox.env` file in your workspace:

```bash
# Copy the example file
cp .ccbox.env.example .ccbox.env

# Edit to add your mounts
# Format: MOUNT_<NAME>="/host/path:/container/path:options"
```

Example `.ccbox.env`:
```bash
# Mount data directories
MOUNT_DATA="/mnt/data:/mnt/data:ro"
MOUNT_DATASETS="/home/user/datasets:/workspace/datasets:ro"

# Mount code repositories
MOUNT_PROJECTS="/home/user/projects:/workspace/projects:cached"

# Mount shared caches
MOUNT_NPM_CACHE="/home/user/.npm:/home/user/.npm:cached"
```

**Important**: 
- The container dynamically adjusts to use your host user ID, group ID, and home directory structure
- Your workspace is mounted at the exact same path inside the container as on your host
- File permissions are preserved perfectly since the container runs as your user
- Only necessary config files are mounted (not your entire home directory)
- Custom mounts are loaded from `.ccbox.env` (git-ignored by default)

## Environment Variables

### Project Environment
- `PYTHONPATH`: Set to your project directory path
- `VIRTUAL_ENV`: Set dynamically by entrypoint based on Poetry environment
- `TZ`: Set to UTC
- `NODE_ENV`: Set to development

### Claude Code Environment Variables
All Claude Code environment variables from your host are automatically passed through to the container, including:

- **API Settings**: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, etc.
- **Behavior Settings**: `BASH_DEFAULT_TIMEOUT_MS`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, etc.
- **Feature Toggles**: `DISABLE_TELEMETRY`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, etc.
- **Proxy Settings**: `HTTP_PROXY`, `HTTPS_PROXY`
- **Model Settings**: `MAX_THINKING_TOKENS`, `MCP_TIMEOUT`, etc.
- **Vertex/Bedrock Settings**: Region configurations and authentication settings

To set any Claude Code environment variable, export it before running the container:
```bash
export ANTHROPIC_API_KEY=your-key-here
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192
export DISABLE_TELEMETRY=true
ccdk run
```

For persistent settings, add them to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.)

## Usage Examples

### Running Python Scripts
```bash
# Inside container - paths are the same as on host
python your_script.py
```

### Running Scripts
```bash
# Inside container
python scripts/your_script.py
```

### Installing Python Dependencies
```bash
# Inside container - Poetry will use .venv-docker automatically
poetry install  # Creates/updates .venv-docker in project folder

# The environment is auto-activated, just run:
python your_main.py

# Or explicitly with Poetry:
poetry run python your_main.py
```

**Note**: Docker uses `.venv-docker/` to keep Linux binaries separate from your host's `.venv/`. This prevents architecture conflicts.

### Running React Development Server
```bash
# Inside container
cd visualization-react
npm install  # First time only
npm run dev
```

## Management Commands

### Check Container Status
```bash
ccdk status
```

### View Logs
```bash
ccdk logs
```

### Execute Command Without Shell
```bash
# Run Claude Code (default when no command specified)
ccdk exec

# Or run specific commands
ccdk exec python --version
ccdk exec npm --version
```

### Restart Container
```bash
ccdk restart
```

### Stop Container
```bash
ccdk stop
```

### Clean Up (WARNING: Removes volumes)
```bash
ccdk clean
```

## Troubleshooting

### Permission Issues
The container runs as your host user with sudo access. Permission issues are rare since the container uses your host user ID.

### Port Access
The container uses host networking mode, so all ports are accessible directly.

### Virtual Environment
The Python virtual environment is automatically activated by the entrypoint script. If you need to check which environment is active:
```bash
# Inside container
poetry env info
```

### Node Modules
If you need to rebuild node_modules:
```bash
# Inside container
cd visualization-react
rm -rf node_modules
npm install
```

## Advanced Configuration

### Adding API Keys
To add your Anthropic API key:
```bash
# Export before running container
export ANTHROPIC_API_KEY=your-key-here
ccdk run

# Or add to your shell profile for persistence
echo "export ANTHROPIC_API_KEY=your-key-here" >> ~/.bashrc
```

### Working with Custom Mounts
Custom mounts defined in `.ccbox.env` are automatically loaded when you run the container. The mounts support various options:

- `:ro` - Read-only access (recommended for data directories)
- `:rw` - Read-write access (default)
- `:cached` - Better performance on macOS for code directories

Example usage with custom mounts:
```bash
# Create your .ccbox.env file
cat > .ccbox.env << EOF
MOUNT_DATA="/mnt/external/data:/mnt/data:ro"
MOUNT_CACHE="/home/$USER/.mycache:/workspace/.cache:cached"
EOF

# Run container - mounts are automatically applied
ccdk run

# Inside container, access your mounted data
ls /mnt/data/
ls /workspace/.cache/
```

### Resource Limits
By default, containers have no explicit resource limits. To add limits, use Docker flags when running:
```bash
# With resource limits
docker run -d --name ccbox \
    --memory="8g" --memory-reservation="4g" \
    --cpus="4" --cpu-shares="512" \
    # ... other options
```

## New Tools Available

### claude-bg (Background Process Manager)
claude-bg is pre-installed for managing long-running processes:
```bash
# Inside container
claude-bg start 'python long_script.py' my-job
claude-bg list
claude-bg status my-job_20250731_120000
claude-bg logs my-job_20250731_120000
claude-bg stop my-job_20250731_120000
```

### ccdk (Docker Claude Code Manager)
ccdk is pre-installed for managing nested Docker containers:
```bash
# Inside container (Docker-in-Docker)
ccdk build        # Build another CCBox image
ccdk run          # Run nested container
ccdk start        # Start nested persistent container
ccdk exec bash    # Execute in nested container
```

Note: Use with caution when nesting containers.

### SQLite3
SQLite3 is now available in the container for database operations:
```bash
# Inside container
sqlite3 mydatabase.db
sqlite3 :memory:  # In-memory database
```

### GitHub CLI
GitHub CLI (`gh`) is pre-installed for repository operations:
```bash
# Inside container
gh auth login        # Authenticate with GitHub
gh repo create       # Create a new repository
gh pr create        # Create a pull request
gh issue list       # List issues
```

### Docker Access
Docker is now accessible from within the container:
```bash
# Inside container
docker ps           # List running containers
docker build .      # Build images
docker run image    # Run containers
docker-compose up   # Run compose stacks
```

Note: The user is automatically added to the docker group for seamless Docker access.

## Security Notes

- The container has sudo access for development convenience
- Git configuration and SSH keys are mounted read-only
- Docker socket is now mounted by default for Docker operations (be cautious with container operations)
- The container user is automatically added to the docker group for Docker access
- Always use proper API key management (environment variables or secrets)