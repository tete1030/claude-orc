"""
MCP Server Manager Service

Handles the lifecycle of the MCP (Model Context Protocol) server,
including startup, shutdown, and background thread management.
"""
import asyncio
import threading
import logging
from typing import Optional, Any
from contextlib import asynccontextmanager


class MCPServerManager:
    """Manages MCP server lifecycle and background execution"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.server = None
        self.server_loop = None
        self.server_thread = None
        self.shutdown_event = threading.Event()
        self.startup_complete = threading.Event()
        self._server_exception = None
    
    def start_server(self, mcp_server: Any, startup_delay: float = 2.0) -> None:
        """
        Start MCP server in a background thread.
        
        Args:
            mcp_server: The CentralMCPServer instance
            startup_delay: Time to wait after starting before returning
        """
        if self.server_thread and self.server_thread.is_alive():
            raise RuntimeError("MCP server is already running")
        
        self.server = mcp_server
        self.shutdown_event.clear()
        self.startup_complete.clear()
        self._server_exception = None
        
        # Start server in background thread
        self.server_thread = threading.Thread(
            target=self._run_server_loop,
            daemon=True,
            name="MCP-Server-Thread"
        )
        self.server_thread.start()
        
        # Wait for server to start
        if not self.startup_complete.wait(timeout=startup_delay + 5):
            raise RuntimeError("MCP server failed to start within timeout")
        
        # Check if server started successfully
        if self._server_exception:
            raise RuntimeError(f"MCP server failed to start: {self._server_exception}")
        
        # Additional startup delay for stability
        if startup_delay > 0:
            import time
            time.sleep(startup_delay)
        
        self.logger.info(f"MCP server started successfully on port {mcp_server.port}")
    
    def stop_server(self, timeout: float = 2.0) -> None:
        """
        Stop the MCP server gracefully.
        
        Args:
            timeout: Maximum time to wait for shutdown
        """
        if not self.server_thread or not self.server_thread.is_alive():
            return
        
        self.logger.info("Stopping MCP server...")
        self.shutdown_event.set()
        
        # Signal the event loop to stop
        if self.server_loop and not self.server_loop.is_closed():
            self.server_loop.call_soon_threadsafe(self.server_loop.stop)
        
        # Wait for thread to finish
        self.server_thread.join(timeout=timeout)
        
        if self.server_thread.is_alive():
            self.logger.warning("MCP server thread did not stop within timeout")
        else:
            self.logger.info("MCP server stopped successfully")
    
    def _run_server_loop(self):
        """Run the async event loop for the MCP server"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.server_loop = loop
        
        async def server_lifecycle():
            try:
                # Start the server
                await self.server.start()
                self.startup_complete.set()
                
                # Run until shutdown is requested
                while not self.shutdown_event.is_set():
                    await asyncio.sleep(0.1)
                    
                # Clean shutdown
                if hasattr(self.server, 'stop'):
                    await self.server.stop()
                    
            except Exception as e:
                self.logger.error(f"MCP server error: {e}")
                self._server_exception = e
                self.startup_complete.set()
                # Signal shutdown on startup failure
                self.shutdown_event.set()
                raise
        
        try:
            loop.run_until_complete(server_lifecycle())
        except Exception:
            # Suppress exceptions during shutdown
            if not self.shutdown_event.is_set():
                self.logger.exception("Unexpected error in MCP server")
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            
            loop.close()
            self.server_loop = None
    
    @property
    def is_running(self) -> bool:
        """Check if the MCP server is currently running"""
        return (
            self.server_thread is not None 
            and self.server_thread.is_alive()
            and not self.shutdown_event.is_set()
        )
    
    @asynccontextmanager
    async def managed_server(self, mcp_server: Any):
        """
        Context manager for running MCP server.
        
        Usage:
            async with manager.managed_server(mcp_server):
                # Server is running
                await do_work()
            # Server is stopped
        """
        self.start_server(mcp_server)
        try:
            yield
        finally:
            self.stop_server()
    
    def get_event_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the server's event loop if running"""
        if self.is_running and self.server_loop:
            return self.server_loop
        return None