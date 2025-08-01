#!/usr/bin/env python3
"""
Show current state detection for all panes - quick diagnostic tool
"""

import subprocess
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tmux_manager import TmuxManager
from src.agent_state_monitor import AgentStateMonitor

def main():
    session_name = "team-mcp-demo"
    
    # Check if session exists
    result = subprocess.run(['tmux', 'has-session', '-t', session_name], capture_output=True)
    if result.returncode != 0:
        print(f"Error: No tmux session '{session_name}' found")
        sys.exit(1)
    
    tmux = TmuxManager(session_name)
    monitor = AgentStateMonitor(tmux)
    
    agents = ["Leader", "Researcher", "Writer"]
    
    print("Current State Detection:")
    print("-" * 40)
    
    for i in range(3):
        agent_name = agents[i]
        
        # Capture pane content
        content = tmux.capture_pane(i, history_limit=-20)
        if not content:
            print(f"{agent_name}: [CAPTURE FAILED]")
            continue
            
        # Detect state
        state = monitor.detect_agent_state(content, agent_name)
        
        # Check for key indicators
        lines = content.strip().split('\n')
        has_prompt = any('│' in line and '>' in line for line in lines[-5:])
        has_processing = any('…' in line for line in lines[-5:])
        
        # Find prompt content if any
        prompt_content = ""
        for line in lines[-5:]:
            if '│' in line and '>' in line:
                # Extract text after >
                parts = line.split('>')
                if len(parts) > 1:
                    text = parts[1].split('│')[0].strip()
                    if text:
                        prompt_content = f" (text: '{text[:20]}...')" if len(text) > 20 else f" (text: '{text}')"
        
        status_info = []
        if has_processing:
            status_info.append("PROCESSING")
        if has_prompt:
            status_info.append("PROMPT")
        
        print(f"{agent_name}: {state.value.upper():<12} [{', '.join(status_info)}]{prompt_content}")
    
    # Show border color
    result = subprocess.run([
        'tmux', 'show-options', '-w', '-t', session_name, 'pane-border-style'
    ], capture_output=True, text=True)
    
    if result.returncode == 0 and '=' in result.stdout:
        border_color = result.stdout.strip().split('=')[-1].replace('fg=', '')
        print(f"\nBorder color: {border_color}")

if __name__ == "__main__":
    main()