# Workspace Configuration Guide

This guide provides comprehensive instructions for configuring workspace-specific environments using the `.ccbox/` directory structure in Claude Code containers.

## Overview

The `.ccbox/` directory enables you to customize your Docker container environment for different project types and requirements. This system supports:

- **Custom environment initialization** via `init.sh`
- **Additional volume mounts** via `mounts` file
- **Language-specific setup** for Python, Node.js, Go, and more
- **Project-specific configurations** that don't interfere with other projects

## Quick Start

### 1. Create the .ccbox Directory

```bash
# In your project root
mkdir -p .ccbox

# Add to .gitignore to avoid committing environment-specific configs
echo ".ccbox/" >> .gitignore
```

### 2. Set Up Basic Configuration

```bash
# Copy example mounts configuration
cp .ccbox/mounts.example .ccbox/mounts

# Create a basic init.sh
cat > .ccbox/init.sh << 'EOF'
#!/bin/bash
# Basic workspace initialization
echo "Loading workspace configuration..."

# Add your project-specific setup here
EOF

chmod +x .ccbox/init.sh
```

### 3. Run Your Container

```bash
# The container will automatically load your .ccbox configuration
ccdk run
```

## Configuration Files

### Directory Structure

```
.ccbox/
├── init.sh           # Custom initialization script (executable)
├── mounts           # Custom volume mounts configuration
├── .gitignore       # Excludes environment-specific files
└── README.md        # Documentation for your team (optional)
```

### init.sh - Environment Initialization

The `init.sh` script is sourced when the container starts, allowing you to:

- Set environment variables
- Configure development tools
- Install dependencies
- Activate virtual environments
- Set up database connections
- Configure project-specific paths

**Basic Template**:
```bash
#!/bin/bash
# .ccbox/init.sh - Workspace initialization

# Set project-specific environment variables
export PROJECT_NAME="my-project"
export DEBUG=true
export LOG_LEVEL=info

# Configure development tools
# Add your setup commands here

echo "Workspace '${PROJECT_NAME}' initialized successfully"
```

### mounts - Custom Volume Mounts

The `mounts` file defines additional directories to mount in the container:

**Format**: `MOUNT_<NAME>="/host/path:/container/path:options"`

**Options**:
- `ro` - Read-only mount
- `rw` - Read-write mount (default)
- `cached` - Better performance on macOS

## Language-Specific Configurations

### Python Projects

#### Basic Python Setup
```bash
#!/bin/bash
# .ccbox/init.sh for Python projects

# Ensure Python 3.12 is used
export PYTHON_VERSION="3.12"

# Set up project-specific environment
export PYTHONPATH="${WORKSPACE_PATH}:${PYTHONPATH}"
export PIP_CACHE_DIR="${WORKSPACE_PATH}/.cache/pip"

# Configure development settings
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
```

#### Poetry Projects
```bash
#!/bin/bash
# .ccbox/init.sh for Poetry projects

# Configure Poetry for Docker environment
export POETRY_VIRTUALENVS_IN_PROJECT=false
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"
export POETRY_CACHE_DIR="${WORKSPACE_PATH}/.cache/poetry"

# Initialize Poetry configuration
if command -v poetry &> /dev/null; then
    poetry config virtualenvs.in-project false
    poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker"
    poetry config cache-dir "${WORKSPACE_PATH}/.cache/poetry"
    
    # Use Python 3.12
    poetry env use python3.12 2>/dev/null || true
    
    # Auto-install dependencies if pyproject.toml exists and no venv
    if [ -f "${WORKSPACE_PATH}/pyproject.toml" ] && ! [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
        echo "Installing Python dependencies with Poetry..."
        poetry install --no-root
    fi
fi

# Auto-activate virtual environment
if [ -d "${WORKSPACE_PATH}/.venv-docker" ]; then
    DOCKER_VENV=$(find "${WORKSPACE_PATH}/.venv-docker" -maxdepth 1 -type d -name "*-py3.12" | head -1)
    if [ -n "$DOCKER_VENV" ] && [ -d "$DOCKER_VENV" ]; then
        export VIRTUAL_ENV="$DOCKER_VENV"
        export PATH="$VIRTUAL_ENV/bin:$PATH"
        source "$VIRTUAL_ENV/bin/activate" 2>/dev/null || true
        echo "Activated Python virtual environment: $(basename $DOCKER_VENV)"
    fi
fi
```

