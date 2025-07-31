# Multi-Agent Management System Design

## Project Overview

A tmux-based multi-agent management system for Claude-Code that provides real-time monitoring, coordination, and control of multiple AI agents working on software development tasks.

## Key Design Decisions

### 1. Using Claude-Code's Interactive TUI
- **Decision**: Keep agents running in Claude's native TUI rather than using SDK/pipe mode
- **Rationale**: 
  - Simplified implementation - no need to build custom TUI
  - Agents get full Claude interface (thinking indicators, formatting)
  - Session files still capture complete history
  - Visual debugging through tmux panes

### 2. Session File Monitoring
- **Decision**: Monitor Claude's session files instead of tmux pane content
- **Rationale**:
  - Claude's TUI overwrites content dynamically
  - Session files contain complete, unfiltered history
  - Includes all tool calls, responses, and system messages
  - Better for detecting patterns and extracting insights

### 3. Long-Lived Agent Sessions
- **Decision**: Keep agent sessions running indefinitely with active management
- **Features**:
  - Context compaction when approaching limits
  - Session reset capabilities
  - State preservation across resets
  - Summary generation for continuity

### 4. Master-Agent Architecture
- **Decision**: Single master controller with multiple specialized sub-agents
- **Communication**: 
  - Initial setup via CLI prompt options (exact syntax TBD)
  - Multiple input channels: interrupts, mailbox, and hooks
  - Output monitoring via session file watching
  - Identity prefixing to prevent role confusion
  - Bidirectional but asynchronous

### 5. Multi-Channel Communication System
- **Three Input Channels**:
  1. **Interrupts** (High Priority): ESC via tmux for emergencies
  2. **Mailbox** (Normal Priority): Agents poll for messages/events
  3. **Hooks** (Continuous): Status display via Claude-code hooks
- **Agent Autonomy**: Agents can choose to ignore non-critical messages
- **Global Bulletin**: Shared system status visible to all agents

### 6. Specialized Agent Prompts via CLI Options
- **Decision**: Use Claude's prompt capability to append role-specific instructions (exact CLI syntax TBD)
- **Rationale**:
  - Each agent (including master) gets focused, task-specific prompts
  - Maintains agent specialization without complex prompt engineering
  - Better than official sub-agent design where master lacks focus
  - Enables clear role boundaries and responsibilities
- **Implementation**:
  - Each agent type gets specific role instructions
  - Prompts include communication protocol for identity management

### 7. Identity Management via Message Prefixing
- **Decision**: Use message prefixes to identify sender in multi-agent conversations
- **Problem**: Claude sees all input as "user" regardless of actual sender
- **Solution**: 
  - Prefix all messages with `[FROM: Agent Name]`
  - Train agents via prompt to recognize and use prefixes
  - Enables agents to understand conversation context
- **Example**:
  ```
  [FROM: Master Agent] Please implement the login feature
  [FROM: Developer Agent] I'll implement that now...
  ```

### 8. Central Orchestration Service
- **Decision**: All agent interactions go through a central service
- **Problem**: Direct agent-to-agent control would be chaotic and insecure
- **Solution**:
  - Agents use `<orc-command>` formatted commands
  - Central service manages all tmux operations
  - Service enforces communication rules and permissions
  - Complete audit trail of all interactions
- **Benefits**:
  - Single point of control and monitoring
  - Agents can't directly manipulate tmux or other agents
  - Easy to add new features and commands

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              CENTRAL ORCHESTRATION SERVICE               │
│  ┌─────────────────────────────────────────────────┐   │
│  │          Command Parser & Validator              │   │
│  │    - Detects <orc-command> in session files     │   │
│  │    - Validates command structure                 │   │
│  │    - Enforces permission rules                   │   │
│  └─────────────────┬───────────────────────────────┘   │
│                    │                                     │
│  ┌─────────────────▼───────────────────────────────┐   │
│  │             Command Executor                     │   │
│  │    - Tmux session management                     │   │
│  │    - Message routing with rules                  │   │
│  │    - Agent lifecycle control                     │   │
│  │    - State & status tracking                     │   │
│  └─────────────────┬───────────────────────────────┘   │
│                    │                                     │
│  ┌─────────────────▼───────────────────────────────┐   │
│  │         Session Monitor & Logger                 │   │
│  │    - Watches all agent session files             │   │
│  │    - Extracts commands and progress              │   │
│  │    - Maintains audit trail                       │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────┘
                    │ Controls all tmux operations
                    ▼
