# Agent State Detection Diagnostics

This document explains the diagnostic tools available for analyzing and improving agent state detection.

## Overview

The orchestrator uses pattern matching to detect whether agents are busy, idle, or in other states. To help refine these patterns based on real Claude behavior, we have two diagnostic tools:

1. **diagnose_agent_states.py** - Captures comprehensive data for analysis
2. **monitor_live_states.py** - Real-time monitoring with visual feedback

## Tool 1: Agent State Diagnostics

### Purpose
Systematically capture tmux pane data over time to identify patterns that indicate different agent states.

### Usage

```bash
# Single snapshot capture
python orchestrator/scripts/diagnose_agent_states.py team-mcp-demo --single

# Continuous monitoring for 60 seconds
python orchestrator/scripts/diagnose_agent_states.py team-mcp-demo --duration 60

# Custom output directory
python orchestrator/scripts/diagnose_agent_states.py team-mcp-demo --output-dir my-diagnostics
```

### Output Files

The tool creates a timestamped directory with:

1. **capture_history.json** - Raw captured data from all panes
2. **pattern_analysis.json** - Analyzed patterns and state transitions
3. **diagnostic_report.md** - Human-readable report with findings

### What It Captures

For each pane, the tool records:
- Current detected state (idle, busy, error, etc.)
- Presence of prompt box pattern
- Debug lines count
- Processing words found
- Special patterns (spinner characters, tool calls)
- Last 10 lines of content
- State transitions with before/after indicators

## Tool 2: Live State Monitor

### Purpose
Real-time visualization of agent states to observe transitions as they happen.

### Usage

```bash
# Interactive curses interface (recommended)
python orchestrator/scripts/monitor_live_states.py team-mcp-demo

# Simple text output
python orchestrator/scripts/monitor_live_states.py team-mcp-demo --simple

# Custom duration and update interval
python orchestrator/scripts/monitor_live_states.py team-mcp-demo --duration 600 --interval 0.25
```

### Features

- Color-coded states (green=idle, yellow=busy, red=error)
- Shows last line from each pane
- Detects and displays processing indicators
- Tracks state transitions in real-time
- Interactive controls (q=quit, c=clear history)

## Using the Tools Together

### Workflow for Improving State Detection

1. **Start the live monitor** to observe agents in real-time:
   ```bash
   python orchestrator/scripts/monitor_live_states.py team-mcp-demo
   ```

2. **Interact with agents** to trigger different states:
   - Send messages between agents
   - Ask agents to perform tasks
   - Observe when states change

3. **Run diagnostic capture** during interesting activity:
   ```bash
   # In another terminal
   python orchestrator/scripts/diagnose_agent_states.py team-mcp-demo --duration 30
   ```

4. **Analyze the results**:
   - Check `diagnostic_report.md` for state transitions
   - Look for patterns that weren't detected correctly
   - Identify new indicators of busy/idle states

5. **Update patterns** in `agent_state_monitor.py` based on findings

## Current State Detection Patterns

### Busy State Indicators
- Debug hooks execution: `[DEBUG] Executing hooks`
- Processing words at line start: `✶ Shucking...`, `◐ Processing...`
- Tool calls: `Calling tool:`
- Stream started: `[DEBUG] Stream started`

### Idle State Indicators
- Prompt box pattern: `│ > │`
- Shortcuts line: `? for shortcuts`
- Empty prompt waiting for input

### Known Issues and Improvements

1. **Processing Words in Content**: Words like "synthesizing" in regular conversation can trigger false busy detection. Current fix requires processing words to appear at line start with special characters.

2. **Spinner Characters**: Claude uses various Unicode characters as spinners. The exact set may vary and needs continuous refinement.

3. **Transition Detection**: Quick state changes might be missed between polling intervals. Reduce interval for more accurate capture.

## Example Analysis Session

```bash
# Terminal 1: Start your orchestrator
cd orchestrator
python examples/team_mcp_demo_enhanced.py

# Terminal 2: Start live monitor
python scripts/monitor_live_states.py team-mcp-demo

# Terminal 3: Trigger agent activity via tmux
tmux send-keys -t team-mcp-demo:0.0 "send_message to=Researcher message='Please analyze this codebase'" Enter

# Terminal 4: Capture diagnostic data
python scripts/diagnose_agent_states.py team-mcp-demo --duration 60

# Review the generated report
cat diagnostics/agent_states_*/diagnostic_report.md
```

## Contributing Pattern Improvements

If you identify new patterns or issues:

1. Document the exact text that appears in tmux panes
2. Note whether it indicates busy, idle, or another state
3. Update the patterns in `src/agent_state_monitor.py`
4. Test with both diagnostic tools to verify improvements

The goal is to make state detection as accurate as possible for optimal message delivery timing.