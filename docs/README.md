# Documentation Index

Welcome to the Claude Multi-Agent Orchestrator documentation. This guide will help you understand, use, and extend the orchestrator system.

## 🚀 Getting Started

### For Users
- **[Usage Guide](USAGE_GUIDE.md)** - Core concepts, workflows, and best practices
- **[CLI Reference](CLI_REFERENCE.md)** - Complete command reference for `ccorc` and `ccdk`
- **[Quick Start](../README.md#quick-start)** - Installation and first steps

### For Developers
- **[Development Guide](DEVELOPMENT.md)** - Setting up development environment
- **[CLAUDE.md](../CLAUDE.md)** - Essential guide for AI agents working on this codebase

## 📚 Core Documentation

### Configuration & Teams
- **[Team Configuration Guide](TEAM_CONFIGURATION.md)** - Creating and configuring custom teams
- **[Pre-built Teams](../examples/teams/)** - Ready-to-use team configurations

### Architecture & Design
- **[Session Architecture](SESSION_ARCHITECTURE.md)** - Team contexts and session persistence
- **[Architecture Overview](ARCHITECTURE.md)** - System design and components
- **[State Detection](state_detection_diagnostics.md)** - Agent state monitoring details

### Advanced Topics
- **[Cost Monitoring Guide](COST_MONITORING_GUIDE.md)** - Integrating with cost tracking tools
- **[Docker Environment](../docker/claude-code/README.md)** - CCBox container details
- **[Background Processing](../scripts/claude-bg)** - Running teams in background

## 🔧 Reference Documentation

### API & Protocols
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Command Protocol](COMMAND_PROTOCOL.md)** - XML command format details

### Troubleshooting
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Diagnostic Tools](../scripts/)** - Utilities for debugging

## 📋 Quick Reference

### Common Commands
```bash
# Team management
ccorc launch devops-team              # Launch team
ccorc ls                              # List contexts
ccorc info my-project                 # Show details
ccorc rm my-project                   # Clean up

# Container management
ccdk run dev                          # Run Claude
ccdk sh frontend                      # Open shell
ccdk ps                               # List containers
```

### Key Concepts
- **Teams**: Pre-configured groups of agents with specific roles
- **Contexts**: Persistent team sessions that survive restarts
- **Agents**: Individual Claude instances that communicate via MCP
- **Sessions**: Conversation history that persists across launches

## 🔬 Research & Implementation

### Technical Details
- **[Implementation Notes](IMPLEMENTATION_NOTES.md)** - Evolution and key decisions
- **[Session Management](SESSION_MANAGEMENT.md)** - How Claude sessions work
- **[Research Documentation](research/)** - Original research and experiments

### Architecture Research
- **[Architecture Research](research/ARCHITECTURE_RESEARCH.md)** - Design explorations
- **[CLI Options Discovery](research/CLI_OPTIONS_DISCOVERED.md)** - Claude CLI capabilities

## 📁 Documentation Structure

```
docs/
├── README.md                    # This file
├── USAGE_GUIDE.md              # User guide
├── CLI_REFERENCE.md            # Command reference
├── TEAM_CONFIGURATION.md       # Team setup guide
├── SESSION_ARCHITECTURE.md     # Context persistence
├── DEVELOPMENT.md              # Developer guide
├── TROUBLESHOOTING.md          # Problem solving
├── research/                   # Research documents
└── archive/                    # Deprecated docs
```

## 🆘 Getting Help

1. Check the relevant guide above
2. Use diagnostic tools: `python scripts/diagnose_agent_states.py`
3. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. Check [closed issues](https://github.com/anthropics/claude-orchestrator/issues?q=is%3Aissue+is%3Aclosed)

## 📝 Contributing

See the [Development Guide](DEVELOPMENT.md) for contribution guidelines.