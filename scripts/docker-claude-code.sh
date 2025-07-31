#!/bin/bash

# Docker Claude Code Environment Management Script

set -e

DOCKER_DIR="$(dirname "$0")/../docker/claude-code"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"
SERVICE_NAME="claude-code-env"
IMAGE_NAME="ccbox:latest"
DEFAULT_CONTAINER_NAME="ccbox"

# Support for multiple instances
INSTANCE_NAME="${CLAUDE_INSTANCE:-}"

# Generate random suffix if requested
if [ "$1" = "--random" ] || [ "$CLAUDE_INSTANCE_RANDOM" = "true" ]; then
    # Generate 8-character random string (alphanumeric)
    RANDOM_SUFFIX=$(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 8 || true)
    if [ -z "$RANDOM_SUFFIX" ]; then
        # Fallback to date-based suffix if urandom fails
        RANDOM_SUFFIX=$(date +%s | tail -c 8)
    fi
    
    if [ -n "$INSTANCE_NAME" ]; then
        INSTANCE_NAME="${INSTANCE_NAME}-${RANDOM_SUFFIX}"
    else
        INSTANCE_NAME="${RANDOM_SUFFIX}"
    fi
    
    # Shift argument if --random was first arg
    [ "$1" = "--random" ] && shift
fi

if [ -n "$INSTANCE_NAME" ]; then
    CONTAINER_NAME="${DEFAULT_CONTAINER_NAME}-${INSTANCE_NAME}"
    PROJECT_NAME="claudecode${INSTANCE_NAME}"
else
    CONTAINER_NAME="$DEFAULT_CONTAINER_NAME"
    PROJECT_NAME="claudecode"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [--random] {build|start|stop|restart|shell|run|run-bash|exec|logs|status|list|clean}"
    echo ""
    echo "Commands:"
    echo "  build    - Build the Docker image (only needed once)"
    echo "  start    - Start a persistent container"
    echo "  stop     - Stop the container"
    echo "  restart  - Restart the container"
    echo "  shell    - Open an interactive shell in the container"
    echo "  run      - Run Claude Code in a new temporary container (auto-removes on exit)"
    echo "  run-bash - Run interactive bash in a new temporary container (auto-removes on exit)"
    echo "  exec     - Execute a command in the container (default: claude --dangerously-skip-permissions)"
    echo "  logs     - Show container logs"
    echo "  status   - Show container status"
    echo "  list     - List all Claude Code containers"
    echo "  clean    - Remove container and volumes (WARNING: deletes data)"
    echo "             Usage: clean [filter] - With filter, removes all matching containers"
    echo ""
    echo "Options:"
    echo "  --random - Add a random 8-character suffix to the container name"
    echo ""
    echo "Environment Variables:"
    echo "  CLAUDE_INSTANCE        - Set to create named instances (e.g., CLAUDE_INSTANCE=test1)"
    echo "  CLAUDE_INSTANCE_RANDOM - Set to 'true' to always append random suffix"
    echo ""
    echo "Examples:"
    echo "  # Run Claude Code directly"
    echo "  $0 run"
    echo "  # Run interactive bash"
    echo "  $0 run-bash"
    echo "  # Run multiple instances"
    echo "  CLAUDE_INSTANCE=project1 $0 start"
    echo "  CLAUDE_INSTANCE=project2 $0 start"
    echo "  # Start container with random suffix"
    echo "  $0 --random start"
    echo "  # Named instance with random suffix"
    echo "  CLAUDE_INSTANCE=dev $0 --random start  # Creates: ccbox-dev-a1b2c3d4"
    echo "  # Always use random suffix via environment"
    echo "  export CLAUDE_INSTANCE_RANDOM=true"
    echo "  $0 start  # Creates: ccbox-a1b2c3d4"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if docker and docker compose are installed
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
}

# Check if image exists
image_exists() {
    docker image inspect "$IMAGE_NAME" >/dev/null 2>&1
}

