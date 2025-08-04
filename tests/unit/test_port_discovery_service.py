"""
Unit tests for Port Discovery Service
"""
import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from src.services.port_discovery_service import PortDiscoveryService


class TestPortDiscoveryService:
    """Test the port discovery service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = PortDiscoveryService()
    
    def test_find_available_port_first_available(self):
        """Test finding port when preferred port is available"""
        with patch.object(self.service, 'is_port_available', return_value=True):
            port = self.service.find_available_port(8765)
            assert port == 8765
    
    def test_find_available_port_with_offset(self):
        """Test finding port when preferred port is taken"""
        # Mock: first two ports taken, third available
        with patch.object(self.service, 'is_port_available') as mock_check:
            mock_check.side_effect = [False, False, True]
            
            port = self.service.find_available_port(8765)
            assert port == 8767
            assert mock_check.call_count == 3
    
    def test_find_available_port_exhausted(self):
        """Test when no ports available in range"""
        with patch.object(self.service, 'is_port_available', return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                self.service.find_available_port(8765, max_attempts=3)
            
            assert "No available port found in range 8765-8767" in str(exc_info.value)
    
    def test_is_port_available_free_port(self):
        """Test checking a free port"""
        # Find a likely free port
        with socket.socket() as sock:
            sock.bind(('', 0))
            free_port = sock.getsockname()[1]
        
        # Should be available immediately after closing
        assert self.service.is_port_available(free_port) is True
    
    def test_is_port_available_bound_port(self):
        """Test checking a bound port"""
        # Bind a port
        with socket.socket() as sock:
            sock.bind(('', 0))
            bound_port = sock.getsockname()[1]
            
            # Should not be available while bound
            assert self.service.is_port_available(bound_port) is False
    
    def test_find_service_port_logs_correctly(self):
        """Test that service port discovery logs appropriately"""
        with patch.object(self.service, 'is_port_available', return_value=True):
            with patch.object(self.service.logger, 'info') as mock_log:
                port = self.service.find_service_port("MCP Server", 8765)
                
                assert port == 8765
                mock_log.assert_called_once_with("MCP Server will use port 8765")
    
    def test_find_service_port_with_fallback(self):
        """Test service port discovery with fallback logging"""
        with patch.object(self.service, 'is_port_available') as mock_check:
            mock_check.side_effect = [False, True]
            
            with patch.object(self.service.logger, 'info') as mock_log:
                port = self.service.find_service_port("Test Service", 9000)
                
                assert port == 9001
                # Should log both the unavailable message and service message
                assert mock_log.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])