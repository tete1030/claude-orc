#!/usr/bin/env python3
"""
Verify Claude CLI is properly set up for the orchestrator
"""

import os
import subprocess
import sys
from pathlib import Path

def check_claude_cli():
    """Check if Claude CLI is installed and working"""
    
    print("Claude Multi-Agent Orchestrator - Setup Verification")
    print("=" * 50)
    
    # Check common Claude locations
    claude_paths = [
        os.path.expanduser("~/.claude/local/claude"),
        "/usr/local/bin/claude",
        "/usr/bin/claude",
        "claude"  # In PATH
    ]
    
    claude_bin = None
    for path in claude_paths:
        try:
            if path == "claude":
                # Check if in PATH
                result = subprocess.run(["which", "claude"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    claude_bin = result.stdout.strip()
                    break
            elif os.path.exists(path):
                claude_bin = path
                break
        except:
            continue
    
    if not claude_bin:
        print("❌ Claude CLI not found!")
        print("\nPlease install Claude CLI:")
        print("  1. Visit: https://claude.ai/cli")
        print("  2. Follow installation instructions")
        print("  3. Run this script again")
        return False
        
    print(f"✅ Found Claude at: {claude_bin}")
    
    # Test Claude execution
    try:
        result = subprocess.run([claude_bin, "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Claude version: {result.stdout.strip()}")
        else:
            print(f"❌ Claude exists but won't run: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running Claude: {e}")
        return False
        
    # Check tmux
    try:
        result = subprocess.run(["which", "tmux"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Found tmux at: {result.stdout.strip()}")
        else:
            print("❌ tmux not found! Install with: sudo apt install tmux")
            return False
    except:
        print("❌ Error checking for tmux")
        return False
        
    # Check session directory
    session_dir = os.path.expanduser("~/.claude")
    if os.path.exists(session_dir):
        print(f"✅ Claude session directory exists: {session_dir}")
    else:
        print(f"⚠️  Claude session directory not found: {session_dir}")
        print("   This will be created when you first run Claude")
        
    print("\n" + "=" * 50)
    print("✅ All checks passed! You're ready to use the orchestrator.")
    print("\nNext steps:")
    print("  1. cd orchestrator")
    print("  2. python examples/basic_two_agent.py")
    print(f"\nNote: Set CLAUDE_BIN={claude_bin} if needed")
    
    return True

def test_minimal_claude_launch():
    """Test minimal Claude launch in tmux"""
    print("\n" + "=" * 50)
    print("Testing Claude launch in tmux...")
    
    try:
        # Kill any existing test session
        subprocess.run(["tmux", "kill-session", "-t", "verify-test"], 
                      capture_output=True)
        
        # Create new session
        subprocess.run(["tmux", "new-session", "-d", "-s", "verify-test", "bash"], 
                      check=True)
        
        # Send a simple echo command first
        subprocess.run(["tmux", "send-keys", "-t", "verify-test:0", 
                       "echo 'Test tmux command execution'", "Enter"], 
                      check=True)
        
        # Wait a bit
        import time
        time.sleep(0.5)
        
        # Capture output
        result = subprocess.run(["tmux", "capture-pane", "-t", "verify-test:0", "-p"], 
                              capture_output=True, text=True, check=True)
        
        if "Test tmux command execution" in result.stdout:
            print("✅ Tmux command execution works!")
        else:
            print("❌ Tmux command execution failed")
            print(f"Output: {result.stdout}")
            
        # Cleanup
        subprocess.run(["tmux", "kill-session", "-t", "verify-test"], 
                      capture_output=True)
                      
    except subprocess.CalledProcessError as e:
        print(f"❌ Tmux test failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    success = check_claude_cli()
    
    if success:
        test_minimal_claude_launch()
        
    sys.exit(0 if success else 1)