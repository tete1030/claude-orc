# Claude Multi-Agent Orchestrator

A standalone multi-agent orchestration system for Claude that enables real-time communication and coordination between multiple Claude instances using tmux and Model Context Protocol (MCP).

> **Important**: Claude requires authentication when launched programmatically. The system uses Docker containers for isolated Claude instances. See [DOCKER_MCP_SUMMARY.md](DOCKER_MCP_SUMMARY.md) for implementation details.

## Overview

This orchestrator enables multiple Claude agents to work together by:
- **MCP Integration**: Pure MCP tool-based communication (no XML commands needed!)
- **Intelligent Message Delivery**: Detects agent states (busy/idle) and delivers messages at optimal times
- **Real-time Communication**: Agents can send messages to each other asynchronously
- **Session Management**: Each agent runs in its own tmux pane with a unique session ID
- **Message Routing**: Central MCP server handles all agent communication
- **Smart Notifications**: Automatically notifies idle agents about new messages
- **Message Queueing**: Holds messages for busy agents until they're ready

## Key Features

- **Agent State Detection**: Monitors tmux panes to detect when agents are busy, idle, or have errors
- **Intelligent Notifications**: Sends messages directly to agent TUI when they're idle and ready
- **Message Queueing**: Holds messages for busy agents and delivers when they become available
- **Team Context Persistence**: Team contexts survive container restarts and system reboots
- **Docker Integration**: Runs agents in isolated containers with shared communication directory
- **Model Selection**: Choose Claude model via command line (defaults to Sonnet)
- **Debug Control**: Enable/disable debug mode as needed
- **Clean Architecture**: Modular design with clear separation of concerns

## Installation

1. Prerequisites:
   - Python 3.8+
   - Poetry (install with `curl -sSL https://install.python-poetry.org | python3 -`)
   - tmux installed (`sudo apt install tmux` or `brew install tmux`)
   - Claude CLI installed and configured
   - Docker and Docker Compose (for isolated agent environments)

2. Install dependencies:
   ```bash
   cd orchestrator
   poetry install         # Install all dependencies including dev
   # or
   poetry install --only main  # Install only production dependencies
   ```

3. Install utilities:
   ```bash
   # Install claude-bg (background process manager)
   ./scripts/install-claude-bg.sh
   
   # Install ccdk (Docker Claude Code manager)
   ./scripts/install-ccdk.sh
   
   # Install ccorc (team context management)
   ./scripts/install-ccorc.sh
   ```

## Quick Start

### Launch a Pre-Configured Team

Get started with team-based configuration in seconds:

```bash
# List available teams
ccorc teams list

# Launch the DevOps team
ccorc launch --team devops-team

# Launch with custom session name
ccorc launch --team devops-team --session my-project
```

This launches a complete team (Architect, Developer, QA, DevOps, Docs) with intelligent message delivery, agent state detection, and automatic notifications.

### Team Configuration

Create teams using YAML configuration files:

```yaml
# teams/my-team.yaml
team:
  name: "My Team"
  description: "Custom team configuration"

agents:
  - name: "Lead"
    role: "Team Lead"
    model: "sonnet"
  - name: "Developer"
    role: "Implementation Engineer"
    model: "sonnet"

settings:
  default_context_name: "my-team"
  orchestrator_type: "enhanced"
```

Launch your custom team:
```bash
ccorc launch --team my-team
```

### Persistent Team Contexts

Teams automatically create persistent contexts that survive restarts:

```bash
# List active team contexts
ccorc list

# Get detailed team status
ccorc info my-project

# Clean up when done
ccorc clean my-project
```

See the [Team Configuration Guide](docs/TEAM_CONFIGURATION.md) for complete details on creating custom teams.

### Basic Example (Requires Authentication)

```python
from src.orchestrator import Orchestrator, OrchestratorConfig
from src.mcp_central_server import CentralMCPServer

# Create orchestrator
config = OrchestratorConfig(
    session_name="demo-agents",
    poll_interval=0.5
)
orchestrator = Orchestrator(config)

# Register agents
orchestrator.register_agent(
    name="Alice",
    session_id="alice-001",
    system_prompt="""You are Alice. Use these MCP tools:
    - list_agents: See all agents
    - send_message: Send to specific agent (params: to, message)
    - check_messages: Check your inbox
    - broadcast_message: Send to all agents
    
    Please list agents and send a greeting to Bob."""
)

orchestrator.register_agent(
    name="Bob",
    session_id="bob-001",
    system_prompt="""You are Bob. Use these MCP tools:
    - list_agents: See all agents
    - send_message: Send to specific agent (params: to, message)
    - check_messages: Check your inbox
    
    Please check messages regularly and respond."""
)

# Start MCP server
mcp_server = CentralMCPServer(orchestrator, port=8767)
await mcp_server.start()

# Start orchestrator with MCP
if orchestrator.start(mcp_port=8767):
    print("Orchestrator started!")
    print("View agents: tmux attach -t demo-agents")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        orchestrator.stop()
```

## MCP Tools Available

With MCP integration, agents use native tools instead of XML commands:

