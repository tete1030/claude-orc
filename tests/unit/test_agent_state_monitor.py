"""
Comprehensive unit tests for AgentStateMonitor

This test suite ensures that agent state detection works correctly across
all scenarios we've encountered, preventing regression of fixed issues.

Key test areas:
1. Basic state detection (idle, busy, writing, error, quit, unknown)
2. Edge cases with welcome boxes and multiple prompt boxes
3. Claude suggestion handling (should not be detected as writing)
4. Processing indicator patterns with various spinners
5. State transitions and initialization handling
6. Message queuing based on agent states
"""

import unittest
from unittest.mock import MagicMock, patch
import time
import sys
from pathlib import Path

# Fix import path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent_state_monitor import (
    AgentStateMonitor, AgentState, AgentStatus
)


class TestAgentStateMonitor(unittest.TestCase):
    """Test agent state monitoring functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_tmux = MagicMock()
        self.monitor = AgentStateMonitor(self.mock_tmux)
        
    def _set_agent_as_initialized(self, agent_name="TestAgent"):
        """Helper to set agent as initialized (not in startup phase)"""
        self.monitor.agent_states[agent_name] = AgentStatus(
            state=AgentState.UNKNOWN,
            last_update=0,
            initialization_time=0  # Very old, so not initializing
        )
        
    def test_detect_idle_state_with_prompt_box(self):
        """Test detection of idle state with prompt box"""
        pane_content = """
[DEBUG] Some previous output
Ready for input

╭──────────────────────────────────────╮
│ >                                    │
╰──────────────────────────────────────╯
  ? for shortcuts           Debug mode
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.IDLE)
        
    def test_detect_busy_state_with_processing(self):
        """Test detection of busy state - requires proper structure"""
        pane_content = """
> Request

· Processing… (1s)

╭──────────────────────────────────────╮
│ >                                    │
╰──────────────────────────────────────╯
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.BUSY)
        
    def test_detect_error_state(self):
        """Test detection of error state"""
        pane_content = """
Error: MCP error -32603: Cannot connect to host localhost:8767
Failed to initialize connection
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.ERROR)
        
    def test_detect_quit_state(self):
        """Test detection of quit state"""
        pane_content = """
Saving session...
Goodbye!
Process terminated with exit code 0
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.QUIT)
        
    def test_update_agent_state_creates_new_status(self):
        """Test that updating state creates new agent status"""
        # For a new agent, first update is always INITIALIZING
        self.mock_tmux.capture_pane.return_value = "│ > │"
        
        state = self.monitor.update_agent_state("TestAgent", 0)
        
        self.assertEqual(state, AgentState.INITIALIZING)  # First update is always initializing
        self.assertIn("TestAgent", self.monitor.agent_states)
        self.assertEqual(self.monitor.agent_states["TestAgent"].state, AgentState.INITIALIZING)
        
    def test_update_agent_state_tracks_changes(self):
        """Test that state changes are tracked"""
        # First update - initializing
        self.mock_tmux.capture_pane.return_value = "│ > │"
        self.monitor.update_agent_state("TestAgent", 0)
        
        # Mark as initialized and set to idle
        self.monitor.agent_states["TestAgent"].initialization_time = 0
        self.mock_tmux.capture_pane.return_value = "│ > │"
        self.monitor.update_agent_state("TestAgent", 0)
        
        # Now update to busy with proper format
        self.mock_tmux.capture_pane.return_value = """
> Test

✽ Processing… (5s)

