#!/bin/bash
# Install ccorc to user's PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="$HOME/.local/bin"

# Create install directory if needed
mkdir -p "$INSTALL_DIR"

# Create wrapper script
cat > "$INSTALL_DIR/ccorc" << EOL
#!/bin/bash
exec python3 "$REPO_ROOT/bin/ccorc" "\$@"
EOL

chmod +x "$INSTALL_DIR/ccorc"

echo "✓ Installed ccorc to $INSTALL_DIR"
echo "Make sure $INSTALL_DIR is in your PATH"
