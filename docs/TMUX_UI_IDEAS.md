# Tmux UI Enhancement Ideas

This document contains various ideas for enhancing the tmux-based user interface of the Claude Orchestrator. These are potential future improvements to make the system more visual, interactive, and informative.

## 1. Status Bar Enhancements

### Agent Health Indicators
- Show each agent's current state (IDLE/BUSY/ERROR) in the status bar
- Use color coding: 🟢 green=idle, 🟡 yellow=busy, 🔴 red=error
- Example: `[Leader: 🟢] [Researcher: 🟡] [Writer: 🟢]`

### Message Queue Count
- Display number of pending messages for each agent
- Format: `[Leader: 0] [Researcher: 2] [Writer: 0]`
- Could combine with health: `[Leader: 🟢/0]`

### MCP Connection Status
- Show overall MCP server health
- Indicator for each agent's MCP connection
- Example: `MCP: ✓ Connected (3/3 agents)`

### Resource Usage
- CPU/Memory usage per agent (from Docker stats)
- Compact format: `Leader: 2%/120MB`
- Could be toggled on/off to reduce clutter

## 2. Pane Border Improvements

### Color-Coded Borders
- Dynamic border colors based on agent state
- Green borders for idle agents
- Yellow/amber for busy/processing
- Red for errors or disconnected
- Implementation: Use tmux's `pane-active-border-style`

### Activity Indicators
- Animated spinner in border when agent is processing
- Similar to Claude's own processing indicator
- Could use Unicode characters: ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏

### Last Activity Time
- Show how long agent has been in current state
- Format: `[Leader] Idle for 2m 30s`
- Or: `[Researcher] Busy for 45s`

### Message Badge
- Show unread message count in the pane border
- Format: `[Leader] (3 new) Current Task`
- Highlight when new messages arrive

## 3. Interactive Features

### Quick Agent Switch
- Keyboard shortcuts to jump between agents
- `Ctrl+1` → Leader pane
- `Ctrl+2` → Researcher pane  
- `Ctrl+3` → Writer pane
- Could use tmux's `select-pane` with key bindings

### Message Preview
- Pop-up window showing last message received
- Triggered by key combination or mouse hover
- Use tmux's `display-popup` command

### Command Palette
- Leader key (e.g., `Ctrl+Space`) opens command menu
- Common commands:
  - Send message to agent
  - Check agent status
  - View message history
  - Restart agent
- Implemented with tmux menus

### Focus Mode
- Temporarily maximize one agent's pane
- `Ctrl+M` to maximize/restore
- Other panes still visible but minimized
- Use tmux's `resize-pane -Z`

## 4. Visual Feedback

### Message Flow Animation
- Brief highlight/flash when messages are sent
- Could change border color temporarily
- Or show arrow indicators: `→ Researcher`

### State Change Notifications
- Flash pane border when agent state changes
- Different colors for different transitions
- Optional sound alerts (terminal bell)

### Progress Bars
- For long-running operations
- Show in pane title or status bar
- Example: `[Leader] Planning... [████░░░░] 60%`

### Alert System
- Visual alerts for errors or important events
- Could use tmux's `display-message`
- Color-coded by severity
- Optional desktop notifications

## 5. Layout Options

### Dynamic Layouts
- Auto-adjust layout based on number of agents
- 2 agents: vertical split
- 3 agents: even-horizontal
- 4+ agents: tiled
- Could detect and remove inactive agents

### Picture-in-Picture
- Small floating pane for orchestrator logs
- Always visible regardless of active pane
- Could show recent message flow
- Implemented with tmux's floating panes

### Split Views
- Show agent + its message history side by side
- Or agent + detailed stats
- Toggle between views with hotkeys

### Tabbed Mode
- Each agent in a separate tmux window
- Window names show agent + status
- Quick switching with `Ctrl+N/P`
- Status bar shows all agents

## 6. Information Dashboard

### Mini Stats Pane
- Small pane showing system overview
- Total messages sent/received
- Uptime, error count
- Current team objective

### Message History Graph
- ASCII visualization of message flow
- Shows communication patterns
- Could use sparklines: ▁▂▄▅▇█▇▅▄▂▁

### Performance Metrics
- Response times between agents
- Message throughput (msgs/minute)
- Average processing time per agent
- Could export to monitoring tools

### Team Activity Feed
- Scrolling log of all agent activities
- Compact format with timestamps
- Color-coded by agent
- Filterable by type/agent

## 7. Developer Tools

### Debug Mode Toggle
- Show/hide verbose MCP traffic
- Display raw JSON messages
- Log all tmux commands
- Performance timing info

### Message Inspector
- Detailed view of message contents
- JSON pretty-printing
- Message metadata (size, timestamp)
- Diff view for message changes

### State Debugger
- Live view of agent internal states
- Variable watchers
- Breakpoint support
- State history/timeline

### Replay Mode
- Record all agent sessions
- Replay with time controls
- Export for analysis
- Useful for debugging and demos

## Implementation Priority

### Quick Wins (Low Complexity)
1. Status bar with agent states
2. Color-coded pane borders
3. Keyboard shortcuts for pane switching
4. Basic message count in borders

### Medium Complexity
1. Activity indicators
2. Message flow visualization
3. Command palette
4. Focus mode

### High Complexity
1. Interactive dashboards
2. Replay system
3. Full debugging tools
4. Dynamic layouts

## Technical Considerations

- **Performance**: Avoid updates that cause flicker or high CPU usage
- **Compatibility**: Ensure features work across different tmux versions
- **Customization**: Make features configurable/optional
- **Integration**: Work well with existing orchestrator architecture

## Future Ideas

- Integration with external monitoring tools (Grafana, etc.)
- Web-based UI that mirrors tmux display
- Mobile app for monitoring agents
- Voice notifications for important events
- AI-powered anomaly detection in agent behavior

---

*Note: This is a living document. As we implement features or get new ideas, we should update this file.*