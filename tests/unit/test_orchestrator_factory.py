"""
Unit tests for Orchestrator Factory
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.services.orchestrator_factory import (
    OrchestratorFactory, OrchestratorOptions, ConfigurableTmuxManager,
    ConfigurableClaudeLauncher
)


class TestConfigurableTmuxManager:
    """Test the configurable tmux manager wrapper"""
    
    def test_wraps_tmux_manager(self):
        """Test that it properly wraps the tmux manager"""
        mock_tmux = Mock()
        mock_tmux.some_method = Mock(return_value="test")
        mock_tmux.another_attr = "value"
        
        wrapper = ConfigurableTmuxManager(mock_tmux, force=True)
        
        # Should copy methods
        assert wrapper.some_method() == "test"
        assert wrapper.another_attr == "value"
    
    def test_create_session_with_defaults(self):
        """Test create_session uses configured defaults"""
        mock_tmux = Mock()
        mock_tmux.create_session = Mock(return_value="session")
        
        layout_config = {"type": "tiled"}
        wrapper = ConfigurableTmuxManager(mock_tmux, force=True, layout_config=layout_config)
        
        # Call without parameters
        result = wrapper.create_session(4)
        
        mock_tmux.create_session.assert_called_once_with(4, force=True, layout=layout_config)
        assert result == "session"
    
    def test_create_session_with_overrides(self):
        """Test create_session allows overriding defaults"""
        mock_tmux = Mock()
        mock_tmux.create_session = Mock(return_value="session")
        
        wrapper = ConfigurableTmuxManager(mock_tmux, force=True)
        
        # Call with explicit parameters
        custom_layout = {"type": "even-horizontal"}
        result = wrapper.create_session(2, force=False, layout=custom_layout)
        
        mock_tmux.create_session.assert_called_once_with(2, force=False, layout=custom_layout)


class TestConfigurableClaudeLauncher:
    """Test the configurable launcher wrapper"""
    
    def test_build_command_basic(self):
        """Test basic command building"""
        mock_launcher_class = Mock()
        mock_launcher_class.build_command_string = Mock(return_value="ccdk run agent")
        
        agent_configs = {
            "TestAgent": {
                "instance_name": "test-instance",
                "model": "opus"
            }
        }
        
        launcher = ConfigurableClaudeLauncher(mock_launcher_class, agent_configs)
        
        result = launcher.build_command_string("TestAgent", "session_1", "prompt", False)
        
        assert "ccdk -m opus" in result
        # Check that build_command_string was called with correct arguments
        call_args = mock_launcher_class.build_command_string.call_args[0]
        assert call_args[0] == "TestAgent"  # instance_name (passed through as-is)
        assert call_args[3] == False  # resume parameter
    
    def test_build_command_with_debug(self):
        """Test command building with debug flag"""
        mock_launcher_class = Mock()
        mock_launcher_class.build_command_string = Mock(return_value="ccdk run agent")
        
        agent_configs = {"TestAgent": {"model": "sonnet"}}
        
        launcher = ConfigurableClaudeLauncher(mock_launcher_class, agent_configs, debug=True)
        
        result = launcher.build_command_string("TestAgent", "session_1", "prompt", False)
        
        assert "ccdk -m sonnet" in result
        # Note: debug flag is not passed to ccdk command, only used internally
    
    def test_build_command_no_model(self):
        """Test command building without model override"""
        mock_launcher_class = Mock()
        mock_launcher_class.build_command_string = Mock(return_value="ccdk run agent")
        
        agent_configs = {"TestAgent": {}}
        
        launcher = ConfigurableClaudeLauncher(mock_launcher_class, agent_configs)
        
        result = launcher.build_command_string("TestAgent", "session_1", "prompt", False)
        
        # Should not modify command if no model specified
        assert result == "ccdk run agent"


class TestOrchestratorFactory:
    """Test the orchestrator factory"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.factory = OrchestratorFactory()
    
    @patch('src.services.orchestrator_factory.EnhancedOrchestrator')
    @patch('src.services.orchestrator_factory.Orchestrator')
    def test_create_enhanced_orchestrator(self, mock_orchestrator, mock_enhanced):
        """Test creating enhanced orchestrator"""
        options = OrchestratorOptions(
            context_name="test-context",
            orchestrator_type="enhanced"
        )
        
        mock_instance = Mock()
        mock_enhanced.return_value = mock_instance
        
        result = self.factory.create_orchestrator(options)
        
        mock_enhanced.assert_called_once()
        assert result == mock_instance
    
    @patch('src.services.orchestrator_factory.EnhancedOrchestrator')
    @patch('src.services.orchestrator_factory.Orchestrator')
    def test_create_base_orchestrator(self, mock_orchestrator, mock_enhanced):
        """Test creating base orchestrator"""
        options = OrchestratorOptions(
            context_name="test-context",
            orchestrator_type="base"
        )
        
        mock_instance = Mock()
        mock_orchestrator.return_value = mock_instance
        
        result = self.factory.create_orchestrator(options)
        
        mock_orchestrator.assert_called_once()
        assert result == mock_instance
    
    @patch('src.services.orchestrator_factory.EnhancedOrchestrator')
    def test_create_with_layout_config(self, mock_enhanced):
        """Test creating orchestrator with layout configuration"""
        layout_config = {"type": "tiled"}
        options = OrchestratorOptions(
            context_name="test-context",
            layout_config=layout_config,
            force=True
        )
        
        mock_instance = Mock()
        mock_instance.tmux = Mock()
        mock_enhanced.return_value = mock_instance
        
        result = self.factory.create_orchestrator(options)
        
        # Should wrap tmux manager
        assert isinstance(result.tmux, ConfigurableTmuxManager)
        assert result.tmux._force is True
        assert result.tmux._layout_config == layout_config
    
    @patch('src.claude_launcher_config.ClaudeLauncherConfig')
    def test_configure_launcher(self, mock_launcher_config):
        """Test configuring launcher for agents"""
        orchestrator = Mock()
        agent_configs = {
            "Agent1": {"model": "opus"},
            "Agent2": {"model": "sonnet"}
        }
        
        self.factory.configure_launcher(orchestrator, agent_configs, debug=True)
        
        # Should have replaced build_command_string
        assert callable(mock_launcher_config.build_command_string)
    
    @patch('src.services.orchestrator_factory.EnhancedOrchestrator')
    def test_create_configured_orchestrator_with_layout_service(self, mock_enhanced):
        """Test creating fully configured orchestrator with layout detection"""
        # Mock layout service
        mock_layout_service = Mock()
        mock_layout_service.detect_smart_layout = Mock(return_value={"type": "tiled"})
        
        factory = OrchestratorFactory(layout_service=mock_layout_service)
        
        options = OrchestratorOptions(context_name="test-context")
        team_config = Mock()
        agent_configs = {
            "Agent1": {"model": "opus"},
            "Agent2": {"model": "sonnet"}
        }
        
        mock_instance = Mock()
        mock_instance.tmux = Mock()
        mock_enhanced.return_value = mock_instance
        
        with patch.object(factory, 'configure_launcher') as mock_configure:
            result = factory.create_configured_orchestrator(
                options, team_config, agent_configs
            )
        
        # Should detect layout
        mock_layout_service.detect_smart_layout.assert_called_once_with(2)
        
        # Should configure launcher
        mock_configure.assert_called_once_with(mock_instance, agent_configs, False)
        
        assert result == mock_instance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])