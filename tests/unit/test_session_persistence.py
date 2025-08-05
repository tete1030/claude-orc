#!/usr/bin/env python3
"""
Unit tests for session persistence functionality.

Tests the TeamContextManager and related components for their ability
to persist and restore agent session IDs.
"""

import unittest
import tempfile
import os
import json
import shutil
from typing import List
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import actual TeamContextManager implementation
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.team_context_manager import TeamContextManager, TeamContextAgentInfo, TeamContext


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
    
    def test_agent_info_with_session_id(self):
        """Test TeamContextAgentInfo with session_id field"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer",
            model="sonnet",
            pane_index=0,
            session_id="test-session-uuid-123"
        )
        
        self.assertEqual(agent.name, "TestAgent")
        self.assertEqual(agent.role, "Developer")
        self.assertEqual(agent.model, "sonnet")
        self.assertEqual(agent.pane_index, 0)
        self.assertEqual(agent.session_id, "test-session-uuid-123")
    
    def test_agent_info_without_session_id(self):
        """Test TeamContextAgentInfo defaults session_id to None"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer"
        )
        
        self.assertEqual(agent.name, "TestAgent")
        self.assertEqual(agent.role, "Developer")
        self.assertEqual(agent.model, "sonnet")  # Default
        self.assertIsNone(agent.pane_index)
        self.assertIsNone(agent.session_id)
    
    def test_basic_session_creation_with_session_ids(self):
        """Test basic context creation with session IDs"""
        # Create TeamContextAgentInfo objects with session IDs
        agents = [
            TeamContextAgentInfo(
                name=agent, 
                role=f"{agent} role",
                session_id=f"session-{agent}-uuid"
            )
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
        
        # Verify agents have expected session IDs
        for i, expected_agent_name in enumerate(self.test_agents):
            agent = context.agents[i]
            expected_session_id = f"session-{expected_agent_name}-uuid"
            self.assertEqual(agent.session_id, expected_session_id)
    
    def test_session_resume_preserves_session_ids(self):
        """Test resuming an existing session preserves session IDs"""
        # Create initial session with session IDs
        agents = [
            TeamContextAgentInfo(
                name=agent, 
                role=f"{agent} role",
                session_id=f"original-{agent}-session"
            )
            for agent in self.test_agents
        ]
        self.team_context_manager.create_context(
            self.test_context_name, 
            agents, 
            f"{self.test_context_name}-tmux"
        )
        
        # Create new manager instance (simulates restart)
        new_manager = TeamContextManager(self.registry_path)
        
        # Resume session
        resumed_context = new_manager.resume_context(self.test_context_name)
        
        self.assertEqual(resumed_context.context_name, self.test_context_name)
        self.assertEqual(len(resumed_context.agents), len(self.test_agents))
        
        # Verify session IDs are preserved
        for i, agent in enumerate(resumed_context.agents):
            expected_session_id = f"original-{self.test_agents[i]}-session"
            self.assertEqual(agent.session_id, expected_session_id)
    
    def test_update_session_ids(self):
        """Test updating agent session IDs after context creation"""
        # Create context with no session IDs
        agents = [
            TeamContextAgentInfo(name=agent, role=f"{agent} role")
            for agent in self.test_agents
        ]
        context = self.team_context_manager.create_context(
            self.test_context_name,
            agents,
            f"{self.test_context_name}-tmux"
        )
        
        # Verify initial state - no session IDs
        for agent in context.agents:
            self.assertIsNone(agent.session_id)
        
        # Update agents with session IDs
        updated_agents = []
        for agent in context.agents:
            agent.session_id = f"updated-{agent.name}-session"
            updated_agents.append(agent)
        
        # Update context
        updated_context = self.team_context_manager.update_context(
            self.test_context_name,
            agents=updated_agents
        )
        
        # Verify session IDs were updated
        for agent in updated_context.agents:
            expected_session_id = f"updated-{agent.name}-session"
            self.assertEqual(agent.session_id, expected_session_id)
        
        # Verify persistence - reload and check
        reloaded_manager = TeamContextManager(self.registry_path)
        reloaded_context = reloaded_manager.get_context(self.test_context_name)
        
        for agent in reloaded_context.agents:
            expected_session_id = f"updated-{agent.name}-session"
            self.assertEqual(agent.session_id, expected_session_id)
    
    def test_resume_nonexistent_session(self):
        """Test resuming a context that doesn't exist"""
        with self.assertRaises(ValueError) as context:
            self.team_context_manager.resume_context("nonexistent-session")
        
        self.assertIn("not found", str(context.exception))
    
    def test_list_contexts_with_session_ids(self):
        """Test listing all contexts shows session ID info"""
        # Initially empty
        contexts = self.team_context_manager.list_contexts()
        self.assertEqual(len(contexts), 0)
        
        # Create multiple contexts with session IDs
        agents1 = [TeamContextAgentInfo(
            name="agent1", 
            role="role1",
            session_id="session-1-uuid"
        )]
        agents2 = [
            TeamContextAgentInfo(
                name="agent2", 
                role="role2",
                session_id="session-2a-uuid"
            ),
            TeamContextAgentInfo(
                name="agent3", 
                role="role3",
                session_id="session-2b-uuid"
            )
        ]
        
        self.team_context_manager.create_context("session-1", agents1, "session-1-tmux")
        self.team_context_manager.create_context("session-2", agents2, "session-2-tmux")
        
        contexts = self.team_context_manager.list_contexts()
        self.assertEqual(len(contexts), 2)
        self.assertIn("session-1", contexts)
        self.assertIn("session-2", contexts)
        
        # Verify session IDs are in the listed data
        session1_data = contexts["session-1"]
        self.assertEqual(session1_data["agents"][0]["session_id"], "session-1-uuid")
        
        session2_data = contexts["session-2"]
        self.assertEqual(session2_data["agents"][0]["session_id"], "session-2a-uuid")
        self.assertEqual(session2_data["agents"][1]["session_id"], "session-2b-uuid")
    
    def test_session_cleanup(self):
        """Test cleaning up context resources"""
        # Create session with session IDs
        agents = [
            TeamContextAgentInfo(
                name=agent, 
                role=f"{agent} role",
                session_id=f"cleanup-{agent}-session"
            )
            for agent in self.test_agents
        ]
        self.team_context_manager.create_context(
            self.test_context_name, 
            agents, 
            f"{self.test_context_name}-tmux"
        )
        
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
    
    def test_registry_persistence_with_session_ids(self):
        """Test that registry persists session IDs across manager instances"""
        # Create context with first manager
        agents = [
            TeamContextAgentInfo(
                name=agent, 
                role=f"{agent} role",
                session_id=f"persist-{agent}-session"
            )
            for agent in self.test_agents
        ]
        self.team_context_manager.create_context(
            self.test_context_name, 
            agents, 
            f"{self.test_context_name}-tmux"
        )
        
        # Create new manager instance
        manager2 = TeamContextManager(self.registry_path)
        
        # Verify context is available with session IDs
        contexts = manager2.list_contexts()
        self.assertIn(self.test_context_name, contexts)
        
        # Get the actual context object
        context = manager2.get_context(self.test_context_name)
        self.assertIsNotNone(context)
        
        # Verify session IDs persisted
        for i, agent in enumerate(context.agents):
            expected_session_id = f"persist-{self.test_agents[i]}-session"
            self.assertEqual(agent.session_id, expected_session_id)
    
    def test_mixed_session_ids(self):
        """Test context with some agents having session IDs and some not"""
        # Create agents with mixed session ID states
        agents = [
            TeamContextAgentInfo(
                name="agent1",
                role="role1",
                session_id="has-session-id"
            ),
            TeamContextAgentInfo(
                name="agent2",
                role="role2",
                session_id=None  # Explicitly None
            ),
            TeamContextAgentInfo(
                name="agent3",
                role="role3"
                # session_id not provided, should default to None
            )
        ]
        
        context = self.team_context_manager.create_context(
            "mixed-session-test",
            agents,
            "mixed-tmux"
        )
        
        # Verify mixed state
        self.assertEqual(context.agents[0].session_id, "has-session-id")
        self.assertIsNone(context.agents[1].session_id)
        self.assertIsNone(context.agents[2].session_id)
        
        # Verify persistence of mixed state
        reloaded = TeamContextManager(self.registry_path).get_context("mixed-session-test")
        self.assertEqual(reloaded.agents[0].session_id, "has-session-id")
        self.assertIsNone(reloaded.agents[1].session_id)
        self.assertIsNone(reloaded.agents[2].session_id)
    
    def test_backward_compatibility(self):
        """Test loading contexts created before session_id was added"""
        # Manually create an old-style registry without session_id
        old_registry = {
            "old-context": {
                "context_name": "old-context",
                "tmux_session": "old-tmux",
                "created_at": datetime.now().isoformat(),
                "agents": [
                    {
                        "name": "OldAgent",
                        "role": "OldRole",
                        "model": "sonnet",
                        "pane_index": 0
                        # Note: no session_id field
                    }
                ],
                "updated_at": None,
                "orchestrator_config": {}
            }
        }
        
        # Write old-style registry
        with open(self.registry_path, 'w') as f:
            json.dump(old_registry, f)
        
        # Load with new manager
        manager = TeamContextManager(self.registry_path)
        
        # Should load successfully
        context = manager.get_context("old-context")
        self.assertIsNotNone(context)
        self.assertEqual(context.context_name, "old-context")
        self.assertEqual(len(context.agents), 1)
        
        # session_id should default to None
        self.assertIsNone(context.agents[0].session_id)
    
    def test_corrupted_registry_handling(self):
        """Test handling of corrupted registry file"""
        # Create corrupted registry file
        with open(self.registry_path, 'w') as f:
            f.write("invalid json content {{{")
        
        # Should handle gracefully - start with empty registry
        manager = TeamContextManager(self.registry_path)
        contexts = manager.list_contexts()
        self.assertEqual(len(contexts), 0)


class TestSessionIDIntegration(unittest.TestCase):
    """Integration tests for session ID functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_integration_")
        self.registry_path = os.path.join(self.temp_dir, "integration_registry.json")
        self.team_context_manager = TeamContextManager(self.registry_path)
        
    def tearDown(self):
        """Clean up integration test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_session_lifecycle(self):
        """Test complete session lifecycle with session IDs"""
        context_name = "lifecycle-test"
        
        # Phase 1: Create context without session IDs
        agents = [
            TeamContextAgentInfo(name="Lead", role="Team Lead"),
            TeamContextAgentInfo(name="Dev", role="Developer")
        ]
        
        context = self.team_context_manager.create_context(
            context_name,
            agents,
            f"{context_name}-tmux"
        )
        
        # Verify no session IDs initially
        for agent in context.agents:
            self.assertIsNone(agent.session_id)
        
        # Phase 2: Simulate launch - assign session IDs
        session_ids = {
            "Lead": "lead-session-uuid-123",
            "Dev": "dev-session-uuid-456"
        }
        
        updated_agents = []
        for agent in context.agents:
            agent.session_id = session_ids[agent.name]
            updated_agents.append(agent)
        
        self.team_context_manager.update_context(
            context_name,
            agents=updated_agents
        )
        
        # Phase 3: Simulate restart - verify session IDs persist
        new_manager = TeamContextManager(self.registry_path)
        resumed = new_manager.resume_context(context_name)
        
        # Verify session IDs are intact
        for agent in resumed.agents:
            expected_id = session_ids[agent.name]
            self.assertEqual(agent.session_id, expected_id)
        
        # Phase 4: Clean up
        result = new_manager.cleanup_context(context_name)
        self.assertTrue(result)
    
    def test_multiple_contexts_isolation(self):
        """Test that multiple contexts maintain separate session IDs"""
        # Create two contexts with agents of same names
        for i in range(1, 3):
            context_name = f"context-{i}"
            agents = [
                TeamContextAgentInfo(
                    name="Leader",
                    role="Team Lead",
                    session_id=f"context{i}-leader-session"
                ),
                TeamContextAgentInfo(
                    name="Developer",
                    role="Developer",
                    session_id=f"context{i}-dev-session"
                )
            ]
            
            self.team_context_manager.create_context(
                context_name,
                agents,
                f"{context_name}-tmux"
            )
        
        # Verify isolation
        context1 = self.team_context_manager.get_context("context-1")
        context2 = self.team_context_manager.get_context("context-2")
        
        # Same agent names but different session IDs
        self.assertEqual(context1.agents[0].name, context2.agents[0].name)
        self.assertNotEqual(context1.agents[0].session_id, context2.agents[0].session_id)
        
        self.assertEqual(context1.agents[0].session_id, "context1-leader-session")
        self.assertEqual(context2.agents[0].session_id, "context2-leader-session")


if __name__ == '__main__':
    # Print helper information
    print("Session Persistence Unit Tests")
    print("==============================")
    print()
    print("This test suite validates session persistence functionality")
    print("focusing on session IDs rather than container names.")
    print()
    
    # Run tests
    unittest.main(verbosity=2)