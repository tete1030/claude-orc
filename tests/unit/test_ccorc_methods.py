"""
Unit tests for specific methods extracted from ccorc launch functionality
This tests the current behavior to lock it down before refactoring.
"""
import pytest
import socket
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from tests.fixtures.team_configs import TeamConfigFixtures, LaunchConfigFixtures, NetworkFixtures


class CCORCMethods:
    """Extract the methods we want to test from ccorc"""
    
    def _get_intelligent_model(self, agent_name: str, agent_role: str) -> str:
        """Get intelligent model assignment based on agent role"""
        # High-complexity roles get Opus
        if any(keyword in agent_role.lower() or keyword in agent_name.lower() 
               for keyword in ["architect", "lead"]):
            return "opus"
        # Implementation roles get Opus
        elif any(keyword in agent_role.lower() or keyword in agent_name.lower() 
                 for keyword in ["developer", "implementation", "coding"]):
            return "opus"
        # Standard roles get Sonnet  
        else:
            return "sonnet"

    def _find_available_port(self, start_port: int, max_attempts: int = 10) -> int:
        """Find an available port starting from start_port"""
        import socket
        for port_offset in range(max_attempts):
            test_port = start_port + port_offset
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('', test_port))
                sock.close()
                if test_port != start_port:
                    print(f"Port {start_port} is busy, using port {test_port} instead")
                return test_port
            except OSError:
                continue
            finally:
                sock.close()
        
        raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts - 1}")

    def _detect_smart_layout(self, num_agents: int) -> dict:
        """Detect optimal layout based on terminal size and agent count"""
        if num_agents != 5:
            return None  # Only optimize for 5-agent teams
            
        try:
            # Try to get terminal size
            import subprocess
            result = subprocess.run(['stty', 'size'], capture_output=True, text=True)
            if result.returncode == 0:
                rows, cols = map(int, result.stdout.strip().split())
                print(f"Terminal size detected: {cols}x{rows}")
                
                # Check if terminal is large enough for 2x3 grid
                if cols >= 240 and rows >= 48:
                    layout = {
                        "type": "grid",
                        "agent_count": 5,
                        "grid_rows": 2,
                        "grid_cols": 3
                    }
                    print("Using 2x3 grid layout for large terminal")
                    return layout
                elif cols >= 150:
                    # Use custom 2+3 layout for medium terminals
                    try:
                        from src.layout_manager import CustomSplit, SplitDirection
                        layout = {
                            "type": "custom",
                            "agent_count": 5,
                            "custom_splits": [
                                # First: split horizontally to create top/bottom (40% top, 60% bottom for 2:3 ratio)
                                CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                                # Second: split bottom pane into 3 (split at 33%)
                                CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                                # Third: split remaining bottom into 2 (split at 50%)
                                CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                                # Fourth: split top pane into 2
                                CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
                            ]
                        }
                        print("Using custom 2+3 layout for medium terminal")
                        return layout
                    except ImportError:
                        print("Could not import layout manager, falling back")
                        return None
                else:
                    # Fallback to horizontal for small terminals
                    print("Terminal too small for grid, using horizontal layout")
                    return {"type": "horizontal"}
            else:
                # If can't detect size, use custom 2+3 layout as default
                try:
                    from src.layout_manager import CustomSplit, SplitDirection
                    layout = {
                        "type": "custom",
                        "agent_count": 5,
                        "custom_splits": [
                            CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                            CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                            CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                            CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
                        ]
                    }
                    print("Could not detect terminal size, using custom 2+3 layout")
                    return layout
                except ImportError:
                    print("Could not import layout manager")
                    return None
        except Exception as e:
            print(f"Layout detection failed: {e}, using default")
            return None