╭──────────────────────────────────────╮
│ >                                    │
╰──────────────────────────────────────╯
"""
        with patch.object(self.monitor.logger, 'info') as mock_log:
            state = self.monitor.update_agent_state("TestAgent", 0)
            
        self.assertEqual(state, AgentState.BUSY)
        # Since the simple "│ > │" pattern is detected as WRITING, not IDLE, the transition is writing -> busy
        mock_log.assert_called_with("Agent TestAgent state changed: writing -> busy")
        
    def test_is_agent_busy(self):
        """Test busy state checking"""
        # Agent not registered
        self.assertFalse(self.monitor.is_agent_busy("Unknown"))
        
        # Set agent as busy
        self.monitor.agent_states["TestAgent"] = AgentStatus(
            state=AgentState.BUSY,
            last_update=time.time()
        )
        self.assertTrue(self.monitor.is_agent_busy("TestAgent"))
        
    def test_queue_message_for_agent(self):
        """Test message queueing"""
        message = {"from": "Sender", "content": "Test message"}
        
        self.monitor.queue_message_for_agent("TestAgent", message)
        
        self.assertIn("TestAgent", self.monitor.agent_states)
        self.assertEqual(len(self.monitor.agent_states["TestAgent"].pending_messages), 1)
        self.assertEqual(self.monitor.agent_states["TestAgent"].messages_sent_while_busy, 1)
        
    def test_get_pending_messages_clears_queue(self):
        """Test that getting pending messages clears the queue"""
        message1 = {"from": "Sender1", "content": "Message 1"}
        message2 = {"from": "Sender2", "content": "Message 2"}
        
        self.monitor.queue_message_for_agent("TestAgent", message1)
        self.monitor.queue_message_for_agent("TestAgent", message2)
        
        messages = self.monitor.get_pending_messages("TestAgent")
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], message1)
        self.assertEqual(messages[1], message2)
        
        # Queue should be cleared
        self.assertEqual(len(self.monitor.agent_states["TestAgent"].pending_messages), 0)
        self.assertEqual(self.monitor.agent_states["TestAgent"].messages_sent_while_busy, 0)
        
    def test_has_pending_messages(self):
        """Test checking for pending messages"""
        self.assertFalse(self.monitor.has_pending_messages("Unknown"))
        
        self.monitor.queue_message_for_agent("TestAgent", {"content": "test"})
        self.assertTrue(self.monitor.has_pending_messages("TestAgent"))
        
        self.monitor.get_pending_messages("TestAgent")
        self.assertFalse(self.monitor.has_pending_messages("TestAgent"))
        
    def test_get_agent_summary(self):
        """Test getting summary of all agents"""
        # Set up some agents
        self.monitor.agent_states["Agent1"] = AgentStatus(
            state=AgentState.IDLE,
            last_update=time.time()
        )
        self.monitor.agent_states["Agent2"] = AgentStatus(
            state=AgentState.BUSY,
            last_update=time.time()
        )
        self.monitor.queue_message_for_agent("Agent2", {"content": "test"})
        
        summary = self.monitor.get_agent_summary()
        
        self.assertIn("Agent1", summary)
        self.assertIn("Agent2", summary)
        self.assertEqual(summary["Agent1"]["state"], "idle")
        self.assertEqual(summary["Agent2"]["state"], "busy")
        self.assertEqual(summary["Agent2"]["pending_messages"], 1)
        
    def test_idle_detection_with_prompt_character(self):
        """Test detection with simple prompt pattern"""
        # The implementation looks for specific patterns - this one has extra space which is detected as text
        self._set_agent_as_initialized()
        # Test case 1: Pattern that looks like writing (space after >)
        pane_content = """
Some output
Another line
│ >  │
"""
        state = self.monitor.detect_agent_state(pane_content, "TestAgent")
        self.assertEqual(state, AgentState.WRITING, "Space after > should be detected as WRITING")
        
        # Test case 2: True idle pattern (properly formatted)
        pane_content2 = """
╭────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""
        state2 = self.monitor.detect_agent_state(pane_content2, "TestAgent")
        self.assertEqual(state2, AgentState.IDLE, "Properly formatted empty prompt should be IDLE")
        
    def test_writing_state_detection(self):
        """Test writing state when there's text in the prompt box"""
        pane_content = """
Some output
Another line
│ > check_messages │
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.WRITING)
        
    def test_unknown_state_detection(self):
        """Test unknown state when patterns don't match"""
        pane_content = """
Some random output
Without any specific patterns
Just text
"""
        state = self.monitor.detect_agent_state(pane_content)
        self.assertEqual(state, AgentState.UNKNOWN)
    
    # New comprehensive tests to prevent regression of fixed issues
    
    def test_claude_suggestion_not_detected_as_writing(self):
        """Test that Claude's 'Try ...' suggestions are not detected as WRITING state"""
        self._set_agent_as_initialized()
        pane_content = """
> System initialized. You are Leader agent with MCP tools available.

╭────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ > Try "list_agents" to see your team                                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ? for shortcuts                                                                  Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(pane_content, "TestAgent")
        self.assertEqual(state, AgentState.IDLE, "Claude suggestions should not trigger WRITING state")
    
    def test_busy_state_with_proper_structure(self):
        """Test BUSY state detection with processing indicator above prompt box"""
        self._set_agent_as_initialized()
        pane_content = """
