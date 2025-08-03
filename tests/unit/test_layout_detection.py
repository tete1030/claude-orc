"""
Unit tests for smart layout detection logic in ccorc launch
"""
import pytest
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


class TestLayoutDetection:
    """Test the smart layout detection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ccorc_module.SessionCLIManager()
    
    def test_layout_detection_non_five_agents(self):
        """Test that layout detection only works for 5 agents"""
        # Should return None for non-5-agent teams
        assert self.manager._detect_smart_layout(1) is None
        assert self.manager._detect_smart_layout(3) is None
        assert self.manager._detect_smart_layout(4) is None
        assert self.manager._detect_smart_layout(6) is None
        assert self.manager._detect_smart_layout(10) is None
    
    @patch('subprocess.run')
    def test_layout_detection_large_terminal(self, mock_subprocess):
        """Test layout detection for large terminal"""
        # Mock terminal size: 250x50 (large)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "50 250"  # rows cols
        mock_subprocess.return_value = mock_result
        
        layout = self.manager._detect_smart_layout(5)
        
        expected = {
            "type": "grid",
            "agent_count": 5,
            "grid_rows": 2,
            "grid_cols": 3
        }
        assert layout == expected, "Large terminal should use grid layout"
    
    @patch('subprocess.run')
    def test_layout_detection_medium_terminal(self, mock_subprocess):
        """Test layout detection for medium terminal"""
        # Mock terminal size: 160x30 (medium)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "30 160"  # rows cols
        mock_subprocess.return_value = mock_result
        
        with patch('src.layout_manager.CustomSplit') as mock_custom_split, \
             patch('src.layout_manager.SplitDirection') as mock_split_direction:
            
            # Mock the CustomSplit and SplitDirection
            mock_split_direction.VERTICAL = "VERTICAL"
            mock_split_direction.HORIZONTAL = "HORIZONTAL"
            
            layout = self.manager._detect_smart_layout(5)
            
            assert layout["type"] == "custom", "Medium terminal should use custom layout"
            assert layout["agent_count"] == 5
            assert "custom_splits" in layout
            assert len(layout["custom_splits"]) == 4, "Should have 4 custom splits for 5 agents"
    
    @patch('subprocess.run')
    def test_layout_detection_small_terminal(self, mock_subprocess):
        """Test layout detection for small terminal"""
        # Mock terminal size: 100x20 (small)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "20 100"  # rows cols
        mock_subprocess.return_value = mock_result
        
        layout = self.manager._detect_smart_layout(5)
        
        expected = {"type": "horizontal"}
        assert layout == expected, "Small terminal should use horizontal layout"
    
    @patch('subprocess.run')
    def test_layout_detection_stty_failure(self, mock_subprocess):
        """Test layout detection when stty command fails"""
        # Mock stty command failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result
        
        with patch('src.layout_manager.CustomSplit') as mock_custom_split, \
             patch('src.layout_manager.SplitDirection') as mock_split_direction:
            
            mock_split_direction.VERTICAL = "VERTICAL"
            mock_split_direction.HORIZONTAL = "HORIZONTAL"
            
            layout = self.manager._detect_smart_layout(5)
            
            assert layout["type"] == "custom", "Should fall back to custom layout when stty fails"
            assert layout["agent_count"] == 5
    
    @patch('subprocess.run')
    def test_layout_detection_exception_handling(self, mock_subprocess):
        """Test layout detection when subprocess raises exception"""
        # Mock subprocess to raise exception
        mock_subprocess.side_effect = Exception("Command failed")
        
        layout = self.manager._detect_smart_layout(5)
        
        assert layout is None, "Should return None when exception occurs"
    
    @patch('subprocess.run')
    def test_layout_detection_import_error(self, mock_subprocess):
        """Test layout detection when CustomSplit import fails"""
        # Mock terminal size for medium terminal
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "30 160"
        mock_subprocess.return_value = mock_result
        
        # Mock import error for layout_manager
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            layout = self.manager._detect_smart_layout(5)
            
            # Should fall back gracefully
            assert layout is None or layout == {"type": "horizontal"}, "Should handle import errors gracefully"
    
    @patch('subprocess.run')
    def test_layout_detection_boundary_conditions(self, mock_subprocess):
        """Test layout detection at boundary conditions"""
        # Test exactly at large terminal boundary (240x48)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "48 240"
        mock_subprocess.return_value = mock_result
        
        layout = self.manager._detect_smart_layout(5)
        assert layout["type"] == "grid", "Should use grid at boundary"
        
        # Test just below large terminal boundary (239x47)
        mock_result.stdout = "47 239"
        
        with patch('src.layout_manager.CustomSplit'), \
             patch('src.layout_manager.SplitDirection') as mock_split_direction:
            mock_split_direction.VERTICAL = "VERTICAL"
            mock_split_direction.HORIZONTAL = "HORIZONTAL"
            
            layout = self.manager._detect_smart_layout(5)
            assert layout["type"] == "custom", "Should use custom just below boundary"
        
        # Test exactly at medium terminal boundary (150x24)
        mock_result.stdout = "24 150"
        
        with patch('src.layout_manager.CustomSplit'), \
             patch('src.layout_manager.SplitDirection') as mock_split_direction:
            mock_split_direction.VERTICAL = "VERTICAL"
            mock_split_direction.HORIZONTAL = "HORIZONTAL"
            
            layout = self.manager._detect_smart_layout(5)
            assert layout["type"] == "custom", "Should use custom at medium boundary"
        
        # Test just below medium terminal boundary (149x23)
        mock_result.stdout = "23 149"
        layout = self.manager._detect_smart_layout(5)
        assert layout["type"] == "horizontal", "Should use horizontal just below medium boundary"
    
    def test_layout_detection_custom_splits_structure(self):
        """Test the structure of custom splits for medium terminals"""
        with patch('subprocess.run') as mock_subprocess, \
             patch('src.layout_manager.CustomSplit') as mock_custom_split, \
             patch('src.layout_manager.SplitDirection') as mock_split_direction:
            
            # Mock medium terminal
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "30 160"
            mock_subprocess.return_value = mock_result
            
            # Mock the enums
            mock_split_direction.VERTICAL = "VERTICAL"
            mock_split_direction.HORIZONTAL = "HORIZONTAL"
            
            # Create mock CustomSplit instances
            mock_splits = []
            for i in range(4):
                mock_split = Mock()
                mock_splits.append(mock_split)
            mock_custom_split.side_effect = mock_splits
            
            layout = self.manager._detect_smart_layout(5)
            
            # Verify the custom splits were created correctly
            assert mock_custom_split.call_count == 4, "Should create 4 custom splits"
            
            # Verify the structure of the layout
            assert layout["type"] == "custom"
            assert layout["agent_count"] == 5
            assert len(layout["custom_splits"]) == 4
            
            # Verify the splits match the expected mock objects
            for i, split in enumerate(layout["custom_splits"]):
                assert split == mock_splits[i], f"Split {i} should match mock"


class TestLayoutDetectionIntegration:
    """Integration tests for layout detection in the launch process"""
    
    def setup_method(self):
        self.manager = ccorc_module.SessionCLIManager()
    
    @patch('subprocess.run')
    def test_layout_detection_with_tmux_integration(self, mock_subprocess):
        """Test that layout detection integrates properly with tmux"""
        # Mock large terminal
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "50 250"
        mock_subprocess.return_value = mock_result
        
        layout = self.manager._detect_smart_layout(5)
        
        # This layout should be compatible with tmux grid layout
        assert layout["type"] == "grid"
        assert layout["grid_rows"] * layout["grid_cols"] >= layout["agent_count"]
        assert layout["grid_rows"] == 2
        assert layout["grid_cols"] == 3
    
    def test_layout_detection_with_orchestrator_create_session(self):
        """Test that layout detection works with orchestrator create_session override"""
        # This tests the integration point where layout detection is used
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "50 250"  # Large terminal
            mock_subprocess.return_value = mock_result
            
            # Mock orchestrator and tmux
            mock_orchestrator = Mock()
            mock_tmux = Mock()
            mock_orchestrator.tmux = mock_tmux
            original_create_session = Mock()
            mock_tmux.create_session = original_create_session
            
            # Test the create_session override logic (simplified)
            def create_session_with_layout(num_panes, force=None, layout=None):
                if layout is None:
                    layout = self.manager._detect_smart_layout(num_panes)
                return original_create_session(num_panes, force=force, layout=layout)
            
            # Test the override
            result_layout = create_session_with_layout(5)
            
            # Verify that original_create_session was called with the detected layout
            original_create_session.assert_called_once()
            call_args = original_create_session.call_args
            
            # The layout should be passed through
            assert 'layout' in call_args.kwargs or len(call_args.args) >= 3


class TestLayoutDetectionMocking:
    """Test layout detection with comprehensive mocking scenarios"""
    
    def setup_method(self):
        self.manager = ccorc_module.SessionCLIManager()
    
    @patch('builtins.print')
    @patch('subprocess.run')
    def test_layout_detection_debug_output(self, mock_subprocess, mock_print):
        """Test that layout detection produces correct debug output"""
        # Test large terminal debug output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "50 250"
        mock_subprocess.return_value = mock_result
        
        layout = self.manager._detect_smart_layout(5)
        
        # Check that debug messages were printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Should print terminal size and layout choice
        terminal_size_printed = any("Terminal size detected: 250x50" in call for call in print_calls)
        layout_choice_printed = any("Using 2x3 grid layout" in call for call in print_calls)
        
        assert terminal_size_printed, "Should print terminal size"
        assert layout_choice_printed, "Should print layout choice"
    
    @patch('subprocess.run')
    def test_layout_detection_malformed_stty_output(self, mock_subprocess):
        """Test handling of malformed stty output"""
        # Test with malformed output
        test_cases = [
            "invalid",           # Not numbers
            "50",               # Only one number  
            "50 250 extra",     # Too many numbers
            "",                 # Empty
            "abc def",          # Non-numeric
        ]
        
        for malformed_output in test_cases:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = malformed_output
            mock_subprocess.return_value = mock_result
            
            # Should handle malformed output gracefully
            try:
                layout = self.manager._detect_smart_layout(5)
                # Should either return None or a fallback layout
                if layout is not None:
                    assert "type" in layout, f"Layout should have type for input: {malformed_output}"
            except Exception as e:
                pytest.fail(f"Should handle malformed output gracefully: {malformed_output}, got: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])