#!/bin/bash
# Wrapper script that sources workspace-specific initialization

# Prioritize local Claude Code installation (auto-updating version)
if [[ "$PATH" != *"${HOME}/.claude/local"* ]] && [ -d "${HOME}/.claude/local" ] && [ -x "${HOME}/.claude/local/claude" ] ; then
    export PATH="${HOME}/.claude/local:$PATH"
fi

# Ensure WORKSPACE_PATH is set
if [ -z "${WORKSPACE_PATH}" ]; then
    echo "ERROR: WORKSPACE_PATH is not set"
    exit 1
fi

# Change to workspace directory
cd "${WORKSPACE_PATH}" 2>/dev/null || true

# Source workspace-specific initialization if exists
if [ -f "${WORKSPACE_PATH}/.ccbox/init.sh" ]; then
    echo "Loading workspace configuration from .ccbox/init.sh"
    source "${WORKSPACE_PATH}/.ccbox/init.sh"
fi

# Execute the command
exec "$@"