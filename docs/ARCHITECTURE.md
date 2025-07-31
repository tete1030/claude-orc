# Orchestrator Architecture

## Overview

The Claude Multi-Agent Orchestrator is designed to enable multiple Claude AI instances to communicate and collaborate through a centralized message routing system. The architecture emphasizes simplicity, reliability, and real-time monitoring.

### Dual-Plane Architecture

- **Control Plane (Tmux I/O)**: Direct monitoring and control of agents through tmux panes. Used for system management, emergency interrupts, and real-time observation.
- **Data Plane (MCP Mailbox)**: Efficient agent-to-agent communication using MCP tools. Eliminates polling overhead and provides structured message passing.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCPOrchestrator                          │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │   Agent     │  │   Agent     │  │   Message         │  │
│  │  Registry   │  │  Lifecycle  │  │   Router          │  │
│  └─────────────┘  └─────────────┘  └───────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │             MCP Mailbox Server (Data Plane)         │   │
│  │  • mailbox_send  • mailbox_check  • list_agents    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐    ┌────────▼────────┐    ┌───────▼────────┐
│  TmuxManager   │    │ SessionMonitor  │    │ SimpleLauncher │
│  (Control)     │    │   (Legacy)      │    │  (+ MCP Config)│
│ - Session Mgmt │    │ - File Watching │    │ - Claude Start │
│ - Direct I/O   │    │ - Cmd Extraction│    │ - Session IDs  │
└────────────────┘    └─────────────────┘    └────────────────┘
        │                                             │
        └─────────────────────┬───────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Claude Sessions  │
                    │  ┌──────┬──────┐  │
                    │  │Tmux  │ MCP  │  │
                    │  │ I/O  │Tools │  │
                    │  └──────┴──────┘  │
                    └────────────────────┘
