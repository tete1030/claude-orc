# Research Experiments

## Experiment 1: Find Claude Session Files

```bash
#!/bin/bash
# find_claude_sessions.sh
echo "=== Searching for Claude session files ==="

# Common locations to check
PATHS=(
    "$HOME/.claude"
    "$HOME/.config/claude"
    "$HOME/.local/share/claude"
    "$HOME/Library/Application Support/claude"
    "$HOME/.cache/claude"
)

for path in "${PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "Found Claude directory: $path"
        find "$path" -type f -name "*.json*" -o -name "*.log" | head -20
    fi
done

# Also search for any claude-related files modified recently
echo -e "\n=== Recently modified Claude files ==="
find ~ -name "*claude*" -type f -mtime -1 2>/dev/null | grep -v ".git" | head -20
```

## Experiment 2: Monitor Claude File Activity

```python
#!/usr/bin/env python3
# monitor_claude_files.py
"""
Run this WHILE using Claude to see what files it accesses
"""
import subprocess
import sys
import time

def monitor_with_lsof():
    """Use lsof to see what files Claude has open"""
    print("Monitoring Claude file activity (Ctrl+C to stop)...")
    
    while True:
        try:
            # Find Claude process
            ps_result = subprocess.run(
                ["pgrep", "-f", "claude"], 
                capture_output=True, 
                text=True
            )
            
            if ps_result.stdout:
                pid = ps_result.stdout.strip().split('\n')[0]
                
                # List open files
                lsof_result = subprocess.run(
                    ["lsof", "-p", pid], 
                    capture_output=True, 
                    text=True
                )
                
                # Filter for interesting files
                for line in lsof_result.stdout.split('\n'):
                    if any(x in line.lower() for x in ['json', 'session', 'chat', 'log']):
                        print(f"📁 {line}")
                
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\nStopped monitoring")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    monitor_with_lsof()
```

## Experiment 3: Test Claude CLI Options

```bash
#!/bin/bash
# test_claude_cli.sh
echo "=== Testing Claude CLI Options ==="

# Test 1: Basic help
echo -e "\n1. Claude help output:"
claude --help 2>&1 | grep -E "(prompt|context|system|role)" || echo "No prompt-related options found"

# Test 2: Chat help
echo -e "\n2. Claude chat help:"
claude chat --help 2>&1 | grep -E "(prompt|context|system|role)" || echo "No prompt options in chat"

# Test 3: Try various prompt options
echo -e "\n3. Testing potential prompt options:"

# Array of options to try
OPTIONS=(
    "--prompt"
    "--system-prompt"
    "--system"
    "--context"
    "--role"
    "--instruction"
    "--p"
    "-p"
)

for opt in "${OPTIONS[@]}"; do
    echo -n "Testing $opt: "
    claude chat $opt "Test prompt" --dry-run 2>&1 | grep -q "error" && echo "❌ Failed" || echo "✅ Might work"
done

# Test 4: Environment variables
echo -e "\n4. Checking for environment variables:"
env | grep -i claude
```

## Experiment 4: Test Tmux-Claude Integration

```python
#!/usr/bin/env python3
# test_tmux_claude.py
"""
Test how Claude behaves with tmux automation
"""
import subprocess
import time

class TmuxClaudeTest:
    def __init__(self):
        self.session = "claude-test"
        
    def setup(self):
        """Create test tmux session"""
        # Kill existing session
        subprocess.run(["tmux", "kill-session", "-t", self.session], capture_output=True)
        
        # Create new session
        subprocess.run(["tmux", "new-session", "-d", "-s", self.session])
        print(f"✅ Created tmux session: {self.session}")
        
    def test_send_keys(self):
        """Test various send-keys patterns"""
        tests = [
            ("Simple message", "Hello Claude"),
            ("Message with quotes", 'Test "quoted" text'),
            ("Special characters", "Test $PATH and %ENV%"),
            ("Multi-line", "Line 1\\nLine 2\\nLine 3"),
            ("XML-like", "<command>test</command>"),
            ("Long message", "A" * 200),
        ]
        
        for name, message in tests:
            print(f"\n🧪 Testing: {name}")
            
            # Send message
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session}:0", 
                message, "Enter"
            ])
            
            time.sleep(0.5)
            
            # Capture pane content
            result = subprocess.run([
                "tmux", "capture-pane", "-t", f"{self.session}:0", "-p"
            ], capture_output=True, text=True)
            
            # Check if message appears correctly
            if message in result.stdout:
                print(f"✅ Message sent correctly")
            else:
                print(f"❌ Issue with message delivery")
                print(f"   Expected: {message}")
                print(f"   Got: {result.stdout[-100:]}")  # Last 100 chars
    
    def test_rapid_sends(self):
        """Test timing issues with rapid messages"""
        print("\n🧪 Testing rapid message sending:")
        
        for i in range(5):
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session}:0",
                f"Message {i}", "Enter"
            ])
            # No delay - testing rapid fire
        
        time.sleep(1)
        
        # Check results
        result = subprocess.run([
            "tmux", "capture-pane", "-t", f"{self.session}:0", "-p"
        ], capture_output=True, text=True)
        
        # Count how many messages made it
        count = sum(1 for i in range(5) if f"Message {i}" in result.stdout)
        print(f"✅ {count}/5 messages delivered successfully")
        
    def cleanup(self):
        """Clean up test session"""
        subprocess.run(["tmux", "kill-session", "-t", self.session])
        print("✅ Cleaned up test session")

if __name__ == "__main__":
    test = TmuxClaudeTest()
    test.setup()
    
    print("=== Testing Tmux-Claude Integration ===\n")
    print("NOTE: Start Claude in the tmux session manually:")
    print(f"  tmux attach -t {test.session}")
    print("  Then run: claude chat")
    print("\nPress Enter when Claude is running...")
    input()
    
    test.test_send_keys()
    test.test_rapid_sends()
    
    print("\n✅ Tests complete!")
    print(f"View session: tmux attach -t {test.session}")
    
    print("\nClean up? (y/n): ", end="")
    if input().lower() == 'y':
        test.cleanup()
```