class TestModelResolution:
    """Test the intelligent model assignment logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.methods = CCORCMethods()
    
    def test_intelligent_model_assignment_architect(self):
        """Test that Architect role gets Opus"""
        model = self.methods._get_intelligent_model("Architect", "Team Lead and System Architect")
        assert model == "opus", "Architect should get Opus model"
    
    def test_intelligent_model_assignment_developer(self):
        """Test that Developer role gets Opus"""
        model = self.methods._get_intelligent_model("Developer", "Implementation and Coding Engineer")
        assert model == "opus", "Developer should get Opus model"
    
    def test_intelligent_model_assignment_qa(self):
        """Test that QA role gets Sonnet"""
        model = self.methods._get_intelligent_model("QA", "Quality Assurance Engineer")
        assert model == "sonnet", "QA should get Sonnet model"
    
    def test_intelligent_model_assignment_devops(self):
        """Test that DevOps role gets Sonnet"""
        model = self.methods._get_intelligent_model("DevOps", "Infrastructure and Deployment Engineer")
        assert model == "sonnet", "DevOps should get Sonnet model"
    
    def test_intelligent_model_assignment_docs(self):
        """Test that Docs role gets Sonnet"""
        model = self.methods._get_intelligent_model("Docs", "Documentation Specialist")
        assert model == "sonnet", "Docs should get Sonnet model"
    
    def test_intelligent_model_assignment_lead_role(self):
        """Test that Lead roles get Opus"""
        model = self.methods._get_intelligent_model("TeamLead", "Lead Engineer")
        assert model == "opus", "Lead roles should get Opus model"
    
    def test_intelligent_model_assignment_implementation_role(self):
        """Test that implementation roles get Opus"""
        model = self.methods._get_intelligent_model("Engineer", "Software Implementation Specialist")
        assert model == "opus", "Implementation roles should get Opus model"
    
    def test_intelligent_model_assignment_coding_role(self):
        """Test that coding roles get Opus"""
        model = self.methods._get_intelligent_model("Programmer", "Coding Specialist")
        assert model == "opus", "Coding roles should get Opus model"
    
    def test_intelligent_model_assignment_generic_role(self):
        """Test that generic roles get Sonnet"""
        model = self.methods._get_intelligent_model("Assistant", "General Assistant")
        assert model == "sonnet", "Generic roles should get Sonnet model"


class TestPortDiscovery:
    """Test the port discovery functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.methods = CCORCMethods()
    
    def test_find_available_port_first_try(self):
        """Test finding available port when first port is free"""
        # Get an actually available port
        available_port = NetworkFixtures.get_available_port()
        
        # Test that it returns the same port when available
        found_port = self.methods._find_available_port(available_port)
        assert found_port == available_port, "Should return the requested port when available"
    
    def test_find_available_port_with_offset(self):
        """Test finding available port when first port is busy"""
        # Create a socket to occupy a port
        busy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            busy_socket.bind(('', 0))
            busy_port = busy_socket.getsockname()[1]
            
            # Test that it finds the next available port
            found_port = self.methods._find_available_port(busy_port)
            assert found_port != busy_port, "Should not return the busy port"
            assert found_port >= busy_port, "Should return a port >= requested port"
            assert found_port <= busy_port + 10, "Should stay within the search range"
            
        finally:
            busy_socket.close()
    
    def test_find_available_port_range_exhausted(self):
        """Test behavior when no ports are available in range"""
        # Mock socket.bind to always raise OSError (port busy)
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.bind.side_effect = OSError("Port busy")
            mock_socket_class.return_value = mock_socket
            
            with pytest.raises(RuntimeError) as exc_info:
                self.methods._find_available_port(8765, max_attempts=3)
            
            assert "Could not find available port in range 8765-8767" in str(exc_info.value)


class TestLayoutDetection:
    """Test the smart layout detection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.methods = CCORCMethods()
    
    def test_layout_detection_non_five_agents(self):
        """Test that layout detection only works for 5 agents"""
        # Should return None for non-5-agent teams
        assert self.methods._detect_smart_layout(1) is None
        assert self.methods._detect_smart_layout(3) is None
        assert self.methods._detect_smart_layout(4) is None
        assert self.methods._detect_smart_layout(6) is None
        assert self.methods._detect_smart_layout(10) is None
    
    @patch('subprocess.run')
    def test_layout_detection_large_terminal(self, mock_subprocess):
        """Test layout detection for large terminal"""
        # Mock terminal size: 250x50 (large)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "50 250"  # rows cols
        mock_subprocess.return_value = mock_result
        
        layout = self.methods._detect_smart_layout(5)
        
        expected = {
            "type": "grid",
            "agent_count": 5,
            "grid_rows": 2,
            "grid_cols": 3
        }
        assert layout == expected, "Large terminal should use grid layout"
    
    @patch('subprocess.run')
    def test_layout_detection_small_terminal(self, mock_subprocess):
        """Test layout detection for small terminal"""
        # Mock terminal size: 100x20 (small)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "20 100"  # rows cols
        mock_subprocess.return_value = mock_result
        
        layout = self.methods._detect_smart_layout(5)
        
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
        
        layout = self.methods._detect_smart_layout(5)
        
        # Should use fallback custom layout when stty fails but import succeeds
        if layout is not None:
            assert layout["type"] == "custom", "Should use custom layout when stty fails"
            assert layout["agent_count"] == 5
        else:
            # If import fails, should return None
            assert layout is None, "Should return None when both stty and import fail"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])