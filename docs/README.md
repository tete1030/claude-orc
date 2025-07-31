# Orchestrator Documentation

Welcome to the Claude Multi-Agent Orchestrator documentation. This guide will help you understand, use, and extend the orchestrator system.

## Documentation Structure

### 📚 Core Documentation

1. **[Architecture Guide](ARCHITECTURE.md)**
   - System design and components
   - Data flow and threading model
   - Security and performance considerations
   - Future architecture plans

2. **[API Reference](API_REFERENCE.md)**
   - Complete API documentation
   - Class and method references
   - Command protocol specification
   - Code examples

3. **[Troubleshooting Guide](TROUBLESHOOTING.md)**
   - Common issues and solutions
   - Debugging techniques
   - Diagnostic commands
   - Emergency recovery procedures

4. **[Development Guide](DEVELOPMENT.md)**
   - Setting up development environment
   - Code style and best practices
   - Testing strategies
   - Contributing guidelines

### 🔧 Implementation Details

5. **[Session Management](SESSION_MANAGEMENT.md)**
   - How Claude sessions work
   - Session ID strategy
   - File monitoring implementation
   - Session lifecycle

6. **[Command Protocol](COMMAND_PROTOCOL.md)**
   - XML command format details
   - Supporting multiple formats
   - Extending the protocol
   - Message routing logic

7. **[Implementation Notes](IMPLEMENTATION_NOTES.md)**
   - Evolution of the implementation
   - Key discoveries and decisions
   - Lessons learned

### 🔬 Research & History

8. **[Research Documentation](research/)**
   - Original research and experiments
   - Technical discoveries
   - Historical development artifacts

### 📋 Quick References

9. **[Quick Start](../README.md#quick-start)**
   - Installation steps
   - Basic example
   - First orchestrator setup

10. **[Examples](../examples/)**
   - `basic_two_agent.py` - Simple master-worker setup
   - `verify_claude_setup.py` - Check Claude CLI installation

## Getting Started

### For Users

1. Start with the [Quick Start](../README.md#quick-start) in the main README
2. Review [Architecture](ARCHITECTURE.md) to understand the system
3. Check [API Reference](API_REFERENCE.md) for detailed usage
4. Use [Troubleshooting](TROUBLESHOOTING.md) when you encounter issues

### For Developers

1. Read the [Development Guide](DEVELOPMENT.md) to set up your environment
2. Understand the [Architecture](ARCHITECTURE.md) before making changes
3. Follow the code style guidelines
4. Write tests for new features

## Key Concepts

### Agents
Autonomous Claude instances that can communicate with each other through the orchestrator.

### Commands
XML-formatted messages that agents embed in their responses to communicate.

### Mailbox
Message queue system where messages wait until the recipient agent checks them.

### Session Files
JSONL files that Claude uses to store conversation history, monitored by the orchestrator.

## Common Tasks

### Running Two Agents
```python
from src.orchestrator import Orchestrator, OrchestratorConfig

config = OrchestratorConfig(session_name="my-agents")
orc = Orchestrator(config)

orc.register_agent(name="Agent1", session_id="placeholder", 
                   system_prompt="Your instructions...")
orc.register_agent(name="Agent2", session_id="placeholder",
                   system_prompt="Your instructions...")

if orc.start():
    # Agents are running
    pass
```

### Sending Messages Between Agents
Agents use XML commands in their responses:
```xml
<orc-command name="send_message" from="Agent1" to="Agent2">
Your message here
</orc-command>
```

### Debugging Issues
1. Enable debug logging
2. Check tmux session: `tmux attach -t <session-name>`
3. Verify session files exist
4. See [Troubleshooting Guide](TROUBLESHOOTING.md)

## System Requirements

- Python 3.8+
- tmux
- Claude CLI (authenticated)
- Unix-like OS (Linux, macOS)

## Support

For issues and questions:
1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review [closed issues](../issues?q=is%3Aissue+is%3Aclosed)
3. Open a new issue with diagnostic information

## Contributing

See the [Development Guide](DEVELOPMENT.md) for contribution guidelines.

## License

[Your license information]