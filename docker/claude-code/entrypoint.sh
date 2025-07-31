#!/bin/bash
set -e

# Get the UID and GID from environment variables (passed from docker-compose/run)
USER_ID=${LOCAL_USER_ID:-1000}
GROUP_ID=${LOCAL_GROUP_ID:-1000}
USER_NAME=${LOCAL_USER_NAME:-developer}
USER_HOME=${LOCAL_USER_HOME:-/home/developer}

# Create group if it doesn't exist (check by GID not name)
if ! getent group $GROUP_ID > /dev/null 2>&1; then
    groupadd -g $GROUP_ID ${USER_NAME}group
fi

# Get the group name for the GID
GROUP_NAME=$(getent group $GROUP_ID | cut -d: -f1)

# Check if user exists with the given UID
if ! id -u $USER_ID > /dev/null 2>&1; then
    # User doesn't exist, create it
    # Use -M to not create home directory if it already exists (from mount)
    if [ -d "$USER_HOME" ]; then
        # Home directory already exists (from mount), don't create it
        useradd -M -s /bin/bash -u $USER_ID -g $GROUP_NAME -d $USER_HOME $USER_NAME 2>/dev/null || true
    else
        # Home directory doesn't exist, create it
        useradd -m -s /bin/bash -u $USER_ID -g $GROUP_NAME -d $USER_HOME $USER_NAME
    fi
    echo "$USER_NAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
else
    # User exists but might need updates
    EXISTING_USER=$(id -nu $USER_ID)
    if [ "$EXISTING_USER" != "$USER_NAME" ]; then
        # Different username for this UID, use the existing one
        USER_NAME=$EXISTING_USER
        USER_HOME=$(getent passwd $USER_NAME | cut -d: -f6)
    fi
fi

# Ensure home directory exists and has correct permissions
mkdir -p $USER_HOME
chown $USER_ID:$GROUP_ID $USER_HOME

# Add user to docker group if docker socket is mounted
if [ -S /var/run/docker.sock ]; then
    # Get docker group GID from the socket
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
    
    # Check if we're running as root (needed for usermod)
    if [ "$(id -u)" -eq 0 ]; then
        # Check if docker group exists
        if ! grep -q "^docker:" /etc/group; then
            # Create docker group with the correct GID
            groupadd -g $DOCKER_GID docker
            usermod -aG docker $USER_NAME
        else
            # Ensure docker group has the correct GID
            EXISTING_DOCKER_GID=$(grep "^docker:" /etc/group | cut -d: -f3)
            if [ "$EXISTING_DOCKER_GID" != "$DOCKER_GID" ]; then
                # Docker group exists but with wrong GID, create a new group
                groupadd -g $DOCKER_GID dockerhost
                usermod -aG dockerhost $USER_NAME
            else
                usermod -aG docker $USER_NAME
            fi
        fi
    fi
fi

# Fix ownership of .cache directory and subdirectories
# This is needed because Docker volume mounts create directories as root
if [ -d "$USER_HOME/.cache" ]; then
    # Change ownership of .cache and all subdirectories
    chown "$USER_ID:$GROUP_ID" "$USER_HOME/.cache"
    
    [ ! -d "$USER_HOME/.cache/ms-playwright" ] || chown "$USER_ID:$GROUP_ID" "$USER_HOME/.cache/ms-playwright"
fi

# Ensure /tmp/claude-orc has write permissions for all
if [ -d "/tmp/claude-orc" ]; then
    chmod 777 /tmp/claude-orc
else
    mkdir -p /tmp/claude-orc
    chmod 777 /tmp/claude-orc
fi

if [ -d "$USER_HOME/.config" ]; then
    # Change ownership of .config and all subdirectories
    chown "$USER_ID:$GROUP_ID" "$USER_HOME/.config"
fi

# Setup Claude configuration
# The host's ~/.claude and ~/.claude.json are mounted to ~/.claude-host/
# CLAUDE_CONTAINER_MODE can be "shared" (default) or "isolated"
CLAUDE_CONTAINER_MODE=${CLAUDE_CONTAINER_MODE:-shared}