> System initialized. You are Leader agent with MCP tools available.

· Ruminating… (3s · ↓ 14 tokens · esc to interrupt)

╭────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ? for shortcuts                                                                  Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(pane_content, "TestAgent")
        self.assertEqual(state, AgentState.BUSY, "Should detect BUSY with processing indicator")
    
    def test_busy_state_with_welcome_box_present(self):
        """Test BUSY detection when Claude welcome box is also visible"""
        self._set_agent_as_initialized()
        pane_content = """
╭───────────────────────────────────────────────────╮
│ ✻ Welcome to Claude Code!                         │
│                                                   │
│   /help for help, /status for your current setup  │
│                                                   │
│   cwd: /home/texotqi/Documents/claude-orc         │
╰───────────────────────────────────────────────────╯

 ※ Tip: Did you know you can drag and drop image files into your terminal?

> System initialized. You are Leader agent with MCP tools available.

✽ Stewing… (3s · ↑ 0 tokens · esc to interrupt)

╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ? for shortcuts                                                                 Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(pane_content, "TestAgent")
        self.assertEqual(state, AgentState.BUSY, 
                        "Should detect BUSY even with welcome box present (finds correct prompt box)")
    
    def test_various_processing_indicators(self):
        """Test detection of various processing indicator spinners and words"""
        self._set_agent_as_initialized()
        
        spinners = ['·', '✻', '✽', '◐', '◓', '◑', '◒']
        actions = ['Ruminating', 'Stewing', 'Cooking', 'Processing', 'Thinking', 
                  'Accomplishing', 'Flibbertigibbeting', 'Perusing']
        
        for spinner in spinners[:3]:  # Test a few spinners
            for action in actions[:3]:  # Test a few actions
                pane_content = f"""
> Test

{spinner} {action}… (1s)

╭────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""
                state = self.monitor.detect_agent_state(pane_content, "TestAgent")
                self.assertEqual(state, AgentState.BUSY, 
                               f"Should detect BUSY with spinner '{spinner}' and action '{action}'")
    
    def test_processing_without_empty_line_not_busy(self):
        """Test that processing indicator without empty line is not detected as BUSY"""
        self._set_agent_as_initialized()
        pane_content = """
> Test
· Processing… (1s)
╭────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""
        state = self.monitor.detect_agent_state(pane_content, "TestAgent")
        self.assertNotEqual(state, AgentState.BUSY, 
                           "Should NOT detect BUSY without empty line between indicator and prompt")
    
    def test_multiline_user_input(self):
        """Test detection of multiline user input as WRITING"""
        self._set_agent_as_initialized()
        pane_content = """
> Previous message sent.

╭────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ > send_message to: Researcher message: "Please research the latest AI trends and                       │
│   report back with a summary"                                                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ? for shortcuts                                                                  Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(pane_content, "TestAgent")
        self.assertEqual(state, AgentState.WRITING, "Should detect WRITING with multiline input")
    
    def test_error_with_prompt_is_idle(self):
        """Test that error followed by prompt box means agent recovered (IDLE)"""
        self._set_agent_as_initialized()
        pane_content = """
> System initialized. You are Leader agent with MCP tools available.

Error: MCP error -32603: 'MessageDeliverySystem' object has no attribute 'queue_message'

╭────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ? for shortcuts                                                                  Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(pane_content, "TestAgent")
        self.assertEqual(state, AgentState.IDLE, 
                        "Error followed by prompt box means agent recovered - should be IDLE")
    
    def test_initialization_state_detection(self):
        """Test INITIALIZING state detection for new agents"""
        # First, test that update_agent_state returns INITIALIZING for new agents
        self.mock_tmux.capture_pane.return_value = "Starting..."
        state = self.monitor.update_agent_state("BrandNewAgent", 0)
        self.assertEqual(state, AgentState.INITIALIZING, 
                        "First update for new agent should always be INITIALIZING")
    
    def test_quit_state_patterns(self):
        """Test various quit/exit patterns"""
        self._set_agent_as_initialized()
        quit_patterns = [
            "Goodbye!",
            "Session ended.",
            "[Process docker terminated]",  # Updated to match new specific pattern
            "Process exited with status 0",  # Updated to match new specific pattern
        ]
        
        for pattern in quit_patterns:
            pane_content = f"""
