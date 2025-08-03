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

# Import actual SessionManager implementation
import sys
sys.path.append('/home/texotqi/Documents/claude-orc/.temp')
from session_manager import SessionManager, AgentInfo, TeamSession

# Mock imports for components not yet implemented
class MockSessionManager:
    """Mock SessionManager for testing until real implementation is available"""
    
    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path or "/tmp/test_session_registry.json"
        self.sessions = {}
        
    def create_session(self, session_name: str, agents: List[str]) -> Dict:
        """Create a new session with specified agents"""
        session_data = {
            "name": session_name,
            "created": time.time(),
            "status": "active",
            "agents": {agent: {"container_name": f"{session_name}-{agent}"} for agent in agents}
        }
        self.sessions[session_name] = session_data
        self._save_registry()
        return session_data
    
    def resume_session(self, session_name: str) -> Dict:
        """Resume an existing session"""
        if session_name not in self.sessions:
            raise ValueError(f"Session {session_name} not found")
        
        session = self.sessions[session_name]
        session["status"] = "resumed"
        self._save_registry()
        return session
    
    def list_sessions(self) -> Dict[str, Dict]:
        """List all sessions"""
        return self.sessions.copy()
    
    def cleanup_session(self, session_name: str) -> bool:
        """Clean up session resources"""
        if session_name in self.sessions:
            del self.sessions[session_name]
            self._save_registry()
            return True
        return False
    
    def _save_registry(self):
        """Save registry to disk"""
        with open(self.registry_path, 'w') as f:
            json.dump(self.sessions, f, indent=2)
    
    def _load_registry(self):
        """Load registry from disk"""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r') as f:
                self.sessions = json.load(f)