if [ -d "$USER_HOME/.claude-host" ]; then
    if [ "$CLAUDE_CONTAINER_MODE" = "shared" ]; then
        # Shared mode: Just symlink everything without modification
        if [ -d "$USER_HOME/.claude-host/.claude" ]; then
            ln -sf "$USER_HOME/.claude-host/.claude" "$USER_HOME/.claude"
            chown -h "$USER_ID:$GROUP_ID" "$USER_HOME/.claude"
        fi
        
        if [ -f "$USER_HOME/.claude-host/.claude.json" ]; then
            ln -sf "$USER_HOME/.claude-host/.claude.json" "$USER_HOME/.claude.json"
            chown -h "$USER_ID:$GROUP_ID" "$USER_HOME/.claude.json"
        fi
    else
        # Isolated mode (default): Copy and filter configuration
        # Create .claude directory if it doesn't exist
        mkdir -p "$USER_HOME/.claude"
        chown "$USER_ID:$GROUP_ID" "$USER_HOME/.claude"
        
        # Copy and process claude.json if it exists
        if [ -f "$USER_HOME/.claude-host/.claude.json" ]; then
            # First copy the file
            cp "$USER_HOME/.claude-host/.claude.json" "$USER_HOME/.claude.json"
            
            # Process with jq to keep only the current workspace project
            if command -v jq &> /dev/null && [ -n "$WORKSPACE_PATH" ]; then
                # Create a filtered version that:
                # 1. Keeps only the current workspace project and its sub-projects
                # 2. Removes history from all kept projects
                jq --arg workspace "$WORKSPACE_PATH" '
                    # Keep workspace project and its sub-projects, remove history from all
                    .projects |= (
                        to_entries |
                        map(
                            if .key == $workspace or (.key | startswith($workspace + "/"))
                            then .value.history = [] | .
                            else empty
                            end
                        ) |
                        from_entries
                    )
                ' "$USER_HOME/.claude.json" > "$USER_HOME/.claude.json.tmp" && \
                mv "$USER_HOME/.claude.json.tmp" "$USER_HOME/.claude.json"
            fi
            
            chown "$USER_ID:$GROUP_ID" "$USER_HOME/.claude.json"
        fi
        
        # Copy or symlink configuration files from .claude-host/.claude to .claude
        if [ -d "$USER_HOME/.claude-host/.claude" ]; then
            # Symlink credentials.json if it exists (shared across all containers)
            if [ -f "$USER_HOME/.claude-host/.claude/.credentials.json" ]; then
                ln -sf "$USER_HOME/.claude-host/.claude/.credentials.json" "$USER_HOME/.claude/.credentials.json"
                chown -h "$USER_ID:$GROUP_ID" "$USER_HOME/.claude/.credentials.json"
            fi
            
            # Copy settings.json if it exists (isolated per container)
            if [ -f "$USER_HOME/.claude-host/.claude/settings.json" ]; then
                cp "$USER_HOME/.claude-host/.claude/settings.json" "$USER_HOME/.claude/settings.json"
                chown "$USER_ID:$GROUP_ID" "$USER_HOME/.claude/settings.json"
            fi
            
            # Create symlinks for specific directories
            for dir in ide local statsig; do
                if [ -d "$USER_HOME/.claude-host/.claude/$dir" ]; then
                    ln -sf "$USER_HOME/.claude-host/.claude/$dir" "$USER_HOME/.claude/$dir"
                    chown -h "$USER_ID:$GROUP_ID" "$USER_HOME/.claude/$dir"
                fi
            done
        fi
    fi
fi

# Create a wrapper script that initializes pyenv and sources venv if available
cat > /tmp/run_command.sh << 'EOF'
#!/bin/bash
# Initialize pyenv
export PYENV_ROOT="/opt/pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - --no-rehash)"

# Initialize Poetry
export POETRY_HOME="/opt/poetry"
export PATH="$POETRY_HOME/bin:$PATH"

# Prioritize local Claude Code installation (auto-updating version)
if [ -d "${HOME}/.claude/local" ]; then
    export PATH="${HOME}/.claude/local:$PATH"
fi

# Ensure WORKSPACE_PATH is set
if [ -z "${WORKSPACE_PATH}" ]; then
    export WORKSPACE_PATH="/workspace"
fi

# Configure Poetry for Docker environment
cd "${WORKSPACE_PATH}" 2>/dev/null || true

# Simple solution: Create a docker-specific venv directory using Poetry env command
export POETRY_VIRTUALENVS_IN_PROJECT=false
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"

# Configure Poetry
if command -v poetry &> /dev/null; then
    poetry config virtualenvs.in-project false
    poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker"
    
    # Ensure Python 3.12 is used
    poetry env use python3.12 2>/dev/null || true
fi

# Check if a venv exists in .venv-docker
if [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
    # Find the actual venv (it will be named like project-xxx-py3.12)
    DOCKER_VENV=$(find "${WORKSPACE_PATH}/.venv-docker" -maxdepth 1 -type d -name "*-py3.12" | head -1)
    if [ -n "$DOCKER_VENV" ] && [ -d "$DOCKER_VENV" ]; then
        export VIRTUAL_ENV="$DOCKER_VENV"
        export PATH="$VIRTUAL_ENV/bin:$PATH"
        source "$VIRTUAL_ENV/bin/activate" 2>/dev/null || true
    else
        echo "Docker venv directory exists but no valid environment found."
        echo "Run 'poetry install --no-root' to create it."
    fi
else
    echo "Docker venv not found. Run 'poetry install --no-root' to create it."
    echo "Poetry will create environment in: ${WORKSPACE_PATH}/.venv-docker/"
fi

# Execute the command
exec "$@"
EOF

chmod +x /tmp/run_command.sh

# Execute the command as the user with the wrapper
# Use username instead of UID:GID so gosu picks up all supplementary groups
exec gosu $USER_NAME /tmp/run_command.sh "$@"