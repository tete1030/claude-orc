#!/bin/bash
#
# Install ccorc command from the claude-orc repository
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}Error: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_info() {
    echo -e "${YELLOW}$1${NC}"
}

# Get script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to repo root
cd "$REPO_ROOT"

# Check if we're in the claude-orc directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/cli" ]; then
    print_error "This script must be run from the claude-orc repository"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not found"
    exit 1
fi

# Check Python version (require 3.8+)
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

# Check for pip
if ! python3 -m pip --version &> /dev/null; then
    print_error "pip is required but not found"
    print_info "Install pip with: python3 -m ensurepip --upgrade"
    exit 1
fi

print_info "Installing ccorc..."

# Install the package in editable mode with minimal dependencies
python3 -m pip install -e . --user --quiet

# Check if installation was successful
if python3 -m pip show claude-orc &> /dev/null; then
    print_success "✓ ccorc installed successfully"
else
    print_error "Installation failed"
    exit 1
fi

# Check if ccorc is in PATH
if command -v ccorc &> /dev/null; then
    print_success "✓ ccorc is available in your PATH"
    print_info "You can now run: ccorc --help"
else
    # Provide PATH update instructions
    print_info "ccorc was installed but is not in your PATH"
    print_info "Add the following to your shell configuration file (.bashrc, .zshrc, etc.):"
    echo ""
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    print_info "Then reload your shell or run: source ~/.bashrc"
fi

print_success "Installation complete!"
