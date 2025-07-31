#!/bin/bash

# Simple Background Process Manager
# Usage: ./scripts/bg.sh <command> [name]
# Commands: start, stop, status, logs, list, kill-all

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Use system temp directory with unique identifier (hostname or container ID)
# This provides isolation between containers and different machines
INSTANCE_ID="${HOSTNAME:-$(uname -n)}"
PID_DIR="${TMPDIR:-/tmp}/bg-tasks-${INSTANCE_ID}"
LOG_DIR="${TMPDIR:-/tmp}/bg-logs-${INSTANCE_ID}"

# Create directories if they don't exist
mkdir -p "$PID_DIR" "$LOG_DIR"

# Centralized cleanup function
cleanup_old_files() {
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            name=$(basename "$pid_file" .pid)
            log_file="$LOG_DIR/$name.log"
            
            # Extract metadata
            pid=$(grep "^PID:" "$pid_file" 2>/dev/null | cut -d: -f2)
            created=$(grep "^CREATED:" "$pid_file" 2>/dev/null | cut -d: -f2)
            command=$(grep "^COMMAND:" "$pid_file" 2>/dev/null | cut -d: -f2-)
            task_name=$(grep "^NAME:" "$pid_file" 2>/dev/null | cut -d: -f2)
            
            # Check if file is 3+ days old
            if [ "$(find "$pid_file" -mtime +3 2>/dev/null)" ]; then
                echo "Cleaning up old files: $name (>3 days old)"
                rm -f "$pid_file" "$log_file"
                continue
            fi
            
            # Check if metadata is incomplete
            if [ -z "$pid" ] || [ -z "$created" ] || [ -z "$command" ] || [ -z "$task_name" ]; then
                echo "Cleaning up incomplete metadata: $name"
                rm -f "$pid_file" "$log_file"
                continue
            fi
        fi
    done
}

# Run cleanup at startup
cleanup_old_files

case "$1" in
    "start")
        if [ -z "$2" ]; then
            echo "Usage: $0 start '<command>' [name]"
            echo "Example: $0 start 'npm run dev' dev-server"
            exit 1
        fi
        
        COMMAND="$2"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BASE_NAME="${3:-bg}"
        NAME="${BASE_NAME}_$TIMESTAMP"
        PID_FILE="$PID_DIR/$NAME.pid"
        LOG_FILE="$LOG_DIR/$NAME.log"
        
        # Check if any process with same base name is already running
        for existing_pid_file in "$PID_DIR"/"${BASE_NAME}"_*.pid; do
            if [ -f "$existing_pid_file" ]; then
                existing_pid=$(grep "^PID:" "$existing_pid_file" | cut -d: -f2)
                if kill -0 "$existing_pid" 2>/dev/null; then
                    existing_name=$(grep "^NAME:" "$existing_pid_file" | cut -d: -f2)
                    existing_created=$(grep "^CREATED:" "$existing_pid_file" | cut -d: -f2)
                    existing_command=$(grep "^COMMAND:" "$existing_pid_file" | cut -d: -f2-)
                    echo "Process with base name '$BASE_NAME' already running:"
                    echo "  Job Name: $existing_name"
                    echo "  PID: $existing_pid"
                    echo "  Created: $existing_created"
                    echo "  Command: $existing_command"
                    exit 1
                fi
            fi
        done
        
        echo "Starting: $COMMAND"
        echo "Name: $NAME"
        echo "Logs: $LOG_FILE"
        
        nohup bash -c "$COMMAND" > "$LOG_FILE" 2>&1 &
        # Store PID and metadata in single file
        cat > "$PID_FILE" << EOF
