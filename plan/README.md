# Multi-Agent System Plan

This directory contains the planning and design documents for the Claude Multi-Agent Orchestration System.

## Structure

### High-Level Design Documents
- **[DESIGN_OVERVIEW.md](DESIGN_OVERVIEW.md)** - Overall system design and key decisions
- **[ORCHESTRATION_SERVICE.md](ORCHESTRATION_SERVICE.md)** - Central orchestrator architecture
- **[COMMUNICATION_CHANNELS.md](COMMUNICATION_CHANNELS.md)** - Inter-agent communication design
- **[COMMUNICATION_RULES.md](COMMUNICATION_RULES.md)** - Message routing and access control rules
- **[AGENT_PROMPT_DESIGN.md](AGENT_PROMPT_DESIGN.md)** - Agent system prompt templates
- **[ROLE_IDENTITY_DESIGN.md](ROLE_IDENTITY_DESIGN.md)** - Agent identity and role management
- **[KEY_INSIGHTS.md](KEY_INSIGHTS.md)** - Critical observations and design notes

### Phase-Based Implementation

#### [Phase 1](phase1/) - Two-Agent MVP ✅ COMPLETED
- Basic orchestration with Master and Worker agents
- Session file monitoring
- Simple message passing
- XML command protocol

**Key Documents:**
- [PHASE1_MVP_PLAN.md](phase1/PHASE1_MVP_PLAN.md) - Phase 1 specifications
- [IMPLEMENTATION_GUIDE.md](phase1/IMPLEMENTATION_GUIDE.md) - Implementation details
- [PHASE1_COMPLETION_REPORT.md](phase1/PHASE1_COMPLETION_REPORT.md) - Completion summary

#### Phase 2 (Planned) - Multi-Agent System
- Multiple worker agents
- Complex communication rules
- Mailbox system
- Context management

#### Phase 3 (Future) - Advanced Features
- Agent spawning/termination
- Global bulletin board
- Hook-based extensions
- Performance optimizations

## Design Philosophy

1. **Central Orchestration**: All agent interactions go through the orchestrator
2. **Session File Monitoring**: Use Claude's session files for reliable message capture
3. **Long-Lived Sessions**: Agents run continuously with context management
4. **Tmux-Based**: Visual debugging and manual intervention capabilities
5. **XML Protocol**: Human-readable command format for agent communication

## Current Status

- **Phase 1**: ✅ Completed and implemented
- **Phase 2**: 📋 Planned (specifications in root design docs)
- **Phase 3**: 🔮 Future consideration

## Implementation

The Phase 1 implementation is in the directories:
- **Production Code**: `src/`
- **Documentation**: `docs/`
- **Examples**: `examples/`

## Next Steps

To begin Phase 2:
1. Review the high-level design documents
2. Create `phase2/PHASE2_PLAN.md` based on the designs
3. Update communication rules for multi-agent scenarios
4. Extend the orchestrator to support new features