"""
Unit tests for Layout Detection Service
"""
import pytest
from unittest.mock import patch, MagicMock
from src.services.layout_detection_service import LayoutDetectionService


class TestLayoutDetectionService:
    """Test the layout detection service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = LayoutDetectionService()
    
    def test_get_terminal_size_default(self):
        """Test getting terminal size with default"""
        with patch('shutil.get_terminal_size') as mock_size:
            mock_size.return_value = MagicMock(columns=120, lines=40)
            
            width, height = self.service.get_terminal_size()
            assert width == 120
            assert height == 40
    
    def test_detect_smart_layout_small_terminal(self):
        """Test layout detection with small terminal"""
        with patch.object(self.service, 'get_terminal_size', return_value=(70, 20)):
            layout = self.service.detect_smart_layout(3)
            
            # Should use fallback for small terminal
            assert layout["type"] == "grid"
    
    def test_detect_smart_layout_2_agents_wide(self):
        """Test layout for 2 agents in wide terminal"""
        with patch.object(self.service, 'get_terminal_size', return_value=(200, 50)):
            layout = self.service.detect_smart_layout(2)
            
            assert layout["type"] == "horizontal"
    
    def test_detect_smart_layout_2_agents_narrow(self):
        """Test layout for 2 agents in narrow terminal"""
        with patch.object(self.service, 'get_terminal_size', return_value=(100, 50)):
            layout = self.service.detect_smart_layout(2)
            
            assert layout["type"] == "vertical"
    
    def test_detect_smart_layout_3_agents_very_wide(self):
        """Test layout for 3 agents in very wide terminal"""
        with patch.object(self.service, 'get_terminal_size', return_value=(250, 50)):
            layout = self.service.detect_smart_layout(3)
            
            assert layout["type"] == "horizontal"
    
    def test_detect_smart_layout_3_agents_medium(self):
        """Test layout for 3 agents in medium terminal"""
        with patch.object(self.service, 'get_terminal_size', return_value=(170, 45)):
            layout = self.service.detect_smart_layout(3)
            
            assert layout["type"] == "main-vertical"
    
    def test_detect_smart_layout_4_agents_large(self):
        """Test layout for 4 agents in large terminal"""
        with patch.object(self.service, 'get_terminal_size', return_value=(180, 60)):
            layout = self.service.detect_smart_layout(4)
            
            assert layout["type"] == "grid"
    
    def test_detect_smart_layout_5_agents(self):
        """Test layout for 5 agents"""
        with patch.object(self.service, 'get_terminal_size', return_value=(180, 60)):
            layout = self.service.detect_smart_layout(5)
            
            assert layout["type"] == "main-horizontal"
    
    def test_detect_smart_layout_many_agents(self):
        """Test layout for many agents"""
        with patch.object(self.service, 'get_terminal_size', return_value=(180, 60)):
            layout = self.service.detect_smart_layout(8)
            
            assert layout["type"] == "grid"
    
    def test_validate_layout_valid(self):
        """Test validating a valid layout"""
        layout = {"type": "horizontal", "description": "test"}
        assert self.service.validate_layout(layout, 2) is True
        
        layout = {"type": "grid", "description": "test"}
        assert self.service.validate_layout(layout, 4) is True
    
    def test_validate_layout_invalid(self):
        """Test validating invalid layouts"""
        # No type
        assert self.service.validate_layout({}, 2) is False
        
        # Invalid type
        layout = {"type": "invalid-layout"}
        assert self.service.validate_layout(layout, 2) is False
        
        # Empty type
        layout = {"type": ""}
        assert self.service.validate_layout(layout, 2) is False
    
    def test_fallback_layout_small_teams(self):
        """Test fallback layout for small teams"""
        layout = self.service._get_fallback_layout(2)
        assert layout["type"] == "vertical"
        
        layout = self.service._get_fallback_layout(1)
        assert layout["type"] == "vertical"
    
    def test_fallback_layout_large_teams(self):
        """Test fallback layout for large teams"""
        layout = self.service._get_fallback_layout(4)
        assert layout["type"] == "grid"
        
        layout = self.service._get_fallback_layout(6)
        assert layout["type"] == "grid"
    
    def test_terminal_size_with_fallback(self):
        """Test terminal size with fallback values"""
        # shutil.get_terminal_size handles fallback internally
        with patch('shutil.get_terminal_size') as mock_size:
            mock_size.return_value = MagicMock(columns=80, lines=24)
            
            width, height = self.service.get_terminal_size()
            assert width == 80
            assert height == 24
            
            # Verify fallback was passed
            mock_size.assert_called_once_with(fallback=(80, 24))
    
    def test_detect_smart_layout_exception_handling(self):
        """Test exception handling in smart layout detection"""
        with patch.object(self.service, 'get_terminal_size', side_effect=Exception("Error")):
            layout = self.service.detect_smart_layout(3)
            # Should return fallback layout on error
            assert layout is not None
            assert "type" in layout
    
    def test_boundary_conditions(self):
        """Test layout detection at boundary conditions"""
        # Test at exact thresholds
        test_cases = [
            # (width, height, agents, expected_type)
            (240, 48, 5, "main-horizontal"),  # Large terminal boundary for 5 agents
            (180, 50, 4, "grid"),              # Grid threshold for 4 agents
            (160, 40, 3, "main-vertical"),     # Medium terminal for 3 agents (threshold is 160, not 150)
            (120, 30, 2, "vertical"),          # Narrow terminal for 2 agents
        ]
        
        for width, height, agents, expected in test_cases:
            with patch.object(self.service, 'get_terminal_size', return_value=(width, height)):
                layout = self.service.detect_smart_layout(agents)
                assert layout["type"] == expected, f"Failed for {width}x{height} with {agents} agents"
    
    def test_detect_smart_layout_logging(self):
        """Test that layout detection logs appropriate messages"""
        import logging
        
        with patch.object(self.service, 'get_terminal_size', return_value=(250, 50)):
            with patch.object(self.service.logger, 'debug') as mock_debug:
                layout = self.service.detect_smart_layout(3)
                
                # Should log terminal size and chosen layout
                mock_debug.assert_called()
                calls = [call[0][0] for call in mock_debug.call_args_list]
                assert any("Terminal size" in call for call in calls)
                assert any("layout for 3 agents" in call for call in calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])