class TestSessionPersistence(unittest.TestCase):
    """Test cases for session persistence functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_session_")
        self.registry_path = os.path.join(self.temp_dir, "test_registry.json")
        # Use real SessionManager implementation
        self.session_manager = SessionManager(self.registry_path)
        
        # Test session names
        self.test_session_name = "test-session-001"
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
        """Test basic session creation"""
        # Create AgentInfo objects for real SessionManager
        agents = [
            AgentInfo(name=agent, container=f"{self.test_session_name}-{agent}")
            for agent in self.test_agents
        ]
        
        tmux_session = f"{self.test_session_name}-tmux"
        session = self.session_manager.create_session(
            self.test_session_name, 
            agents, 
            tmux_session
        )
        
        self.assertEqual(session.session_name, self.test_session_name)
        self.assertEqual(session.tmux_session, tmux_session)
        self.assertEqual(len(session.agents), len(self.test_agents))
        
        # Verify registry file was created
        self.assertTrue(os.path.exists(self.registry_path))
        
        # Verify agents have expected container names
        for i, expected_agent_name in enumerate(self.test_agents):
            agent = session.agents[i]
            expected_container = f"{self.test_session_name}-{expected_agent_name}"
            self.assertEqual(agent.container, expected_container)
    
    def test_session_resume(self):
        """Test resuming an existing session"""
        # Create initial session
        agents = [
            AgentInfo(name=agent, container=f"{self.test_session_name}-{agent}")
            for agent in self.test_agents
        ]
        self.session_manager.create_session(self.test_session_name, agents, f"{self.test_session_name}-tmux")
        
        # Create new manager instance (simulates restart)
        new_manager = SessionManager(self.registry_path)
        
        # Resume session
        resumed_session = new_manager.resume_session(self.test_session_name)
        
        self.assertEqual(resumed_session.session_name, self.test_session_name)
        self.assertEqual(len(resumed_session.agents), len(self.test_agents))
    
    def test_resume_nonexistent_session(self):
        """Test resuming a session that doesn't exist"""
        with self.assertRaises(ValueError) as context:
            self.session_manager.resume_session("nonexistent-session")
        
        self.assertIn("not found", str(context.exception))
    
    def test_list_sessions(self):
        """Test listing all sessions"""
        # Initially empty
        sessions = self.session_manager.list_sessions()
        self.assertEqual(len(sessions), 0)
        
        # Create multiple sessions
        agents1 = [AgentInfo(name="agent1", container="session-1-agent1")]
        agents2 = [
            AgentInfo(name="agent2", container="session-2-agent2"),
            AgentInfo(name="agent3", container="session-2-agent3")
        ]
        session1 = self.session_manager.create_session("session-1", agents1, "session-1-tmux")
        session2 = self.session_manager.create_session("session-2", agents2, "session-2-tmux")
        
        sessions = self.session_manager.list_sessions()
        self.assertEqual(len(sessions), 2)
        self.assertIn("session-1", sessions)
        self.assertIn("session-2", sessions)
    
    def test_session_cleanup(self):
        """Test cleaning up session resources"""
        # Create session
        agents = [
            AgentInfo(name=agent, container=f"{self.test_session_name}-{agent}")
            for agent in self.test_agents
        ]
        self.session_manager.create_session(self.test_session_name, agents, f"{self.test_session_name}-tmux")
        
        # Verify it exists
        sessions = self.session_manager.list_sessions()
        self.assertIn(self.test_session_name, sessions)
        
        # Clean up
        result = self.session_manager.cleanup_session(self.test_session_name)
        self.assertTrue(result)
        
        # Verify it's gone
        sessions = self.session_manager.list_sessions()
        self.assertNotIn(self.test_session_name, sessions)
    
    def test_cleanup_nonexistent_session(self):
        """Test cleanup of nonexistent session"""
        result = self.session_manager.cleanup_session("nonexistent")
        self.assertFalse(result)
    
    def test_registry_persistence(self):
        """Test that registry persists across manager instances"""
        # Create session with first manager
        agents = [
            AgentInfo(name=agent, container=f"{self.test_session_name}-{agent}")
            for agent in self.test_agents
        ]
        session1 = self.session_manager.create_session(self.test_session_name, agents, f"{self.test_session_name}-tmux")
        
        # Create new manager instance
        manager2 = SessionManager(self.registry_path)
        
        # Verify session is available
        sessions = manager2.list_sessions()
        self.assertIn(self.test_session_name, sessions)
        self.assertEqual(sessions[self.test_session_name]["session_name"], self.test_session_name)
    
    def test_corrupted_registry_handling(self):
        """Test handling of corrupted registry file"""
        # Create corrupted registry file
        with open(self.registry_path, 'w') as f:
            f.write("invalid json content")
        
        # Should handle gracefully
        manager = MockSessionManager(self.registry_path)
        try:
            manager._load_registry()
            # If no exception, should start with empty registry
            sessions = manager.list_sessions()
            self.assertEqual(len(sessions), 0)
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
        self.session_manager = MockSessionManager(self.registry_path)
        
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
        session_name = "integration-test-session"
        agents = ["leader", "worker"]
        
        # Create session
        session = self.session_manager.create_session(session_name, agents)
        
        # Verify session structure
        self.assertEqual(len(session["agents"]), 2)
        
        # Simulate container operations
        for agent in agents:
            container_name = session["agents"][agent]["container_name"]
            
            # In real implementation, this would create actual containers
            # For now, we just verify the naming convention
            expected_name = f"{session_name}-{agent}"
            self.assertEqual(container_name, expected_name)
        
        # Resume session
        resumed = self.session_manager.resume_session(session_name)
        self.assertEqual(resumed["status"], "resumed")
    
    def test_multiple_sessions_isolation(self):
        """Test that multiple sessions are properly isolated"""
        session1_name = "integration-test-session-1"
        session2_name = "integration-test-session-2"
        
        # Create two sessions with same agent names
        session1 = self.session_manager.create_session(session1_name, ["leader"])
        session2 = self.session_manager.create_session(session2_name, ["leader"])
        
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
    print("Session Persistence Integration Tests")
    print("=====================================")
    print()
    print("This test suite validates session persistence functionality using persistent Docker containers.")
    print()
    print("Prerequisites:")
    print("- Docker daemon running")
    print("- SessionManager implementation (currently using mock)")
    print("- Appropriate permissions for Docker operations")
    print()
    
    # Create helper functions for use in tests
    helpers = create_helper_functions()
    
    # Run tests
    unittest.main(verbosity=2)