# Build the Docker image
build_image() {
    print_status "Building Claude Code Docker image..."
    export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    export CONTAINER_NAME="$CONTAINER_NAME"
    docker compose -f "$COMPOSE_FILE" build
    print_status "Build completed successfully"
}

# Start the container
start_container() {
    # Check if image exists, build if not
    if ! image_exists; then
        print_warning "Docker image not found. Building it first..."
        build_image
    fi
    
    print_status "Starting Claude Code container '${CONTAINER_NAME}'..."
    # Export user info and paths for docker-compose
    export USER_UID=$(id -u)
    export USER_GID=$(id -g)
    export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    export CONTAINER_NAME="$CONTAINER_NAME"
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d
    print_status "Container '${CONTAINER_NAME}' started successfully"
    print_status "You can now access the container with: $0 shell"
    if [ -n "$INSTANCE_NAME" ]; then
        print_status "Instance: ${INSTANCE_NAME}"
    fi
}

# Stop the container
stop_container() {
    print_status "Stopping Claude Code container '${CONTAINER_NAME}'..."
    export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    export CONTAINER_NAME="$CONTAINER_NAME"
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" stop
    print_status "Container stopped successfully"
}

# Restart the container
restart_container() {
    stop_container
    start_container
}

# Open shell in container
open_shell() {
    print_status "Opening shell in Claude Code container '${CONTAINER_NAME}'..."
    # Export user info and paths for docker-compose
    export USER_UID=$(id -u)
    export USER_GID=$(id -g)
    export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    export CONTAINER_NAME="$CONTAINER_NAME"
    
    # Pass user environment to exec command
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec \
        -e LOCAL_USER_ID=$(id -u) \
        -e LOCAL_GROUP_ID=$(id -g) \
        -e LOCAL_USER_NAME=$USER \
        -e LOCAL_USER_HOME=$HOME \
        "$SERVICE_NAME" /usr/local/bin/entrypoint.sh /bin/bash
}