### Send Message
```xml
<orc-command name="send_message" from="AgentName" to="RecipientName" title="Title" priority="normal">
Message content here
</orc-command>
```

### Check Mailbox
```xml
<orc-command name="mailbox_check"></orc-command>
```

The orchestrator also supports the legacy format:
```xml
<orc-command type="send_message">
  <from>AgentName</from>
  <to>RecipientName</to>
  <title>Title</title>
  <content>Message content</content>
  <priority>normal</priority>
</orc-command>
```

## Architecture

### Core Components

- **Orchestrator** (`src/orchestrator.py`): Main coordinator managing agents and message routing
- **TmuxManager** (`src/tmux_manager.py`): Handles tmux session and pane operations
- **SessionMonitor** (`src/session_monitor.py`): Watches Claude session files for commands
- **SimpleLauncher** (`src/simple_launcher.py`): Launches Claude with pre-generated session IDs

### How It Works

1. **Agent Registration**: Each agent is registered with a name, system prompt, and configuration
2. **Session Creation**: Tmux panes are created and Claude is launched with unique session IDs
3. **Command Monitoring**: Session files are continuously monitored for XML commands
4. **Message Routing**: Commands are parsed and messages are delivered to agent mailboxes
5. **Mailbox Delivery**: When agents check their mailbox, queued messages are sent to them

## Configuration

The `OrchestratorConfig` class supports:

- `session_name`: Tmux session name (default: "claude-agents")
- `poll_interval`: How often to check for new messages (default: 0.5 seconds)

## Testing

Run the test suite:
```bash
poetry run pytest
# or
poetry run ./scripts/run_tests.sh
```

## Examples

### Pre-Built Teams

Explore the `examples/teams/` directory for ready-to-use team configurations:
- `devops-team/`: Complete DevOps team (Architect, Developer, QA, DevOps, Docs)
- `security-team/`: Cybersecurity team (Security Architect, Security Analyst, Developer, QA)
- `data-team/`: Data engineering team (Data Architect, Data Engineer, ML Engineer, Analyst)

### Utility Scripts

See the `examples/` directory for:
- `verify_claude_setup.py`: Verify Claude CLI is properly installed

## Project Structure

```
orchestrator/
├── src/
│   ├── orchestrator.py          # Main orchestrator
│   ├── orchestrator_enhanced.py # Enhanced orchestrator with state monitoring
│   ├── tmux_manager.py          # Tmux operations
│   ├── mcp_central_server.py    # MCP server for agent communication
│   ├── team_context_manager.py  # Team context persistence
│   ├── team_config_loader.py    # YAML/JSON team configuration
│   ├── services/                # Refactored service components
│   │   ├── container_discovery_service.py  # Docker container discovery
│   │   ├── container_health_service.py     # Container health checks
│   │   ├── context_cleanup_service.py      # Context cleanup operations
│   │   ├── context_persistence_service.py  # Context save/load operations
│   │   ├── layout_detection_service.py     # Smart terminal layout detection
│   │   ├── mcp_server_manager.py          # MCP server lifecycle management
│   │   ├── orchestrator_factory.py        # Orchestrator configuration factory
│   │   ├── port_discovery_service.py      # Available port discovery
│   │   ├── signal_handler_service.py      # Graceful shutdown handling
│   │   ├── team_launch_service.py         # Team launching orchestration
│   │   └── tmux_management_service.py     # Tmux session management
│   └── cli/                     # CLI command implementations
│       ├── base_command.py      # Abstract command base class
│       ├── command_registry.py  # Command registration and dispatch
│       └── *_command.py         # Individual command implementations
├── bin/
│   ├── ccorc                   # Team context management CLI
│   ├── ccdk                    # Docker container management
│   └── claude-bg               # Background process manager
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── examples/
│   └── teams/                  # Pre-configured team examples
│       ├── devops-team/        # 5-agent DevOps team
│       ├── security-team/      # Security analysis team
│       └── data-team/          # Data engineering team
├── docs/                       # Documentation
└── scripts/                    # Utility scripts
```

## Docker Environment (CCBox)

The orchestrator includes CCBox (Claude Code Box) - a Docker environment for running isolated Claude instances.

### Basic Usage
```bash
# Build the Docker image
ccdk build

# Run Claude in temporary container
ccdk run

# Start persistent container
ccdk start
```

### Custom Volume Mounts
Create a `.ccbox/mounts` file to add custom mounts:

```bash
# Example .ccbox/mounts
MOUNT_DATA="/path/to/data:/mnt/data:ro"
MOUNT_CACHE="/home/user/.cache:/workspace/.cache:cached"
```

See [docker/claude-code/README.md](docker/claude-code/README.md) for detailed Docker documentation and [docs/CCDK_USAGE.md](docs/CCDK_USAGE.md) for ccdk command reference.

## Troubleshooting

### Messages not being delivered
- Agent names are case-insensitive but must match registered names
- Check that agents are outputting XML commands in their responses
- Verify session files are being created in `~/.claude/projects/`

### Claude not starting
- Verify Claude CLI is installed: `which claude`
- Check that Claude can start manually: `claude chat`
- Look for errors in tmux panes: `tmux attach -t <session-name>`

## License

[Your license here]