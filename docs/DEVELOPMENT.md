# Development Guide

## Setting Up Development Environment

### Prerequisites

1. **Python 3.8+** with pip
2. **tmux** for terminal multiplexing
3. **Claude CLI** installed and authenticated
4. **Git** for version control

### Installation for Development

```bash
# Clone the repository
git clone <repository-url>
cd orchestrator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov pytest-asyncio black isort mypy
```

## Code Structure

### Design Principles

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Dependency Injection**: Components receive dependencies rather than creating them
3. **Type Safety**: Use type hints throughout the codebase
4. **Testability**: Design for easy unit testing with mockable interfaces

### Module Organization

```
src/
├── orchestrator.py      # Core orchestration logic
├── tmux_manager.py      # Tmux operations abstraction
├── session_monitor.py   # Session file monitoring
├── simple_launcher.py   # Claude launching logic
└── main.py             # CLI entry point
```

### Key Design Patterns

#### 1. Registry Pattern (Agent Management)
```python
class Orchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}  # Registry
    
    def register_agent(self, name: str, ...):
        self.agents[name] = Agent(...)  # Registration
```

#### 2. Observer Pattern (Session Monitoring)
```python
# SessionMonitor observes file changes
# Orchestrator processes observed commands
monitor = SessionMonitor(file_path, agent_name)
commands = monitor.extract_commands(messages)
orchestrator.process_command(agent_name, command)
```

#### 3. Command Pattern (Message Protocol)
```python
@dataclass
class Command:
    command_type: str
    from_agent: Optional[str]
    to_agent: Optional[str]
    # ... command encapsulation
```

## Adding New Features

### 1. Adding a New Command Type

#### Step 1: Update Command Extraction
```python
# In session_monitor.py
def extract_commands(self, messages: List[Message]) -> List[Command]:
    # Add parsing logic for new command type
    if command_type == "your_new_command":
        # Extract specific attributes
```

#### Step 2: Add Command Handler
```python
# In orchestrator.py
def __init__(self):
    self.command_handlers = {
        "send_message": self._handle_send_message,
        "mailbox_check": self._handle_mailbox_check,
        "your_new_command": self._handle_your_command,  # Add this
    }

def _handle_your_command(self, agent_name: str, command: Command):
    # Implement command logic
```

#### Step 3: Update Documentation
- Add command to `API_REFERENCE.md`
- Update agent prompt examples
- Add tests for new functionality

### 2. Adding Agent Capabilities

#### Example: Adding Agent Status Tracking
```python
# In orchestrator.py
@dataclass
class Agent:
    # Existing fields...
    status: str = "idle"  # New field
    last_command_time: float = 0

def update_agent_status(self, agent_name: str, status: str):
    if agent_name in self.agents:
        self.agents[agent_name].status = status
        self.agents[agent_name].last_active = time.time()
```

### 3. Extending the Message Protocol

#### Example: Adding Message Attachments
```python
# In session_monitor.py
@dataclass
class Command:
    # Existing fields...
    attachments: Optional[List[Dict[str, Any]]] = None

# Update XML parsing to handle:
# <orc-command name="send_message">
#   <attachment type="file" path="/path/to/file.txt"/>
# </orc-command>
```

## Monitoring and Diagnostics

### Agent State Monitoring

The system includes sophisticated monitoring capabilities for detecting and tracking agent anomalies during operation.

#### Live State Monitor with Continuous Anomaly Recording

**Basic Usage:**
```bash
# Monitor session with default behavior (exits on first anomaly)
python scripts/monitor_live_states.py session-name

# Continuous monitoring for extended sessions
python scripts/monitor_live_states.py session-name --continuous-anomaly-recording --duration 1800
```

**Advanced Options:**
- `--continuous-anomaly-recording`: Continue monitoring without exiting on first anomaly
- `--anomaly-report-format`: Choose output format (text/json/csv)
- `--duration`: Monitoring duration in seconds
- `--interval`: Update frequency in seconds
- `--simple`: Use text mode instead of curses interface

**Report Formats:**
- **JSON**: Machine-readable, recommended for automated analysis
- **CSV**: Spreadsheet-compatible, ideal for statistical analysis  
- **Text**: Human-readable but has minor formatting issues

#### AnomalyHistory System

The monitoring system uses a sophisticated anomaly tracking system (`AnomalyHistory` in `agent_state_monitor.py`):

**Key Features:**
- **Automatic Classification**: Categorizes anomalies by type
- **Memory Management**: Configurable retention policies prevent unbounded growth
- **Resource Efficiency**: ~30MB for 20,000 records
- **Query Interface**: Flexible filtering by agent, type, and time range

**Configuration Example:**
```python
from src.agent_state_monitor import AnomalyHistoryConfig, AgentStateMonitor

# Configure for extended monitoring
anomaly_config = AnomalyHistoryConfig(
    max_records_per_agent=5000,
    max_total_records=20000,
    retention_hours=12.0
)
monitor = AgentStateMonitor(tmux_manager, anomaly_config)
```

**Performance Characteristics:**
- Memory: ~1.5KB per anomaly record
- CPU: <2% overhead during normal operation
- Scales to thousands of anomalies efficiently

#### Usage Examples

**Development Workflow:**
```bash
# Start orchestrator
python examples/team_mcp_demo_enhanced.py --session dev-session

# Monitor in separate terminal
python scripts/monitor_live_states.py dev-session --continuous-anomaly-recording --duration 1200 --anomaly-report-format json
```

**Quality Assurance:**
```bash
# Extended monitoring for QA testing
python scripts/monitor_live_states.py qa-session --continuous-anomaly-recording --duration 3600 --anomaly-report-format csv
```

