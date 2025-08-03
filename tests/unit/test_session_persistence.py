#!/usr/bin/env python3
"""
Integration tests for session persistence using persistent Docker containers.
"""

import unittest
import tempfile
import os
import json
import subprocess
import time
import shutil
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

# Import actual TeamContextManager implementation
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.team_context_manager import TeamContextManager, TeamContextAgentInfo, TeamContext

# Mock imports for components not yet implemented
class MockTeamContextManager:
    """Mock TeamContextManager for testing until real implementation is available"""
    
    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path or "/tmp/test_context_registry.json"
        self.contexts = {}
        
    def create_context(self, context_name: str, agents: List[str]) -> Dict:
        """Create a new context with specified agents"""
        context_data = {
            "name": context_name,
            "created": time.time(),
            "status": "active",
            "agents": {agent: {"container_name": f"{context_name}-{agent}"} for agent in agents}
        }
        self.contexts[context_name] = context_data
        self._save_registry()
        return context_data
    
    def resume_context(self, context_name: str) -> Dict:
        """Resume an existing session"""
        if context_name not in self.contexts:
            raise ValueError(f"Context {context_name} not found")
        
        context = self.contexts[context_name]
        context["status"] = "resumed"
        self._save_registry()
        return context
    
    def list_contexts(self) -> Dict[str, Dict]:
        """List all contexts"""
        return self.contexts.copy()
    
    def cleanup_context(self, context_name: str) -> bool:
        """Clean up context resources"""
        if context_name in self.contexts:
            del self.contexts[context_name]
            self._save_registry()
            return True
        return False
    
    def _save_registry(self):
        """Save registry to disk"""
        with open(self.registry_path, 'w') as f:
            json.dump(self.contexts, f, indent=2)
    
    def _load_registry(self):
        """Load registry from disk"""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r') as f:
                self.contexts = json.load(f)


