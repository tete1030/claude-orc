#!/usr/bin/env python3
"""
Additional session persistence tests covering edge cases and error scenarios.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from src.team_context_manager import TeamContextManager, TeamContextAgentInfo
from src.services.context_persistence_service import ContextPersistenceService


class TestSessionPersistenceEdgeCases:
    """Test edge cases for session persistence"""
    
    def test_empty_session_id_handling(self):
        """Test handling of empty session IDs"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer",
            model="sonnet",
            pane_index=0,
            session_id=""  # Empty string
        )
        
        # Empty string is valid, just means no session to resume
        assert agent.session_id == ""
    
    def test_none_session_id_handling(self):
        """Test handling of None session IDs"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer",
            model="sonnet",
            pane_index=0,
            session_id=None
        )
        
        assert agent.session_id is None
    
    def test_very_long_session_id(self):
        """Test handling of very long session IDs"""
        long_id = "a" * 500  # 500 character session ID
        
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer",
            model="sonnet",
            pane_index=0,
            session_id=long_id
        )
        
        # Should accept long IDs
        assert agent.session_id == long_id
        assert len(agent.session_id) == 500
    
    def test_session_id_with_special_characters(self):
        """Test session IDs with various special characters"""
        special_ids = [
            "session-with-dash-123",
            "session_with_underscore_456",
            "session.with.dots.789",
            "session:with:colons:000",
            "session/with/slashes/111",
        ]
        
        for special_id in special_ids:
            agent = TeamContextAgentInfo(
                name="TestAgent",
                role="Developer",
                model="sonnet",
                pane_index=0,
                session_id=special_id
            )
            assert agent.session_id == special_id


class TestContextPersistenceErrorHandling:
    """Test error handling in context persistence"""
    
    def test_corrupted_registry_recovery(self):
        """Test recovery from corrupted registry file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "team_contexts.json"
            
            # Write corrupted JSON
            with open(registry_path, 'w') as f:
                f.write("{invalid json content")
            
            # Manager should handle gracefully and start fresh
            manager = TeamContextManager(registry_path=str(registry_path))
            
            # Should have no contexts due to corruption
            contexts = manager.list_contexts()
            assert contexts == {}
            
            # Should be able to create new context
            context = manager.create_context(
                "recovery-test",
                agents=[],
                tmux_session="recovery"
            )
            assert context is not None
            assert context.context_name == "recovery-test"
    
    def test_partial_json_recovery(self):
        """Test recovery from partially written JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "team_contexts.json"
            
            # Write truncated but parseable JSON
            partial_data = '{"contexts": {}}'
            
            with open(registry_path, 'w') as f:
                f.write(partial_data)
            
            # Manager should load empty contexts
            manager = TeamContextManager(registry_path=str(registry_path))
            contexts = manager.list_contexts()
            assert contexts == {}
    
    def test_context_update_with_invalid_field(self):
        """Test updating context with invalid fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_contexts.json"
            manager = TeamContextManager(registry_path=str(registry_path))
        
            # Create context
            context = manager.create_context(
                "test-context",
                agents=[],
                tmux_session="test"
            )
            
            # Try to update with invalid field - should be ignored
            result = manager.update_context(
                "test-context",
                invalid_field="should_be_ignored",
                orchestrator_config={"valid": "data"}
            )
            
            # Valid field should be updated
            assert result is not None
            assert result.orchestrator_config == {"valid": "data"}
        
        # Invalid field should not exist
        assert not hasattr(result, 'invalid_field')
    
    def test_missing_context_operations(self):
        """Test operations on non-existent contexts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_contexts.json"
            manager = TeamContextManager(registry_path=str(registry_path))
        
            # Get non-existent context
            context = manager.get_context("does-not-exist")
            assert context is None
            
            # Update non-existent context
            result = manager.update_context("does-not-exist", orchestrator_config={"test": "data"})
            assert result is None
            
            # Delete non-existent context
            result = manager.delete_context("does-not-exist")
            assert result is False
            
            # Resume non-existent context should raise ValueError
            with pytest.raises(ValueError, match="not found"):
                manager.resume_context("does-not-exist")


class TestSessionPersistenceIntegration:
    """Integration tests for session persistence"""
    
    def test_full_lifecycle_with_session_persistence(self):
        """Test complete lifecycle: create, update, resume, delete"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "team_contexts.json"
            manager = TeamContextManager(registry_path=str(registry_path))
            
            # Step 1: Create context with agents having session IDs
            agents = [
                TeamContextAgentInfo("Lead", "Team Lead", "opus", 0, "lead-session-123"),
                TeamContextAgentInfo("Dev", "Developer", "sonnet", 1, None),  # No session initially
            ]
            
            context = manager.create_context(
                "lifecycle-test",
                agents=agents,
                tmux_session="lifecycle"
            )
            
            assert len(context.agents) == 2
            assert context.agents[0].session_id == "lead-session-123"
            assert context.agents[1].session_id is None
            
            # Step 2: Update to add session ID for Dev
            # This would happen after agent launches
            context.agents[1].session_id = "dev-session-456"
            
            # Step 3: Resume context
            resumed = manager.resume_context("lifecycle-test")
            assert resumed is not None
            assert resumed.agents[0].session_id == "lead-session-123"
            assert resumed.agents[1].session_id == "dev-session-456"
            
            # Step 4: Delete context
            result = manager.delete_context("lifecycle-test")
            assert result is True
            
            # Verify it's gone
            assert manager.get_context("lifecycle-test") is None
    
    def test_persistence_across_manager_instances(self):
        """Test that contexts persist across manager restarts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "team_contexts.json"
            
            # First manager instance
            manager1 = TeamContextManager(registry_path=str(registry_path))
            
            agents = [
                TeamContextAgentInfo("Agent1", "Role1", "sonnet", 0, "session-111"),
                TeamContextAgentInfo("Agent2", "Role2", "sonnet", 1, "session-222"),
            ]
            
            context1 = manager1.create_context(
                "persistent-test",
                agents=agents,
                tmux_session="persist"
            )
            
            # Simulate manager shutdown
            del manager1
            
            # New manager instance
            manager2 = TeamContextManager(registry_path=str(registry_path))
            
            # Context should be loaded
            context2 = manager2.get_context("persistent-test")
            assert context2 is not None
            assert len(context2.agents) == 2
            assert context2.agents[0].session_id == "session-111"
            assert context2.agents[1].session_id == "session-222"
    
    def test_context_metadata_persistence(self):
        """Test that metadata persists correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "team_contexts.json"
            manager = TeamContextManager(registry_path=str(registry_path))
            
            # Create context with metadata
            context = manager.create_context(
                "metadata-test",
                agents=[],
                tmux_session="meta"
            )
            
            # Update with orchestrator_config
            manager.update_context(
                "metadata-test",
                orchestrator_config={
                    "task": "testing",
                    "priority": "high",
                    "custom_data": {"nested": "value"}
                }
            )
            
            # Reload and verify
            new_manager = TeamContextManager(registry_path=str(registry_path))
            loaded = new_manager.get_context("metadata-test")
            
            assert loaded.orchestrator_config["task"] == "testing"
            assert loaded.orchestrator_config["priority"] == "high"
            assert loaded.orchestrator_config["custom_data"]["nested"] == "value"
    
    def test_export_import_with_session_ids(self):
        """Test export/import functionality preserves session IDs"""
        service = ContextPersistenceService()
        
        # Mock the manager
        mock_manager = Mock()
        service.context_manager = mock_manager
        
        # Mock get_context for export - use proper TeamContext object
        from tests.unit.mock_helpers import create_mock_team_context
        mock_manager.get_context.return_value = create_mock_team_context(
            context_name="export-test",
            agents=[
                {"name": "A1", "role": "R1", "model": "sonnet", "pane_index": 0, "session_id": "export-session-1"},
                {"name": "A2", "role": "R2", "model": "sonnet", "pane_index": 1, "session_id": "export-session-2"},
            ],
            tmux_session="export",
            created_at="2024-01-01T00:00:00",
            exported=True  # This will go in orchestrator_config
        )
        
        # Export
        export_data = service.export_context("export-test")
        assert export_data is not None
        assert len(export_data["agents"]) == 2
        assert export_data["agents"][0]["session_id"] == "export-session-1"
        assert export_data["agents"][1]["session_id"] == "export-session-2"
        
        # Import
        mock_manager.get_context.return_value = None  # Not exists
        mock_manager.create_context.return_value = None
        
        result = service.import_context(export_data)
        assert result is True
        
        # Verify create was called with agents including session IDs
        create_call = mock_manager.create_context.call_args
        created_agents = create_call[1]["agents"]
        assert len(created_agents) == 2
        assert created_agents[0].session_id == "export-session-1"
        assert created_agents[1].session_id == "export-session-2"