Some previous output
{pattern}
"""
            state = self.monitor.detect_agent_state(pane_content, "TestAgent")
            self.assertEqual(state, AgentState.QUIT, f"Should detect QUIT with pattern '{pattern}'")
    
    def test_state_transition_sequence(self):
        """Test realistic sequence of state transitions"""
        agent_name = "TestAgent"
        
        # Simulate state transitions
        transitions = [
            # (pane_content, expected_state)
            ("$ bash prompt", AgentState.INITIALIZING),
            ("│ > │", AgentState.WRITING),  # Simple prompt is detected as WRITING
            ("│ > list_agents │", AgentState.WRITING),
            ("· Processing… (1s)\n\n╭────╮\n│ > │\n╰────╯", AgentState.BUSY),  # Need proper box structure
            ("╭────╮\n│ > │\n╰────╯", AgentState.IDLE),  # Proper empty box for IDLE
        ]
        
        for i, (content, expected) in enumerate(transitions):
            self.mock_tmux.capture_pane.return_value = content
            state = self.monitor.update_agent_state(agent_name, 0)
            
            # After first transition, mark as initialized
            if i > 0:
                self.monitor.agent_states[agent_name].initialization_time = 0
            
            # For this simple test, we'll check the detected state
            # Note: actual state might differ due to initialization logic
            if i > 1:  # Skip first two due to initialization behavior
                detected = self.monitor.detect_agent_state(content, agent_name)
                self.assertEqual(detected, expected, 
                               f"Transition {i}: Expected {expected} for content: {content[:50]}...")


    def test_busy_state_with_message_notification(self):
        """Test BUSY state detection with message notification between indicator and prompt"""
        content = '''Some previous content

⠙ Reviewing… (3s)
[MESSAGE] You have a new message from Leader. Check it when convenient using 'check_messages' - no need to interrupt your current task unless urgent.

╭─ Enter your message ──────────────────────────────────────────────────╮
│ >                                                                      │
╰────────────────────────────────────────────────────────────────────────╯'''
        
        # Mark agent as initialized first
        self._set_agent_as_initialized()
        state = self.monitor.detect_agent_state(content, "TestAgent")
        self.assertEqual(state, AgentState.BUSY)
    
    def test_busy_state_with_multiple_notifications(self):
        """Test BUSY state with multiple message notifications"""
        content = '''✸ Analyzing… (1s)
↓ 523 tokens
[MESSAGE] You have a new message from Architect. Check it when convenient using 'check_messages' - no need to interrupt your current task unless urgent.
[MESSAGE] Reminder: You have 3 unread message(s) in your mailbox. Use 'check_messages' to read them.

╭─ Enter your message ──────────────────────────────────────────────────╮
│ >                                                                      │
╰────────────────────────────────────────────────────────────────────────╯'''
        
        # Mark agent as initialized first
        self._set_agent_as_initialized()
        state = self.monitor.detect_agent_state(content, "TestAgent")
        self.assertEqual(state, AgentState.BUSY)

    def test_false_quit_detection_prevention(self):
        """Test that vague process termination messages don't trigger QUIT state"""
        self._set_agent_as_initialized()
        
        # Content with vague "Process terminated" that should NOT trigger QUIT
        false_quit_content = """
Previous conversation...
Process terminated unexpectedly
But agent recovered...

╭─────────────────────────────────────────────────────────────╮
│ >                                                           │
╰─────────────────────────────────────────────────────────────╯
  ? for shortcuts                       Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(false_quit_content, "TestAgent")
        self.assertEqual(state, AgentState.IDLE, "Vague 'Process terminated' should not trigger QUIT")
        
        # Content with specific termination that SHOULD trigger QUIT
        real_quit_content = """
Previous conversation...
[Process docker terminated]
Agent has exited
"""
        state = self.monitor.detect_agent_state(real_quit_content, "TestAgent")
        self.assertEqual(state, AgentState.QUIT, "Specific termination pattern should trigger QUIT")

    def test_feedback_prompt_ui_filtering(self):
        """Test that Claude's feedback prompt UI doesn't interfere with state detection"""
        self._set_agent_as_initialized()
        
        # Feedback prompt with idle state
        feedback_idle_content = """
Some conversation...

How is Claude doing this session?
1: Bad  2: Fine  3: Good  0: Dismiss

