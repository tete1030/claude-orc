#!/bin/bash

# Install script for claude-bg (background process manager)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_FILE="$SCRIPT_DIR/claude-bg"

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    print_error "Source file not found: $SOURCE_FILE"
    exit 1
fi

# Determine installation directory
if [ "$(id -u)" -eq 0 ]; then
    # Running as root
    INSTALL_DIR="/usr/local/bin"
else
    # Running as regular user
    INSTALL_DIR="$HOME/.local/bin"
    
    # Create directory if it doesn't exist
    if [ ! -d "$INSTALL_DIR" ]; then
        print_status "Creating directory: $INSTALL_DIR"
        mkdir -p "$INSTALL_DIR"
    fi
    
    # Check if ~/.local/bin is in PATH
    if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
        print_warning "$INSTALL_DIR is not in your PATH"
        print_warning "Add this line to your ~/.bashrc or ~/.zshrc:"
        print_warning "  export PATH=\"$HOME/.local/bin:\$PATH\""
    fi
fi

TARGET_FILE="$INSTALL_DIR/claude-bg"

# Copy the script
print_status "Installing claude-bg to $INSTALL_DIR"
cp "$SOURCE_FILE" "$TARGET_FILE"
chmod +x "$TARGET_FILE"

# Verify installation
if [ -f "$TARGET_FILE" ] && [ -x "$TARGET_FILE" ]; then
    print_status "Successfully installed claude-bg to $TARGET_FILE"
    
    # Test if it's accessible
    if command -v claude-bg >/dev/null 2>&1; then
        print_status "claude-bg is now available in your PATH"
        print_status "You can now use 'claude-bg'"
    else
        print_warning "claude-bg installed but not yet in PATH"
        print_warning "Please restart your shell or run: source ~/.bashrc"
    fi
else
    print_error "Installation failed"
    exit 1
fi

print_status "Installation complete!"
print_status "Usage: claude-bg {start|stop|status|list|logs|follow|kill-all} ..."
