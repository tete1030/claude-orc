# Minimal Test Script for Phase 1

## Purpose

A simple Python script to test the core concept before building the full system. This helps verify our assumptions about Claude session files and tmux control.

## Test Script: `minimal_test.py`

```python
#!/usr/bin/env python3
"""
Minimal test of two-agent communication concept
Run this to verify basic assumptions before full implementation
"""

import subprocess
import time
import re
import os

class MinimalOrchestrator:
    def __init__(self):
        self.session_name = "test-agents"
        self.command_pattern = re.compile(
            r'<orc-command type="send_message">(.*?)</orc-command>',
            re.DOTALL
        )
        
    def setup_tmux(self):
        """Create tmux session with two panes"""
        print("Setting up tmux session...")
        
        # Kill existing session if any
        subprocess.run(["tmux", "kill-session", "-t", self.session_name], 
                      capture_output=True)
        
        # Create new session with two panes
        subprocess.run([
            "tmux", "new-session", "-d", "-s", self.session_name
        ])
        subprocess.run([
            "tmux", "split-window", "-h", "-t", f"{self.session_name}:0"
        ])
        
        print("✓ Tmux session created with 2 panes")
        
    def send_to_pane(self, pane_index, message):
        """Send message to specific pane"""
        target = f"{self.session_name}:0.{pane_index}"
        
        # Escape single quotes in message
        escaped_msg = message.replace("'", "'\"'\"'")
        
        subprocess.run([
            "tmux", "send-keys", "-t", target, escaped_msg, "Enter"
        ])
        
    def simulate_agent_message(self, from_agent, to_agent, content):
        """Simulate what an agent would send"""
        command = f"""<orc-command type="send_message">
  <from>{from_agent}</from>
  <to>{to_agent}</to>
  <title>Test message</title>
  <content>{content}</content>
</orc-command>"""
        
        print(f"\n📤 {from_agent} sending command:")
        print(command)
        
        # In real system, this would be detected from session file
        # For now, we'll process it directly
        self.process_command(command, from_agent)
        
    def process_command(self, command_text, from_agent):
        """Process orc-command"""
        # Extract fields (simplified parsing)
        from_match = re.search(r'<from>(.*?)</from>', command_text)
        to_match = re.search(r'<to>(.*?)</to>', command_text)
        content_match = re.search(r'<content>(.*?)</content>', command_text, re.DOTALL)
        
        if not all([from_match, to_match, content_match]):
            print("❌ Failed to parse command")
            return
            
        to_agent = to_match.group(1).strip()
        content = content_match.group(1).strip()
        
        # Format message with identity prefix
        formatted_msg = f"[FROM: {from_agent}] {content}"
        
        print(f"📥 Delivering to {to_agent}: {formatted_msg}")
        
        # Determine target pane
        pane_index = 0 if to_agent == "master_agent" else 1
        
        # Send via tmux
        self.send_to_pane(pane_index, formatted_msg)
        
    def demo_conversation(self):
        """Demonstrate a conversation between agents"""
        print("\n🚀 Starting demo conversation...\n")
        
        # Master assigns task
        self.simulate_agent_message(
            "Master Agent",
            "Worker Agent",
            "Please analyze the project structure and count Python files"
        )
        
        time.sleep(2)
        
        # Worker responds
        self.simulate_agent_message(
            "Worker Agent", 
            "Master Agent",
            "I found 15 Python files in 3 directories. Analysis complete."
        )
        
        time.sleep(2)
        
        # Master acknowledges
        self.simulate_agent_message(
            "Master Agent",
            "Worker Agent", 
            "Good work. Please proceed with the next task."
        )
        
    def show_panes(self):
        """Display what's in each pane"""
        print("\n📺 Current pane contents:")
        
        for i in range(2):
            print(f"\n--- Pane {i} ---")
            result = subprocess.run([
                "tmux", "capture-pane", "-t", f"{self.session_name}:0.{i}", "-p"
            ], capture_output=True, text=True)
            
            if result.stdout:
                print(result.stdout)
            else:
                print("(empty)")

if __name__ == "__main__":
    print("=== Minimal Two-Agent Orchestrator Test ===\n")
    
    orch = MinimalOrchestrator()
    
    # Set up environment
    orch.setup_tmux()
    
    # Simulate conversation
    orch.demo_conversation()
    
    # Show results
    orch.show_panes()
    
    print("\n✅ Test complete!")
    print(f"💡 View live session: tmux attach -t {orch.session_name}")
    print(f"🧹 Clean up: tmux kill-session -t {orch.session_name}")
```

## How to Run

1. Save as `minimal_test.py`
2. Make executable: `chmod +x minimal_test.py`
3. Run: `./minimal_test.py`

## Expected Output

```
=== Minimal Two-Agent Orchestrator Test ===

Setting up tmux session...
✓ Tmux session created with 2 panes

🚀 Starting demo conversation...

📤 Master Agent sending command:
<orc-command type="send_message">
  <from>Master Agent</from>
  <to>Worker Agent</to>
  <title>Test message</title>
  <content>Please analyze the project structure and count Python files</content>
</orc-command>
📥 Delivering to Worker Agent: [FROM: Master Agent] Please analyze the project structure and count Python files

📤 Worker Agent sending command:
<orc-command type="send_message">
  <from>Worker Agent</from>
  <to>Master Agent</to>
  <title>Test message</title>
  <content>I found 15 Python files in 3 directories. Analysis complete.</content>
</orc-command>
📥 Delivering to Master Agent: [FROM: Worker Agent] I found 15 Python files in 3 directories. Analysis complete.

📺 Current pane contents:

--- Pane 0 ---
[FROM: Worker Agent] I found 15 Python files in 3 directories. Analysis complete.

--- Pane 1 ---
[FROM: Master Agent] Please analyze the project structure and count Python files
[FROM: Master Agent] Good work. Please proceed with the next task.

✅ Test complete!
```

## What This Tests

1. **Tmux Control**: Can we create panes and send messages?
2. **Message Routing**: Can we route messages to correct panes?
3. **Identity Prefixing**: Do prefixes appear correctly?
4. **Command Parsing**: Can we extract command fields?

## Next Steps

If this test works:
1. Add real session file monitoring
2. Integrate with actual Claude agents
3. Add proper error handling
4. Build full orchestrator

If issues arise:
1. Debug tmux commands
2. Adjust message formatting
3. Check permissions
4. Verify assumptions