#### Django Projects
```bash
#!/bin/bash
# .ccbox/init.sh for Django projects

# Include Poetry setup (from above)
# ... Poetry configuration ...

# Django-specific settings
export DJANGO_SETTINGS_MODULE="myproject.settings.development"
export DJANGO_DEBUG=true
export DJANGO_SECRET_KEY="dev-secret-key-do-not-use-in-production"

# Database configuration for development
export DATABASE_URL="sqlite:///${WORKSPACE_PATH}/db.sqlite3"

# Auto-run migrations if Django is detected
if [ -f "${WORKSPACE_PATH}/manage.py" ]; then
    echo "Django project detected"
    
    # Run migrations if database doesn't exist
    if [ ! -f "${WORKSPACE_PATH}/db.sqlite3" ]; then
        echo "Running initial Django migrations..."
        python manage.py migrate --noinput 2>/dev/null || echo "Migrations will run when you start Django"
    fi
fi
```

### Node.js Projects

#### Basic Node.js Setup
```bash
#!/bin/bash
# .ccbox/init.sh for Node.js projects

# Node.js environment settings
export NODE_ENV=development
export NPM_CONFIG_CACHE="${WORKSPACE_PATH}/.cache/npm"
export NODE_OPTIONS="--max_old_space_size=4096"

# Auto-install dependencies
if [ -f "${WORKSPACE_PATH}/package.json" ] && ! [ -d "${WORKSPACE_PATH}/node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

echo "Node.js environment configured"
```

#### React Projects
```bash
#!/bin/bash
# .ccbox/init.sh for React projects

# Include basic Node.js setup
export NODE_ENV=development
export NPM_CONFIG_CACHE="${WORKSPACE_PATH}/.cache/npm"

# React-specific settings
export REACT_APP_API_URL="http://localhost:3001"
export BROWSER=none  # Prevent browser from opening in container
export PORT=3000

# Auto-install dependencies
if [ -f "${WORKSPACE_PATH}/package.json" ] && ! [ -d "${WORKSPACE_PATH}/node_modules" ]; then
    echo "Installing React dependencies..."
    npm install
fi

echo "React development environment ready"
echo "Run 'npm start' to start the development server"
```

#### Next.js Projects
```bash
#!/bin/bash
# .ccbox/init.sh for Next.js projects

# Include basic Node.js setup
export NODE_ENV=development
export NPM_CONFIG_CACHE="${WORKSPACE_PATH}/.cache/npm"

# Next.js specific settings
export NEXT_TELEMETRY_DISABLED=1
export PORT=3000

# Auto-install dependencies
if [ -f "${WORKSPACE_PATH}/package.json" ] && ! [ -d "${WORKSPACE_PATH}/node_modules" ]; then
    echo "Installing Next.js dependencies..."
    npm install
fi

echo "Next.js development environment ready"
echo "Run 'npm run dev' to start the development server"
```

### Go Projects

```bash
#!/bin/bash
# .ccbox/init.sh for Go projects

# Go environment settings
export GOPATH="${WORKSPACE_PATH}/.go"
export GOCACHE="${WORKSPACE_PATH}/.cache/go-build"
export GOMODCACHE="${WORKSPACE_PATH}/.cache/go-mod"
export PATH="${GOPATH}/bin:$PATH"

# Create Go directories
mkdir -p "${GOPATH}/bin" "${GOCACHE}" "${GOMODCACHE}"

# Auto-download dependencies
if [ -f "${WORKSPACE_PATH}/go.mod" ]; then
    echo "Downloading Go dependencies..."
    go mod download
fi

echo "Go development environment configured"
```

