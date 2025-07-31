# API Reference

## Table of Contents
- [Orchestrator](#orchestrator)
- [OrchestratorConfig](#orchestratorconfig)
- [Agent](#agent)
- [TmuxManager](#tmuxmanager)
- [SessionMonitor](#sessionmonitor)
- [Command Protocol](#command-protocol)

## Orchestrator

The main orchestrator class that coordinates all agents.

### Class: `Orchestrator`

```python
from src.orchestrator import Orchestrator, OrchestratorConfig

orchestrator = Orchestrator(config)
```

#### Methods

##### `__init__(config: Optional[OrchestratorConfig] = None)`
Initialize the orchestrator with optional configuration.

##### `register_agent(name: str, session_id: str, system_prompt: str, working_dir: Optional[str] = None) -> None`
Register a new agent with the orchestrator.

**Parameters:**
- `name` (str): Unique name for the agent (case-insensitive for routing)
- `session_id` (str): Placeholder value (will be auto-generated)
- `system_prompt` (str): System prompt containing agent instructions
- `working_dir` (Optional[str]): Working directory for the agent

**Example:**
```python
orc.register_agent(
    name="DataProcessor",
    session_id="placeholder",
    system_prompt="You are a data processing agent...",
    working_dir="/path/to/data"
)
```

##### `start() -> bool`
Start the orchestrator and all registered agents.

**Returns:** 
- `True` if successful, `False` otherwise

**Example:**
```python
if orc.start():
    print("Orchestrator started successfully")
```

##### `stop() -> None`
Stop the orchestrator and cleanup all resources.

##### `send_to_agent(agent_name: str, message: str) -> bool`
Send a message directly to an agent's Claude interface.

**Parameters:**
- `agent_name` (str): Name of target agent
- `message` (str): Message to send

**Returns:**
- `True` if message was sent successfully

##### `process_command(agent_name: str, command: Command) -> None`
Process a command from an agent (usually called internally).

#### Properties

##### `agents: Dict[str, Agent]`
Dictionary of registered agents by name.

##### `mailbox: Dict[str, List[str]]`
Message queues for each agent.

##### `is_running: bool`
Whether the orchestrator is currently running.

## OrchestratorConfig

Configuration class for the orchestrator.

### Class: `OrchestratorConfig`

```python
from src.orchestrator import OrchestratorConfig

config = OrchestratorConfig(
    session_name="my-agents",
    poll_interval=1.0
)
```

#### Attributes

- `session_name` (str): Name of the tmux session. Default: `"claude-agents"`
- `claude_bin` (str): Path to Claude binary. Default: `"~/.claude/local/claude"`
- `session_dir` (str): Directory for session files. Auto-set based on CWD
- `poll_interval` (float): Seconds between session file checks. Default: `0.5`
- `interrupt_cooldown` (float): Minimum seconds between interrupts. Default: `2.0`
- `context_threshold` (int): Line count warning threshold. Default: `10000`

## Agent

Represents a registered agent in the system.

### Dataclass: `Agent`

#### Attributes

- `name` (str): Agent's unique name
- `session_id` (str): Claude session ID
- `pane_index` (int): Tmux pane index
- `session_file` (str): Path to session JSONL file
- `system_prompt` (str): Agent's system instructions
- `working_dir` (Optional[str]): Agent's working directory
- `monitor` (Optional[SessionMonitor]): Session file monitor
- `last_active` (float): Timestamp of last activity

## TmuxManager

Manages tmux sessions and panes.

### Class: `TmuxManager`

```python
from src.tmux_manager import TmuxManager

tmux = TmuxManager("my-session")
```

#### Methods

##### `create_session(num_panes: int = 2) -> bool`
Create a new tmux session with specified number of panes.

##### `send_to_pane(pane_index: int, command: str) -> bool`
Send a command to a specific pane.

##### `capture_pane(pane_index: int, history_limit: int = 0) -> Optional[str]`
Capture content from a pane.

##### `kill_session() -> bool`
Terminate the tmux session.

## SessionMonitor

Monitors Claude session files for commands.

### Class: `SessionMonitor`

```python
from src.session_monitor import SessionMonitor

monitor = SessionMonitor(session_file_path, agent_name)
```

#### Methods

##### `get_new_messages() -> List[Message]`
Get all new messages since last check.

##### `extract_commands(messages: List[Message]) -> List[Command]`
Extract XML commands from messages.

##### `reset() -> None`
Reset file position to beginning.

### Class: `Command`

Represents a parsed command.

#### Attributes

- `command_type` (str): Type of command (e.g., "send_message")
- `from_agent` (Optional[str]): Source agent name
- `to_agent` (Optional[str]): Target agent name
- `title` (Optional[str]): Message title
- `content` (Optional[str]): Message content
- `priority` (str): Message priority ("normal" or "high")
- `raw_content` (str): Original XML content

## Command Protocol

### XML Command Format

Commands are embedded in agent responses using XML tags.

#### Send Message Command

**Modern Format:**
```xml
<orc-command name="send_message" from="Agent1" to="Agent2" title="Subject" priority="normal">
Message content goes here
</orc-command>
```

**Legacy Format:**
```xml
<orc-command type="send_message">
  <from>Agent1</from>
  <to>Agent2</to>
  <title>Subject</title>
  <content>Message content</content>
  <priority>normal</priority>
</orc-command>
```

**Attributes:**
- `name`/`type`: Command type (required)
- `from`: Sending agent name (required for send_message)
- `to`: Receiving agent name (required for send_message)
- `title`: Message title (optional)
- `priority`: "normal" or "high" (default: "normal")

#### Mailbox Check Command

```xml
<orc-command name="mailbox_check"></orc-command>
```

Returns all queued messages for the requesting agent.

### System Prompts

Agents should include command instructions in their system prompts:

```python
system_prompt = """You are an agent in a multi-agent system.

To send messages to other agents:
<orc-command name="send_message" from="YourName" to="TargetAgent" title="Subject">
Your message here
</orc-command>

To check your mailbox:
<orc-command name="mailbox_check"></orc-command>
"""
```

## Error Handling

### Exceptions

The orchestrator doesn't define custom exceptions but handles:
- `FileNotFoundError`: Session files not yet created
- `json.JSONDecodeError`: Malformed session file entries
- `subprocess.CalledProcessError`: Tmux command failures

### Logging

All components use Python's standard logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Log levels:
- `DEBUG`: Detailed operation flow
- `INFO`: Normal operation events
- `WARNING`: Recoverable issues
- `ERROR`: Failures requiring attention

## Complete Example

```python
import time
import logging
from src.orchestrator import Orchestrator, OrchestratorConfig

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create orchestrator
config = OrchestratorConfig(
    session_name="example-agents",
    poll_interval=0.5
)
orc = Orchestrator(config)

# Register agents
orc.register_agent(
    name="Coordinator",
    session_id="placeholder",
    system_prompt="""You coordinate tasks between agents.
    
To delegate work:
<orc-command name="send_message" from="Coordinator" to="Worker">Task details</orc-command>

To check responses:
<orc-command name="mailbox_check"></orc-command>"""
)

orc.register_agent(
    name="Worker",
    session_id="placeholder", 
    system_prompt="""You execute assigned tasks.
    
To check assignments:
<orc-command name="mailbox_check"></orc-command>

To report results:
<orc-command name="send_message" from="Worker" to="Coordinator">Results</orc-command>"""
)

# Start system
if orc.start():
    # Send initial task
    orc.send_to_agent("Coordinator", "Please assign a calculation task to the Worker.")
    
    # Run for 60 seconds
    try:
        time.sleep(60)
    finally:
        orc.stop()
```