## Experiment 5: Session File Format Analysis

```python
#!/usr/bin/env python3
# analyze_session_format.py
"""
Once we find session files, analyze their format
"""
import json
import os
import sys

def analyze_json_file(filepath):
    """Analyze JSON/JSONL session file"""
    print(f"\n📄 Analyzing: {filepath}")
    print(f"Size: {os.path.getsize(filepath)} bytes")
    
    try:
        # Try as JSON first
        with open(filepath, 'r') as f:
            data = json.load(f)
            print("Format: JSON")
            print(f"Type: {type(data)}")
            
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())[:10]}")
            elif isinstance(data, list):
                print(f"Items: {len(data)}")
                if data:
                    print(f"First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
                    
    except json.JSONDecodeError:
        # Try as JSONL
        print("Format: JSONL (JSON Lines)")
        with open(filepath, 'r') as f:
            lines = f.readlines()
            print(f"Lines: {len(lines)}")
            
            # Parse first few lines
            for i, line in enumerate(lines[:3]):
                try:
                    data = json.loads(line)
                    print(f"Line {i} keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                except:
                    print(f"Line {i}: Failed to parse")
    
    # Look for command patterns
    print("\n🔍 Searching for command patterns:")
    with open(filepath, 'r') as f:
        content = f.read()
        
        patterns = [
            "<orc-command",
            "[FROM:",
            "message",
            "content",
            "role",
            "assistant",
            "user"
        ]
        
        for pattern in patterns:
            count = content.count(pattern)
            if count > 0:
                print(f"  '{pattern}': {count} occurrences")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_json_file(sys.argv[1])
    else:
        print("Usage: python analyze_session_format.py <session_file>")
        print("\nSearching for session files to analyze...")
        
        # Search for files
        import subprocess
        result = subprocess.run(
            ["find", os.path.expanduser("~"), "-name", "*claude*", "-name", "*.json*", "-type", "f"],
            capture_output=True,
            text=True
        )
        
        files = [f for f in result.stdout.split('\n') if f and 'session' in f.lower()]
        
        if files:
            print(f"\nFound {len(files)} potential session files:")
            for f in files[:5]:
                print(f"  {f}")
                analyze_json_file(f)
        else:
            print("No session files found")
```

## Quick Research Checklist

Run these experiments in order:

1. **Find Session Files** (5 min)
   ```bash
   ./find_claude_sessions.sh
   ```

2. **Monitor File Activity** (10 min)
   ```bash
   # Terminal 1: Start monitoring
   python monitor_claude_files.py
   
   # Terminal 2: Use Claude normally
   claude chat
   # Have a conversation, use commands
   ```

3. **Test CLI Options** (5 min)
   ```bash
   ./test_claude_cli.sh
   ```

4. **Test Tmux Integration** (15 min)
   ```bash
   python test_tmux_claude.py
   ```

5. **Analyze Session Format** (10 min)
   ```bash
   python analyze_session_format.py /path/to/session/file
   ```

## Research Log Template

```markdown
## Research Results

### Session Files
- **Location Found**: 
- **Format**: JSON / JSONL / Other
- **Update Frequency**: 
- **Key Structure**: 

### CLI Options
- **Working Prompt Option**: 
- **Syntax**: 
- **Limitations**: 

### Tmux Integration
- **Send-keys Reliability**: 
- **Special Character Handling**: 
- **Timing Requirements**: 

### Identified Risks
1. 
2. 
3. 

### Recommended Approach
Based on research:
- Use [X] for session monitoring because...
- Use [Y] for prompt injection because...
- Handle [Z] edge case by...
```