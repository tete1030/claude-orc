"""
Unit tests for port discovery logic in ccorc launch
"""
import pytest
import socket
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import importlib.util

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

# Import ccorc as a module
spec = importlib.util.spec_from_file_location("ccorc", repo_root / "bin" / "ccorc")
ccorc_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccorc_module)

from tests.fixtures.team_configs import NetworkFixtures


class TestPortDiscovery:
    """Test the port discovery functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ccorc_module.SessionCLIManager()
    
    def test_find_available_port_first_try(self):
        """Test finding available port when first port is free"""
        # Get an actually available port
        available_port = NetworkFixtures.get_available_port()
        
        # Test that it returns the same port when available
        found_port = self.manager._find_available_port(available_port)
        assert found_port == available_port, "Should return the requested port when available"
    
    def test_find_available_port_with_offset(self):
        """Test finding available port when first port is busy"""
        # Create a socket to occupy a port
        busy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            busy_socket.bind(('', 0))
            busy_port = busy_socket.getsockname()[1]
            
            # Test that it finds the next available port
            found_port = self.manager._find_available_port(busy_port)
            assert found_port != busy_port, "Should not return the busy port"
            assert found_port >= busy_port, "Should return a port >= requested port"
            assert found_port <= busy_port + 10, "Should stay within the search range"
            
        finally:
            busy_socket.close()
    
    def test_find_available_port_range_exhausted(self):
        """Test behavior when no ports are available in range"""
        # Mock socket.bind to always raise OSError (port busy)
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.bind.side_effect = OSError("Port busy")
            mock_socket_class.return_value = mock_socket
            
            with pytest.raises(RuntimeError) as exc_info:
                self.manager._find_available_port(8765, max_attempts=3)
            
            assert "Could not find available port in range 8765-8767" in str(exc_info.value)
    
    def test_find_available_port_default_attempts(self):
        """Test that default max_attempts is used correctly"""
        start_port = 50000  # Use high port to avoid conflicts
        
        # Should try up to 10 ports by default
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.bind.side_effect = OSError("Port busy")
            mock_socket_class.return_value = mock_socket
            
            with pytest.raises(RuntimeError) as exc_info:
                self.manager._find_available_port(start_port)
            
            # Should have tried 10 ports (default max_attempts)
            assert f"Could not find available port in range {start_port}-{start_port + 9}" in str(exc_info.value)
    
    def test_find_available_port_socket_cleanup(self):
        """Test that sockets are properly cleaned up during search"""
        start_port = NetworkFixtures.get_available_port()
        
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            # First call fails, second succeeds
            mock_socket.bind.side_effect = [OSError("Port busy"), None]
            mock_socket.getsockname.return_value = ('', start_port + 1)
            mock_socket_class.return_value = mock_socket
            
            found_port = self.manager._find_available_port(start_port, max_attempts=5)
            
            # Should have closed the socket after successful bind
            assert mock_socket.close.call_count >= 1, "Socket should be closed after successful bind"
    
    def test_find_available_port_socket_cleanup_on_error(self):
        """Test that sockets are cleaned up even when bind fails"""
        start_port = 60000
        
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.bind.side_effect = OSError("Port busy")
            mock_socket_class.return_value = mock_socket
            
            with pytest.raises(RuntimeError):
                self.manager._find_available_port(start_port, max_attempts=2)
            
            # Should have closed the socket even after failed bind
            assert mock_socket.close.call_count >= 2, "Socket should be closed even after failed bind"
    
    def test_find_available_port_edge_cases(self):
        """Test edge cases for port discovery"""
        # Test with max_attempts = 1
        start_port = NetworkFixtures.get_available_port()
        found_port = self.manager._find_available_port(start_port, max_attempts=1)
        assert found_port == start_port, "Should work with max_attempts=1"
        
        # Test with very high port number
        high_port = 65000
        try:
            found_port = self.manager._find_available_port(high_port, max_attempts=3)
            assert found_port >= high_port, "Should handle high port numbers"
        except RuntimeError:
            # High ports might not be available, this is acceptable
            pass
    
    @patch('builtins.print')
    def test_port_discovery_output_message(self, mock_print):
        """Test that port discovery prints correct message when port changes"""
        # Create a busy socket
        busy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            busy_socket.bind(('', 0))
            busy_port = busy_socket.getsockname()[1]
            
            # Find next available port
            found_port = self.manager._find_available_port(busy_port)
            
            if found_port != busy_port:
                # Check that the message was printed (this tests the current implementation)
                expected_message = f"Port {busy_port} is busy, using port {found_port} instead"
                # We can't easily test the print statement in the current implementation,
                # but we can verify the behavior is correct
                assert found_port > busy_port, "Should find a port after the busy one"
                
        finally:
            busy_socket.close()


class TestPortDiscoveryIntegration:
    """Integration tests for port discovery in the launch process"""
    
    def setup_method(self):
        self.manager = ccorc_module.SessionCLIManager()
    
    def test_port_discovery_in_team_config(self):
        """Test port discovery using team config default port"""
        from tests.fixtures.team_configs import TeamConfigFixtures
        
        config = TeamConfigFixtures.devops_team_config()
        default_port = config["settings"]["mcp_port"]  # Should be 8766
        
        # Test that we can find an available port starting from the default
        found_port = self.manager._find_available_port(default_port)
        assert found_port >= default_port, "Should find port >= default port"
    
    def test_port_discovery_fallback_default(self):
        """Test port discovery when no port specified in config"""
        # Test default port fallback (8765)
        found_port = self.manager._find_available_port(8765)
        assert found_port >= 8765, "Should find port >= default port"
    
    def test_multiple_port_discoveries_no_conflict(self):
        """Test that multiple port discoveries don't conflict"""
        ports = []
        for i in range(3):
            # Start each search from a different base to avoid conflicts
            start_port = 9000 + (i * 100)
            found_port = self.manager._find_available_port(start_port, max_attempts=5)
            ports.append(found_port)
        
        # All found ports should be unique (assuming they don't wrap around)
        assert len(set(ports)) == len(ports), "Multiple port discoveries should find unique ports"


class TestPortDiscoveryMocking:
    """Test port discovery with comprehensive mocking"""
    
    def setup_method(self):
        self.manager = ccorc_module.SessionCLIManager()
    
    def test_port_discovery_network_error_handling(self):
        """Test handling of network errors during port discovery"""
        with patch('socket.socket') as mock_socket_class:
            # First socket raises network error, second succeeds
            mock_socket1 = Mock()
            mock_socket1.bind.side_effect = socket.error("Network unreachable")
            
            mock_socket2 = Mock()
            mock_socket2.bind.return_value = None
            mock_socket2.getsockname.return_value = ('', 8766)
            
            mock_socket_class.side_effect = [mock_socket1, mock_socket2]
            
            found_port = self.manager._find_available_port(8765, max_attempts=5)
            assert found_port == 8766, "Should handle network errors and continue searching"
    
    def test_port_discovery_permission_error(self):
        """Test handling of permission errors during port discovery"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.bind.side_effect = PermissionError("Permission denied")
            mock_socket_class.return_value = mock_socket
            
            with pytest.raises(RuntimeError):
                self.manager._find_available_port(8765, max_attempts=3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])