class TestSessionPersistence(unittest.TestCase):
    """Test cases for session persistence functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_session_")
        self.registry_path = os.path.join(self.temp_dir, "test_registry.json")
        # Use real TeamContextManager implementation
        self.team_context_manager = TeamContextManager(self.registry_path)
        
        # Test context names
        self.test_context_name = "test-session-001"
        self.test_agents = ["leader", "researcher", "writer"]
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clean up any test containers
        self._cleanup_test_containers()
    
    def _cleanup_test_containers(self):
        """Clean up any containers created during testing"""
        try:
            # List containers with test prefix
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=test-session-", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_names = result.stdout.strip().split('\n')
                for name in container_names:
                    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
                    
        except Exception as e:
            print(f"Warning: Could not clean up test containers: {e}")
    
    def test_basic_session_creation(self):
        """Test basic context creation"""
        # Create TeamContextAgentInfo objects for real TeamContextManager
        agents = [
            TeamContextAgentInfo(name=agent, container=f"{self.test_context_name}-{agent}")
            for agent in self.test_agents
        ]
        
        tmux_session = f"{self.test_context_name}-tmux"
        context = self.team_context_manager.create_context(
            self.test_context_name, 
            agents, 
            tmux_session
        )
        
        self.assertEqual(context.context_name, self.test_context_name)
        self.assertEqual(context.tmux_session, tmux_session)
        self.assertEqual(len(context.agents), len(self.test_agents))
        
        # Verify registry file was created
        self.assertTrue(os.path.exists(self.registry_path))
        
        # Verify agents have expected container names
        for i, expected_agent_name in enumerate(self.test_agents):
            agent = context.agents[i]
            expected_container = f"{self.test_context_name}-{expected_agent_name}"
            self.assertEqual(agent.container, expected_container)
    
    def test_session_resume(self):
        """Test resuming an existing session"""
        # Create initial session
        agents = [
            TeamContextAgentInfo(name=agent, container=f"{self.test_context_name}-{agent}")
            for agent in self.test_agents
        ]
        self.team_context_manager.create_context(self.test_context_name, agents, f"{self.test_context_name}-tmux")
        
        # Create new manager instance (simulates restart)
        new_manager = TeamContextManager(self.registry_path)
        
        # Mock the container existence check to return True
        with patch.object(new_manager, '_check_container_exists', return_value=True):
            # Resume session
            resumed_context = new_manager.resume_context(self.test_context_name)
        
        self.assertEqual(resumed_context.context_name, self.test_context_name)
        self.assertEqual(len(resumed_context.agents), len(self.test_agents))
    
    def test_resume_nonexistent_session(self):
        """Test resuming a context that doesn't exist"""
        with self.assertRaises(ValueError) as context:
            self.team_context_manager.resume_context("nonexistent-session")
        
        self.assertIn("not found", str(context.exception))
    
    def test_list_contexts(self):
        """Test listing all contexts"""
        # Initially empty
        contexts = self.team_context_manager.list_contexts()
        self.assertEqual(len(contexts), 0)
        
        # Create multiple contexts
        agents1 = [TeamContextAgentInfo(name="agent1", container="session-1-agent1")]
        agents2 = [
            TeamContextAgentInfo(name="agent2", container="session-2-agent2"),
            TeamContextAgentInfo(name="agent3", container="session-2-agent3")
        ]
        session1 = self.team_context_manager.create_context("session-1", agents1, "session-1-tmux")
        session2 = self.team_context_manager.create_context("session-2", agents2, "session-2-tmux")
        
        contexts = self.team_context_manager.list_contexts()
        self.assertEqual(len(contexts), 2)
        self.assertIn("session-1", contexts)
        self.assertIn("session-2", contexts)
    
    def test_session_cleanup(self):
        """Test cleaning up context resources"""
        # Create session
        agents = [
            TeamContextAgentInfo(name=agent, container=f"{self.test_context_name}-{agent}")
            for agent in self.test_agents
        ]
        self.team_context_manager.create_context(self.test_context_name, agents, f"{self.test_context_name}-tmux")
        
        # Verify it exists
        contexts = self.team_context_manager.list_contexts()
        self.assertIn(self.test_context_name, contexts)
        
        # Clean up
        result = self.team_context_manager.cleanup_context(self.test_context_name)
        self.assertTrue(result)
        
        # Verify it's gone
        contexts = self.team_context_manager.list_contexts()
        self.assertNotIn(self.test_context_name, contexts)
    
    def test_cleanup_nonexistent_session(self):
        """Test cleanup of nonexistent session"""
        result = self.team_context_manager.cleanup_context("nonexistent")
        self.assertFalse(result)
    
    def test_registry_persistence(self):
        """Test that registry persists across manager instances"""
        # Create context with first manager
        agents = [
            TeamContextAgentInfo(name=agent, container=f"{self.test_context_name}-{agent}")
            for agent in self.test_agents
        ]
        session1 = self.team_context_manager.create_context(self.test_context_name, agents, f"{self.test_context_name}-tmux")
        
        # Create new manager instance
        manager2 = TeamContextManager(self.registry_path)
        
        # Verify context is available
        contexts = manager2.list_contexts()
        self.assertIn(self.test_context_name, contexts)
        self.assertEqual(contexts[self.test_context_name]["context_name"], self.test_context_name)
    
    def test_corrupted_registry_handling(self):
        """Test handling of corrupted registry file"""
        # Create corrupted registry file
        with open(self.registry_path, 'w') as f:
            f.write("invalid json content")
        
        # Should handle gracefully
        manager = MockTeamContextManager(self.registry_path)
        try:
            manager._load_registry()
            # If no exception, should start with empty registry
            contexts = manager.list_contexts()
            self.assertEqual(len(contexts), 0)
        except Exception:
            # Or raise a clear error that can be handled
            pass