# Run temporary container
run_temporary() {
    shift

    # Check if image exists, build if not
    if ! image_exists; then
        print_warning "Docker image not found. Building it first..."
        build_image
    fi
    
    # Get the actual workspace path
    WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    
    # Load custom mounts from .ccbox.env if it exists
    CUSTOM_MOUNTS=""
    if [ -f "$WORKSPACE_PATH/.ccbox.env" ]; then
        print_status "Loading custom mounts from .ccbox.env"
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
                # Parse MOUNT_* variables
                if [[ "$line" =~ ^MOUNT_[A-Z0-9_]+=(.+)$ ]]; then
                    mount_spec="${BASH_REMATCH[1]}"
                    # Remove quotes if present
                    mount_spec="${mount_spec%\"}"
                    mount_spec="${mount_spec#\"}"
                    CUSTOM_MOUNTS="$CUSTOM_MOUNTS -v $mount_spec"
                fi
            fi
        done < "$WORKSPACE_PATH/.ccbox.env"
    fi
    
    print_status "Running temporary Claude Code container (will auto-remove on exit)..."
    
    # Build environment variable arguments
    ENV_ARGS=""
    
    # Claude Code API settings
    [ -n "$ANTHROPIC_API_KEY" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_API_KEY"
    [ -n "$ANTHROPIC_AUTH_TOKEN" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_AUTH_TOKEN"
    [ -n "$ANTHROPIC_CUSTOM_HEADERS" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_CUSTOM_HEADERS"
    [ -n "$ANTHROPIC_MODEL" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_MODEL"
    [ -n "$ANTHROPIC_SMALL_FAST_MODEL" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_SMALL_FAST_MODEL"
    [ -n "$ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION"
    [ -n "$AWS_BEARER_TOKEN_BEDROCK" ] && ENV_ARGS="$ENV_ARGS -e AWS_BEARER_TOKEN_BEDROCK"
    
    # Claude Code behavior settings
    [ -n "$BASH_DEFAULT_TIMEOUT_MS" ] && ENV_ARGS="$ENV_ARGS -e BASH_DEFAULT_TIMEOUT_MS"
    [ -n "$BASH_MAX_TIMEOUT_MS" ] && ENV_ARGS="$ENV_ARGS -e BASH_MAX_TIMEOUT_MS"
    [ -n "$BASH_MAX_OUTPUT_LENGTH" ] && ENV_ARGS="$ENV_ARGS -e BASH_MAX_OUTPUT_LENGTH"
    [ -n "$CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR"
    [ -n "$CLAUDE_CODE_API_KEY_HELPER_TTL_MS" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_API_KEY_HELPER_TTL_MS"
    [ -n "$CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL"
    [ -n "$CLAUDE_CODE_MAX_OUTPUT_TOKENS" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_MAX_OUTPUT_TOKENS"
    [ -n "$CLAUDE_CODE_SSE_PORT" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_SSE_PORT"
    [ -n "$CLAUDE_CODE_USE_BEDROCK" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_USE_BEDROCK"
    [ -n "$CLAUDE_CODE_USE_VERTEX" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_USE_VERTEX"
    [ -n "$CLAUDE_CODE_SKIP_BEDROCK_AUTH" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_SKIP_BEDROCK_AUTH"
    [ -n "$CLAUDE_CODE_SKIP_VERTEX_AUTH" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_SKIP_VERTEX_AUTH"
    
    # Claude Code feature toggles
    [ -n "$CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"
    [ -n "$CLAUDE_CODE_DISABLE_TERMINAL_TITLE" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_DISABLE_TERMINAL_TITLE"
    [ -n "$DISABLE_AUTOUPDATER" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_AUTOUPDATER"
    [ -n "$DISABLE_BUG_COMMAND" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_BUG_COMMAND"
    [ -n "$DISABLE_COST_WARNINGS" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_COST_WARNINGS"
    [ -n "$DISABLE_ERROR_REPORTING" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_ERROR_REPORTING"
    [ -n "$DISABLE_NON_ESSENTIAL_MODEL_CALLS" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_NON_ESSENTIAL_MODEL_CALLS"
    [ -n "$DISABLE_TELEMETRY" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_TELEMETRY"
    
    # Proxy settings
    [ -n "$HTTP_PROXY" ] && ENV_ARGS="$ENV_ARGS -e HTTP_PROXY"
    [ -n "$HTTPS_PROXY" ] && ENV_ARGS="$ENV_ARGS -e HTTPS_PROXY"
    
    # Model token settings
    [ -n "$MAX_THINKING_TOKENS" ] && ENV_ARGS="$ENV_ARGS -e MAX_THINKING_TOKENS"
    [ -n "$MCP_TIMEOUT" ] && ENV_ARGS="$ENV_ARGS -e MCP_TIMEOUT"
    [ -n "$MCP_TOOL_TIMEOUT" ] && ENV_ARGS="$ENV_ARGS -e MCP_TOOL_TIMEOUT"
    [ -n "$MAX_MCP_OUTPUT_TOKENS" ] && ENV_ARGS="$ENV_ARGS -e MAX_MCP_OUTPUT_TOKENS"
    
    # Vertex region settings
    [ -n "$VERTEX_REGION_CLAUDE_3_5_HAIKU" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_3_5_HAIKU"
    [ -n "$VERTEX_REGION_CLAUDE_3_5_SONNET" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_3_5_SONNET"
    [ -n "$VERTEX_REGION_CLAUDE_3_7_SONNET" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_3_7_SONNET"
    [ -n "$VERTEX_REGION_CLAUDE_4_0_OPUS" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_4_0_OPUS"
    [ -n "$VERTEX_REGION_CLAUDE_4_0_SONNET" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_4_0_SONNET"
    
    # Claude configuration mode
    [ -n "$CLAUDE_CONTAINER_MODE" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CONTAINER_MODE"
    
    docker run --rm -it --init \
        --name "$CONTAINER_NAME-temp-$$" \
        -e LOCAL_USER_ID=$(id -u) \
        -e LOCAL_GROUP_ID=$(id -g) \
        -e LOCAL_USER_NAME=$USER \
        -e LOCAL_USER_HOME=$HOME \
        -e WORKSPACE_PATH=$WORKSPACE_PATH \
        -e PYTHONPATH=$WORKSPACE_PATH \
        -e TERM=xterm-256color \
        $ENV_ARGS \
        -v "$WORKSPACE_PATH:$WORKSPACE_PATH" \
        -v ~/.claude:$HOME/.claude-host/.claude \
        -v ~/.claude.json:$HOME/.claude-host/.claude.json \
        -v ~/.gitconfig:$HOME/.gitconfig:ro \
        -v ~/.ssh:$HOME/.ssh:ro \
        -v ~/.cache/ms-playwright:$HOME/.cache/ms-playwright:cached \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v ~/.config/gh:$HOME/.config/gh:ro \
        -v /tmp/claude-orc:/tmp/claude-orc \
        $CUSTOM_MOUNTS \
        -w "$WORKSPACE_PATH" \
        --network host \
        "$IMAGE_NAME" \
        claude --dangerously-skip-permissions "$@"
}

# Run temporary container with bash
run_bash() {
    # Check if image exists, build if not
    if ! image_exists; then
        print_warning "Docker image not found. Building it first..."
        build_image
    fi
    
    # Get the actual workspace path
    WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    
    # Load custom mounts from .ccbox.env if it exists
    CUSTOM_MOUNTS=""
    if [ -f "$WORKSPACE_PATH/.ccbox.env" ]; then
        print_status "Loading custom mounts from .ccbox.env"
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
                # Parse MOUNT_* variables
                if [[ "$line" =~ ^MOUNT_[A-Z0-9_]+=(.+)$ ]]; then
                    mount_spec="${BASH_REMATCH[1]}"
                    # Remove quotes if present
                    mount_spec="${mount_spec%\"}"
                    mount_spec="${mount_spec#\"}"
                    CUSTOM_MOUNTS="$CUSTOM_MOUNTS -v $mount_spec"
                fi
            fi
        done < "$WORKSPACE_PATH/.ccbox.env"
    fi
    
    print_status "Running temporary Claude Code container with bash (will auto-remove on exit)..."
    
    # Build environment variable arguments
    ENV_ARGS=""
    
    # Claude Code API settings
    [ -n "$ANTHROPIC_API_KEY" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_API_KEY"
    [ -n "$ANTHROPIC_AUTH_TOKEN" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_AUTH_TOKEN"
    [ -n "$ANTHROPIC_CUSTOM_HEADERS" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_CUSTOM_HEADERS"
    [ -n "$ANTHROPIC_MODEL" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_MODEL"
    [ -n "$ANTHROPIC_SMALL_FAST_MODEL" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_SMALL_FAST_MODEL"
    [ -n "$ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION" ] && ENV_ARGS="$ENV_ARGS -e ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION"
    [ -n "$AWS_BEARER_TOKEN_BEDROCK" ] && ENV_ARGS="$ENV_ARGS -e AWS_BEARER_TOKEN_BEDROCK"
    
    # Claude Code behavior settings
    [ -n "$BASH_DEFAULT_TIMEOUT_MS" ] && ENV_ARGS="$ENV_ARGS -e BASH_DEFAULT_TIMEOUT_MS"
    [ -n "$BASH_MAX_TIMEOUT_MS" ] && ENV_ARGS="$ENV_ARGS -e BASH_MAX_TIMEOUT_MS"
    [ -n "$BASH_MAX_OUTPUT_LENGTH" ] && ENV_ARGS="$ENV_ARGS -e BASH_MAX_OUTPUT_LENGTH"
    [ -n "$CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR"
    [ -n "$CLAUDE_CODE_API_KEY_HELPER_TTL_MS" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_API_KEY_HELPER_TTL_MS"
    [ -n "$CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL"
    [ -n "$CLAUDE_CODE_MAX_OUTPUT_TOKENS" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_MAX_OUTPUT_TOKENS"
    [ -n "$CLAUDE_CODE_SSE_PORT" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_SSE_PORT"
    [ -n "$CLAUDE_CODE_USE_BEDROCK" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_USE_BEDROCK"
    [ -n "$CLAUDE_CODE_USE_VERTEX" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_USE_VERTEX"
    [ -n "$CLAUDE_CODE_SKIP_BEDROCK_AUTH" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_SKIP_BEDROCK_AUTH"
    [ -n "$CLAUDE_CODE_SKIP_VERTEX_AUTH" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_SKIP_VERTEX_AUTH"
    
    # Claude Code feature toggles
    [ -n "$CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"
    [ -n "$CLAUDE_CODE_DISABLE_TERMINAL_TITLE" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CODE_DISABLE_TERMINAL_TITLE"
    [ -n "$DISABLE_AUTOUPDATER" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_AUTOUPDATER"
    [ -n "$DISABLE_BUG_COMMAND" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_BUG_COMMAND"
    [ -n "$DISABLE_COST_WARNINGS" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_COST_WARNINGS"
    [ -n "$DISABLE_ERROR_REPORTING" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_ERROR_REPORTING"
    [ -n "$DISABLE_NON_ESSENTIAL_MODEL_CALLS" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_NON_ESSENTIAL_MODEL_CALLS"
    [ -n "$DISABLE_TELEMETRY" ] && ENV_ARGS="$ENV_ARGS -e DISABLE_TELEMETRY"
    
    # Proxy settings
    [ -n "$HTTP_PROXY" ] && ENV_ARGS="$ENV_ARGS -e HTTP_PROXY"
    [ -n "$HTTPS_PROXY" ] && ENV_ARGS="$ENV_ARGS -e HTTPS_PROXY"
    
    # Model token settings
    [ -n "$MAX_THINKING_TOKENS" ] && ENV_ARGS="$ENV_ARGS -e MAX_THINKING_TOKENS"
    [ -n "$MCP_TIMEOUT" ] && ENV_ARGS="$ENV_ARGS -e MCP_TIMEOUT"
    [ -n "$MCP_TOOL_TIMEOUT" ] && ENV_ARGS="$ENV_ARGS -e MCP_TOOL_TIMEOUT"
    [ -n "$MAX_MCP_OUTPUT_TOKENS" ] && ENV_ARGS="$ENV_ARGS -e MAX_MCP_OUTPUT_TOKENS"
    
    # Vertex region settings
    [ -n "$VERTEX_REGION_CLAUDE_3_5_HAIKU" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_3_5_HAIKU"
    [ -n "$VERTEX_REGION_CLAUDE_3_5_SONNET" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_3_5_SONNET"
    [ -n "$VERTEX_REGION_CLAUDE_3_7_SONNET" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_3_7_SONNET"
    [ -n "$VERTEX_REGION_CLAUDE_4_0_OPUS" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_4_0_OPUS"
    [ -n "$VERTEX_REGION_CLAUDE_4_0_SONNET" ] && ENV_ARGS="$ENV_ARGS -e VERTEX_REGION_CLAUDE_4_0_SONNET"
    
    # Claude configuration mode
    [ -n "$CLAUDE_CONTAINER_MODE" ] && ENV_ARGS="$ENV_ARGS -e CLAUDE_CONTAINER_MODE"
    
    docker run --rm -it --init \
        --name "$CONTAINER_NAME-bash-$$" \
        -e LOCAL_USER_ID=$(id -u) \
        -e LOCAL_GROUP_ID=$(id -g) \
        -e LOCAL_USER_NAME=$USER \
        -e LOCAL_USER_HOME=$HOME \
        -e WORKSPACE_PATH=$WORKSPACE_PATH \
        -e PYTHONPATH=$WORKSPACE_PATH \
        -e TERM=xterm-256color \
        $ENV_ARGS \
        -v "$WORKSPACE_PATH:$WORKSPACE_PATH" \
        -v ~/.claude:$HOME/.claude-host/.claude \
        -v ~/.claude.json:$HOME/.claude-host/.claude.json \
        -v ~/.gitconfig:$HOME/.gitconfig:ro \
        -v ~/.ssh:$HOME/.ssh:ro \
        -v ~/.cache/ms-playwright:$HOME/.cache/ms-playwright:cached \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v ~/.config/gh:$HOME/.config/gh:ro \
        -v /tmp/claude-orc:/tmp/claude-orc \
        $CUSTOM_MOUNTS \
        -w "$WORKSPACE_PATH" \
        --network host \
        "$IMAGE_NAME" \
        /bin/bash
}

# Execute command in container
exec_command() {
    shift # Remove 'exec' from arguments
    
    # Default to running claude if no command provided
    if [ $# -eq 0 ]; then
        print_status "Starting Claude Code in container..."
        set -- claude --dangerously-skip-permissions
    else
        print_status "Executing command in container: $@"
    fi
    
    export USER_UID=$(id -u)
    export USER_GID=$(id -g)
    export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    export CONTAINER_NAME="$CONTAINER_NAME"
    
    # Pass user environment to exec command
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec \
        -e LOCAL_USER_ID=$(id -u) \
        -e LOCAL_GROUP_ID=$(id -g) \
        -e LOCAL_USER_NAME=$USER \
        -e LOCAL_USER_HOME=$HOME \
        "$SERVICE_NAME" /usr/local/bin/entrypoint.sh "$@"
}

# Show logs
show_logs() {
    print_status "Showing container logs..."
    export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    export CONTAINER_NAME="$CONTAINER_NAME"
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" logs -f "$SERVICE_NAME"
}

# Show status
show_status() {
    print_status "Container status for project '${PROJECT_NAME}':"
    export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
    export CONTAINER_NAME="$CONTAINER_NAME"
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps
}

# List all Claude Code containers
list_containers() {
    print_status "All Claude Code containers:"
    docker ps -a --filter "name=ccbox" --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
}

# Clean up
clean_up() {
    # Check if a filter was provided
    if [ -n "$2" ]; then
        # Batch clean with filter
        local filter="$2"
        print_status "Finding Claude Code containers matching filter: '$filter'"
        
        # Get matching containers
        local containers=$(docker ps -a --filter "name=ccbox" --format "{{.Names}}" | grep "$filter")
        
        if [ -z "$containers" ]; then
            print_warning "No containers found matching filter: '$filter'"
            return
        fi
        
        # Show containers that will be removed
        echo "The following containers will be removed:"
        echo "$containers" | while read -r container; do
            echo "  - $container"
        done
        
        read -p "Are you sure you want to remove these containers? (y/N) " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$containers" | while read -r container; do
                print_status "Removing container: $container"
                docker rm -f "$container" 2>/dev/null || true
            done
            print_status "Batch cleanup completed"
        else
            print_status "Cleanup cancelled"
        fi
    else
        # Single container clean (original behavior)
        print_warning "This will remove the container '${CONTAINER_NAME}' and all associated volumes!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Cleaning up..."
            export WORKSPACE_PATH="$(cd "$DOCKER_DIR/../.." && pwd)"
            export CONTAINER_NAME="$CONTAINER_NAME"
            docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v
            print_status "Cleanup completed"
        else
            print_status "Cleanup cancelled"
        fi
    fi
}

# Main script logic
check_dependencies

case "$1" in
    build)
        build_image
        ;;
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    shell)
        open_shell
        ;;
    run)
        run_temporary "$@"
        ;;
    run-bash)
        run_bash
        ;;
    exec)
        exec_command "$@"
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    list)
        list_containers
        ;;
    clean)
        clean_up "$@"
        ;;
    *)
        print_usage
        exit 1
        ;;
esac