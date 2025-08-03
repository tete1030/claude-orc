#!/bin/bash
# Wrapper script that initializes pyenv and sources venv if available

# Initialize pyenv
export PYENV_ROOT="/opt/pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - --no-rehash)"

# Initialize Poetry
export POETRY_HOME="/opt/poetry"
export PATH="$POETRY_HOME/bin:$PATH"

# Prioritize local Claude Code installation (auto-updating version)
if [ -d "${HOME}/.claude/local" ]; then
    export PATH="${HOME}/.claude/local:$PATH"
fi

# Ensure WORKSPACE_PATH is set
if [ -z "${WORKSPACE_PATH}" ]; then
    export WORKSPACE_PATH="/workspace"
fi

# Configure Poetry for Docker environment
cd "${WORKSPACE_PATH}" 2>/dev/null || true

# Simple solution: Create a docker-specific venv directory using Poetry env command
export POETRY_VIRTUALENVS_IN_PROJECT=false
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"

# Configure Poetry
if command -v poetry &> /dev/null; then
    poetry config virtualenvs.in-project false
    poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker"
    
    # Ensure Python 3.12 is used
    poetry env use python3.12 2>/dev/null || true
fi

# Check if a venv exists in .venv-docker
if [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
    # Find the actual venv (it will be named like project-xxx-py3.12)
    DOCKER_VENV=$(find "${WORKSPACE_PATH}/.venv-docker" -maxdepth 1 -type d -name "*-py3.12" | head -1)
    if [ -n "$DOCKER_VENV" ] && [ -d "$DOCKER_VENV" ]; then
        export VIRTUAL_ENV="$DOCKER_VENV"
        export PATH="$VIRTUAL_ENV/bin:$PATH"
        source "$VIRTUAL_ENV/bin/activate" 2>/dev/null || true
    else
        echo "Docker venv directory exists but no valid environment found."
        echo "Run 'poetry install --no-root' to create it."
    fi
else
    echo "Docker venv not found. Run 'poetry install --no-root' to create it."
    echo "Poetry will create environment in: ${WORKSPACE_PATH}/.venv-docker/"
fi

# Execute the command
exec "$@"