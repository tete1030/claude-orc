#!/usr/bin/env python3
"""Monitor and detect Claude session forks"""

import logging
import time
import threading
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from .session_parser import SessionParser
from .team_context_manager import TeamContextManager, TeamContextAgentInfo

# Try to import inotify (Linux only)
try:
    import inotify_simple
    INOTIFY_AVAILABLE = True
except ImportError:
    INOTIFY_AVAILABLE = False

class SessionForkMonitor:
    """Monitor for Claude session forks in real-time and on-demand"""
    
    def __init__(self, context_manager: TeamContextManager):
        """Initialize session fork monitor
        
        Args:
            context_manager: TeamContextManager instance for updating contexts
        """
        self.context_manager = context_manager
        self.parser = SessionParser()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.running = False
        self.monitor_thread = None
        self.check_interval = 30  # seconds
        
    def get_session_directory(self, context_name: str, agent_name: str, working_dir: str) -> Path:
        """Get session directory for agent
        
        Each agent runs in its own container with its own session directory:
        ~/.claude/projects/ccbox-<context-name>-<agent-name>-<escaped-working-dir>
        
        Args:
            context_name: Name of the context
            agent_name: Name of the agent
            working_dir: Working directory of the agent
            
        Returns:
            Path to session directory
            
        Raises:
            FileNotFoundError: If no session directory found
        """
        # Access the claude projects directory directly
        host_base = Path.home() / ".claude/projects"
        
        if not host_base.exists():
            raise FileNotFoundError(f"Claude projects directory not found: {host_base}")
        
        # Escape the working directory path
        escaped_path = working_dir.replace("/", "-")
        
        # Build the expected session directory name for this agent
        # Pattern: ccbox-<context-name>-<agent-name>-<escaped-path>
        agent_name_sanitized = agent_name.lower().replace(" ", "-")
        session_dir_name = f"ccbox-{context_name}-{agent_name_sanitized}-{escaped_path}"
        session_dir = host_base / session_dir_name
        
        if not session_dir.exists():
            raise FileNotFoundError(
                f"Session directory not found for agent '{agent_name}': {session_dir}"
            )
        
        self.logger.debug(f"Found session directory for {agent_name}: {session_dir}")
        return session_dir
    
    def find_active_session(self, context_name: str, agent: TeamContextAgentInfo, working_dir: str) -> str:
        """Find the active session for an agent
        
        Args:
            context_name: Name of the context
            agent: Agent information
            working_dir: Working directory of the context
            
        Returns:
            Active session ID (may be same as stored or a descendant)
            
        Raises:
            FileNotFoundError: If no session files found
            ValueError: If stored session not found and no descendants
        """
        if not working_dir:
            raise ValueError(f"No working_dir for context {context_name}")
            
        session_dir = self.get_session_directory(context_name, agent.name, working_dir)
            
        # Get all session files sorted by modification time (newest first)
        session_files = sorted(
            session_dir.glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        if not session_files:
            raise FileNotFoundError(
                f"No session files found in {session_dir} for agent {agent.name}"
            )
        
        self.logger.debug(f"Checking {len(session_files)} session files for {agent.name}")
        
        # Check each file from newest to oldest
        for session_file in session_files:
            session_id = session_file.stem
            
            # If we encounter the stored session, it's still active
            if session_id == agent.session_id:
                self.logger.debug(f"Stored session {agent.session_id} is still most recent for {agent.name}")
                return agent.session_id
                
            # Check if this newer session is a descendant
            try:
                if self.parser.verify_descendant(agent.session_id, session_file):
                    self.logger.info(
                        f"Fork detected: {agent.name} has descendant session {session_id} "
                        f"(forked from {agent.session_id})"
                    )
                    return session_id
            except Exception as e:
                self.logger.debug(f"Failed to check descendant for {session_id}: {e}")
                continue
                
        # If we get here and haven't found the stored session, it's a problem
        raise ValueError(
            f"Stored session {agent.session_id} not found for {agent.name} in {session_dir}. "
            f"Checked {len(session_files)} files."
        )
    
    def check_context_sessions(self, context_name: str) -> Dict[str, str]:
        """Check all agents in context for session forks
        
        Args:
            context_name: Name of the context to check
            
        Returns:
            Dictionary of agent_name -> new_session_id for agents with forks
        """
        context = self.context_manager.get_context(context_name)
        if not context:
            raise ValueError(f"Context '{context_name}' not found")
            
        if not context.working_dir:
            raise ValueError(f"Context '{context_name}' has no working_dir")
            
        updates = {}
        errors = []
        
        for agent in context.agents:
            if not agent.session_id:
                self.logger.debug(f"Skipping {agent.name} - no session ID stored")
                continue
                
            try:
                # Try to find active session
                active_session = self.find_active_session(context_name, agent, context.working_dir)
                
                if active_session and active_session != agent.session_id:
                    # Fork detected
                    old_session = agent.session_id
                    self.logger.info(
                        f"Session fork detected: {agent.name} "
                        f"{old_session} -> {active_session}"
                    )
                    
                    # Update context
                    if self.context_manager.update_agent_session(
                        context_name, agent.name, active_session
                    ):
                        updates[agent.name] = active_session
                    else:
                        errors.append(f"Failed to update session for {agent.name}")
                    
            except FileNotFoundError as e:
                # Session directory or files not found - skip this agent
                self.logger.warning(f"Session check skipped for {agent.name}: {e}")
            except Exception as e:
                # Any other error
                self.logger.error(f"Session check failed for {agent.name}: {e}")
                errors.append(f"{agent.name}: {e}")
                
        if errors:
            self.logger.error(f"Errors during session check: {errors}")
                
        return updates
    
    def start_monitoring(self, context_name: str):
        """Start background monitoring thread
        
        Uses inotify on Linux for instant detection, falls back to polling.
        
        Args:
            context_name: Name of context to monitor
        """
        if self.running:
            self.logger.warning("Monitor already running")
            return
            
        self.running = True
        
        # Choose monitoring method based on availability
        if INOTIFY_AVAILABLE:
            self._start_inotify_monitoring(context_name)
        else:
            self._start_polling_monitoring(context_name)
    
    def _start_inotify_monitoring(self, context_name: str):
        """Start inotify-based monitoring (Linux only)"""
        def inotify_loop():
            self.logger.info(f"Starting inotify monitor for context '{context_name}'")
            
            # Get session directories to watch
            watch_dirs = set()
            context = self.context_manager.get_context(context_name)
            if not context:
                self.logger.error(f"Context '{context_name}' not found")
                return
                
            if not context.working_dir:
                self.logger.error(f"Context '{context_name}' has no working_dir")
                return
                
            # Try to find session directories for agents
            for agent in context.agents:
                try:
                    session_dir = self.get_session_directory(context_name, agent.name, context.working_dir)
                    watch_dirs.add(str(session_dir))
                except FileNotFoundError:
                    self.logger.warning(f"No session directory for {agent.name}")
                    
            if not watch_dirs:
                self.logger.warning("No directories to watch, falling back to polling")
                self._start_polling_monitoring(context_name)
                return
                
            # Setup inotify
            inotify = inotify_simple.INotify()
            watch_descriptors = {}
            
            for dir_path in watch_dirs:
                wd = inotify.add_watch(dir_path, 
                    inotify_simple.flags.CREATE | 
                    inotify_simple.flags.MODIFY |
                    inotify_simple.flags.MOVED_TO)
                watch_descriptors[wd] = dir_path
                self.logger.debug(f"Watching directory: {dir_path}")
                
            # Monitor for file changes
            while self.running:
                # Check for events with timeout
                events = inotify.read(timeout=1000)  # 1 second timeout
                
                for event in events:
                    if event.name and event.name.endswith('.jsonl'):
                        dir_path = watch_descriptors.get(event.wd)
                        self.logger.debug(f"Session file event in {dir_path}: {event.name}")
                        
                        # Check for forks after a small delay (let file write complete)
                        time.sleep(0.5)
                        
                        try:
                            updates = self.check_context_sessions(context_name)
                            if updates:
                                self.logger.info(f"Session forks detected via inotify: {updates}")
                        except Exception as e:
                            self.logger.error(f"Fork check failed: {e}")
                            
            self.logger.info("Inotify monitor stopped")
            
        self.monitor_thread = threading.Thread(
            target=inotify_loop,
            daemon=True,
            name=f"InotifyMonitor-{context_name}"
        )
        self.monitor_thread.start()
    
    def _start_polling_monitoring(self, context_name: str):
        """Start polling-based monitoring (fallback)"""
        def poll_loop():
            self.logger.info(
                f"Starting polling monitor for context '{context_name}' "
                f"(checking every {self.check_interval}s)"
            )
            
            while self.running:
                try:
                    updates = self.check_context_sessions(context_name)
                    if updates:
                        self.logger.info(f"Session forks detected via polling: {updates}")
                        
                except Exception as e:
                    self.logger.error(f"Monitor check failed: {e}")
                    
                time.sleep(self.check_interval)
                
            self.logger.info("Polling monitor stopped")
            
        self.monitor_thread = threading.Thread(
            target=poll_loop,
            daemon=True,
            name=f"PollingMonitor-{context_name}"
        )
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring thread"""
        if not self.running:
            return
            
        self.logger.info("Stopping session fork monitor...")
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                self.logger.warning("Monitor thread did not stop cleanly")
                
