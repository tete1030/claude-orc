# Cost Monitoring Integration Guide

## Overview

The Claude Multi-Agent Orchestrator now supports cost monitoring by making Claude session files accessible to host-based monitoring tools. This feature works in both **shared** and **isolated** container modes, enabling comprehensive usage tracking and cost analysis.

**Key Capability**: Claude session files (*.jsonl) containing usage metrics are automatically made available on the host filesystem for external monitoring tools to analyze.

## How It Works

### Container Modes

#### Shared Mode
- **Mount Strategy**: Host's `~/.claude` is mounted directly to container's `~/.claude`
- **Session Files**: Immediately available at host path `~/.claude/projects/`
- **Cost Monitoring**: Direct access to all session data
- **Configuration**: No additional setup required

#### Isolated Mode (Default)
- **Mount Strategy**: Container has isolated `~/.claude` directory
- **Session Sharing**: Daemon creates symlinks to host filesystem
- **Host Location**: `~/.claude/projects/ccbox-<container-name>-<project>/`
- **Cost Monitoring**: Requires daemon for session file access

### Session File Sharing Architecture

```
Host Filesystem                    Container (Isolated Mode)
├── ~/.claude/                     ├── ~/.claude/
│   └── projects/                   │   └── projects/
│       └── ccbox-agent1-proj/       │       └── proj/
│           └── session.jsonl  ←────┤           └── session.jsonl
│                                   │
└── Cost Monitoring Tool            └── Session Monitor Daemon
    (reads from host)                   (creates symlinks)
```

## Setup for Cost Monitoring

### Prerequisites
- Claude Multi-Agent Orchestrator installed
- `ccdk` Docker management tool installed
- Cost monitoring tool that can read Claude session files

### Configuration

#### For Shared Mode (Simplest)
```bash
# Start agents in shared mode
ccdk run --shared-mode

# Session files immediately available at:
ls ~/.claude/projects/*/
```

#### For Isolated Mode (Default)
```bash
# Start agents normally (isolated mode default)
ccdk run -i my-agent

# Session files available at:
ls ~/.claude/projects/ccbox-my-agent-*/
```

### Accessing Session Files

#### File Locations
```bash
# Shared mode - direct access
~/.claude/projects/<project-name>/session.jsonl

# Isolated mode - symlinked access
~/.claude/projects/ccbox-<container-name>-<project>/session.jsonl
```

#### Example Monitoring Script
```bash
#!/bin/bash
# Simple cost monitoring example

echo "=== Claude Session Usage ==="
for session_dir in ~/.claude/projects/*/; do
    if [[ -f "$session_dir/session.jsonl" ]]; then
        echo "Session: $(basename "$session_dir")"
        echo "Records: $(wc -l < "$session_dir/session.jsonl")"
        echo "Last activity: $(stat -c %y "$session_dir/session.jsonl")"
        echo "---"
    fi
done
```

## Cost Monitoring Tool Integration

### Compatible Tools
- **Claude CLI built-in metrics**: Access via `claude usage`
- **Custom monitoring scripts**: Read session.jsonl files directly
- **Enterprise monitoring**: Integrate with existing log aggregation systems

### Data Format
Session files contain JSON lines with usage information:
```json
{"timestamp": "2025-08-02T10:30:00Z", "model": "claude-3-sonnet", "tokens": 1250, "cost": 0.015}
{"timestamp": "2025-08-02T10:31:15Z", "model": "claude-3-sonnet", "tokens": 890, "cost": 0.011}
```

### Monitoring Examples

#### Real-time Usage Tracking
```bash
# Monitor all active sessions
tail -f ~/.claude/projects/*/session.jsonl | grep -E '"cost":|"tokens":'
```

#### Daily Usage Reports
```python
import json
import glob
from datetime import datetime, timedelta

def daily_usage_report():
    total_cost = 0
    total_tokens = 0
    
    for session_file in glob.glob("~/.claude/projects/*/session.jsonl"):
        with open(session_file) as f:
            for line in f:
                data = json.loads(line)
                # Filter for today's usage
                if is_today(data['timestamp']):
                    total_cost += data.get('cost', 0)
                    total_tokens += data.get('tokens', 0)
    
    print(f"Daily Usage: ${total_cost:.2f}, {total_tokens} tokens")
```

## Team Session Cost Tracking

### Session-Based Monitoring
When using persistent team contexts, costs can be tracked per project:

