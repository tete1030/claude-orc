"""
Port Discovery Service - Find available ports for services
"""
import socket
import logging
from typing import Optional


class PortDiscoveryService:
    """Service for discovering available network ports"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_available_port(self, preferred_port: int, max_attempts: int = 10) -> int:
        """
        Find an available port starting from the preferred port.
        
        Args:
            preferred_port: The desired port to try first
            max_attempts: Maximum number of ports to try
            
        Returns:
            An available port number
            
        Raises:
            RuntimeError: If no available port found within max_attempts
        """
        for offset in range(max_attempts):
            port = preferred_port + offset
            if self.is_port_available(port):
                if offset > 0:
                    self.logger.info(
                        f"Port {preferred_port} unavailable, using {port} instead"
                    )
                return port
        
        raise RuntimeError(
            f"No available port found in range {preferred_port}-{preferred_port + max_attempts - 1}"
        )
    
    def is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for binding.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('', port))
                return True
        except OSError:
            return False
    
    def find_service_port(self, service_name: str, default_port: int) -> int:
        """
        Find a port for a named service, with logging.
        
        Args:
            service_name: Name of the service (for logging)
            default_port: Default port to try
            
        Returns:
            Available port number
        """
        port = self.find_available_port(default_port)
        self.logger.info(f"{service_name} will use port {port}")
        return port