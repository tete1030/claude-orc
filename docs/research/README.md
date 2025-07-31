# Research Documentation

This directory contains research and experimental findings from the Phase 1 development of the orchestrator.

## Contents

### Research Documents

1. **CURRENT_STATUS.md** - Research status tracking during development
2. **RESEARCH_EXPERIMENTS.md** - Scripts and experiments conducted
3. **SESSION_FILE_ANALYSIS.md** - Deep dive into Claude session file structure
4. **TECHNICAL_UNCERTAINTIES.md** - Questions and unknowns during research
5. **TEST_RESULTS.md** - Results from various test executions
6. **CLI_OPTIONS_DISCOVERED.md** - Claude CLI options and flags discovered
7. **MINIMAL_TEST_SCRIPT.md** - Documentation of minimal test approaches

## Key Findings

### Session File Discovery
- Location: `~/.claude/projects/<escaped-cwd>/*.jsonl`
- Format: JSONL with UUID filenames
- Content: User and assistant messages with metadata

### Claude CLI Options
- `--session-id <uuid>` - Specify session ID upfront
- `--append-system-prompt` - Add system instructions
- `--resume <session-id>` - Resume existing session

### Command Detection
- XML commands can be embedded in assistant responses
- Both modern (`name=`) and legacy (`type=`) formats work
- Commands must not be in code blocks

## Historical Context

These documents represent the research phase that led to the current orchestrator implementation. They contain:
- Early experiments and discoveries
- Problem-solving approaches
- Technical dead-ends and solutions
- Evolution of the architecture

## Related Documents

- **Phase 1 Plan**: `/plan/multi-agent-system/phase1/PHASE1_MVP_PLAN.md`
- **Implementation Guide**: `/plan/multi-agent-system/phase1/IMPLEMENTATION_GUIDE.md`
- **Completion Report**: `/plan/multi-agent-system/phase1/PHASE1_COMPLETION_REPORT.md`
- **Current Documentation**: `/orchestrator/docs/`