#!/bin/bash
# Install session-cli to user's PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="$HOME/.local/bin"

# Create install directory if needed
mkdir -p "$INSTALL_DIR"

# Create wrapper script
cat > "$INSTALL_DIR/session-cli" << EOL
#!/bin/bash
exec python3 "$REPO_ROOT/bin/session-cli" "\$@"
EOL

chmod +x "$INSTALL_DIR/session-cli"

echo "✓ Installed session-cli to $INSTALL_DIR"
echo "Make sure $INSTALL_DIR is in your PATH"
