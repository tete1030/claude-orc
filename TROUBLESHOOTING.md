# TROUBLESHOOTING.md

## Lessons Learned from Recent Debug Sessions

### 1. Timing Issues with Background Threads

**Problem**: State monitoring thread started 30+ seconds late
**Root Cause**: Parent orchestrator's `start()` method had multiple `time.sleep()` calls totaling ~26 seconds
**Debug Approach**:
- Created comprehensive timing diagnostic script that logs events with timestamps
- Ran orchestrator subprocess while capturing output and pane content in parallel
- Used event-based logging to identify exact delays

**Solution**: Override parent methods cleanly without inheriting delays
**Key Learning**: When inheriting from a class with timing issues, don't just call `super().method()` - understand what it does and potentially reimplement the necessary parts

### 2. Terminal Rendering Issues

**Problem**: Unicode emojis causing tmux status bar to wrap to 2 lines
**Root Cause**: Terminal emojis can be double-width characters, breaking layout
**Debug Approach**:
- Tested different terminal representations (emojis, ASCII, colors)
- Created visual test script to compare options

**Solution**: Use tmux color codes instead of emojis
**Key Learning**: Always provide ASCII alternatives for terminal UIs

### 3. Visual Feedback Flashing

**Problem**: Pane borders flashing/flickering
**Root Cause**: Updating tmux properties every 0.5s even when nothing changed
**Debug Approach**:
- Added state tracking to see update frequency
- Tested tmux capabilities separately

**Solution**: Only update visual elements when state actually changes
**Key Learning**: Track previous state to avoid redundant updates

### 4. Testing Complex Timing Scenarios

**Problem**: Multiple interacting components with timing dependencies
**Debug Approach**:
```python
# Create comprehensive test that captures everything
class TimingDiagnostic:
    def __init__(self):
        self.start_time = time.time()
        self.events = []
        
    def log_event(self, event, data=None):
        elapsed = time.time() - self.start_time
        self.events.append({
            'time': elapsed,
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'data': data
        })
```

**Key Learning**: When debugging timing, capture EVERYTHING - subprocess output, tmux pane content, event timestamps

### 5. Tmux Capability Testing

**Problem**: Not sure which tmux features are supported
**Debug Approach**:
```python
# Test specific features in isolation
try:
    subprocess.run(["tmux", "set-option", "-p", ...], check=True)
    print("Feature supported!")
except subprocess.CalledProcessError:
    print("Feature not supported")
```

**Key Learning**: Test terminal/tmux features separately before implementing

### 6. State Detection Pattern Matching

**Problem**: Agent states not being detected correctly
**Root Cause**: Complex regex patterns and pane content parsing
**Debug Approach**:
- Capture raw pane content to files
- Test regex patterns against real content
- Add debug logging for content length and matches

**Solution**: Simplify patterns and handle edge cases
**Key Learning**: Always capture and save real data for pattern testing

### 7. BUSY State Detection with New Tip Messages (2025-08-14)

**Problem**: Agents showing as IDLE when processing indicators were present
**Root Cause**: New tip messages appearing after processing indicators (like "Tip:", "⎿", "/statusline") were not in the allowed_patterns, causing state detection issues
**Debug Approach**:
- Analyzed actual tmux pane content during busy states
- Identified new tip message patterns that appear after processing
- Tested pattern matching against real processing indicators

**Solution**: Added 'Tip:', '⎿', and '/statusline' to allowed_patterns in `agent_state_monitor.py` to handle the new tip messages
**Key Learning**: BUSY_PATTERNS should not be changed (marked DO NOT CHANGE), but allowed_patterns can be updated to handle new UI elements that appear alongside processing indicators. Line numbers only appear in tmux capture output for display, not in actual pane content.
**Special Note**: Always check if patterns are marked as unchangeable before modifying them.

## Debug Methodology That Works

### 1. Single Comprehensive Test Script
Instead of multiple bash commands, write ONE script that:
- Sets up the test environment
- Captures all relevant data
- Runs the test
- Analyzes results
- Outputs clear findings

### 2. Parallel Data Collection
When timing is critical:
```python
# Run capture in thread while main process runs
capture_thread = threading.Thread(target=capture_continuously)
capture_thread.start()

# Run main process
main_process = subprocess.Popen(...)

# Capture provides timeline of what happened
```

### 3. Visual Testing for Terminal UIs
Always create visual test scripts for UI elements:
```python
formats = [
    ("Option 1", "format_string_1"),
    ("Option 2", "format_string_2"),
]
for name, format_str in formats:
    print(f"Testing: {name}")
    apply_format(format_str)
    time.sleep(2)  # Visual inspection
```

### 4. State Change Tracking
Prevent unnecessary updates:
```python
previous_states = {}
while True:
    state = get_current_state()
    if previous_states.get(key) != state:
        update_ui(state)
        previous_states[key] = state
```

## Common Pitfalls to Avoid

1. **Don't trust timing** - What looks instant might take 30 seconds
2. **Don't update UI every loop** - Only update on changes
3. **Don't assume terminal capabilities** - Test everything
4. **Don't use complex inheritance** - Sometimes rewriting is cleaner
5. **Don't debug with print()** - Use proper logging with timestamps

## Useful Diagnostic Patterns

### Check What's Actually Happening
```python
# Capture everything
subprocess.run(['tmux', 'capture-pane', '-p'], capture_output=True)

# Log with timestamps
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/debug.log'),
        logging.StreamHandler()
    ]
)
```

### Test in Isolation
Before integrating, always test the specific feature alone:
- Tmux capabilities
- Terminal rendering  
- Pattern matching
- Timing behavior

## Remember for Next Time

1. **Start with diagnostic script** - Don't debug production code directly
2. **Capture parallel timelines** - Main process + monitoring + state changes
3. **Test visually** - Terminal UIs need human verification
4. **Track previous state** - Avoid redundant updates
5. **Use subprocess correctly** - `PYTHONUNBUFFERED=1` for real-time output
6. **Save everything** - Captured data, events, logs for analysis