**Production Monitoring:**
```bash
# Low-overhead background monitoring
python scripts/monitor_live_states.py prod-session --continuous-anomaly-recording --simple --duration 14400 --interval 1.0
```

## Testing

### Test Structure
```
tests/
├── unit/
│   ├── test_orchestrator.py
│   ├── test_session_monitor.py
│   └── test_tmux_manager.py
├── integration/
│   ├── test_two_agent_communication.py
│   └── test_e2e_mock_claude.py
└── fixtures/
    └── mock_claude.py
```

### Writing Unit Tests

#### Example: Testing Command Processing
```python
import pytest
from unittest.mock import Mock, MagicMock
from src.orchestrator import Orchestrator, Agent
from src.session_monitor import Command

class TestOrchestrator:
    def test_send_message_command(self):
        # Arrange
        orc = Orchestrator()
        orc.tmux = Mock()  # Mock tmux operations
        
        # Register agents
        orc.agents["Sender"] = Agent(
            name="Sender",
            session_id="sender-123",
            pane_index=0,
            session_file="/tmp/sender.jsonl",
            system_prompt="Test"
        )
        orc.agents["Receiver"] = Agent(
            name="Receiver",
            session_id="receiver-123",
            pane_index=1,
            session_file="/tmp/receiver.jsonl",
            system_prompt="Test"
        )
        
        # Create command
        cmd = Command(
            command_type="send_message",
            from_agent="Sender",
            to_agent="Receiver",
            content="Test message",
            priority="normal"
        )
        
        # Act
        orc.process_command("Sender", cmd)
        
        # Assert
        assert len(orc.mailbox["Receiver"]) == 1
        assert "Test message" in orc.mailbox["Receiver"][0]
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_orchestrator.py

# Run with verbose output
pytest -v

# Run only marked tests
pytest -m "not slow"
```

### Integration Testing

#### Mock Claude for Testing
```python
# tests/fixtures/mock_claude.py
class MockClaude:
    """Mock Claude CLI for testing without real Claude"""
    
    def __init__(self, responses: Dict[str, str]):
        self.responses = responses
        self.history = []
    
    def send_message(self, message: str) -> str:
        self.history.append(message)
        # Return predetermined response
        return self.responses.get(message, "Default response")
```

## Code Style

### Python Style Guide

Follow PEP 8 with these additions:

1. **Line Length**: Max 88 characters (Black default)
2. **Imports**: Group and sort with isort
3. **Type Hints**: Required for all functions
4. **Docstrings**: Google style for all public methods

### Example Code Style
```python
"""Module docstring explaining purpose."""

from dataclasses import dataclass
from typing import Dict, List, Optional

import third_party_lib

from .local_module import LocalClass


@dataclass
class ExampleClass:
    """Class documentation.
    
    Attributes:
        name: Description of name attribute
        value: Description of value attribute
    """
    name: str
    value: Optional[int] = None
    
    def process(self, data: List[str]) -> Dict[str, int]:
        """Process data and return results.
        
        Args:
            data: List of strings to process
            
        Returns:
            Dictionary mapping strings to counts
            
        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("Data cannot be empty")
            
        return {item: len(item) for item in data}
```

### Code Formatting

```bash
# Format code with Black
black src tests

# Sort imports with isort
isort src tests

# Type check with mypy
mypy src

# Lint with flake8 (optional)
flake8 src tests
```

## Debugging

### Debug Mode

```python
# Enable debug logging in your code
import logging

logger = logging.getLogger(__name__)

class Orchestrator:
    def process_command(self, agent_name: str, command: Command):
        logger.debug(f"Processing command from {agent_name}: {command.command_type}")
        # ... rest of implementation
```

### Interactive Debugging

```python
# Use breakpoints
import pdb

def problematic_function():
    # ... some code ...
    pdb.set_trace()  # Debugger will stop here
    # ... more code ...
```

### Tmux Debugging

```bash
# Attach to session to see what's happening
tmux attach -t claude-agents

# Log all tmux commands
export TMUX_DEBUG=1
```

## Performance Considerations

### 1. Session File Reading
- Use incremental reading (current implementation)
- Consider file size limits
- Implement log rotation if needed

### 2. Message Queue Management
- Current: In-memory lists
- Future: Consider Redis for persistence
- Implement message expiration

### 3. Threading
- One monitor thread per agent
- Use thread-safe collections
- Avoid blocking operations in main thread

## Contributing

### Pull Request Process

1. **Fork and Clone**
   ```bash
   git fork <repo>
   git clone <your-fork>
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes**
   - Write tests first (TDD)
   - Implement feature
   - Update documentation

4. **Run Tests and Checks**
   ```bash
   pytest
   black src tests
   isort src tests
   mypy src
   ```

5. **Submit PR**
   - Clear description
   - Link related issues
   - Include test results

### Code Review Checklist

- [ ] Tests pass and cover new code
- [ ] Type hints added/updated
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Performance impact considered

## Future Development Ideas

### Phase 2 Features
1. **Web UI Dashboard**
   - Real-time agent status
   - Message flow visualization
   - Performance metrics

2. **Plugin System**
   - Hook system for extensions
   - Custom command types
   - Third-party integrations

3. **Distributed Operation**
   - Multiple orchestrator instances
   - Cross-machine agent communication
   - Load balancing

### Architecture Evolution
1. **Message Persistence**
   - Database backend
   - Message history
   - Audit trails

2. **Advanced Routing**
   - Topic-based subscriptions
   - Message filtering
   - Priority queues

3. **Monitoring & Metrics**
   - Prometheus integration
   - Performance tracking
   - Alert system