#!/usr/bin/env python3
"""
Agent State Diagnostic Tool

Systematically captures and analyzes tmux pane data to help improve state detection patterns.
Records pane content over time and identifies patterns for busy/idle states.
"""

import sys
import time
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import re
from typing import Optional, Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tmux_manager import TmuxManager
from src.agent_state_monitor import AgentStateMonitor


class AgentStateDiagnostics:
    """Diagnostic tool for analyzing agent states"""
    
    def __init__(self, session_name: str, output_dir: Optional[str] = None):
        self.session_name = session_name
        self.tmux = TmuxManager(session_name)
        self.monitor = AgentStateMonitor(self.tmux)
        
        # Create output directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"diagnostics/agent_states_{timestamp}"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.capture_history: List[Dict[str, Any]] = []
        self.pattern_analysis: Dict[str, Any] = {
            "busy_indicators": {},
            "idle_indicators": {},
            "transition_patterns": []
        }
        
    def capture_snapshot(self) -> Dict[str, Any]:
        """Capture current state of all panes"""
        snapshot: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "panes": []
        }
        
        # Get number of panes
        pane_count = len(self.tmux.list_panes())
        
        for i in range(pane_count):
            # Capture full content and recent content
            full_content = self.tmux.capture_pane(i, history_limit=-1000)
            recent_content = self.tmux.capture_pane(i, history_limit=-50)
            
            # Get detected state
            state = self.monitor.update_agent_state(f"Agent{i}", i)
            
            # Extract key indicators
            pane_data: Dict[str, Any] = {
                "pane_index": i,
                "detected_state": state.value,
                "full_content_lines": len(full_content.split('\n')) if full_content else 0,
                "recent_content": recent_content,
                "last_10_lines": '\n'.join(recent_content.split('\n')[-10:]) if recent_content else "",
                "indicators": self._extract_indicators(recent_content)
            }
            
            snapshot["panes"].append(pane_data)  # type: ignore
            
        self.capture_history.append(snapshot)
        return snapshot
        
    def _extract_indicators(self, content: Optional[str]) -> Dict[str, Any]:
        """Extract potential state indicators from content"""
        if not content:
            return {}
            
        indicators: Dict[str, Any] = {
            "has_prompt_box": bool(re.search(r"│\s*>\s*│", content)),
            "has_shortcuts_line": "? for shortcuts" in content,
            "has_debug_lines": content.count("[DEBUG]"),
            "has_spinner_chars": bool(re.search(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏✶◐◓◑◒]", content)),
            "processing_words": [],
            "last_line_empty": content.rstrip().endswith('\n\n'),
            "special_patterns": []
        }
        
        # Check for processing words
        processing_words = ["Accomplishing", "Processing", "Thinking", "Shucking", "Pondering", 
                          "Generating", "Computing", "Analyzing", "Working", "Calculating"]
        for word in processing_words:
            if re.search(rf"\b{word}\b", content, re.IGNORECASE):
                indicators["processing_words"].append(word)  # type: ignore
                
        # Check for special patterns
        if re.search(r"●\s+\w+ing", content):
            indicators["special_patterns"].append("bullet_with_ing_word")  # type: ignore
        if re.search(r"Calling tool:", content):
            indicators["special_patterns"].append("calling_tool")  # type: ignore
        if re.search(r"\[DEBUG\] Stream started", content):
            indicators["special_patterns"].append("stream_started")  # type: ignore
            
        return indicators
        
    def monitor_continuously(self, duration_seconds: int, interval: float = 1.0):
        """Monitor panes continuously for a duration"""
        print(f"Monitoring session '{self.session_name}' for {duration_seconds} seconds...")
        print(f"Capturing every {interval} seconds")
        
        start_time = time.time()
        capture_count = 0
        
        while time.time() - start_time < duration_seconds:
            snapshot = self.capture_snapshot()
            capture_count += 1
            
            # Print current states
            print(f"\n[{capture_count}] States at {snapshot['timestamp']}:")
            for pane in snapshot["panes"]:  # type: ignore
                print(f"  Pane {pane['pane_index']}: {pane['detected_state']} "
                      f"(prompt_box: {pane['indicators']['has_prompt_box']}, "
                      f"processing_words: {len(pane['indicators']['processing_words'])})")
                      
            time.sleep(interval)
            
        print(f"\nCompleted {capture_count} captures")
        
    def analyze_patterns(self):
        """Analyze captured data for patterns"""
        print("\n=== PATTERN ANALYSIS ===")
        
        # Analyze state transitions
        for i in range(1, len(self.capture_history)):
            prev_snapshot = self.capture_history[i-1]
            curr_snapshot = self.capture_history[i]
            
            for j, (prev_pane, curr_pane) in enumerate(zip(prev_snapshot["panes"], curr_snapshot["panes"])):
                prev_state = prev_pane["detected_state"]  # type: ignore
                curr_state = curr_pane["detected_state"]  # type: ignore
                
                if prev_state != curr_state:
                    transition = {
                        "pane": j,
                        "transition": f"{prev_state} -> {curr_state}",
                        "timestamp": curr_snapshot["timestamp"],
                        "indicators_before": prev_pane["indicators"],  # type: ignore
                        "indicators_after": curr_pane["indicators"],  # type: ignore
                        "content_sample": curr_pane["last_10_lines"]  # type: ignore
                    }
                    self.pattern_analysis["transition_patterns"].append(transition)  # type: ignore
                    
        # Collect indicators by state
        for snapshot in self.capture_history:
            for pane in snapshot["panes"]:  # type: ignore
                state = pane["detected_state"]  # type: ignore
                indicators = pane["indicators"]  # type: ignore
                
                if state == "busy":
                    self._update_indicator_counts(self.pattern_analysis["busy_indicators"], indicators)
                elif state == "idle":
                    self._update_indicator_counts(self.pattern_analysis["idle_indicators"], indicators)
                    
    def _update_indicator_counts(self, indicator_dict, indicators):
        """Update indicator occurrence counts"""
        for key, value in indicators.items():
            if isinstance(value, bool):
                if value:
                    indicator_dict[key] = indicator_dict.get(key, 0) + 1
            elif isinstance(value, list):
                for item in value:
                    full_key = f"{key}:{item}"
                    indicator_dict[full_key] = indicator_dict.get(full_key, 0) + 1
            elif isinstance(value, (int, float)):
                if value > 0:
                    indicator_dict[key] = indicator_dict.get(key, 0) + value
                    
    def save_diagnostics(self):
        """Save diagnostic data to files"""
        # Save raw capture history
        history_file = self.output_dir / "capture_history.json"
        with open(history_file, 'w') as f:
            json.dump(self.capture_history, f, indent=2)
        print(f"\nSaved capture history to: {history_file}")
        
        # Save pattern analysis
        analysis_file = self.output_dir / "pattern_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(self.pattern_analysis, f, indent=2)
        print(f"Saved pattern analysis to: {analysis_file}")
        
        # Generate report
        self._generate_report()
        
    def _generate_report(self):
        """Generate human-readable report"""
        report_file = self.output_dir / "diagnostic_report.md"
        
        with open(report_file, 'w') as f:
            f.write("# Agent State Diagnostic Report\n\n")
            f.write(f"Session: {self.session_name}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total captures: {len(self.capture_history)}\n\n")
            
            # State transitions
            f.write("## State Transitions\n\n")
            for trans in self.pattern_analysis["transition_patterns"]:
                f.write(f"### Pane {trans['pane']}: {trans['transition']} at {trans['timestamp']}\n")
                f.write("**Indicators Before:**\n")
                f.write(f"```json\n{json.dumps(trans['indicators_before'], indent=2)}\n```\n")
                f.write("**Indicators After:**\n")
                f.write(f"```json\n{json.dumps(trans['indicators_after'], indent=2)}\n```\n")
                f.write("**Content Sample:**\n")
                f.write(f"```\n{trans['content_sample']}\n```\n\n")
                
            # Indicator frequency
            f.write("## Indicator Frequency Analysis\n\n")
            
            f.write("### Busy State Indicators\n")
            for indicator, count in sorted(self.pattern_analysis["busy_indicators"].items(),  # type: ignore
                                         key=lambda x: x[1], reverse=True):
                f.write(f"- {indicator}: {count} occurrences\n")
                
            f.write("\n### Idle State Indicators\n")
            for indicator, count in sorted(self.pattern_analysis["idle_indicators"].items(),  # type: ignore
                                         key=lambda x: x[1], reverse=True):
                f.write(f"- {indicator}: {count} occurrences\n")
                
        print(f"Generated report: {report_file}")
        
    def capture_single_state(self, agent_instructions: Optional[Dict[int, str]] = None):
        """Capture a single state with optional agent instructions"""
        if agent_instructions:
            print("\nSending instructions to agents...")
            for pane_idx, instruction in agent_instructions.items():
                self.tmux.send_to_pane(pane_idx, instruction)
            print("Waiting 3 seconds for agents to process...")
            time.sleep(3)
            
        snapshot = self.capture_snapshot()
        
        # Save snapshot to timestamped file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = Path(".temp") / f"state_snapshot_{timestamp}.txt"
        snapshot_file.parent.mkdir(exist_ok=True)
        
        with open(snapshot_file, 'w') as f:
            f.write(f"State Snapshot - {snapshot['timestamp']}\n")
            f.write(f"Session: {self.session_name}\n")
            f.write("="*80 + "\n\n")
            
            for pane in snapshot["panes"]:  # type: ignore
                # Try to get agent name
                agent_name = f"Agent{pane['pane_index']}"
                try:
                    result = subprocess.run(
                        ["tmux", "show-options", "-p", "-t", 
                         f"{self.session_name}:0.{pane['pane_index']}", "@agent_name"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0 and "=" in result.stdout:
                        agent_name = result.stdout.strip().split("=", 1)[1]
                except:
                    pass
                
                f.write(f"PANE {pane['pane_index']} - {agent_name} - STATE: {pane['detected_state']}\n")
                f.write("-"*80 + "\n")
                f.write("Last 10 lines:\n")
                f.write(pane['last_10_lines'])
                f.write("\n\nFull recent content (last 50 lines):\n")
                f.write("-"*40 + "\n")
                f.write(pane['recent_content'] or "")
                f.write("\n\n" + "="*80 + "\n\n")
        
        print(f"\nSnapshot saved to: {snapshot_file}")
        print("\nCurrent states:")
        for pane in snapshot["panes"]:  # type: ignore
            print(f"Pane {pane['pane_index']}: {pane['detected_state']}")
            print(f"  Indicators: {json.dumps(pane['indicators'], indent=2)}")
            

def main():
    parser = argparse.ArgumentParser(description="Diagnose agent state detection")
    parser.add_argument("session", help="Tmux session name")
    parser.add_argument("--duration", type=int, default=30,
                       help="Monitoring duration in seconds (default: 30)")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Capture interval in seconds (default: 1.0)")
    parser.add_argument("--output-dir", help="Output directory for diagnostics")
    parser.add_argument("--single", action="store_true",
                       help="Capture single snapshot only")
    
    args = parser.parse_args()
    
    # Create diagnostic tool
    diag = AgentStateDiagnostics(args.session, args.output_dir)
    
    if args.single:
        # Single capture mode
        diag.capture_single_state()
        diag.save_diagnostics()
    else:
        # Continuous monitoring
        try:
            diag.monitor_continuously(args.duration, args.interval)
            diag.analyze_patterns()
            diag.save_diagnostics()
            
            print("\n=== SUMMARY ===")
            print(f"Total state transitions detected: {len(diag.pattern_analysis['transition_patterns'])}")
            print(f"Busy state captures: {sum(1 for s in diag.capture_history for p in s['panes'] if p['detected_state'] == 'busy')}")
            print(f"Idle state captures: {sum(1 for s in diag.capture_history for p in s['panes'] if p['detected_state'] == 'idle')}")
            
        except KeyboardInterrupt:
            print("\nMonitoring interrupted by user")
            diag.save_diagnostics()
            

if __name__ == "__main__":
    main()