### Rust Projects

```bash
#!/bin/bash
# .ccbox/init.sh for Rust projects

# Rust environment settings
export CARGO_HOME="${WORKSPACE_PATH}/.cargo"
export RUSTUP_HOME="${WORKSPACE_PATH}/.rustup"
export PATH="${CARGO_HOME}/bin:$PATH"

# Create Rust directories
mkdir -p "${CARGO_HOME}" "${RUSTUP_HOME}"

# Auto-build dependencies
if [ -f "${WORKSPACE_PATH}/Cargo.toml" ]; then
    echo "Rust project detected"
    echo "Run 'cargo build' to compile dependencies"
fi

echo "Rust development environment configured"
```

## Multi-Language Projects

For projects that use multiple languages:

```bash
#!/bin/bash
# .ccbox/init.sh for multi-language projects

echo "Configuring multi-language environment..."

# Python setup
if [ -f "${WORKSPACE_PATH}/pyproject.toml" ] || [ -f "${WORKSPACE_PATH}/requirements.txt" ]; then
    echo "Setting up Python environment..."
    export PYTHONPATH="${WORKSPACE_PATH}:${PYTHONPATH}"
    
    # Poetry configuration if pyproject.toml exists
    if [ -f "${WORKSPACE_PATH}/pyproject.toml" ]; then
        export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"
        poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker" 2>/dev/null || true
    fi
fi

# Node.js setup
if [ -f "${WORKSPACE_PATH}/package.json" ]; then
    echo "Setting up Node.js environment..."
    export NODE_ENV=development
    export NPM_CONFIG_CACHE="${WORKSPACE_PATH}/.cache/npm"
fi

# Go setup
if [ -f "${WORKSPACE_PATH}/go.mod" ]; then
    echo "Setting up Go environment..."
    export GOPATH="${WORKSPACE_PATH}/.go"
    export PATH="${GOPATH}/bin:$PATH"
fi

# Rust setup
if [ -f "${WORKSPACE_PATH}/Cargo.toml" ]; then
    echo "Setting up Rust environment..."
    export CARGO_HOME="${WORKSPACE_PATH}/.cargo"
    export PATH="${CARGO_HOME}/bin:$PATH"
fi

echo "Multi-language environment configured"
```

## Custom Volume Mounts

### Common Mount Patterns

#### Development Environment
```bash
# .ccbox/mounts
# Mount shared development tools
MOUNT_TOOLS="/opt/dev-tools:/opt/dev-tools:ro"
MOUNT_SCRIPTS="/home/user/scripts:/workspace/scripts:cached"

# Mount shared libraries
MOUNT_SHARED_LIBS="/opt/shared-libs:/opt/shared-libs:ro"
```

#### Data Science Projects
```bash
# .ccbox/mounts
# Mount large datasets (read-only for safety)
MOUNT_DATASETS="/mnt/datasets:/data/datasets:ro"
MOUNT_MODELS="/mnt/models:/data/models:ro"

# Mount model outputs (read-write)
MOUNT_OUTPUTS="/mnt/outputs:/data/outputs:rw"

# Mount Jupyter notebooks (cached for performance)
MOUNT_NOTEBOOKS="/home/user/notebooks:/workspace/notebooks:cached"

# Mount shared data science tools
MOUNT_CONDA="/opt/conda:/opt/conda:ro"
```

#### Multi-Project Development
```bash
# .ccbox/mounts
# Mount related projects
MOUNT_PROJECT_A="/home/user/project-a:/workspace/project-a:cached"
MOUNT_PROJECT_B="/home/user/project-b:/workspace/project-b:cached"
MOUNT_SHARED="/home/user/shared:/workspace/shared:cached"

# Mount shared configuration
MOUNT_CONFIG="/home/user/.config/shared:/workspace/.config:ro"
```