class TestSessionPersistenceBoundaryConditions:
    """Test boundary conditions and limits"""
    
    def test_maximum_agents_per_context(self):
        """Test handling of many agents in a context"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_contexts.json"
            manager = TeamContextManager(registry_path=str(registry_path))
        
            # Create context with 50 agents
            agents = []
            for i in range(50):
                agent = TeamContextAgentInfo(
                    name=f"Agent{i}",
                    role=f"Role{i}",
                    model="sonnet",
                    pane_index=i,
                    session_id=f"session-{i:03d}" if i % 2 == 0 else None  # Half have sessions
                )
                agents.append(agent)
            
            context = manager.create_context(
                "large-context",
                agents=agents,
                tmux_session="large"
            )
            
            assert len(context.agents) == 50
            
            # Count agents with sessions
            with_sessions = sum(1 for a in context.agents if a.session_id is not None)
            assert with_sessions == 25
    
    def test_concurrent_context_updates(self):
        """Test concurrent updates don't corrupt data"""
        import threading
        
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_contexts.json"
            manager = TeamContextManager(registry_path=str(registry_path))
        
            # Create initial context
            context = manager.create_context(
                "concurrent-test",
                agents=[],
                tmux_session="concurrent"
            )
        
            # Function to update orchestrator_config
            def update_metadata(key, value):
                for _ in range(10):
                    manager.update_context(
                        "concurrent-test",
                        orchestrator_config={key: value}
                    )
            
            # Launch concurrent updates
            threads = []
            for i in range(5):
                t = threading.Thread(
                    target=update_metadata,
                    args=(f"key_{i}", f"value_{i}")
                )
                threads.append(t)
                t.start()
            
            # Wait for completion
            for t in threads:
                t.join()
            
            # Context should still be valid
            final = manager.get_context("concurrent-test")
            assert final is not None
            # Check at least one update succeeded (concurrent updates may overwrite each other)
            # This is expected behavior - last write wins
            assert len(final.orchestrator_config) > 0
    
    def test_registry_size_limits(self):
        """Test behavior with large registry files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "team_contexts.json"
            manager = TeamContextManager(registry_path=str(registry_path))
            
            # Create many contexts
            for i in range(20):
                agents = [
                    TeamContextAgentInfo(f"A{i}", "Role", "sonnet", 0, f"session-{i}")
                ]
                manager.create_context(
                    f"context-{i}",
                    agents=agents,
                    tmux_session=f"session-{i}"
                )
            
            # Check registry file size
            registry_size = registry_path.stat().st_size
            
            # Should be reasonable (less than 100KB for 20 contexts)
            assert registry_size < 100 * 1024
            
            # Should still be fast to load
            import time
            start = time.time()
            new_manager = TeamContextManager(registry_path=str(registry_path))
            load_time = time.time() - start
            
            # Should load in under 100ms
            assert load_time < 0.1
            
            # All contexts should be loaded
            contexts = new_manager.list_contexts()
            assert len(contexts) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])