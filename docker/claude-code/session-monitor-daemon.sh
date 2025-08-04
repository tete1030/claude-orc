#!/bin/bash
# Session Monitor Daemon for Claude Code Orchestrator
# Monitors and symlinks session directories to host for cost tracking

MONITOR_USER="$1"
MONITOR_HOME="$2"
CLAUDE_INSTANCE="${CLAUDE_INSTANCE:-unknown}"
LOG_FILE="/tmp/session_monitor.log"
PID_FILE="/tmp/session_monitor.pid"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if daemon already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log "Daemon already running with PID $OLD_PID, exiting"
        exit 0
    else
        log "Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Write our PID
echo $$ > "$PID_FILE"
log "Session monitor daemon starting (PID $$) for user $MONITOR_USER in container $CLAUDE_INSTANCE"

# Cleanup on exit
cleanup() {
    log "Daemon shutting down"
    rm -f "$PID_FILE"
    exit 0
}
trap cleanup EXIT SIGTERM SIGINT

# Ensure base directories exist
CLAUDE_PROJECTS="$MONITOR_HOME/.claude/projects"
HOST_PROJECTS="$MONITOR_HOME/.claude-host/.claude/projects"

# CRITICAL SAFETY CHECKS - Prevent operating on mounted/linked directories
# Check if .claude is a symlink or mountpoint
if [ -L "$MONITOR_HOME/.claude" ]; then
    log "ERROR: .claude is a symlink - refusing to operate for safety"
    exit 1
fi

if mountpoint -q "$MONITOR_HOME/.claude" 2>/dev/null; then
    log "ERROR: .claude is a mountpoint - refusing to operate for safety"
    exit 1
fi

# Check if .claude/projects is a symlink or mountpoint
if [ -L "$CLAUDE_PROJECTS" ]; then
    log "ERROR: .claude/projects is a symlink - refusing to operate for safety"
    exit 1
fi

if mountpoint -q "$CLAUDE_PROJECTS" 2>/dev/null; then
    log "ERROR: .claude/projects is a mountpoint - refusing to operate for safety"
    exit 1
fi

# Create claude projects directory if it doesn't exist
if [ ! -d "$CLAUDE_PROJECTS" ]; then
    mkdir -p "$CLAUDE_PROJECTS"
    # Get the user's primary group
    USER_GROUP=$(id -gn "$MONITOR_USER" 2>/dev/null || echo "$MONITOR_USER")
    chown "$MONITOR_USER:$USER_GROUP" "$CLAUDE_PROJECTS"
    log "Created $CLAUDE_PROJECTS"
fi

# Initial scan - handle any existing directories
process_directory() {
    local dir="$1"
    local dir_name=$(basename "$dir")
    local host_dir="$HOST_PROJECTS/ccbox-${CLAUDE_INSTANCE}-${dir_name}"

    if [ -e "$host_dir" ] && { [ ! -d "$host_dir" ] || [ -L "$host_dir" ]; }; then
        log "ERROR: $host_dir not a directory"
        return
    fi

    # Create host directory
    mkdir -p "$host_dir"
    
    # Move existing content to host
    if [ "$(ls -A "$dir" 2>/dev/null)" ]; then
        mv "$dir"/* "$host_dir"/ 2>/dev/null || true
        log "Moved existing content to $host_dir"
    fi
    
    # Remove original directory and create symlink
    rmdir "$dir" 2>/dev/null || true
    ln -sf "$host_dir" "$dir"
    log "Created symlink: $dir -> $host_dir"
}

process_host_directory() {
    local hostdir="$1"
    local hostdir_name=$(basename "$hostdir")
    local dir_name="${hostdir_name#ccbox-"${CLAUDE_INSTANCE}"-}"
    local dir="$CLAUDE_PROJECTS/$dir_name"

    if [ -L "$dir" ]; then
        # Symlink already created by previous step
        return
    fi

    if [ -d "$dir" ]; then
        log "ERROR: $dir should not be a directory"
        return
    fi

    if [ -e "$dir" ]; then
        log "ERROR: $dir already exists in container"
        return
    fi

    ln -s "$hostdir" "$dir"
    log "Created symlink: $dir -> $hostdir"
}

# Initial scan
for dir in "$CLAUDE_PROJECTS"/*; do
    if [ -d "$dir" ] && [ ! -L "$dir" ]; then
        log "Processing container project: $dir"
        process_directory "$dir"
    fi
done

for hostdir in "$HOST_PROJECTS"/ccbox-${CLAUDE_INSTANCE}-*; do
    if [ -d "$hostdir" ] && [ ! -L "$hostdir" ]; then
        log "Processing host project of this container: $hostdir"
        process_host_directory "$hostdir"
    fi
done

# Monitor for new directories using inotify
log "Starting inotifywait monitoring"

# Monitor for directory creation events
inotifywait -m -e create --format '%w%f' "$CLAUDE_PROJECTS" 2>/dev/null | while read new_path; do
    if [ -d "$new_path" ] && [ ! -L "$new_path" ]; then
        # Wait a moment for directory to stabilize
        sleep 0.1
        process_directory "$new_path"
    fi
done