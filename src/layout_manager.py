"""
Tmux Layout Manager

Provides flexible pane layout management for the orchestrator.
Supports horizontal, vertical, grid, main-horizontal, main-vertical, and custom layouts.
"""

import logging
import math
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class LayoutType(Enum):
    """Predefined layout types"""
    HORIZONTAL = "horizontal"  # All panes in a row
    VERTICAL = "vertical"      # All panes in a column
    GRID = "grid"             # Even grid (e.g., 2x2, 3x3)
    MAIN_HORIZONTAL = "main-horizontal"  # Main pane on top, others below
    MAIN_VERTICAL = "main-vertical"      # Main pane on left, others on right
    CUSTOM = "custom"         # User-defined layout


class SplitDirection(Enum):
    """Direction for splitting panes"""
    HORIZONTAL = "horizontal"  # Split side by side (|)
    VERTICAL = "vertical"      # Split top/bottom (-)


@dataclass
class PaneConfig:
    """Configuration for a single pane"""
    index: int                    # Pane index (0-based)
    size_percent: Optional[int] = None  # Size as percentage (if specified)
    name: Optional[str] = None    # Optional pane name/label
    agent_name: Optional[str] = None  # Agent assigned to this pane
    
    def __post_init__(self):
        if self.size_percent is not None and not (0 < self.size_percent <= 100):
            raise ValueError(f"size_percent must be between 1-100, got {self.size_percent}")


@dataclass
class CustomSplit:
    """Defines a custom split operation"""
    target_pane: int              # Which pane to split
    direction: SplitDirection     # How to split
    size_percent: Optional[int] = 50  # Size of new pane (default 50%)
    
    def __post_init__(self):
        if not (0 < self.size_percent <= 100):
            raise ValueError(f"size_percent must be between 1-100, got {self.size_percent}")