┌─────────────────────────────────────────────────────────┐
│                    Tmux Sessions                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Master     │  │  Developer   │  │   Reviewer   │ │
│  │   Agent      │  │    Agent     │  │    Agent     │ │
│  │  (Claude)    │  │  (Claude)    │  │  (Claude)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         ↕                ↕                ↕             │
│    <orc-command>    <orc-command>    <orc-command>     │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Central Orchestration Service
The main component that controls everything:
- **Command Parser**: Detects and validates `<orc-command>` directives
- **Command Executor**: Executes validated commands
- **Tmux Manager**: Controls all tmux operations
- **Rule Engine**: Enforces communication and permission rules
- **State Tracker**: Maintains agent status and system state

### 2. Session File Monitor
- Watches all agent session files for commands and progress
- Uses watchdog/inotify for real-time detection
- Extracts `<orc-command>` directives
- Parses incremental updates without re-reading entire files

### 3. Communication Router
- Routes messages between agents based on rules
- Maintains message queues and mailboxes
- Logs all communications for master oversight
- Handles blocked messages with notifications

### 4. Agent Lifecycle Manager
- Spawns new agents with proper configuration
- Monitors agent health and activity
- Handles context compaction and session resets
- Manages graceful shutdowns

## Key Workflows

### 1. Agent Spawning
```
1. Master agent issues spawn command:
   <orc-command type="request_action">
     <action>spawn_agent</action>
     <target>developer_agent</target>
   </orc-command>
2. Orchestrator validates request
3. Creates tmux pane for new agent
4. Launches Claude with role-specific prompt
5. Monitors session file creation
6. Sends initial task with identity prefix
7. Begins monitoring agent activity
```

### 2. Inter-Agent Communication
```
1. Agent A wants to message Agent B:
   <orc-command type="send_message">
     <from>agent_a</from>
     <to>agent_b</to>
     <title>Brief description</title>
     <content>Message content</content>
   </orc-command>
2. Orchestrator checks communication rules
3. If allowed: delivers message to Agent B
4. If blocked: notifies Agent A with reason
5. Logs communication for master oversight
```

### 3. Progress Monitoring
```
1. Session monitor detects changes in agent files
2. Extracts new <orc-command> directives
3. Parses regular output for progress indicators
4. Updates agent status in global state
5. Master can query for status updates
```

### 4. Context Compaction
```
1. Orchestrator detects high token usage
2. Sends compaction instruction to agent
3. Agent generates summary using <orc-command>
4. Orchestrator initiates session reset
5. Restarts agent with summary context
```

## Design Principles

1. **Minimal Intrusion**: Agents work naturally without awareness of monitoring
2. **Real-time Visibility**: Complete audit trail with immediate insights
3. **Graceful Degradation**: System continues if monitoring fails
4. **Resource Efficiency**: Smart filtering to avoid overwhelming master agent
5. **Flexibility**: Easy to add new agent types and coordination patterns

## Implementation Phases

### Phase 1: Core Infrastructure
- Basic tmux management
- Session file monitoring
- Simple message routing

### Phase 2: Intelligence Layer
- Progress analysis
- Error detection
- Automatic interventions

### Phase 3: Advanced Features
- Context compaction
- Multi-agent coordination
- Performance optimization

## Open Questions

1. Session file format - need to verify exact structure
2. Token counting method - estimate vs actual API
3. Intervention strategies - when to interrupt vs observe
4. Agent specialization - how many types needed

## Next Steps

1. Verify Claude session file location and format
2. Prototype session file monitor
3. Test tmux control mechanisms
4. Design message filtering rules