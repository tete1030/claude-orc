#!/usr/bin/env python3
"""
Capture a snapshot of current orchestrator state for debugging.
This creates a shareable snapshot that can be pasted to show the exact state.
"""

import subprocess
import json
import time
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tmux_manager import TmuxManager
from src.agent_state_monitor import AgentStateMonitor

def capture_snapshot(session_name="devops-team-demo"):
    """Capture a complete snapshot of the orchestrator state"""
    
    # Check if session exists
    result = subprocess.run(['tmux', 'has-session', '-t', session_name], capture_output=True)
    if result.returncode != 0:
        print(f"Error: No tmux session '{session_name}' found")
        return None
    
    tmux = TmuxManager(session_name)
    monitor = AgentStateMonitor(tmux)
    
    # Capture timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # Capture data for each pane
    snapshot = {
        "timestamp": timestamp,
        "session": session_name,
        "panes": {}
    }
    
    # Get number of panes
    panes = tmux.list_panes()
    pane_count = len(panes)
    
    # Define default agent names for known sessions
    if session_name == "team-mcp-demo":
        agents = ["Leader", "Researcher", "Writer"]
    elif session_name.startswith("devops-team"):
        agents = ["Architect", "Developer", "QA", "DevOps", "Docs"]
    else:
        # Try to get agent names from tmux pane variables
        agents = []
        for i in range(pane_count):
            try:
                result = subprocess.run([
                    'tmux', 'show-options', '-p', '-t', f'{session_name}:0.{i}', '@agent_name'
                ], capture_output=True, text=True)
                if result.returncode == 0 and '=' in result.stdout:
                    agent_name = result.stdout.strip().split('=', 1)[1]
                    agents.append(agent_name)
                else:
                    agents.append(f"Agent{i}")
            except:
                agents.append(f"Agent{i}")
    
    # Ensure we have enough agent names
    while len(agents) < pane_count:
        agents.append(f"Agent{len(agents)}")
    
    for i in range(pane_count):
        agent_name = agents[i] if i < len(agents) else f"Agent{i}"
        print(f"Capturing {agent_name}...", end='', flush=True)
        
        # Capture pane content
        content = tmux.capture_pane(i, history_limit=-50)
        if not content:
            print(" [FAILED]")
            continue
            
        # Detect state
        state = monitor.detect_agent_state(content, agent_name)
        
        # Get last 30 lines for context
        lines = content.strip().split('\n')
        last_lines = lines[-30:] if len(lines) > 30 else lines
        
        # Store pane data
        # Check for actual processing indicator using the same pattern as AgentStateMonitor
        import re
        has_processing_indicator = False
        for line in last_lines:
            # Check if line has the busy pattern: spinner symbol + word + ellipsis
            if re.search(r'[·✢✳✶✻✽*]\s+\w+…', line):
                has_processing_indicator = True
                break
        
        snapshot["panes"][agent_name] = {
            "pane_index": i,
            "detected_state": state.value,
            "content_lines": len(lines),
            "last_30_lines": last_lines,
            "has_prompt_box": any('╭' in line and '╮' in line for line in last_lines),
            "has_processing_indicator": has_processing_indicator
        }
        
        print(f" [State: {state.value}]")
    
    # Get border color
    result = subprocess.run([
        'tmux', 'show-options', '-w', '-t', session_name, 'pane-border-style'
    ], capture_output=True, text=True)
    
    if result.returncode == 0 and '=' in result.stdout:
        snapshot["border_color"] = result.stdout.strip().split('=')[-1]
    else:
        snapshot["border_color"] = "unknown"
    
    return snapshot

def save_snapshot(snapshot, filename=None):
    """Save snapshot to file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f".temp/state_snapshot_{timestamp}.json"
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    return filename

def format_snapshot_for_sharing(snapshot):
    """Format snapshot for easy sharing"""
    output = []
    output.append("=== ORCHESTRATOR STATE SNAPSHOT ===")
    output.append(f"Time: {snapshot['timestamp']}")
    output.append(f"Session: {snapshot['session']}")
    output.append(f"Border Color: {snapshot['border_color']}")
    output.append("")
    
    for agent_name, data in snapshot['panes'].items():
        output.append(f"=== {agent_name} (Pane {data['pane_index']}) ===")
        output.append(f"Detected State: {data['detected_state']}")
        output.append(f"Has Prompt Box: {data['has_prompt_box']}")
        output.append(f"Has Processing Indicator: {data['has_processing_indicator']}")
        output.append(f"\nLast 30 lines:")
        output.append("-" * 60)
        
        for i, line in enumerate(data['last_30_lines']):
            output.append(f"{i:2d}: {line}")
        
        output.append("")
    
    return "\n".join(output)

def main():
    print("Capturing orchestrator state snapshot...")
    
    # Parse arguments
    session_name = "devops-team-demo"
    if len(sys.argv) > 1:
        session_name = sys.argv[1]
    
    # Capture snapshot
    snapshot = capture_snapshot(session_name)
    if not snapshot:
        sys.exit(1)
    
    # Save to file
    filename = save_snapshot(snapshot)
    print(f"\nSnapshot saved to: {filename}")
    
    # Also create a text version for easy sharing
    text_filename = filename.replace('.json', '.txt')
    with open(text_filename, 'w') as f:
        f.write(format_snapshot_for_sharing(snapshot))
    print(f"Text version saved to: {text_filename}")
    
    # Print summary
    print("\nSummary:")
    print(f"Border color: {snapshot['border_color']}")
    for agent_name, data in snapshot['panes'].items():
        state = data['detected_state']
        print(f"  {agent_name}: {state}")
    
    print(f"\nTo share this snapshot, copy the contents of:\n  {text_filename}")
    print("\nOr run:")
    print(f"  cat {text_filename}")

if __name__ == "__main__":
    main()