@dataclass
class LayoutConfig:
    """Configuration for tmux pane layout"""
    type: LayoutType = LayoutType.HORIZONTAL
    agent_count: int = 2
    main_pane_size: int = 70     # For main-* layouts
    even_spacing: bool = True     # Whether to even out pane sizes
    grid_rows: Optional[int] = None
    grid_cols: Optional[int] = None
    panes: List[PaneConfig] = field(default_factory=list)
    custom_splits: List[CustomSplit] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize panes and validate configuration"""
        # Validate agent count
        if self.agent_count < 0:
            raise ValueError(f"agent_count must be non-negative, got {self.agent_count}")
            
        # Create pane configs if not provided
        if not self.panes:
            self.panes = [PaneConfig(index=i) for i in range(self.agent_count)]
            
        # Auto-calculate grid dimensions if needed
        if self.type == LayoutType.GRID and (not self.grid_rows or not self.grid_cols):
            if self.agent_count > 0:
                cols = math.ceil(math.sqrt(self.agent_count))
                rows = math.ceil(self.agent_count / cols)
                self.grid_rows = rows
                self.grid_cols = cols
            else:
                # Handle zero agents case
                self.grid_rows = 0
                self.grid_cols = 0
            
        # Validate main pane size
        if self.type in [LayoutType.MAIN_HORIZONTAL, LayoutType.MAIN_VERTICAL]:
            if not (0 < self.main_pane_size < 100):
                raise ValueError(f"main_pane_size must be between 1-99, got {self.main_pane_size}")
                
    def validate(self) -> bool:
        """Validate the layout configuration"""
        if self.agent_count < 1:
            return False
            
        if self.type == LayoutType.GRID:
            return self.grid_rows * self.grid_cols >= self.agent_count
            
        if self.type == LayoutType.CUSTOM:
            return len(self.custom_splits) > 0
            
        return True


class TmuxLayoutManager:
    """Manages tmux pane layouts"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def generate_layout_commands(self, config: LayoutConfig, session_name: str) -> List[str]:
        """Generate tmux commands to create the specified layout
        
        Args:
            config: Layout configuration
            session_name: Tmux session name
            
        Returns:
            List of tmux commands to execute
        """
        if not config.validate():
            raise ValueError(f"Invalid layout configuration: {config}")
            
        # Dispatch to appropriate layout generator
        generators = {
            LayoutType.HORIZONTAL: self._generate_horizontal_layout,
            LayoutType.VERTICAL: self._generate_vertical_layout,
            LayoutType.GRID: self._generate_grid_layout,
            LayoutType.MAIN_HORIZONTAL: self._generate_main_horizontal_layout,
            LayoutType.MAIN_VERTICAL: self._generate_main_vertical_layout,
            LayoutType.CUSTOM: self._generate_custom_layout,
        }
        
        generator = generators.get(config.type)
        if not generator:
            raise ValueError(f"Unknown layout type: {config.type}")
            
        return generator(config, session_name)
        
    def _generate_horizontal_layout(self, config: LayoutConfig, session_name: str) -> List[str]:
        """Generate commands for horizontal layout (all panes in a row)"""
        commands = []
        
        # Create additional panes
        for i in range(1, config.agent_count):
            if config.even_spacing:
                commands.append(f"split-window -t {session_name}:0 -h")
            else:
                size = config.panes[i].size_percent if i < len(config.panes) and config.panes[i].size_percent else None
                if size:
                    commands.append(f"split-window -t {session_name}:0 -h -p {size}")
                else:
                    commands.append(f"split-window -t {session_name}:0 -h")
                    
        # Even out the layout if requested
        if config.even_spacing:
            commands.append(f"select-layout -t {session_name}:0 even-horizontal")
            
        return commands
        
    def _generate_vertical_layout(self, config: LayoutConfig, session_name: str) -> List[str]:
        """Generate commands for vertical layout (all panes in a column)"""
        commands = []
        
        # Create additional panes
        for i in range(1, config.agent_count):
            if config.even_spacing:
                commands.append(f"split-window -t {session_name}:0 -v")
            else:
                size = config.panes[i].size_percent if i < len(config.panes) and config.panes[i].size_percent else None
                if size:
                    commands.append(f"split-window -t {session_name}:0 -v -p {size}")
                else:
                    commands.append(f"split-window -t {session_name}:0 -v")
                    
        # Even out the layout
        if config.even_spacing:
            commands.append(f"select-layout -t {session_name}:0 even-vertical")
            
        return commands
        
    def _generate_grid_layout(self, config: LayoutConfig, session_name: str) -> List[str]:
        """Generate commands for grid layout"""
        commands = []
        
        # Create all panes first
        for i in range(1, config.agent_count):
            commands.append(f"split-window -t {session_name}:0")
            
        # Apply tiled layout (tmux's built-in grid)
        commands.append(f"select-layout -t {session_name}:0 tiled")
        
        return commands
        
    def _generate_main_horizontal_layout(self, config: LayoutConfig, session_name: str) -> List[str]:
        """Generate commands for main-horizontal layout (main pane on top)"""
        commands = []
        
        if config.agent_count < 2:
            return commands  # No splits needed
            
        # First split creates the main pane on top
        remaining_size = 100 - config.main_pane_size
        commands.append(f"split-window -t {session_name}:0 -v -p {remaining_size}")
        
        # Create remaining panes in the bottom section
        for i in range(2, config.agent_count):
            commands.append(f"split-window -t {session_name}:0.1 -h")
            
        # Even out the bottom panes
        if config.agent_count > 2:
            commands.append(f"select-layout -t {session_name}:0 main-horizontal")
            
        return commands
        
    def _generate_main_vertical_layout(self, config: LayoutConfig, session_name: str) -> List[str]:
        """Generate commands for main-vertical layout (main pane on left)"""
        commands = []
        
        if config.agent_count < 2:
            return commands
            
        # First split creates the main pane on left
        remaining_size = 100 - config.main_pane_size
        commands.append(f"split-window -t {session_name}:0 -h -p {remaining_size}")
        
        # Create remaining panes in the right section
        for i in range(2, config.agent_count):
            commands.append(f"split-window -t {session_name}:0.1 -v")
            
        # Even out the right panes
        if config.agent_count > 2:
            commands.append(f"select-layout -t {session_name}:0 main-vertical")
            
        return commands
        
    def _generate_custom_layout(self, config: LayoutConfig, session_name: str) -> List[str]:
        """Generate commands for custom layout based on split definitions"""
        commands = []
        
        # Track pane indices as we create them
        # Tmux renumbers panes as splits happen
        pane_map = {0: 0}  # Initial pane
        next_pane_id = 1
        
        for split in config.custom_splits:
            # Get the actual tmux pane index for the target
            target_tmux_pane = pane_map.get(split.target_pane, split.target_pane)
            
            # Generate split command
            direction_flag = "-h" if split.direction == SplitDirection.HORIZONTAL else "-v"
            
            cmd = f"split-window -t {session_name}:0.{target_tmux_pane} {direction_flag}"
            if split.size_percent is not None:
                cmd += f" -p {split.size_percent}"
            commands.append(cmd)
            
            # Update pane mapping (simplified - real tmux renumbering is complex)
            pane_map[next_pane_id] = next_pane_id
            next_pane_id += 1
            
        return commands
        
    def get_keyboard_shortcuts(self, config: LayoutConfig) -> Dict[int, str]:
        """Get keyboard shortcut mapping for the layout
        
        Returns:
            Dict mapping pane index to primary shortcut, plus Alt shortcuts
        """
        shortcuts = {}
        
        # Primary shortcuts: F-keys for first 3 panes
        for i in range(min(config.agent_count, 3)):
            shortcuts[i] = f"F{i+1}"
            
        # Add Alt+number shortcuts for all panes (stored with negative keys to include all)
        for i in range(min(config.agent_count, 9)):
            # Use negative indices for Alt shortcuts to keep them separate
            shortcuts[-(i+1)] = f"Alt+{i+1}"
            
        return shortcuts
        
    def calculate_terminal_requirements(self, config: LayoutConfig) -> Tuple[int, int]:
        """Calculate minimum terminal size needed for layout
        
        Returns:
            (min_width, min_height) in characters
        """
        # Minimum size per pane for readability
        MIN_PANE_WIDTH = 80
        MIN_PANE_HEIGHT = 24
        
        if config.type == LayoutType.HORIZONTAL:
            return (MIN_PANE_WIDTH * config.agent_count, MIN_PANE_HEIGHT)
        elif config.type == LayoutType.VERTICAL:
            return (MIN_PANE_WIDTH, MIN_PANE_HEIGHT * config.agent_count)
        elif config.type == LayoutType.GRID:
            return (MIN_PANE_WIDTH * config.grid_cols, MIN_PANE_HEIGHT * config.grid_rows)
        elif config.type in [LayoutType.MAIN_HORIZONTAL, LayoutType.MAIN_VERTICAL]:
            # Conservative estimate for main layouts
            return (MIN_PANE_WIDTH * 2, MIN_PANE_HEIGHT * 2)
        else:
            # Custom layout - use conservative estimate
            return (MIN_PANE_WIDTH * 2, MIN_PANE_HEIGHT * 2)


