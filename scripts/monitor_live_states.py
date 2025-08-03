#!/usr/bin/env python3
"""
Live Agent State Monitor

Continuously monitors and displays agent states with real-time updates.
Helps observe state transitions as they happen.
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
import curses
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tmux_manager import TmuxManager
from src.agent_state_monitor import AgentStateMonitor, AnomalyHistoryConfig


class LiveStateMonitor:
    """Live monitoring of agent states"""
    
    def __init__(self, session_name: str, continuous_anomaly_recording: bool = False):
        self.session_name = session_name
        self.tmux = TmuxManager(session_name)
        
        # Configure anomaly history for continuous recording
        anomaly_config = AnomalyHistoryConfig(
            max_records_per_agent=5000,  # Higher limit for monitoring sessions
            max_total_records=20000,
            retention_hours=12.0  # Keep anomalies for the session duration
        )
        self.monitor = AgentStateMonitor(self.tmux, anomaly_config)
        
        self.history: List[Dict[str, Any]] = []
        self.max_history = 100
        self.continuous_anomaly_recording = continuous_anomaly_recording
        self.anomalies_detected = False
        self.anomaly_data = {}  # Still used for backward compatibility
        self.monitoring_start_time = time.time()
        
    def get_current_states(self) -> Dict[str, Any]:
        """Get current state of all agents"""
        pane_count = len(self.tmux.list_panes())
        states = {
            "timestamp": datetime.now(),
            "panes": []
        }
        
        for i in range(pane_count):
            state = self.monitor.update_agent_state(f"Agent{i}", i)
            recent_content = self.tmux.capture_pane(i, history_limit=-10)
            last_line = recent_content.split('\n')[-1] if recent_content else ""
            
            # Check for anomalies
            full_content = self.tmux.capture_pane(i, history_limit=-50)
            anomalies = self.monitor.detect_ui_anomalies(full_content) if full_content else []
            
            # Record anomalies in the new system
            if anomalies and self.monitor.anomaly_monitoring_enabled:
                self.monitor.anomaly_history.record_anomalies(
                    agent_name=f"Agent{i}",
                    anomalies=anomalies,
                    pane_state=state.value
                )
            
            # If anomalies found, capture them (for backward compatibility)
            if anomalies:
                if not self.anomalies_detected:
                    self.anomalies_detected = True
                # In continuous mode, we don't exit on first anomaly
                if not self.continuous_anomaly_recording:
                    if f"Agent{i}" not in self.anomaly_data:
                        self.anomaly_data[f"Agent{i}"] = {
                            "pane_index": i,
                            "anomalies": anomalies,
                            "full_content": full_content,
                            "timestamp": datetime.now()
                        }
            
            # Check for processing indicators
            processing_indicator = None
            if recent_content:
                lines = recent_content.split('\n')
                for line in lines[-5:]:  # Check last 5 lines
                    # Look for spinner patterns
                    for char in ['✶', '◐', '◓', '◑', '◒', '⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']:
                        if char in line:
                            processing_indicator = line.strip()
                            break
            
            states["panes"].append({  # type: ignore
                "index": i,
                "state": state.value,
                "last_line": last_line[:80],  # Truncate for display
                "processing_indicator": processing_indicator,
                "has_prompt": "│ >" in recent_content if recent_content else False,
                "anomaly_count": len(anomalies)
            })
            
        return states
        
    def save_anomalies(self):
        """Save detected anomalies to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f".temp/anomaly_capture_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"=== ANOMALY CAPTURE ===\n")
            f.write(f"Session: {self.session_name}\n")
            f.write(f"Capture Time: {datetime.now()}\n")
            f.write(f"Total Anomalies Detected: {sum(len(data['anomalies']) for data in self.anomaly_data.values())}\n")
            f.write("=" * 60 + "\n\n")
            
            for agent_name, data in self.anomaly_data.items():
                f.write(f"=== {agent_name} (Pane {data['pane_index']}) ===\n")
                f.write(f"Anomalies found: {len(data['anomalies'])}\n")
                f.write(f"Detection time: {data['timestamp']}\n\n")
                
                # Write anomalies
                for i, anomaly in enumerate(data['anomalies']):
                    f.write(f"Anomaly {i+1}:\n")
                    f.write(f"  Line: {anomaly.get('line_num', 'N/A')}\n")
                    f.write(f"  Content: {anomaly['content']}\n")
                    if 'context' in anomaly and anomaly['context']:
                        f.write("  Context:\n")
                        for ctx_line in anomaly['context']:
                            f.write(f"    {ctx_line}\n")
                    f.write("\n")
                
                # Write full pane content
                f.write("Full Pane Content:\n")
                f.write("-" * 60 + "\n")
                f.write(data['full_content'])
                f.write("\n" + "=" * 60 + "\n\n")
        
        print(f"\nAnomalies saved to: {filename}")
        
        # Print summary
        print("\nAnomaly Summary:")
        for agent_name, data in self.anomaly_data.items():
            print(f"  {agent_name}: {len(data['anomalies'])} anomaly(ies)")
            for i, anomaly in enumerate(data['anomalies']):
                print(f"    - {anomaly['content'][:60]}...")
    
    def save_anomaly_report(self, format='text'):
        """Save comprehensive anomaly report from continuous monitoring"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate report
        report = self.monitor.anomaly_history.export_report(
            output_format=format,
            start_time=self.monitoring_start_time
        )
        
        # Save to file
        ext = {'json': 'json', 'csv': 'csv', 'text': 'txt'}[format]
        filename = f".temp/anomaly_report_{timestamp}.{ext}"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\nAnomaly report saved to: {filename}")
        
        # Print summary
        summary = self.monitor.anomaly_history.get_summary()
        print(f"\nMonitoring Summary:")
        print(f"  Total anomalies recorded: {summary['total_records']}")
        print(f"  Monitoring duration: {(time.time() - self.monitoring_start_time) / 60:.1f} minutes")
        
        if summary['by_type']:
            print("\nAnomalies by type:")
            for atype, count in summary['by_type'].items():
                print(f"    {atype}: {count}")
        
        if summary['by_agent']:
            print("\nAnomalies by agent:")
            for agent, count in summary['by_agent'].items():
                print(f"    {agent}: {count}")
        
    def run_curses(self, stdscr):
        """Run the monitor with curses interface"""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(500) # Refresh every 500ms to reduce flashing
        
        # Color pairs
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Idle
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Busy
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # Error
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Unknown
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Normal
        
        color_map = {
            "idle": 1,
            "busy": 2,
            "error": 3,
            "unknown": 4,
            "quit": 3
        }
        
        running = True
        update_count = 0
        previous_states = {}  # Track previous states to minimize redraws
        
        while running:
            try:
                # Get current states
                current = self.get_current_states()
                self.history.append(current)
                if len(self.history) > self.max_history:
                    self.history.pop(0)
                
                # Only clear if this is the first update or on resize
                if update_count == 0:
                    stdscr.clear()
                
                # Header
                height, width = stdscr.getmaxyx()
                header = f"Live Agent State Monitor - Session: {self.session_name}"
                stdscr.addstr(0, 0, header, curses.A_BOLD)
                
                # Update time with padding to clear old time
                time_str = f"Time: {current['timestamp'].strftime('%H:%M:%S.%f')[:-3]}"
                stdscr.addstr(1, 0, time_str + " " * (width - len(time_str) - 1))
                stdscr.addstr(2, 0, "-" * min(80, width))
                
                # Agent states
                row = 4
                for pane in current["panes"]:
                    if row >= height - 5:
                        break
                        
                    # State with color
                    state = pane["state"]
                    color = curses.color_pair(color_map.get(state, 5))
                    
                    # Clear the line first to prevent ghosting
                    stdscr.move(row, 0)
                    stdscr.clrtoeol()
                    
                    stdscr.addstr(row, 0, f"Pane {pane['index']}: ", curses.A_BOLD)
                    stdscr.addstr(row, 8, f"{state:8}", color | curses.A_BOLD)
                    
                    # Prompt indicator
                    if pane["has_prompt"]:
                        stdscr.addstr(row, 20, "[PROMPT]", curses.color_pair(1))
                    
                    # Anomaly indicator
                    if pane["anomaly_count"] > 0:
                        stdscr.addstr(row, 30, f"[{pane['anomaly_count']} ANOMALY]", 
                                    curses.color_pair(3) | curses.A_BLINK)
                    
                    # Processing indicator
                    if pane["processing_indicator"]:
                        stdscr.move(row + 1, 0)
                        stdscr.clrtoeol()
                        stdscr.addstr(row + 1, 4, f"└─ {pane['processing_indicator'][:60]}", 
                                    curses.color_pair(2))
                        row += 1
                    
                    # Last line preview
                    stdscr.move(row + 1, 0)
                    stdscr.clrtoeol()
                    if pane["last_line"]:
                        stdscr.addstr(row + 1, 4, f"└─ {pane['last_line'][:60]}...", 
                                    curses.color_pair(5))
                    row += 2
                
                # Check if anomalies detected
                if self.anomalies_detected and not self.continuous_anomaly_recording:
                    # In non-continuous mode, exit on first anomaly
                    stdscr.clear()
                    stdscr.addstr(0, 0, "ANOMALIES DETECTED!", curses.color_pair(3) | curses.A_BOLD)
                    stdscr.addstr(2, 0, "Saving anomaly data and exiting...")
                    stdscr.refresh()
                    time.sleep(1)
                    running = False
                elif self.anomalies_detected and self.continuous_anomaly_recording:
                    # In continuous mode, show indicator but keep running
                    anomaly_summary = self.monitor.anomaly_history.get_summary()
                    total_anomalies = anomaly_summary['total_records']
                    stdscr.addstr(height - 6, 0, f"Total anomalies recorded: {total_anomalies}", 
                                 curses.color_pair(3) | curses.A_BOLD)
                
                # State transition history
                if len(self.history) > 1:
                    stdscr.addstr(height - 4, 0, "-" * min(80, width))
                    stdscr.addstr(height - 3, 0, "Recent transitions:", curses.A_BOLD)
                    
                    # Find recent transitions
                    transitions = []
                    for i in range(1, min(len(self.history), 10)):
                        prev = self.history[-i-1]
                        curr = self.history[-i]
                        for j, (p_pane, c_pane) in enumerate(zip(prev["panes"], curr["panes"])):
                            if p_pane["state"] != c_pane["state"]:
                                transitions.append(f"Pane {j}: {p_pane['state']} → {c_pane['state']}")
                    
                    if transitions:
                        stdscr.addstr(height - 2, 0, " | ".join(transitions[:3])[:width-1])
                
                # Footer
                stdscr.addstr(height - 1, 0, "Press 'q' to quit, 'c' to clear history", 
                            curses.A_DIM)
                
                # Handle input
                key = stdscr.getch()
                if key == ord('q'):
                    running = False
                elif key == ord('c'):
                    self.history.clear()
                
                stdscr.refresh()
                update_count += 1
                
            except KeyboardInterrupt:
                running = False
            except Exception as e:
                # Show error but keep running
                try:
                    h, w = stdscr.getmaxyx()
                    stdscr.addstr(h - 5, 0, f"Error: {str(e)[:w-1]}", 
                                curses.color_pair(3))
                except:
                    pass
                    
        return update_count
        
    def run_simple(self, duration: int = 60, interval: float = 0.5):
        """Simple text-based monitoring"""
        print(f"Monitoring session '{self.session_name}' for {duration} seconds...")
        print("Will auto-exit if anomalies are detected.")
        print("Press Ctrl+C to stop\n")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                current = self.get_current_states()
                
                # Clear screen (works on most terminals)
                print("\033[2J\033[H", end="")
                
                print(f"Time: {current['timestamp'].strftime('%H:%M:%S.%f')[:-3]}")
                print("-" * 60)
                
                for pane in current["panes"]:
                    status = f"Pane {pane['index']}: {pane['state']:8}"
                    if pane["has_prompt"]:
                        status += " [PROMPT]"
                    if pane["anomaly_count"] > 0:
                        status += f" [ANOMALY: {pane['anomaly_count']}]"
                    print(status)
                    
                    if pane["processing_indicator"]:
                        print(f"  └─ {pane['processing_indicator'][:50]}")
                    elif pane["last_line"]:
                        print(f"  └─ {pane['last_line'][:50]}...")
                    print()
                
                # Check if anomalies detected
                if self.anomalies_detected and not self.continuous_anomaly_recording:
                    print("\n*** ANOMALIES DETECTED! ***")
                    print("Saving anomaly data and exiting...")
                    break
                elif self.anomalies_detected and self.continuous_anomaly_recording:
                    # Show anomaly count in continuous mode
                    anomaly_summary = self.monitor.anomaly_history.get_summary()
                    total_anomalies = anomaly_summary['total_records']
                    print(f"\nTotal anomalies recorded: {total_anomalies}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            

def main():
    parser = argparse.ArgumentParser(description="Live monitor agent states")
    parser.add_argument("session", help="Tmux session name")
    parser.add_argument("--simple", action="store_true",
                       help="Use simple text output instead of curses")
    parser.add_argument("--duration", type=int, default=300,
                       help="Monitoring duration in seconds (default: 300)")
    parser.add_argument("--interval", type=float, default=0.5,
                       help="Update interval in seconds (default: 0.5)")
    parser.add_argument("--continuous-anomaly-recording", action="store_true",
                       help="Continue monitoring and recording all anomalies (don't exit on first anomaly)")
    parser.add_argument("--anomaly-report-format", choices=['text', 'json', 'csv'],
                       default='text', help="Format for anomaly report (default: text)")
    
    args = parser.parse_args()
    
    monitor = LiveStateMonitor(args.session, args.continuous_anomaly_recording)
    
    if args.simple:
        monitor.run_simple(args.duration, args.interval)
    else:
        # Run with curses
        try:
            update_count = curses.wrapper(monitor.run_curses)
            print(f"\nMonitoring completed. Total updates: {update_count}")
        except Exception as e:
            print(f"Error running curses interface: {e}")
            print("Falling back to simple mode...")
            monitor.run_simple(args.duration, args.interval)
    
    # Save results
    if monitor.continuous_anomaly_recording:
        # In continuous mode, only save report if anomalies were detected
        if monitor.anomalies_detected:
            monitor.save_anomaly_report(args.anomaly_report_format)
        else:
            print("\nNo anomalies detected during monitoring - no report file created.")
    elif monitor.anomalies_detected:
        # In non-continuous mode, save the old-style snapshot
        monitor.save_anomalies()
            

if __name__ == "__main__":
    main()