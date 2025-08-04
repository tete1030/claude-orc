"""
Tmux Management Service

Handles tmux session discovery, health checks, and cleanup.
"""
import subprocess
from typing import Dict, List, Optional, Any


class TmuxManagementService:
    """Service for managing tmux sessions"""
    
    def discover_tmux_sessions(self, contexts: Dict[str, Any]) -> None:
        """Discover and associate tmux sessions with contexts"""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                check=True,
            )
            
            tmux_sessions = result.stdout.strip().split("\n")
            
            for context_name in contexts:
                # Look for tmux session that matches or contains the team context name
                for tmux_session in tmux_sessions:
                    if tmux_session and (
                        context_name in tmux_session or tmux_session in context_name
                    ):
                        contexts[context_name].tmux_session = tmux_session
                        break
        
        except subprocess.CalledProcessError:
            # tmux might not be running or no sessions exist
            pass
    
    def check_tmux_health(self, tmux_session: str) -> Dict[str, Any]:
        """Check health of tmux session"""
        health = {
            "context_name": tmux_session,
            "status": "healthy",
            "exists": False,
            "panes": 0,
            "issues": [],
        }
        
        try:
            # Check if session exists
            result = subprocess.run(
                ["tmux", "has-session", "-t", tmux_session], 
                capture_output=True, 
                text=True
            )
            
            health["exists"] = result.returncode == 0
            
            if health["exists"]:
                # Count panes
                result = subprocess.run(
                    ["tmux", "list-panes", "-t", tmux_session, "-F", "#{pane_index}"],
                    capture_output=True,
                    text=True,
                )
                
                if result.returncode == 0:
                    health["panes"] = len(result.stdout.strip().split("\n"))
            
            else:
                health["status"] = "missing"
                health["issues"].append("Tmux session does not exist")
        
        except subprocess.CalledProcessError:
            health["status"] = "error"
            health["issues"].append("Failed to check tmux session")
        
        return health
    
    def kill_tmux_session(self, session_name: str) -> bool:
        """Kill a tmux session if it exists"""
        try:
            # First check if session exists
            check_result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            if check_result.returncode == 0:
                # Session exists, kill it
                subprocess.run(
                    ["tmux", "kill-session", "-t", session_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                return True
            else:
                # Session doesn't exist
                return True
                
        except subprocess.CalledProcessError:
            return False
    
    def list_all_sessions(self) -> List[str]:
        """List all tmux sessions"""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                check=True,
            )
            
            return result.stdout.strip().split("\n") if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return []