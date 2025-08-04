"""
Signal Handler Service

Provides graceful shutdown handling for the orchestrator system.
Manages cleanup operations and coordinates shutdown of various components.
"""
import signal
import sys
import logging
from typing import Callable, Optional, List, Any
from dataclasses import dataclass, field


@dataclass
class ShutdownTask:
    """Represents a cleanup task to run on shutdown"""
    name: str
    handler: Callable[[], None]
    timeout: float = 2.0
    critical: bool = True  # If True, log errors; if False, suppress


class SignalHandlerService:
    """Manages signal handling and graceful shutdown"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.shutdown_tasks: List[ShutdownTask] = []
        self._original_handlers = {}
        self._shutdown_in_progress = False
        
    def register_shutdown_task(
        self, 
        name: str, 
        handler: Callable[[], None],
        timeout: float = 2.0,
        critical: bool = True
    ) -> None:
        """
        Register a cleanup task to run on shutdown.
        
        Args:
            name: Descriptive name for the task
            handler: Function to call during shutdown
            timeout: Maximum time to wait for this task
            critical: Whether to log errors from this task
        """
        task = ShutdownTask(name=name, handler=handler, timeout=timeout, critical=critical)
        self.shutdown_tasks.append(task)
        self.logger.debug(f"Registered shutdown task: {name}")
    
    def setup_signal_handlers(
        self,
        signals: Optional[List[int]] = None,
        exit_on_signal: bool = True
    ) -> None:
        """
        Set up signal handlers for graceful shutdown.
        
        Args:
            signals: List of signals to handle (default: [SIGINT, SIGTERM])
            exit_on_signal: Whether to exit after handling signals
        """
        if signals is None:
            signals = [signal.SIGINT, signal.SIGTERM]
        
        for sig in signals:
            # Store original handler
            self._original_handlers[sig] = signal.signal(sig, 
                lambda s, f: self._handle_signal(s, f, exit_on_signal))
            
        self.logger.info(f"Signal handlers installed for: {[signal.Signals(s).name for s in signals]}")
    
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers"""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
        self.logger.debug("Original signal handlers restored")
    
    def _handle_signal(self, signum: int, frame: Any, exit_on_signal: bool) -> None:
        """Handle incoming signals"""
        if self._shutdown_in_progress:
            self.logger.warning("Shutdown already in progress, ignoring signal")
            return
            
        self._shutdown_in_progress = True
        sig_name = signal.Signals(signum).name
        
        print(f"\n\nReceived {sig_name} signal. Shutting down gracefully...")
        self.logger.info(f"Received {sig_name} signal, initiating shutdown")
        
        # Run shutdown tasks
        self._run_shutdown_tasks()
        
        print("Shutdown complete.")
        
        if exit_on_signal:
            sys.exit(0)
    
    def _run_shutdown_tasks(self) -> None:
        """Execute all registered shutdown tasks"""
        for task in self.shutdown_tasks:
            try:
                self.logger.info(f"Running shutdown task: {task.name}")
                task.handler()
            except Exception as e:
                if task.critical:
                    self.logger.error(f"Error in shutdown task '{task.name}': {e}")
                else:
                    self.logger.debug(f"Non-critical error in shutdown task '{task.name}': {e}")
    
    def trigger_shutdown(self) -> None:
        """Manually trigger shutdown sequence without a signal"""
        if self._shutdown_in_progress:
            return
            
        self._shutdown_in_progress = True
        self.logger.info("Manual shutdown triggered")
        self._run_shutdown_tasks()
    
    def clear_tasks(self) -> None:
        """Clear all registered shutdown tasks"""
        self.shutdown_tasks.clear()
        self.logger.debug("All shutdown tasks cleared")
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress"""
        return self._shutdown_in_progress