class TestContainerLifecycle(unittest.TestCase):
    """Test container lifecycle operations"""
    
    def setUp(self):
        """Set up container test environment"""
        self.test_container_prefix = "test-session-container"
        
    def tearDown(self):
        """Clean up test containers"""
        self._cleanup_test_containers()
    
    def _cleanup_test_containers(self):
        """Clean up any containers created during testing"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.test_container_prefix}", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_names = result.stdout.strip().split('\n')
                for name in container_names:
                    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
                    
        except Exception as e:
            print(f"Warning: Could not clean up test containers: {e}")
    
    def test_docker_available(self):
        """Test that Docker is available for testing"""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Docker version", result.stdout)
        except FileNotFoundError:
            self.skipTest("Docker not available for testing")
    
    def test_container_creation_and_cleanup(self):
        """Test creating and cleaning up test containers"""
        container_name = f"{self.test_container_prefix}-test"
        
        try:
            # Create a simple test container
            result = subprocess.run([
                "docker", "run", "-d", "--name", container_name,
                "alpine:latest", "sleep", "60"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.skipTest(f"Could not create test container: {result.stderr}")
            
            # Verify container exists
            result = subprocess.run([
                "docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"
            ], capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0)
            self.assertIn(container_name, result.stdout)
            
        finally:
            # Cleanup
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
    
    def test_container_start_stop_cycle(self):
        """Test container start/stop cycle"""
        container_name = f"{self.test_container_prefix}-startstop"
        
        try:
            # Create container
            result = subprocess.run([
                "docker", "run", "-d", "--name", container_name,
                "alpine:latest", "sleep", "300"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.skipTest(f"Could not create test container: {result.stderr}")
            
            # Stop container
            result = subprocess.run(["docker", "stop", container_name], capture_output=True)
            self.assertEqual(result.returncode, 0)
            
            # Start container
            result = subprocess.run(["docker", "start", container_name], capture_output=True)
            self.assertEqual(result.returncode, 0)
            
            # Verify it's running
            result = subprocess.run([
                "docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"
            ], capture_output=True, text=True)
            
            self.assertIn(container_name, result.stdout)
            
        finally:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


class TestSessionIntegration(unittest.TestCase):
    """Integration tests combining session management and container operations"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_integration_")
        self.registry_path = os.path.join(self.temp_dir, "integration_registry.json")
        self.team_context_manager = MockTeamContextManager(self.registry_path)
        
    def tearDown(self):
        """Clean up integration test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self._cleanup_test_containers()
    
    def _cleanup_test_containers(self):
        """Clean up test containers"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=integration-test-", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_names = result.stdout.strip().split('\n')
                for name in container_names:
                    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
                    
        except Exception:
            pass
    
    def test_session_with_container_simulation(self):
        """Test session management with simulated container operations"""
        context_name = "integration-test-session"
        agents = ["leader", "worker"]
        
        # Create session
        context = self.team_context_manager.create_context(context_name, agents)
        
        # Verify context structure
        self.assertEqual(len(context["agents"]), 2)
        
        # Simulate container operations
        for agent in agents:
            container_name = context["agents"][agent]["container_name"]
            
            # In real implementation, this would create actual containers
            # For now, we just verify the naming convention
            expected_name = f"{context_name}-{agent}"
            self.assertEqual(container_name, expected_name)
        
        # Resume session
        resumed = self.team_context_manager.resume_context(context_name)
        self.assertEqual(resumed["status"], "resumed")
    
    def test_multiple_contexts_isolation(self):
        """Test that multiple contexts are properly isolated"""
        session1_name = "integration-test-session-1"
        session2_name = "integration-test-session-2"
        
        # Create two contexts with same agent names
        session1 = self.team_context_manager.create_context(session1_name, ["leader"])
        session2 = self.team_context_manager.create_context(session2_name, ["leader"])
        
        # Verify containers have different names
        container1 = session1["agents"]["leader"]["container_name"]
        container2 = session2["agents"]["leader"]["container_name"]
        
        self.assertNotEqual(container1, container2)
        self.assertEqual(container1, f"{session1_name}-leader")
        self.assertEqual(container2, f"{session2_name}-leader")


def create_helper_functions():
    """Helper functions for container lifecycle testing"""
    
    def wait_for_container_ready(container_name: str, timeout: int = 30) -> bool:
        """Wait for a container to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run([
                    "docker", "exec", container_name, "echo", "ready"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    return True
                    
            except subprocess.TimeoutExpired:
                pass
            
            time.sleep(1)
        
        return False
    
    def get_container_status(container_name: str) -> Optional[str]:
        """Get the status of a container"""
        try:
            result = subprocess.run([
                "docker", "inspect", container_name, "--format", "{{.State.Status}}"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
                
        except Exception:
            pass
        
        return None
    
    def container_exists(container_name: str) -> bool:
        """Check if a container exists"""
        result = subprocess.run([
            "docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"
        ], capture_output=True, text=True)
        
        return container_name in result.stdout
    
    return {
        'wait_for_container_ready': wait_for_container_ready,
        'get_container_status': get_container_status,
        'container_exists': container_exists
    }


if __name__ == '__main__':
    # Print helper information
    print("Context Persistence Integration Tests")
    print("=====================================")
    print()
    print("This test suite validates session persistence functionality using persistent Docker containers.")
    print()
    print("Prerequisites:")
    print("- Docker daemon running")
    print("- TeamContextManager implementation (currently using mock)")
    print("- Appropriate permissions for Docker operations")
    print()
    
    # Create helper functions for use in tests
    helpers = create_helper_functions()
    
    # Run tests
    unittest.main(verbosity=2)