```

## Core Components

### 1. Orchestrator (`src/orchestrator.py`)

The central coordinator that manages the entire system:

- **Agent Registry**: Maintains a registry of all active agents with their configurations
- **Message Router**: Routes messages between agents using MCP tools
- **Mailbox System**: Queues messages for agents until they check their mailbox
- **Lifecycle Management**: Handles agent startup, monitoring, and shutdown

Key responsibilities:
- Starting tmux sessions and launching Claude instances
- Monitoring session files for commands
- Parsing and routing messages
- Managing agent mailboxes
- Handling system shutdown

### 2. TmuxManager (`src/tmux_manager.py`)

Handles all tmux-related operations:

- **Session Management**: Creates and destroys tmux sessions
- **Pane Control**: Creates panes for each agent
- **Command Execution**: Sends commands to specific panes
- **Screen Capture**: Can capture pane content for debugging

Key features:
- Automatic session creation with configurable pane layout
- Reliable command sending with proper Enter key handling
- Pane title management for easy identification

### 3. SessionMonitor (`src/session_monitor.py`) - LEGACY

**Note**: Being phased out in favor of MCP mailbox for agent communication.

Watches Claude session files for commands:

- **File Monitoring**: Continuously reads JSONL session files
- **State Detection**: Monitors agent activity states (busy/idle/error)
- **Intelligent Delivery**: Sends notifications when agents are ready
- **Incremental Reading**: Only processes new messages

### 4. MCP Mailbox Server (`src/mcp_mailbox_server.py`) - NEW

Provides MCP tools for efficient agent communication:

- **Direct API**: No polling, agents call tools directly
- **Structured Messages**: JSON format with schema validation
- **Async Operations**: Non-blocking message operations
- **Tool Registry**: `mailbox_send`, `mailbox_check`, `mailbox_list_agents`

Key benefits:
- Eliminates 0.5s polling delay
- Reduces CPU usage (no file watching)
- Provides better error handling
- Natural integration with Claude's tool use

### 5. SimpleLauncher (`src/simple_launcher.py`)

Manages Claude instance launching:

- **Session ID Generation**: Creates unique UUIDs for each agent
- **Command Building**: Constructs proper Claude CLI commands
- **System Prompt Integration**: Passes agent prompts via `--append-system-prompt`
- **MCP Configuration**: Optionally adds MCP config for mailbox tools

## Data Flow

### Control Plane Flow

1. **System Management**
```
Orchestrator → TmuxManager → Direct pane I/O → Agent
```

2. **Emergency Interrupts**
```
User presses ESC → Tmux captures → Sent to agent pane → Agent responds
```

3. **Monitoring**
```
Agent output → Tmux pane → Visible to operator
```

### Data Plane Flow (MCP)

1. **Agent Registration**
```
User Code → MCPOrchestrator.register_agent() → Agent object + MCP config
```

2. **System Startup**
```
MCPOrchestrator.start() → Enable MCP server → Launch agents with MCP tools
```

3. **Message Flow**
```
Agent uses mailbox_send tool → MCP server → Message added to recipient's mailbox
```

4. **Message Delivery**
```
Agent uses mailbox_check tool → MCP server → Messages returned as JSON
```

## Session Management

### Session Files

Claude stores session data in JSONL files:
- Location: `~/.claude/projects/<escaped-cwd>/<session-id>.jsonl`
- Format: JSON Lines with timestamped entries
- Content: User inputs, assistant responses, system events

### Session ID Strategy

The orchestrator uses pre-generated UUIDs:
- Predictable session file locations
- No need for complex session discovery
- Stable across restarts with `--resume`

## Message Protocol

### Control Plane Messages (Tmux)

- System initialization
- Emergency interrupts (ESC key)
- Recovery commands
- Direct operator instructions
- Error notifications

### Data Plane Messages (MCP Tools)

#### Tool: `mailbox_send`
```json
{
  "to": "target_agent",
  "title": "Task Assignment",
  "content": "Please analyze dataset X",
  "priority": "normal|high|low"
}
```

#### Tool: `mailbox_check`
Returns array of messages with sender, title, content, timestamp.

#### Tool: `mailbox_list_agents`
Returns list of active agents and their status.

### Message Features

1. Case-insensitive agent name matching
2. Mailbox queuing for async delivery
3. Priority support with notifications
4. Structured JSON format

## Threading Model

The orchestrator uses a multi-threaded approach:

1. **Main Thread**: Handles orchestrator lifecycle and user interaction
2. **Monitor Threads**: One per agent, watching session files
3. **Command Processing**: Synchronous processing with thread-safe mailboxes

## Error Handling

### Graceful Degradation
- Missing agents: Messages queued until agent available
- File errors: Retry with exponential backoff
- Tmux failures: Clear error messages with recovery suggestions

### Robustness Features
- Agent state detection and monitoring
- Intelligent message queueing and delivery
- Automatic session cleanup on exit
- Comprehensive logging throughout

## Security Considerations

1. **Session Isolation**: Each agent runs in its own tmux pane
2. **No Direct Execution**: Commands are text-based, not executed
3. **Controlled Communication**: Only through MCP tools and protocols
4. **Local Only**: No network communication in base implementation

## Performance Characteristics

- **Polling Interval**: Configurable (default 0.5s)
- **Message Latency**: Typically under 1 second
- **Memory Usage**: Minimal, only queued messages in memory
- **CPU Usage**: Low, mostly idle between polls

## Future Architecture Considerations

### Recently Implemented
1. **Complete MCP Migration**: All communication now through MCP tools
2. **Intelligent Notifications**: Direct tmux TUI delivery when agents are idle
3. **Agent State Detection**: Monitors busy/idle/error states for optimal delivery
4. **Agent Presence**: Heartbeat monitoring via MCP

### Planned Enhancements
1. **Distributed Orchestration**: Multiple orchestrator instances
2. **Web UI**: Real-time monitoring dashboard (control plane view)
3. **Hook System**: Extensibility through plugins
4. **Message History**: Audit trail for compliance

### Scalability Path
1. **Message Queue**: Replace in-memory with Redis/RabbitMQ
2. **MCP Gateway**: Central MCP router for many agents
3. **Agent Pools**: Dynamic agent spawning with MCP pre-configured
4. **Load Balancing**: Distribute agents across machines