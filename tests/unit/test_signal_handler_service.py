"""
Unit tests for Signal Handler Service
"""
import pytest
import signal
import sys
from unittest.mock import Mock, patch, call
from src.services.signal_handler_service import SignalHandlerService, ShutdownTask


class TestSignalHandlerService:
    """Test the signal handler service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = SignalHandlerService()
        self.mock_handler = Mock()
        
    def teardown_method(self):
        """Clean up after tests"""
        self.service.restore_signal_handlers()
        self.service.clear_tasks()
    
    def test_initial_state(self):
        """Test service initial state"""
        assert len(self.service.shutdown_tasks) == 0
        assert not self.service.is_shutting_down
        assert len(self.service._original_handlers) == 0
    
    def test_register_shutdown_task(self):
        """Test registering shutdown tasks"""
        self.service.register_shutdown_task("test_task", self.mock_handler)
        
        assert len(self.service.shutdown_tasks) == 1
        task = self.service.shutdown_tasks[0]
        assert task.name == "test_task"
        assert task.handler == self.mock_handler
        assert task.timeout == 2.0
        assert task.critical == True
    
    def test_register_multiple_tasks(self):
        """Test registering multiple shutdown tasks"""
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()
        
        self.service.register_shutdown_task("task1", handler1)
        self.service.register_shutdown_task("task2", handler2, timeout=5.0)
        self.service.register_shutdown_task("task3", handler3, critical=False)
        
        assert len(self.service.shutdown_tasks) == 3
        assert self.service.shutdown_tasks[0].name == "task1"
        assert self.service.shutdown_tasks[1].timeout == 5.0
        assert self.service.shutdown_tasks[2].critical == False
    
    def test_trigger_shutdown(self):
        """Test manual shutdown trigger"""
        handler1 = Mock()
        handler2 = Mock()
        
        self.service.register_shutdown_task("task1", handler1)
        self.service.register_shutdown_task("task2", handler2)
        
        assert not self.service.is_shutting_down
        
        self.service.trigger_shutdown()
        
        assert self.service.is_shutting_down
        handler1.assert_called_once()
        handler2.assert_called_once()
    
    def test_shutdown_task_error_handling(self):
        """Test error handling in shutdown tasks"""
        good_handler = Mock()
        bad_handler = Mock(side_effect=Exception("Task failed"))
        
        self.service.register_shutdown_task("good_task", good_handler)
        self.service.register_shutdown_task("bad_task", bad_handler)
        
        # Should not raise exception
        self.service.trigger_shutdown()
        
        good_handler.assert_called_once()
        bad_handler.assert_called_once()
        assert self.service.is_shutting_down
    
    def test_non_critical_task_error(self):
        """Test non-critical task error handling"""
        handler = Mock(side_effect=Exception("Non-critical error"))
        
        self.service.register_shutdown_task("optional_task", handler, critical=False)
        
        # Should not raise or log error
        with patch.object(self.service.logger, 'error') as mock_error:
            with patch.object(self.service.logger, 'debug') as mock_debug:
                self.service.trigger_shutdown()
                
                mock_error.assert_not_called()
                mock_debug.assert_called()
    
    def test_multiple_shutdown_calls(self):
        """Test that multiple shutdown calls are ignored"""
        handler = Mock()
        self.service.register_shutdown_task("task", handler)
        
        self.service.trigger_shutdown()
        handler.assert_called_once()
        
        # Second call should be ignored
        self.service.trigger_shutdown()
        handler.assert_called_once()  # Still only called once
    
    def test_clear_tasks(self):
        """Test clearing all tasks"""
        self.service.register_shutdown_task("task1", Mock())
        self.service.register_shutdown_task("task2", Mock())
        
        assert len(self.service.shutdown_tasks) == 2
        
        self.service.clear_tasks()
        
        assert len(self.service.shutdown_tasks) == 0
    
    @patch('signal.signal')
    def test_setup_signal_handlers(self, mock_signal):
        """Test setting up signal handlers"""
        self.service.setup_signal_handlers()
        
        # Should set up handlers for SIGINT and SIGTERM by default
        assert mock_signal.call_count == 2
        
        # Check that original handlers are stored
        assert len(self.service._original_handlers) == 2
        assert signal.SIGINT in self.service._original_handlers
        assert signal.SIGTERM in self.service._original_handlers
    
    @patch('signal.signal')
    def test_setup_custom_signals(self, mock_signal):
        """Test setting up custom signal handlers"""
        custom_signals = [signal.SIGUSR1, signal.SIGUSR2]
        self.service.setup_signal_handlers(signals=custom_signals)
        
        assert mock_signal.call_count == 2
        call_args = [call[0][0] for call in mock_signal.call_args_list]
        assert signal.SIGUSR1 in call_args
        assert signal.SIGUSR2 in call_args
    
    @patch('signal.signal')
    def test_restore_signal_handlers(self, mock_signal):
        """Test restoring original signal handlers"""
        # Set up handlers first
        self.service.setup_signal_handlers()
        original_call_count = mock_signal.call_count
        
        # Restore handlers
        self.service.restore_signal_handlers()
        
        # Should have called signal.signal again to restore
        assert mock_signal.call_count > original_call_count
        assert len(self.service._original_handlers) == 0
    
    @patch('sys.exit')
    def test_signal_handler_with_exit(self, mock_exit):
        """Test signal handler with exit enabled"""
        handler = Mock()
        self.service.register_shutdown_task("task", handler)
        
        # Simulate signal handling
        self.service._handle_signal(signal.SIGINT, None, exit_on_signal=True)
        
        handler.assert_called_once()
        mock_exit.assert_called_once_with(0)
    
    @patch('sys.exit')
    def test_signal_handler_without_exit(self, mock_exit):
        """Test signal handler without exit"""
        handler = Mock()
        self.service.register_shutdown_task("task", handler)
        
        # Simulate signal handling
        self.service._handle_signal(signal.SIGINT, None, exit_on_signal=False)
        
        handler.assert_called_once()
        mock_exit.assert_not_called()
    
    def test_shutdown_task_execution_order(self):
        """Test that shutdown tasks execute in registration order"""
        call_order = []
        
        def make_handler(name):
            def handler():
                call_order.append(name)
            return handler
        
        self.service.register_shutdown_task("first", make_handler("first"))
        self.service.register_shutdown_task("second", make_handler("second"))
        self.service.register_shutdown_task("third", make_handler("third"))
        
        self.service.trigger_shutdown()
        
        assert call_order == ["first", "second", "third"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])