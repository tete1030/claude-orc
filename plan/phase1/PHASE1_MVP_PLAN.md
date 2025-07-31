# Phase 1 MVP: Two-Agent Interaction System

## Overview

Phase 1 focuses on establishing the fundamental infrastructure for two agents (Master and Worker) to interact through our orchestration service. This MVP proves the core concepts before scaling to multiple agents.

## Scope

### What's Included
- Basic orchestration service with essential commands
- Two-agent setup: Master Agent and Worker Agent
- Session file monitoring for command detection
- Simple message passing between agents
- Basic tmux management (create panes, send keys)
- Identity prefixing for role clarity

### What's NOT Included (Phase 2+)
- Multiple worker agents
- Complex communication rules
- Context compaction
- Mailbox system
- Hook-based status display
- Agent spawning/termination commands
- Global bulletin board

## Architecture (Simplified)

```
┌─────────────────────────────────────────┐
│       ORCHESTRATION SERVICE (MVP)        │
│  ┌──────────────────────────────────┐   │
│  │    Command Parser (Basic)        │   │
│  │  - Detect <orc-command>          │   │
│  │  - Parse send_message only       │   │
│  └────────────┬─────────────────────┘   │
│               │                          │
│  ┌────────────▼─────────────────────┐   │
│  │    Tmux Controller               │   │
│  │  - Send messages via send-keys   │   │
│  │  - Basic pane management         │   │
│  └──────────────────────────────────┘   │
└───────────────┬─────────────────────────┘
                │
       ┌────────▼────────┐
       │  Master Agent   │ ←→ │  Worker Agent  │
       │   (Claude)      │    │   (Claude)     │
       └─────────────────┘    └────────────────┘
```

## Implementation Components

### 1. Core Orchestrator (`orchestrator.py`)
```python
# Minimal viable orchestrator
class Orchestrator:
    def __init__(self):
        self.agents = {}  # agent_name -> pane_id
        self.session_monitors = {}
        
    def start(self):
        # Start monitoring session files
        # Process detected commands
        
    def process_command(self, command):
        # Handle send_message commands only in Phase 1
```

### 2. Session Monitor (`session_monitor.py`)
```python
# Watch Claude session files for commands
class SessionMonitor:
    def __init__(self, session_path, agent_name):
        self.session_path = session_path
        self.agent_name = agent_name
        self.last_position = 0
        
    def check_for_commands(self):
        # Read new content
        # Extract <orc-command> blocks
        # Return parsed commands
```

### 3. Tmux Manager (`tmux_manager.py`)
```python
# Basic tmux operations
class TmuxManager:
    def create_pane(self, window_name):
        # Create new tmux pane
        
    def send_to_pane(self, pane_id, message):
        # Send message via tmux send-keys
        
    def list_panes(self):
        # Get current pane list
```

### 4. Command Types (Phase 1 - Limited Set)

#### Send Message (Only command for Phase 1)
```xml
<orc-command type="send_message">
  <from>master_agent</from>
  <to>worker_agent</to>
  <title>Task assignment</title>
  <content>Please analyze the codebase structure</content>
</orc-command>
```

## Setup Scripts

### 1. `setup_agents.sh`
```bash
#!/bin/bash
# Create tmux session with two panes
# Launch Master Agent in pane 0
# Launch Worker Agent in pane 1
# Start orchestrator monitoring both
```

### 2. Agent Prompts

**Master Agent Prompt:**
```
You are the Master Agent in a two-agent system. 
Your role is to coordinate tasks and communicate with the Worker Agent.

To send messages, use:
<orc-command type="send_message">
  <from>master_agent</from>
  <to>worker_agent</to>
  <title>Brief description</title>
  <content>Your message</content>
</orc-command>

Messages from Worker will appear as:
[FROM: Worker Agent] Message content
```

**Worker Agent Prompt:**
```
You are the Worker Agent in a two-agent system.
Your role is to execute tasks assigned by the Master Agent.

To send messages, use:
<orc-command type="send_message">
  <from>worker_agent</from>
  <to>master_agent</to>
  <title>Brief description</title>
  <content>Your message</content>
</orc-command>

Messages from Master will appear as:
[FROM: Master Agent] Message content
```

## File Structure

```
multi-agent-system/
├── orchestrator.py          # Main orchestration service
├── session_monitor.py       # Session file watcher
├── tmux_manager.py         # Tmux control wrapper
├── config.yaml             # Configuration (paths, agent names)
├── prompts/
│   ├── master_agent.txt    # Master agent prompt
│   └── worker_agent.txt    # Worker agent prompt
├── scripts/
│   ├── setup_agents.sh     # Initialize two-agent system
│   └── cleanup.sh          # Clean up tmux sessions
└── logs/
    └── orchestrator.log    # Service logs
```

## Testing Plan

### 1. Basic Communication Test
- Master sends task to Worker
- Worker acknowledges and executes
- Worker reports completion to Master
- Verify messages appear with correct identity prefixes

### 2. Session Monitoring Test
- Verify orchestrator detects commands in real-time
- Test command parsing accuracy
- Ensure no duplicate processing

### 3. Error Handling Test
- Invalid command format
- Non-existent target agent
- Tmux communication failures

## Success Criteria

1. **Two agents can exchange messages** through orchestrator
2. **Identity prefixes work correctly** - agents know who's talking
3. **Commands are detected and processed** within 2 seconds
4. **No direct tmux manipulation** by agents
5. **Clean logs** showing all communications

## Development Steps

1. **Set up basic file structure** (30 min)
2. **Implement tmux_manager.py** - basic operations (1 hour)
3. **Create session_monitor.py** - detect commands (2 hours)
4. **Build orchestrator.py** - command processing (2 hours)
5. **Write setup scripts** - initialize agents (1 hour)
6. **Test two-agent communication** (1 hour)
7. **Fix issues and refine** (1 hour)

**Total estimate: ~8 hours**

## Limitations (Addressed in Phase 2)

- Only two agents (master and worker)
- Only send_message command
- No persistence across restarts
- No mailbox - only direct delivery
- No communication rules/restrictions
- Basic error handling only

## Next Steps (Phase 2 Preview)

- Add multiple worker agents
- Implement mailbox system
- Add more command types
- Communication rules engine
- Agent lifecycle management
- Persistent state management