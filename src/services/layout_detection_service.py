"""
Layout Detection Service - Smart terminal layout detection
"""
import logging
import shutil
from typing import Dict, Tuple, Optional


class LayoutDetectionService:
    """Service for detecting optimal terminal layouts"""
    
    # Minimum dimensions for usable terminal
    MIN_WIDTH = 80
    MIN_HEIGHT = 24
    
    # Preferred dimensions for comfortable viewing
    PREFERRED_WIDTH = 120
    PREFERRED_HEIGHT = 40
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_smart_layout(self, num_agents: int) -> Dict[str, any]:
        """
        Detect optimal layout based on terminal size and number of agents.
        
        Args:
            num_agents: Number of agents to display
            
        Returns:
            Dictionary with layout configuration
        """
        try:
            width, height = self.get_terminal_size()
            
            self.logger.debug(f"Terminal size: {width}x{height}")
            
            # Check if terminal is too small for the number of agents
            # Each pane needs at least 3 lines (2 for content + 1 for border)
            min_height_per_pane = 3
            max_panes_for_height = height // min_height_per_pane
            
            if num_agents > max_panes_for_height:
                self.logger.error(
                    f"Terminal height {height} can only fit {max_panes_for_height} panes "
                    f"(need {num_agents}). Each pane needs at least {min_height_per_pane} lines."
                )
                # For now, still try with a grid layout but warn the user
                self.logger.warning("Attempting grid layout anyway, but panes will be very small!")
                return {"type": "grid"}
            
            if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
                self.logger.warning(
                    f"Terminal too small ({width}x{height}), using fallback layout"
                )
                return self._get_fallback_layout(num_agents)
            
            # Calculate optimal layout based on terminal size
            layout = self._calculate_optimal_layout(num_agents, width, height)
            
            self.logger.debug(
                f"Selected {layout.get('type', 'custom')} layout for {num_agents} agents"
            )
            
            self.logger.info(
                f"Smart layout for {num_agents} agents in {width}x{height} terminal: "
                f"{layout.get('type', 'custom')}"
            )
            
            return layout
        except Exception as e:
            self.logger.error(f"Error detecting smart layout: {e}")
            return self._get_fallback_layout(num_agents)
    
    def get_terminal_size(self) -> Tuple[int, int]:
        """
        Get current terminal dimensions.
        
        Returns:
            Tuple of (width, height)
        """
        size = shutil.get_terminal_size(fallback=(80, 24))
        return size.columns, size.lines
    
    def _calculate_optimal_layout(
        self, num_agents: int, width: int, height: int
    ) -> Dict[str, any]:
        """
        Calculate the optimal layout configuration.
        
        Args:
            num_agents: Number of agents
            width: Terminal width
            height: Terminal height
            
        Returns:
            Layout configuration dictionary
        """
        # For 2 agents: side-by-side if wide enough
        if num_agents == 2:
            if width >= 160:  # Enough for two comfortable panes
                return {
                    "type": "horizontal"
                }
            else:
                return {
                    "type": "vertical"
                }
        
        # For 3 agents: various arrangements
        elif num_agents == 3:
            if width >= 240:  # Very wide - three columns
                return {
                    "type": "horizontal"
                }
            elif width >= 160 and height >= 40:  # Wide and tall
                return {
                    "type": "main-vertical"
                }
            else:
                return {
                    "type": "vertical"
                }
        
        # For 4 agents: 2x2 grid if space permits
        elif num_agents == 4:
            if width >= 160 and height >= 48:
                return {
                    "type": "grid"
                }
            else:
                return {
                    "type": "vertical"
                }
        
        # For 5+ agents: use custom layout logic
        else:
            return self._get_custom_layout_for_many(num_agents, width, height)
    
    def _get_fallback_layout(self, num_agents: int) -> Dict[str, any]:
        """Get a simple fallback layout for small terminals"""
        if num_agents <= 2:
            return {"type": "vertical"}
        else:
            return {"type": "grid"}
    
    def _get_custom_layout_for_many(
        self, num_agents: int, width: int, height: int
    ) -> Dict[str, any]:
        """
        Create custom layout for many agents.
        
        For 5+ agents, we might want a more sophisticated layout
        like main-horizontal with the coordinator larger.
        """
        if num_agents == 5:
            # Check if terminal is large enough for main-horizontal with 5 panes
            # We need at least 5 lines per pane (25 total) plus borders
            min_height_needed = 30
            if height >= min_height_needed:
                return {
                    "type": "main-horizontal"
                }
            else:
                # Fall back to grid for small terminals
                self.logger.warning(
                    f"Terminal height {height} too small for main-horizontal with 5 panes "
                    f"(need {min_height_needed}+), using grid layout"
                )
                return {
                    "type": "grid"
                }
        else:
            return {
                "type": "grid"
            }
    
    def validate_layout(self, layout: Dict[str, any], num_agents: int) -> bool:
        """
        Validate that a layout is appropriate for the number of agents.
        
        Args:
            layout: Layout configuration
            num_agents: Number of agents
            
        Returns:
            True if layout is valid
        """
        layout_type = layout.get("type", "")
        
        # Basic validation
        if not layout_type:
            return False
        
        # Check if layout type is known
        valid_types = [
            "horizontal", "vertical", "main-horizontal",
            "main-vertical", "grid", "custom"
        ]
        
        return layout_type in valid_types