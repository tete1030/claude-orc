"""
Unit tests for MCP Server Manager
"""
import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, AsyncMock, patch
from src.services.mcp_server_manager import MCPServerManager


class TestMCPServerManager:
    """Test the MCP server manager service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = MCPServerManager()
        self.mock_server = Mock()
        self.mock_server.port = 8765
        self.mock_server.start = AsyncMock()
        self.mock_server.stop = AsyncMock()
    
    def teardown_method(self):
        """Clean up after tests"""
        if self.manager.is_running:
            self.manager.stop_server()
    
    def test_initial_state(self):
        """Test manager initial state"""
        assert not self.manager.is_running
        assert self.manager.server is None
        assert self.manager.server_loop is None
        assert self.manager.server_thread is None
    
    def test_start_server_success(self):
        """Test successful server startup"""
        self.manager.start_server(self.mock_server, startup_delay=0.1)
        
        assert self.manager.is_running
        assert self.manager.server is self.mock_server
        assert self.manager.server_thread is not None
        assert self.manager.server_thread.is_alive()
        assert self.mock_server.start.called
    
    def test_start_server_already_running(self):
        """Test error when starting already running server"""
        self.manager.start_server(self.mock_server, startup_delay=0.1)
        
        with pytest.raises(RuntimeError, match="already running"):
            self.manager.start_server(self.mock_server)
    
    def test_stop_server(self):
        """Test graceful server shutdown"""
        self.manager.start_server(self.mock_server, startup_delay=0.1)
        assert self.manager.is_running
        
        self.manager.stop_server()
        
        assert not self.manager.is_running
        assert self.manager.shutdown_event.is_set()
        assert not self.manager.server_thread.is_alive()
    
    def test_stop_server_not_running(self):
        """Test stopping when server not running"""
        # Should not raise any errors
        self.manager.stop_server()
        assert not self.manager.is_running
    
    def test_server_startup_failure(self):
        """Test handling of server startup failure"""
        mock_server = Mock()
        mock_server.port = 8765
        mock_server.start = AsyncMock(side_effect=Exception("Startup failed"))
        
        with pytest.raises(RuntimeError, match="failed to start"):
            self.manager.start_server(mock_server, startup_delay=0.1)
        
        assert not self.manager.is_running
    
    def test_server_with_exception_during_run(self):
        """Test server behavior with runtime exception"""
        # Create a server that fails after starting
        async def failing_start():
            await asyncio.sleep(0.1)
            raise Exception("Runtime error")
        
        mock_server = Mock()
        mock_server.port = 8765
        mock_server.start = failing_start
        
        with pytest.raises(RuntimeError, match="failed to start"):
            self.manager.start_server(mock_server, startup_delay=0.5)
    
    def test_get_event_loop(self):
        """Test getting the server's event loop"""
        assert self.manager.get_event_loop() is None
        
        self.manager.start_server(self.mock_server, startup_delay=0.1)
        
        loop = self.manager.get_event_loop()
        assert loop is not None
        assert isinstance(loop, asyncio.AbstractEventLoop)
        
        self.manager.stop_server()
        assert self.manager.get_event_loop() is None
    
    def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles"""
        for i in range(3):
            self.manager.start_server(self.mock_server, startup_delay=0.1)
            assert self.manager.is_running
            
            self.manager.stop_server()
            assert not self.manager.is_running
            
            # Give thread time to fully clean up
            time.sleep(0.1)
    
    def test_shutdown_event_propagation(self):
        """Test that shutdown event properly stops the server"""
        self.manager.start_server(self.mock_server, startup_delay=0.1)
        
        # Set shutdown event directly
        self.manager.shutdown_event.set()
        
        # Wait a bit for the loop to react
        time.sleep(0.3)
        
        # Thread should stop
        assert not self.manager.server_thread.is_alive()
        assert not self.manager.is_running
    
    @pytest.mark.asyncio
    async def test_managed_server_context(self):
        """Test the async context manager"""
        assert not self.manager.is_running
        
        async with self.manager.managed_server(self.mock_server):
            assert self.manager.is_running
            assert self.mock_server.start.called
            
            # Simulate some work
            await asyncio.sleep(0.1)
        
        # Server should be stopped after context
        assert not self.manager.is_running
        assert self.manager.shutdown_event.is_set()
    
    def test_server_thread_naming(self):
        """Test that server thread has proper name"""
        self.manager.start_server(self.mock_server, startup_delay=0.1)
        
        assert self.manager.server_thread.name == "MCP-Server-Thread"
        assert self.manager.server_thread.daemon
    
    def test_startup_timeout(self):
        """Test timeout during server startup"""
        # Mock a server that never sets startup_complete
        mock_server = Mock()
        mock_server.port = 8765
        mock_server.start = AsyncMock()
        
        # Patch the startup_complete event to never be set
        with patch.object(self.manager.startup_complete, 'wait', return_value=False):
            with pytest.raises(RuntimeError, match="failed to start within timeout"):
                self.manager.start_server(mock_server, startup_delay=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])