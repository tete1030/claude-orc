#!/bin/bash
# Setup script for Claude ORC host environment
# This script sets up the Python environment and installs dependencies on the host system

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Claude ORC Host Environment Setup${NC}"
echo "=================================="

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Error: Poetry is not installed${NC}"
    echo "Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
REQUIRED_MAJOR=3
REQUIRED_MINOR=12

ACTUAL_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
ACTUAL_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$ACTUAL_MAJOR" -ne "$REQUIRED_MAJOR" ] || [ "$ACTUAL_MINOR" -lt "$REQUIRED_MINOR" ]; then
    echo -e "${RED}Error: Python 3.12+ is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
echo -e "${GREEN}✓${NC} Poetry $(poetry --version | cut -d' ' -f3) found"

# Configure Poetry for in-project virtualenv
echo -e "\n${YELLOW}Configuring Poetry...${NC}"
poetry config virtualenvs.in-project true
poetry config virtualenvs.path --unset 2>/dev/null || true

if [ -d ".venv" ]; then
    echo -e "${YELLOW}Removing existing virtualenv...${NC}"
    rm -rf .venv
fi

# Create new virtualenv and install dependencies
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
poetry install --no-root