```bash
# Monitor specific team context costs
ccorc list --verbose  # See active sessions

# Track costs for specific project
tail -f ~/.claude/projects/ccbox-my-project-*/session.jsonl
```

### Project-Level Reporting
```bash
# Generate report for team context
./scripts/team-session-costs.sh my-project-session

# Example output:
# Team Context: my-project-context
# Leader Agent: $2.45 (3,200 tokens)
# Researcher Agent: $1.89 (2,100 tokens)  
# Writer Agent: $3.12 (4,500 tokens)
# Total: $7.46 (9,800 tokens)
```

## Production Considerations

### Monitoring Requirements

#### Health Checks
- **Daemon Status**: Verify session monitor daemon is running in isolated containers
- **Symlink Integrity**: Ensure symlinks are correctly created and updated
- **File Permissions**: Confirm host can read session files

#### Performance Monitoring
```bash
# Check daemon process in container
ccdk exec -i my-agent ps aux | grep session_monitor

# Verify symlink creation
ls -la ~/.claude/projects/ccbox-*/
```

### Security Considerations
- **File Access**: Session files contain usage data but not conversation content
- **Path Isolation**: Container names in symlink paths prevent conflicts
- **Read-Only Access**: Monitoring tools should only read, not modify session files

### Scaling Considerations
- **Many Containers**: Monitor disk usage for symlinked session directories
- **High Frequency**: Consider log rotation for very active sessions
- **Network Monitoring**: Session files are local - no network overhead

## Troubleshooting

### Session Files Not Appearing
```bash
# Check container mode
ccdk list  # Verify if running in shared or isolated mode

# For isolated mode, check daemon
ccdk logs -i my-agent | grep session_monitor

# Verify container filesystem
ccdk shell -i my-agent ls -la ~/.claude/projects/
```

### Missing Symlinks in Isolated Mode
```bash
# Check daemon is running
ccdk exec -i my-agent pgrep -f session_monitor

# Restart container to restart daemon
ccdk restart -i my-agent

# Manual daemon check
ccdk shell -i my-agent cat /var/log/session_monitor.log
```

### Cost Data Inconsistencies
```bash
# Compare container vs host session files
ccdk exec -i my-agent ls ~/.claude/projects/*/
ls ~/.claude/projects/ccbox-my-agent-*/

# Check for stale symlinks
find ~/.claude/projects/ -type l -exec test ! -e {} \; -print
```

## Advanced Usage

### Multi-Host Deployments
```bash
# For distributed monitoring, consider:
# 1. Centralized log collection
rsync -av ~/.claude/projects/ monitoring-server:/data/claude-sessions/

# 2. Remote monitoring setup
ssh monitoring-server "tail -f /data/claude-sessions/*/session.jsonl"
```

### Custom Monitoring Integration
```python
# Example integration with monitoring system
import os
import json
from watchdog import observers, events

class ClaudeSessionMonitor(events.FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('session.jsonl'):
            # Send to monitoring system
            self.process_session_data(event.src_path)
    
    def process_session_data(self, file_path):
        # Read latest entries and send to monitoring
        container_name = self.extract_container_from_path(file_path)
        # ... send to monitoring system
```

### Automated Cost Alerts
```bash
# Example cost threshold monitoring
#!/bin/bash
COST_THRESHOLD=10.00

current_cost=$(./scripts/calculate-daily-costs.sh)
if (( $(echo "$current_cost > $COST_THRESHOLD" | bc -l) )); then
    echo "Cost alert: Daily usage $current_cost exceeds threshold $COST_THRESHOLD"
    # Send notification
fi
```

## Best Practices

### Regular Monitoring
- **Daily Reports**: Set up automated daily cost summaries
- **Threshold Alerts**: Configure alerts for unusual usage patterns
- **Trend Analysis**: Track usage trends over time

### Data Management
- **Archive Old Sessions**: Regular cleanup of completed session files
- **Backup Cost Data**: Preserve usage data for accounting purposes
- **Monitor Disk Usage**: Session files can accumulate over time

### Team Cost Management
- **Project Budgets**: Track costs per team context
- **Agent Efficiency**: Monitor which agents are most cost-effective
- **Usage Optimization**: Identify opportunities to reduce costs

---

For more information, see:
- `docs/CCORC_SESSION_MANAGEMENT_GUIDE.md` - Team context management
- `docs/CCDK_USAGE.md` - Docker container management
- `src/team_context_manager.py` - Team context persistence implementation