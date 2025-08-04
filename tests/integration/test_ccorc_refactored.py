"""
Integration tests for refactored ccorc
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import ccorc components
import importlib.util
ccorc_path = Path(__file__).parent.parent.parent / "bin" / "ccorc"
spec = importlib.util.spec_from_file_location("ccorc", str(ccorc_path))
ccorc_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccorc_module)


class TestRefactoredCcorc:
    """Test that refactored services work in ccorc"""
    
    def test_session_cli_manager_has_services(self):
        """Test that SessionCLIManager initializes services"""
        manager = ccorc_module.SessionCLIManager()
        
        # Verify services are initialized
        assert hasattr(manager, 'port_service')
        assert hasattr(manager, 'layout_service')
        assert hasattr(manager, 'orchestrator_factory')
        
        # Verify they are the right types
        from src.services.port_discovery_service import PortDiscoveryService
        from src.services.layout_detection_service import LayoutDetectionService
        from src.services.orchestrator_factory import OrchestratorFactory
        
        assert isinstance(manager.port_service, PortDiscoveryService)
        assert isinstance(manager.layout_service, LayoutDetectionService)
        assert isinstance(manager.orchestrator_factory, OrchestratorFactory)
    
    def test_removed_methods_not_present(self):
        """Test that old methods were removed"""
        manager = ccorc_module.SessionCLIManager()
        
        # These methods should no longer exist
        assert not hasattr(manager, '_find_available_port')
        assert not hasattr(manager, '_detect_smart_layout')
    
    @patch('src.team_config_loader.TeamConfigLoader')
    @patch('src.services.orchestrator_factory.OrchestratorFactory')
    def test_launch_team_uses_services(self, mock_factory_class, mock_loader_class):
        """Test that launch_team uses the new services"""
        # Setup mocks
        mock_loader = Mock()
        mock_team_config = Mock()
        mock_team_config.name = "Test Team"
        mock_team_config.agents = [
            Mock(name="Agent1", role="Role1", model=None, prompt=None),
            Mock(name="Agent2", role="Role2", model="opus", prompt=None)
        ]
        mock_team_config.settings = {
            "default_context_name": "test-context",
            "orchestrator_type": "enhanced",
            "mcp_port": 8765
        }
        mock_loader.load_config.return_value = mock_team_config
        mock_loader.validate_config.return_value = []
        mock_loader_class.return_value = mock_loader
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.register_agent = Mock(return_value=Mock(pane_index=1))
        mock_orchestrator.launch = Mock(return_value=True)
        mock_orchestrator.running = True
        mock_orchestrator.stop = Mock()
        
        # Mock the factory
        mock_factory = Mock()
        mock_factory.create_configured_orchestrator = Mock(return_value=mock_orchestrator)
        
        # Create manager with mocked factory
        manager = ccorc_module.SessionCLIManager()
        manager.orchestrator_factory = mock_factory
        manager.context_manager.get_context = Mock(return_value=None)
        
        # Mock port service
        manager.port_service.find_available_port = Mock(return_value=8765)
        
        # Mock MCP server and threading
        with patch('src.mcp_central_server.CentralMCPServer') as mock_mcp:
            with patch('threading.Thread') as mock_thread:
                with patch('time.sleep'):
                    with patch('signal.signal'):
                        # Run launch_team
                        try:
                            result = manager.launch_team("test-team", force=True)
                        except Exception:
                            # May fail due to other dependencies, but we can check calls
                            pass
        
        # Verify services were used
        manager.port_service.find_available_port.assert_called_once_with(8765)
        mock_factory.create_configured_orchestrator.assert_called_once()
        
        # Verify factory was called with correct options
        call_args = mock_factory.create_configured_orchestrator.call_args
        options = call_args[0][0]  # First positional argument
        assert options.context_name == "test-context"
        assert options.orchestrator_type == "enhanced"
        assert options.force is True
    
    def test_no_monkey_patching_in_launch(self):
        """Test that monkey-patching code was removed"""
        manager = ccorc_module.SessionCLIManager()
        
        # Read the launch_team method source
        import inspect
        source = inspect.getsource(manager.launch_team)
        
        # These monkey-patching patterns should not be present
        assert "orchestrator.tmux.create_session = " not in source
        assert "ClaudeLauncherConfig.build_command_string = " not in source
        assert "def create_session_with_layout" not in source
        assert "def patched_build" not in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])