#### Cache Optimization
```bash
# .ccbox/mounts
# Mount language-specific caches
MOUNT_NPM_CACHE="/home/user/.npm:/home/user/.npm:cached"
MOUNT_PIP_CACHE="/home/user/.cache/pip:/home/user/.cache/pip:cached"
MOUNT_CARGO_CACHE="/home/user/.cargo:/home/user/.cargo:cached"
MOUNT_GO_CACHE="/home/user/.cache/go:/home/user/.cache/go:cached"

# Mount package managers
MOUNT_POETRY_CACHE="/home/user/.cache/poetry:/home/user/.cache/poetry:cached"
```

## Best Practices

### Security

1. **Read-Only Mounts**: Use `:ro` for data directories and external tools
2. **No Secrets in Config**: Never put API keys or passwords in `.ccbox/` files
3. **Minimal Permissions**: Only mount what you need with minimal access
4. **Git Ignore**: Always add `.ccbox/` to `.gitignore`

### Performance

1. **Use Cached Mounts**: Add `:cached` for frequently accessed directories on macOS
2. **Optimize Cache Directories**: Mount package manager caches to persist between runs
3. **Avoid Deep Nesting**: Keep mount paths simple and flat
4. **Separate Build Artifacts**: Use container-specific directories for build outputs

### Portability

1. **Environment Variables**: Use `${WORKSPACE_PATH}` for relative paths
2. **Conditional Setup**: Check for project files before configuring tools
3. **Documentation**: Document your setup in a team README
4. **Version Control**: Keep configuration files small and focused

### Troubleshooting

#### Common Issues

**init.sh not executing**:
```bash
# Make sure it's executable
chmod +x .ccbox/init.sh

# Check for syntax errors
bash -n .ccbox/init.sh
```

**Mounts not appearing**:
```bash
# Verify file format
cat .ccbox/mounts

# Check if host paths exist
ls -la /host/path

# Restart container
ccdk restart
```

**Permission issues**:
```bash
# Check ownership
ls -la /host/path

# Verify user ID in container
ccdk shell id
```

**Environment variables not set**:
```bash
# Source the file manually to test
source .ccbox/init.sh

# Check for errors in the script
bash -x .ccbox/init.sh
```

## Examples by Project Type

### Full-Stack Web Application

```bash
#!/bin/bash
# .ccbox/init.sh for full-stack web app

# Backend (Python/Django)
if [ -f "${WORKSPACE_PATH}/backend/manage.py" ]; then
    echo "Setting up Django backend..."
    cd "${WORKSPACE_PATH}/backend"
    export DJANGO_SETTINGS_MODULE="myapp.settings.development"
    export DATABASE_URL="postgresql://dev:dev@localhost:5432/myapp_dev"
    
    # Setup virtual environment
    export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/backend/.venv-docker"
    poetry config virtualenvs.path "${WORKSPACE_PATH}/backend/.venv-docker"
fi

# Frontend (React)
if [ -f "${WORKSPACE_PATH}/frontend/package.json" ]; then
    echo "Setting up React frontend..."
    cd "${WORKSPACE_PATH}/frontend"
    export NODE_ENV=development
    export REACT_APP_API_URL="http://localhost:8000"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        npm install
    fi
fi

# Return to workspace root
cd "${WORKSPACE_PATH}"
echo "Full-stack development environment ready"
```

### Machine Learning Project

