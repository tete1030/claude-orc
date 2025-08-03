#!/bin/bash
set -e

# Prevent locale warnings by using C.UTF-8 as fallback if requested locale isn't available
# Check if the requested locale exists, otherwise use C.UTF-8
if [ -n "$LC_ALL" ]; then
    # Check if the locale is available (handle both en_US.UTF-8 and en_US.utf8 formats)
    LOCALE_CHECK=$(echo "$LC_ALL" | sed 's/UTF-8/utf8/g' | tr '[:upper:]' '[:lower:]')
    if ! locale -a 2>/dev/null | grep -qi "^${LOCALE_CHECK}$"; then
        # Locale not available, use C.UTF-8 as fallback
        export LC_ALL="C.UTF-8"
    fi
fi

# Do the same for LANG
if [ -n "$LANG" ]; then
    LOCALE_CHECK=$(echo "$LANG" | sed 's/UTF-8/utf8/g' | tr '[:upper:]' '[:lower:]')
    if ! locale -a 2>/dev/null | grep -qi "^${LOCALE_CHECK}$"; then
        export LANG="C.UTF-8"
    fi
fi

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

# Create or update .bashrc with useful defaults
if [ ! -f $USER_HOME/.bashrc ]; then
    cat > $USER_HOME/.bashrc << 'EOF'
# Source global bashrc if it exists
if [ -f /etc/bash.bashrc ]; then
    . /etc/bash.bashrc
fi

# Enable color support
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
fi

# Set prompt
PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
EOF
    chown $USER_ID:$GROUP_ID $USER_HOME/.bashrc
fi

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

# Check if .claude-host is actually mounted
CLAUDE_HOST_MOUNTED=false
if mountpoint -q "$USER_HOME/.claude-host" 2>/dev/null; then
    CLAUDE_HOST_MOUNTED=true
fi

if [ "$CLAUDE_HOST_MOUNTED" = "true" ]; then
    echo "Claude host directory is mounted from host system"
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
        # Isolated mode: Copy and filter configuration
        
        # SAFETY CHECK: Ensure .claude is not already a symlink/mount from shared mode
        if [ -L "$USER_HOME/.claude" ] || mountpoint -q "$USER_HOME/.claude" 2>/dev/null; then
            echo "ERROR: .claude is a symlink or mountpoint in isolated mode - this is unsafe!"
            echo "Please remove the symlink/mount before running in isolated mode"
            exit 1
        fi
        
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
else
    echo "Warning: Claude host directory not mounted - running without host configuration"
    # Create a basic .claude directory structure
    mkdir -p "$USER_HOME/.claude/projects"
    chown -R "$USER_ID:$GROUP_ID" "$USER_HOME/.claude"
fi

# Start session monitor daemon (isolated mode only and when host is mounted)
if [ "$CLAUDE_CONTAINER_MODE" = "isolated" ] && [ "$CLAUDE_HOST_MOUNTED" = "true" ]; then
    echo "Starting session monitor daemon for isolated mode..."
    # Start the daemon in background as the user
    su -c "nohup /usr/local/bin/session-monitor-daemon.sh '$USER_NAME' '$USER_HOME' > /tmp/session_monitor_startup.log 2>&1 &" "$USER_NAME"
    
    # Ensure the host projects directory exists
    mkdir -p "$USER_HOME/.claude-host/.claude/projects"
elif [ "$CLAUDE_CONTAINER_MODE" = "isolated" ] && [ "$CLAUDE_HOST_MOUNTED" = "false" ]; then
    echo "Warning: Isolated mode requested but host directory not mounted - session monitoring disabled"
fi

# Ensure run-command.sh can access workspace path
export WORKSPACE_PATH

# Execute the command as the user with the wrapper
# Use username instead of UID:GID so gosu picks up all supplementary groups
exec gosu $USER_NAME /usr/local/bin/run-command.sh "$@"