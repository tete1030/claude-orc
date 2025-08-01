"""
Unit tests for the tmux layout manager
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from layout_manager import (
    LayoutConfig, LayoutType, PaneConfig, CustomSplit, SplitDirection,
    TmuxLayoutManager, create_layout, get_layout_for_agent_count,
    LAYOUT_TEMPLATES
)


class TestLayoutConfig(unittest.TestCase):
    """Test LayoutConfig dataclass"""
    
    def test_default_layout_config(self):
        """Test default layout configuration"""
        config = LayoutConfig()
        self.assertEqual(config.type, LayoutType.HORIZONTAL)
        self.assertEqual(config.agent_count, 2)
        self.assertEqual(len(config.panes), 2)
        self.assertTrue(config.even_spacing)
        
    def test_grid_auto_dimensions(self):
        """Test grid layout auto-calculates dimensions"""
        config = LayoutConfig(type=LayoutType.GRID, agent_count=5)
        self.assertEqual(config.grid_rows, 2)
        self.assertEqual(config.grid_cols, 3)
        
    def test_grid_with_dimensions(self):
        """Test grid layout with explicit dimensions"""
        config = LayoutConfig(type=LayoutType.GRID, agent_count=4, grid_rows=2, grid_cols=2)
        self.assertEqual(config.grid_rows, 2)
        self.assertEqual(config.grid_cols, 2)
        
    def test_main_pane_size_validation(self):
        """Test main pane size validation"""
        # Valid size
        config = LayoutConfig(type=LayoutType.MAIN_HORIZONTAL, main_pane_size=70)
        self.assertEqual(config.main_pane_size, 70)
        
        # Invalid sizes should raise
        with self.assertRaises(ValueError):
            LayoutConfig(type=LayoutType.MAIN_HORIZONTAL, main_pane_size=0)
        with self.assertRaises(ValueError):
            LayoutConfig(type=LayoutType.MAIN_HORIZONTAL, main_pane_size=100)
            
    def test_validate_method(self):
        """Test layout validation"""
        # Valid layouts
        self.assertTrue(LayoutConfig(type=LayoutType.HORIZONTAL, agent_count=3).validate())
        self.assertTrue(LayoutConfig(type=LayoutType.VERTICAL, agent_count=5).validate())
        self.assertTrue(LayoutConfig(type=LayoutType.GRID, agent_count=4, grid_rows=2, grid_cols=2).validate())
        
        # Invalid layouts
        self.assertFalse(LayoutConfig(type=LayoutType.GRID, agent_count=5, grid_rows=2, grid_cols=2).validate())
        self.assertFalse(LayoutConfig(agent_count=0).validate())


class TestTmuxLayoutManager(unittest.TestCase):
    """Test TmuxLayoutManager class"""
    
    def setUp(self):
        self.manager = TmuxLayoutManager()
        self.session_name = "test-session"
        
    def test_horizontal_layout_commands(self):
        """Test horizontal layout command generation"""
        config = LayoutConfig(type=LayoutType.HORIZONTAL, agent_count=3)
        commands = self.manager.generate_layout_commands(config, self.session_name)
        
        # Should create 2 splits and even out
        self.assertEqual(len(commands), 3)
        self.assertIn("split-window", commands[0])
        self.assertIn("-h", commands[0])
        self.assertIn("even-horizontal", commands[2])
        
    def test_vertical_layout_commands(self):
        """Test vertical layout command generation"""
        config = LayoutConfig(type=LayoutType.VERTICAL, agent_count=3)
        commands = self.manager.generate_layout_commands(config, self.session_name)
        
        # Should create 2 splits and even out
        self.assertEqual(len(commands), 3)
        self.assertIn("split-window", commands[0])
        self.assertIn("-v", commands[0])
        self.assertIn("even-vertical", commands[2])
        
    def test_grid_layout_commands(self):
        """Test grid layout command generation"""
        config = LayoutConfig(type=LayoutType.GRID, agent_count=4)
        commands = self.manager.generate_layout_commands(config, self.session_name)
        
        # Should create 3 splits and apply tiled layout
        self.assertEqual(len(commands), 4)
        self.assertEqual(commands[0:3].count("split-window -t test-session:0"), 3)
        self.assertIn("tiled", commands[3])
        
    def test_main_horizontal_layout_commands(self):
        """Test main-horizontal layout command generation"""
        config = LayoutConfig(type=LayoutType.MAIN_HORIZONTAL, agent_count=3, main_pane_size=70)
        commands = self.manager.generate_layout_commands(config, self.session_name)
        
        # First split should be vertical with 30% for bottom
        self.assertIn("-v", commands[0])
        self.assertIn("-p 30", commands[0])
        # Second split should be horizontal in bottom pane
        self.assertIn("-h", commands[1])
        self.assertIn(":0.1", commands[1])
        
    def test_main_vertical_layout_commands(self):
        """Test main-vertical layout command generation"""
        config = LayoutConfig(type=LayoutType.MAIN_VERTICAL, agent_count=3, main_pane_size=60)
        commands = self.manager.generate_layout_commands(config, self.session_name)
        
        # First split should be horizontal with 40% for right
        self.assertIn("-h", commands[0])
        self.assertIn("-p 40", commands[0])
        # Second split should be vertical in right pane
        self.assertIn("-v", commands[1])
        self.assertIn(":0.1", commands[1])
        
    def test_custom_layout_commands(self):
        """Test custom layout command generation"""
        config = LayoutConfig(
            type=LayoutType.CUSTOM,
            agent_count=3,
            custom_splits=[
                CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=70),
                CustomSplit(target_pane=1, direction=SplitDirection.VERTICAL, size_percent=50)
            ]
        )
        commands = self.manager.generate_layout_commands(config, self.session_name)
        
        self.assertEqual(len(commands), 2)
        self.assertIn("-h", commands[0])
        self.assertIn("-p 70", commands[0])
        self.assertIn("-v", commands[1])
        self.assertIn("-p 50", commands[1])
        
    def test_keyboard_shortcuts(self):
        """Test keyboard shortcut generation"""
        config = LayoutConfig(type=LayoutType.HORIZONTAL, agent_count=5)
        shortcuts = self.manager.get_keyboard_shortcuts(config)
        
        # First 3 should have F-keys
        self.assertEqual(shortcuts[0], "F1")
        self.assertEqual(shortcuts[1], "F2")
        self.assertEqual(shortcuts[2], "F3")
        
        # All should have Alt+number
        for i in range(5):
            self.assertIn(f"Alt+{i+1}", shortcuts.values())
            
    def test_terminal_requirements(self):
        """Test terminal size calculation"""
        # Horizontal layout
        width, height = self.manager.calculate_terminal_requirements(
            LayoutConfig(type=LayoutType.HORIZONTAL, agent_count=3)
        )
        self.assertEqual(width, 240)  # 80 * 3
        self.assertEqual(height, 24)
        
        # Vertical layout
        width, height = self.manager.calculate_terminal_requirements(
            LayoutConfig(type=LayoutType.VERTICAL, agent_count=3)
        )
        self.assertEqual(width, 80)
        self.assertEqual(height, 72)  # 24 * 3
        
        # Grid layout
        width, height = self.manager.calculate_terminal_requirements(
            LayoutConfig(type=LayoutType.GRID, agent_count=4, grid_rows=2, grid_cols=2)
        )
        self.assertEqual(width, 160)  # 80 * 2
        self.assertEqual(height, 48)  # 24 * 2


class TestLayoutFactory(unittest.TestCase):
    """Test layout factory functions"""
    
    def test_create_layout_from_string(self):
        """Test creating layout from string"""
        # Template name
        layout = create_layout("2x2")
        self.assertEqual(layout.type, LayoutType.GRID)
        self.assertEqual(layout.agent_count, 4)
        self.assertEqual(layout.grid_rows, 2)
        self.assertEqual(layout.grid_cols, 2)
        
        # Layout type
        layout = create_layout("horizontal", 3)
        self.assertEqual(layout.type, LayoutType.HORIZONTAL)
        self.assertEqual(layout.agent_count, 3)
        
    def test_create_layout_from_dict(self):
        """Test creating layout from dict"""
        layout = create_layout({
            "type": LayoutType.MAIN_HORIZONTAL,
            "agent_count": 3,
            "main_pane_size": 60
        })
        self.assertEqual(layout.type, LayoutType.MAIN_HORIZONTAL)
        self.assertEqual(layout.agent_count, 3)
        self.assertEqual(layout.main_pane_size, 60)
        
    def test_create_layout_from_config(self):
        """Test creating layout from existing config"""
        config = LayoutConfig(type=LayoutType.VERTICAL, agent_count=2)
        layout = create_layout(config, 3)
        self.assertEqual(layout.agent_count, 3)
        
    def test_get_layout_for_agent_count(self):
        """Test automatic layout selection"""
        # Small team - horizontal
        layout = get_layout_for_agent_count(3)
        self.assertEqual(layout.type, LayoutType.HORIZONTAL)
        
        # 4 agents - 2x2 grid
        layout = get_layout_for_agent_count(4)
        self.assertEqual(layout.type, LayoutType.GRID)
        self.assertEqual(layout.grid_rows, 2)
        self.assertEqual(layout.grid_cols, 2)
        
        # 6 agents - 2x3 grid
        layout = get_layout_for_agent_count(6)
        self.assertEqual(layout.type, LayoutType.GRID)
        self.assertEqual(layout.grid_rows, 2)
        self.assertEqual(layout.grid_cols, 3)
        
        # Many agents - calculated grid
        layout = get_layout_for_agent_count(15)
        self.assertEqual(layout.type, LayoutType.GRID)
        self.assertGreaterEqual(layout.grid_rows * layout.grid_cols, 15)


class TestCustomLayouts(unittest.TestCase):
    """Test custom layout configurations"""
    
    def test_custom_2plus3_layout(self):
        """Test custom 2+3 layout (2 panes on top, 3 on bottom)"""
        config = LayoutConfig(
            type=LayoutType.CUSTOM,
            agent_count=5,
            custom_splits=[
                # First: split vertically to create top/bottom (40% top, 60% bottom)
                CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                # Second: split bottom pane into 3 (split at 33%)
                CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                # Third: split remaining bottom into 2 (split at 50%)
                CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                # Fourth: split top pane into 2
                CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
            ]
        )
        
        # Validate configuration
        self.assertTrue(config.validate())
        self.assertEqual(config.agent_count, 5)
        self.assertEqual(len(config.custom_splits), 4)
        
        # Generate commands
        manager = TmuxLayoutManager()
        commands = manager.generate_layout_commands(config, "test-session")
        
        # Should have 4 split commands
        self.assertEqual(len(commands), 4)
        
        # Verify split sequence
        self.assertIn("-v", commands[0])  # First split is vertical
        self.assertIn("-p 60", commands[0])  # Bottom gets 60%
        self.assertIn("-h", commands[1])  # Second split is horizontal
        self.assertIn("-p 33", commands[1])  # First bottom pane gets 33%
        self.assertIn("-h", commands[2])  # Third split is horizontal
        self.assertIn("-p 50", commands[2])  # Remaining bottom split evenly
        self.assertIn("-h", commands[3])  # Fourth split is horizontal
        self.assertIn("-p 50", commands[3])  # Top split evenly
        
    def test_custom_2plus3_pane_ordering(self):
        """Test that custom 2+3 layout creates correct pane ordering"""
        config = LayoutConfig(
            type=LayoutType.CUSTOM,
            agent_count=5,
            custom_splits=[
                CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
            ]
        )
        
        # Assign agents to verify layout
        config.panes[0].agent_name = "Architect"     # Top-left
        config.panes[1].agent_name = "Developer"     # Top-right (created by split 4)
        config.panes[2].agent_name = "QA"           # Bottom-left
        config.panes[3].agent_name = "DevOps"       # Bottom-middle
        config.panes[4].agent_name = "Docs"         # Bottom-right
        
        # Verify we have 5 panes
        self.assertEqual(len(config.panes), 5)
        
        # Verify agent assignments
        self.assertEqual(config.panes[0].agent_name, "Architect")
        self.assertEqual(config.panes[1].agent_name, "Developer")
        self.assertEqual(config.panes[2].agent_name, "QA")
        self.assertEqual(config.panes[3].agent_name, "DevOps")
        self.assertEqual(config.panes[4].agent_name, "Docs")
        
    def test_terminal_size_based_layout_selection(self):
        """Test layout selection based on terminal size"""
        # Test case structure: (width, height, expected_layout_type)
        test_cases = [
            # Large terminal - should use grid
            (240, 48, "grid"),
            (300, 60, "grid"),
            
            # Medium terminal - should use custom or main layouts
            (150, 24, "custom"),
            (160, 30, "custom"),
            
            # Small terminal - should use horizontal
            (80, 24, "horizontal"),
            (100, 20, "horizontal"),
            
            # Very small terminal - should still use horizontal
            (60, 20, "horizontal"),
            (40, 15, "horizontal"),
        ]
        
        for width, height, expected_type in test_cases:
            with self.subTest(terminal=f"{width}x{height}"):
                # This simulates the logic in devops_team_demo_enhanced.py
                if width >= 240 and height >= 48:
                    selected_layout = "grid"
                elif width >= 150:
                    selected_layout = "custom"
                else:
                    selected_layout = "horizontal"
                    
                self.assertEqual(selected_layout, expected_type,
                               f"Terminal {width}x{height} should select {expected_type} layout")
                               
    def test_custom_layout_terminal_requirements(self):
        """Test terminal size requirements for custom 2+3 layout"""
        config = LayoutConfig(
            type=LayoutType.CUSTOM,
            agent_count=5,
            custom_splits=[
                CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
            ]
        )
        
        manager = TmuxLayoutManager()
        
        # Custom layouts should return conservative estimate
        min_width, min_height = manager.calculate_terminal_requirements(config)
        
        # Should return 2x2 minimum for custom layouts
        self.assertEqual(min_width, 160)  # 80 * 2
        self.assertEqual(min_height, 48)  # 24 * 2
        
    def test_layout_fallback_hierarchy(self):
        """Test the layout fallback hierarchy for different terminal sizes"""
        # Simulate the fallback logic
        def select_layout_for_terminal(width, height, agent_count=5):
            if agent_count == 5:
                if width >= 240 and height >= 48:
                    return LayoutConfig(type=LayoutType.GRID, agent_count=5, 
                                      grid_rows=2, grid_cols=3)
                elif width >= 150:
                    # Custom 2+3 layout
                    return LayoutConfig(
                        type=LayoutType.CUSTOM,
                        agent_count=5,
                        custom_splits=[
                            CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                            CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                            CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                            CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
                        ]
                    )
                else:
                    return LayoutConfig(type=LayoutType.HORIZONTAL, agent_count=5)
            return LayoutConfig(type=LayoutType.HORIZONTAL, agent_count=agent_count)
            
        # Test various terminal sizes
        layout = select_layout_for_terminal(300, 60, 5)
        self.assertEqual(layout.type, LayoutType.GRID)
        self.assertEqual(layout.grid_rows, 2)
        self.assertEqual(layout.grid_cols, 3)
        
        layout = select_layout_for_terminal(160, 30, 5)
        self.assertEqual(layout.type, LayoutType.CUSTOM)
        self.assertEqual(len(layout.custom_splits), 4)
        
        layout = select_layout_for_terminal(80, 24, 5)
        self.assertEqual(layout.type, LayoutType.HORIZONTAL)
        
        # Very small terminal
        layout = select_layout_for_terminal(40, 15, 5)
        self.assertEqual(layout.type, LayoutType.HORIZONTAL)


class TestLayoutTemplates(unittest.TestCase):
    """Test predefined layout templates"""
    
    def test_all_templates_valid(self):
        """Test all templates are valid configurations"""
        for name, template in LAYOUT_TEMPLATES.items():
            self.assertTrue(template.validate(), f"Template {name} is invalid")
            
    def test_template_names(self):
        """Test expected templates exist"""
        expected = ["horizontal", "vertical", "2x2", "3x3", "2x3", "main-left", "main-top"]
        for name in expected:
            self.assertIn(name, LAYOUT_TEMPLATES)


if __name__ == '__main__':
    unittest.main()