╭─────────────────────────────────────────────────────────────╮
│ >                                                           │
╰─────────────────────────────────────────────────────────────╯
  ? for shortcuts                       Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(feedback_idle_content, "TestAgent")
        self.assertEqual(state, AgentState.IDLE, "Feedback prompt should not interfere with IDLE detection")
        
        # Feedback confirmation with processing
        feedback_busy_content = """
Some conversation...

✓ Thanks for helping make Claude better!

✻ Processing… (2s · esc to interrupt)

╭─────────────────────────────────────────────────────────────╮
│ >                                                           │
╰─────────────────────────────────────────────────────────────╯
  ? for shortcuts                       Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(feedback_busy_content, "TestAgent")
        self.assertEqual(state, AgentState.BUSY, "Feedback confirmation should not interfere with BUSY detection")

    def test_post_feedback_state_detection(self):
        """Test state detection after feedback UI has appeared"""
        self._set_agent_as_initialized()
        
        # Post-feedback idle state (based on snapshot 20250803_160245.txt)
        post_feedback_content = """
  ⎿  Message sent to Architect

✓ Thanks for helping make Claude better!

╭─────────────────────────────────────────────────────────────╮
│ >                                                           │
╰─────────────────────────────────────────────────────────────╯
  ? for shortcuts                       Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(post_feedback_content, "TestAgent")
        self.assertEqual(state, AgentState.IDLE, "Should correctly detect IDLE after feedback confirmation")
        
        # Multiple feedback interactions should still work
        multiple_feedback_content = """
Previous conversation...

How is Claude doing this session?
1: Bad  2: Fine  3: Good  0: Dismiss

✓ Thanks for helping make Claude better!

More conversation...

✓ Thanks for helping make Claude better!

╭─────────────────────────────────────────────────────────────╮
│ >                                                           │
╰─────────────────────────────────────────────────────────────╯
  ? for shortcuts                       Bypassing Permissions
"""
        state = self.monitor.detect_agent_state(multiple_feedback_content, "TestAgent")
        self.assertEqual(state, AgentState.IDLE, "Multiple feedback interactions should not affect detection")

    def test_ui_anomaly_detection_functionality(self):
        """Test that UI anomaly detection correctly identifies structural anomalies"""
        self._set_agent_as_initialized()
        
        # Content with normal structure - should have no anomalies
        normal_content = """
✻ Processing… (2s · esc to interrupt)
↓ 145 tokens

╭─────────────────────────────────────────────────────────────╮
│ >                                                           │
╰─────────────────────────────────────────────────────────────╯
  ? for shortcuts                       Bypassing Permissions
"""
        anomalies = self.monitor.detect_ui_anomalies(normal_content)
        self.assertEqual(len(anomalies), 0, "Normal structure should have no anomalies")
        
        # Content with structural anomalies - should detect them
        structural_anomaly_content = """
✻ Processing… (2s · esc to interrupt)

╭─────────────────────────────────────────────────────────────╮
│ >                                                           │
╰─────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────╮
│ > Another prompt box                                        │
╰─────────────────────────────────────────────────────────────╯
"""
        anomalies = self.monitor.detect_ui_anomalies(structural_anomaly_content)
        self.assertGreaterEqual(len(anomalies), 1, "Should detect multiple prompt boxes as anomaly")
        
        # Content with incomplete prompt box
        incomplete_box_content = """
✻ Processing… (2s · esc to interrupt)

╭─────────────────────────────────────────────────────────────╮
│ >                                                           
"""
        anomalies = self.monitor.detect_ui_anomalies(incomplete_box_content)
        self.assertGreaterEqual(len(anomalies), 1, "Should detect incomplete prompt box")
        
        # Content with unusual box characters
        unusual_chars_content = """
✻ Processing… (2s · esc to interrupt)

┌─────────────────────────────────────────────────────────────┐
│ >                                                           │
└─────────────────────────────────────────────────────────────┘
"""
        anomalies = self.monitor.detect_ui_anomalies(unusual_chars_content)
        self.assertGreaterEqual(len(anomalies), 1, "Should detect unusual box characters")
        
        # Verify anomaly structure
        if anomalies:
            anomaly = anomalies[0]
            self.assertIn('line_num', anomaly)
            self.assertIn('content', anomaly)
            self.assertIn('context', anomaly)
            self.assertIsInstance(anomaly['line_num'], int)
            self.assertIsInstance(anomaly['content'], str)
            self.assertIsInstance(anomaly['context'], list)


if __name__ == '__main__':
    unittest.main()