```bash
#!/bin/bash
# .ccbox/init.sh for ML project

# Python/Poetry setup for ML
export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/.venv-docker"
poetry config virtualenvs.path "${WORKSPACE_PATH}/.venv-docker"

# ML-specific environment variables
export CUDA_VISIBLE_DEVICES=0
export TENSORFLOW_LOG_LEVEL=2
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Jupyter configuration
export JUPYTER_CONFIG_DIR="${WORKSPACE_PATH}/.jupyter"
export JUPYTER_DATA_DIR="${WORKSPACE_PATH}/.jupyter/data"

# Create necessary directories
mkdir -p "${JUPYTER_CONFIG_DIR}" "${JUPYTER_DATA_DIR}"
mkdir -p "${WORKSPACE_PATH}/data" "${WORKSPACE_PATH}/models" "${WORKSPACE_PATH}/outputs"

echo "Machine learning environment configured"
echo "Data directory: ${WORKSPACE_PATH}/data"
echo "Models directory: ${WORKSPACE_PATH}/models"
echo "Outputs directory: ${WORKSPACE_PATH}/outputs"
```

### Microservices Project

```bash
#!/bin/bash
# .ccbox/init.sh for microservices

# Service discovery
export CONSUL_HTTP_ADDR="http://localhost:8500"
export EUREKA_SERVER_URL="http://localhost:8761"

# Database URLs
export USER_SERVICE_DB="postgresql://dev:dev@localhost:5433/users"
export ORDER_SERVICE_DB="postgresql://dev:dev@localhost:5434/orders"
export INVENTORY_SERVICE_DB="postgresql://dev:dev@localhost:5435/inventory"

# Message queue
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
export REDIS_URL="redis://localhost:6379"

# Configure each service
for service in user-service order-service inventory-service; do
    if [ -d "${WORKSPACE_PATH}/${service}" ]; then
        echo "Configuring ${service}..."
        
        # Each service might have different setup requirements
        if [ -f "${WORKSPACE_PATH}/${service}/pyproject.toml" ]; then
            # Python service
            cd "${WORKSPACE_PATH}/${service}"
            export POETRY_VIRTUALENVS_PATH="${WORKSPACE_PATH}/${service}/.venv-docker"
            poetry config virtualenvs.path "${WORKSPACE_PATH}/${service}/.venv-docker"
        elif [ -f "${WORKSPACE_PATH}/${service}/package.json" ]; then
            # Node.js service
            cd "${WORKSPACE_PATH}/${service}"
            if [ ! -d "node_modules" ]; then
                npm install
            fi
        fi
    fi
done

cd "${WORKSPACE_PATH}"
echo "Microservices environment configured"
```

## Team Collaboration

### Shared Configuration

Create a team-specific configuration that team members can extend:

```bash
#!/bin/bash
# .ccbox/init.sh - Team shared configuration

# Load team-wide defaults
if [ -f "${WORKSPACE_PATH}/.ccbox/team-defaults.sh" ]; then
    source "${WORKSPACE_PATH}/.ccbox/team-defaults.sh"
fi

# Load personal overrides (git-ignored)
if [ -f "${WORKSPACE_PATH}/.ccbox/personal.sh" ]; then
    source "${WORKSPACE_PATH}/.ccbox/personal.sh"
fi
```

### Documentation

Create a README for your team:

```markdown
# .ccbox/README.md

## Project Environment Setup

This project uses .ccbox for workspace configuration.

### Quick Start
1. Copy the example configuration: `cp .ccbox/init.example.sh .ccbox/init.sh`
2. Edit `.ccbox/mounts` to add any personal mounts
3. Run `ccdk run` to start with the configured environment

### Available Configurations
- `init.sh` - Main initialization script
- `mounts` - Custom volume mounts
- `team-defaults.sh` - Shared team configuration
- `personal.sh` - Personal overrides (git-ignored)

### Environment Variables
- `PROJECT_ENV` - Set to "development" by default
- `DATABASE_URL` - Points to local PostgreSQL
- `API_KEY` - Load from your personal.sh file

### Troubleshooting
- Run `source .ccbox/init.sh` to test configuration
- Check `ccdk logs` for container issues
- Ensure all host paths in mounts exist
```

This comprehensive guide provides everything needed to configure workspace-specific environments for any project type while maintaining security, performance, and team collaboration best practices.