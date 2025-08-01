#!/bin/bash
# Start the DevOps team for orchestrator development

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Claude Multi-Agent Orchestrator - DevOps Team Launcher${NC}"
echo "======================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "examples/devops_team_demo.py" ]; then
    echo "Error: Must run from orchestrator root directory"
    exit 1
fi

# Parse command line options
ENHANCED=false
TASK=""
DEBUG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --enhanced)
            ENHANCED=true
            shift
            ;;
        --task)
            TASK="$2"
            shift 2
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --enhanced    Use enhanced version with file system access"
            echo "  --task TEXT   Initial task for the team"
            echo "  --debug       Enable debug logging"
            echo "  --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Start basic DevOps team"
            echo "  $0 --enhanced         # Start with file access"
            echo "  $0 --task 'improve state detection'"
            echo "  $0 --enhanced --task 'add prometheus metrics'"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Choose which demo to run
if [ "$ENHANCED" = true ]; then
    SCRIPT="examples/devops_team_demo_enhanced.py"
    echo -e "${YELLOW}Starting ENHANCED DevOps team (with file system access)...${NC}"
else
    SCRIPT="examples/devops_team_demo.py"
    echo -e "${YELLOW}Starting basic DevOps team (MCP only)...${NC}"
fi

# Build command
CMD="python $SCRIPT $DEBUG"
if [ -n "$TASK" ]; then
    CMD="$CMD --task \"$TASK\""
fi

echo ""
echo "Command: $CMD"
echo ""

# Create .temp directory if it doesn't exist
mkdir -p .temp

# Start the team
eval $CMD