# Predefined layout templates
LAYOUT_TEMPLATES = {
    "horizontal": LayoutConfig(type=LayoutType.HORIZONTAL),
    "vertical": LayoutConfig(type=LayoutType.VERTICAL),
    "2x2": LayoutConfig(type=LayoutType.GRID, agent_count=4, grid_rows=2, grid_cols=2),
    "3x3": LayoutConfig(type=LayoutType.GRID, agent_count=9, grid_rows=3, grid_cols=3),
    "2x3": LayoutConfig(type=LayoutType.GRID, agent_count=6, grid_rows=2, grid_cols=3),
    "main-left": LayoutConfig(type=LayoutType.MAIN_VERTICAL, main_pane_size=70),
    "main-top": LayoutConfig(type=LayoutType.MAIN_HORIZONTAL, main_pane_size=70),
}


def create_layout(layout_spec: Union[str, Dict, LayoutConfig], 
                 agent_count: Optional[int] = None) -> LayoutConfig:
    """Factory function to create layout configurations
    
    Args:
        layout_spec: Layout name, config dict, or LayoutConfig object
        agent_count: Number of agents (optional, inferred from some specs)
        
    Returns:
        LayoutConfig object
    """
    # If already a LayoutConfig, update agent count if provided
    if isinstance(layout_spec, LayoutConfig):
        if agent_count:
            layout_spec.agent_count = agent_count
        return layout_spec
        
    # If string, check templates first
    if isinstance(layout_spec, str):
        if layout_spec in LAYOUT_TEMPLATES:
            config = LAYOUT_TEMPLATES[layout_spec]
            if agent_count:
                config.agent_count = agent_count
            return config
            
        # Parse as layout type
        try:
            layout_type = LayoutType(layout_spec)
            return LayoutConfig(type=layout_type, agent_count=agent_count or 2)
        except ValueError:
            raise ValueError(f"Unknown layout: {layout_spec}")
            
    # If dict, create from dict
    if isinstance(layout_spec, dict):
        if agent_count:
            layout_spec['agent_count'] = agent_count
        
        # Convert string type to LayoutType enum if needed
        if 'type' in layout_spec and isinstance(layout_spec['type'], str):
            try:
                layout_spec['type'] = LayoutType(layout_spec['type'])
            except ValueError:
                raise ValueError(f"Unknown layout type: {layout_spec['type']}")
                
        return LayoutConfig(**layout_spec)
        
    raise TypeError(f"Invalid layout specification type: {type(layout_spec)}")


def get_layout_for_agent_count(num_agents: int) -> LayoutConfig:
    """Get recommended layout based on agent count
    
    Args:
        num_agents: Number of agents
        
    Returns:
        Recommended LayoutConfig
    """
    if num_agents <= 3:
        return LayoutConfig(type=LayoutType.HORIZONTAL, agent_count=num_agents)
    elif num_agents == 4:
        return LayoutConfig(type=LayoutType.GRID, agent_count=4, grid_rows=2, grid_cols=2)
    elif num_agents <= 6:
        return LayoutConfig(type=LayoutType.GRID, agent_count=num_agents, grid_rows=2, grid_cols=3)
    elif num_agents <= 9:
        return LayoutConfig(type=LayoutType.GRID, agent_count=num_agents, grid_rows=3, grid_cols=3)
    else:
        # For many agents, calculate appropriate grid
        cols = math.ceil(math.sqrt(num_agents))
        rows = math.ceil(num_agents / cols)
        return LayoutConfig(type=LayoutType.GRID, agent_count=num_agents, 
                          grid_rows=rows, grid_cols=cols)