PID:$!
CREATED:$TIMESTAMP
COMMAND:$COMMAND
NAME:$NAME
EOF
        
        PID=$(grep "^PID:" "$PID_FILE" | cut -d: -f2)
        echo "Started with PID: $PID"
        ;;
        
    "stop")
        if [ -z "$2" ]; then
            echo "Usage: $0 stop <name>"
            exit 1
        fi
        
        NAME="$2"
        PID_FILE="$PID_DIR/$NAME.pid"
        
        if [ ! -f "$PID_FILE" ]; then
            echo "No process named '$NAME' found"
            exit 0
        fi
        
        PID=$(grep "^PID:" "$PID_FILE" | cut -d: -f2)
        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping '$NAME' (PID: $PID)..."
            kill "$PID"
            sleep 1
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID"
            fi
            rm -f "$PID_FILE"
            echo "Stopped"
        else
            echo "Process not running"
            rm -f "$PID_FILE"
        fi
        ;;
        
    "status")
        if [ -z "$2" ]; then
            echo "Usage: $0 status <name>"
            exit 1
        fi
        
        NAME="$2"
        PID_FILE="$PID_DIR/$NAME.pid"
        
        if [ ! -f "$PID_FILE" ]; then
            echo "Process '$NAME': NOT FOUND"
            exit 1
        fi
        
        PID=$(grep "^PID:" "$PID_FILE" | cut -d: -f2)
        if kill -0 "$PID" 2>/dev/null; then
            echo "Process '$NAME': RUNNING (PID: $PID)"
        else
            echo "Process '$NAME': NOT RUNNING"
            rm -f "$PID_FILE"
        fi
        ;;
        
    "logs")
        if [ -z "$2" ]; then
            echo "Usage: $0 logs <name> [lines]"
            exit 1
        fi
        
        NAME="$2"
        LINES="${3:-50}"
        LOG_FILE="$LOG_DIR/$NAME.log"
        
        if [ ! -f "$LOG_FILE" ]; then
            echo "No log file for '$NAME'"
            exit 0
        fi
        
        tail -n "$LINES" "$LOG_FILE"
        ;;
        
    "follow")
        if [ -z "$2" ]; then
            echo "Usage: $0 follow <name>"
            exit 1
        fi
        
        NAME="$2"
        LOG_FILE="$LOG_DIR/$NAME.log"
        
        if [ ! -f "$LOG_FILE" ]; then
            echo "No log file for '$NAME'"
            exit 0
        fi
        
        tail -f "$LOG_FILE"
        ;;
        
    "list")
        if [ -z "$2" ]; then
            # List all processes
            echo "=== Background Processes ==="
            if [ ! -d "$PID_DIR" ] || [ -z "$(ls -A "$PID_DIR" 2>/dev/null)" ]; then
                echo "No processes running"
            else
                for pid_file in "$PID_DIR"/*.pid; do
                    if [ -f "$pid_file" ]; then
                        name=$(basename "$pid_file" .pid)
                        pid=$(grep "^PID:" "$pid_file" | cut -d: -f2)
                        created=$(grep "^CREATED:" "$pid_file" | cut -d: -f2)
                        command=$(grep "^COMMAND:" "$pid_file" | cut -d: -f2-)
                        if kill -0 "$pid" 2>/dev/null; then
                            echo "$name: RUNNING (PID: $pid, Created: $created)"
                            echo "  Command: $command"
                        else
                            echo "$name: DEAD (Created: $created)"
                            echo "  Command: $command"
                        fi
                        echo
                    fi
                done
            fi
        else
            # Search for processes by partial name
            SEARCH_TERM="$2"
            echo "=== Searching for processes matching: '$SEARCH_TERM' ==="
            found=false
            for pid_file in "$PID_DIR"/*.pid; do
                if [ -f "$pid_file" ]; then
                    name=$(basename "$pid_file" .pid)
                    if echo "$name" | grep -q "$SEARCH_TERM"; then
                        found=true
                        pid=$(grep "^PID:" "$pid_file" | cut -d: -f2)
                        created=$(grep "^CREATED:" "$pid_file" | cut -d: -f2)
                        command=$(grep "^COMMAND:" "$pid_file" | cut -d: -f2-)
                        if kill -0 "$pid" 2>/dev/null; then
                            echo "$name: RUNNING (PID: $pid, Created: $created)"
                            echo "  Command: $command"
                        else
                            echo "$name: DEAD (Created: $created)"
                            echo "  Command: $command"
                        fi
                        echo
                    fi
                fi
            done
            if [ "$found" = false ]; then
                echo "No processes found matching: '$SEARCH_TERM'"
            fi
        fi
        ;;
        
    "kill-all")
        echo "Stopping all background processes..."
        for pid_file in "$PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                name=$(basename "$pid_file" .pid)
                "$0" stop "$name"
            fi
        done
        ;;
        
    *)
        cat << EOF
Simple Background Process Manager

Usage: $0 <command> [args...]

Commands:
  start '<command>' [name]  - Start command in background (name will get timestamp)
  stop <name>              - Stop background process
  status <name>            - Check if process is running
  logs <name> [lines]      - Show last N lines of logs (default: 50)
  follow <name>            - Follow logs in real-time
  list [search]            - List all processes, or search by partial name
  kill-all                 - Stop all background processes

Examples:
  $0 start 'npm run dev' dev-server      # Creates: dev-server_20250126_143025
  $0 start 'python -m http.server 8080'  # Creates: bg_20250126_143025
  $0 stop dev-server_20250126_143025
  $0 logs dev-server_20250126_143025 100
  $0 list                                # List all processes with timestamps
  $0 list dev-server                     # Search for processes containing 'dev-server'

Files stored in:
  PIDs: $PID_DIR/
  Logs: $LOG_DIR/
  
Note: Files are isolated per hostname/container
EOF
        ;;
esac