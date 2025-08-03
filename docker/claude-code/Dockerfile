# Claude Code Development Environment (CCBox)
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
# TZ will be inherited from the host environment at runtime

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic tools
    curl \
    wget \
    git \
    vim \
    nano \
    sudo \
    build-essential \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release \
    # Required for pyenv to build Python
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    # Required for some Python packages
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    # Required for data processing
    libhdf5-dev \
    libatlas-base-dev \
    gfortran \
    # Required for timezone handling
    tzdata \
    # Process management
    supervisor \
    htop \
    # Network tools
    iputils-ping \
    net-tools \
    # Additional development tools
    jq \
    tree \
    tmux \
    screen \
    postgresql-client \
    redis-tools \
    bc \
    # File system monitoring
    inotify-tools \
    # Database tools
    sqlite3 \
    # Performance monitoring
    iotop \
    sysstat \
    # For dynamic user switching
    gosu \
    # Locale support
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 locale since it's commonly used
RUN locale-gen en_US.UTF-8

# Set C.UTF-8 as default locale - this is lightweight and prevents warnings
# The actual locale values will be inherited from the host environment
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install Playwright browser dependencies
RUN apt-get update && apt-get install -y \
    # Core browser dependencies
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libwayland-client0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    # Additional browser support
    ffmpeg \
    libcairo-gobject2 \
    libdbus-glib-1-2 \
    libfontconfig1 \
    libfreetype6 \
    libgdk-pixbuf-2.0-0 \
    libgtk-3-0 \
    libpangocairo-1.0-0 \
    libx11-xcb1 \
    libxcb-shm0 \
    libxcursor1 \
    libxi6 \
    libxrender1 \
    libxtst6 \
    # Fonts for proper rendering
    fonts-noto-color-emoji \
    fonts-unifont \
    xfonts-cyrillic \
    xfonts-scalable \
    fonts-liberation \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-tlwg-loma-otf \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (LTS) for Claude Code
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Install Docker CLI for potential Docker-in-Docker operations
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install gh -y \
    && rm -rf /var/lib/apt/lists/*

# Install pyenv to manage Python versions
ENV PYENV_ROOT="/opt/pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

RUN git clone https://github.com/pyenv/pyenv.git $PYENV_ROOT \
    && cd $PYENV_ROOT && src/configure && make -C src

# Install Python 3.12.11 using pyenv
RUN eval "$(pyenv init -)" \
    && pyenv install 3.12.11 \
    && pyenv global 3.12.11

# Update PATH to use pyenv Python
ENV PATH="$PYENV_ROOT/shims:$PATH"

# Install Poetry for dependency management
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV POETRY_VERSION=1.7.1
ENV POETRY_NO_INTERACTION=1

RUN curl -sSL https://install.python-poetry.org | python3 -


# Install Claude Code globally (as root for system-wide access)
# Note: The local auto-updating version at ~/.claude/local will be prioritized if available
RUN npm install -g @anthropic-ai/claude-code

# Don't create workspace or set working directory - will be handled at runtime
# Python virtual environment location will be set dynamically

# Copy claude-bg for background process management
COPY bin/claude-bg /usr/local/bin/claude-bg
RUN chmod +x /usr/local/bin/claude-bg

# Copy ccdk for Docker container management
COPY bin/ccdk /usr/local/bin/ccdk
RUN chmod +x /usr/local/bin/ccdk

# Copy entrypoint script
# Copy container scripts
COPY docker/claude-code/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/claude-code/session-monitor-daemon.sh /usr/local/bin/session-monitor-daemon.sh
COPY docker/claude-code/run-command-with-env.sh /usr/local/bin/run-command-with-env.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chmod +x /usr/local/bin/session-monitor-daemon.sh \
    && chmod +x /usr/local/bin/run-command-with-env.sh

# Expose common ports
EXPOSE 8000 8080 3000 5000 5001

# Set entrypoint and default command
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
# For persistent containers, just keep it running
CMD ["tail", "-f", "/dev/null"]
