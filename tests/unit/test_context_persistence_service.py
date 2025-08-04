"""
Unit tests for Context Persistence Service
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.services.context_persistence_service import ContextPersistenceService
from src.team_context_manager import TeamContextAgentInfo


class TestContextPersistenceService:
    """Test the context persistence service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_manager = Mock()
        self.service = ContextPersistenceService(self.mock_manager)
        
        # Sample agents
        self.agents = [
            TeamContextAgentInfo("Lead", "ccbox-lead", "opus", 0),
            TeamContextAgentInfo("Dev", "ccbox-dev", "sonnet", 1),
        ]
    
    def test_create_context_success(self):
        """Test successful context creation"""
        self.mock_manager.create_context.return_value = None
        self.mock_manager.get_context.return_value = {"test": "data"}
        self.mock_manager._save_registry.return_value = None
        
        result = self.service.create_context(
            "test-context",
            self.agents,
            tmux_session="test-session",
            metadata={"custom": "value"}
        )
        
        assert result is True
        self.mock_manager.create_context.assert_called_once_with(
            context_name="test-context",
            agents=self.agents,
            tmux_session="test-session"
        )
    
    def test_create_context_failure(self):
        """Test context creation failure"""
        self.mock_manager.create_context.side_effect = Exception("Creation failed")
        
        with pytest.raises(Exception, match="Creation failed"):
            self.service.create_context("test-context", self.agents)
    
    def test_get_context_exists(self):
        """Test getting existing context"""
        self.mock_manager.get_context.return_value = {
            "agents": [
                {"name": "Lead", "container": "ccbox-lead", "model": "opus", "pane_index": 0}
            ],
            "tmux_session": "test-session",
            "created_at": "2024-01-01T00:00:00",
            "custom_field": "value"
        }
        
        context = self.service.get_context("test-context")
        
        assert context is not None
        assert context.name == "test-context"
        assert len(context.agents) == 1
        assert context.agents[0].name == "Lead"
        assert context.tmux_session == "test-session"
        assert context.metadata["custom_field"] == "value"
    
    def test_get_context_not_found(self):
        """Test getting non-existent context"""
        self.mock_manager.get_context.return_value = None
        
        context = self.service.get_context("nonexistent")
        assert context is None
    
    def test_list_contexts(self):
        """Test listing all contexts"""
        self.mock_manager.list_contexts.return_value = {
            "context1": {},
            "context2": {}
        }
        
        # Mock get_context to return details
        def mock_get_context(name):
            if name == "context1":
                return {
                    "agents": [],
                    "tmux_session": "session1"
                }
            elif name == "context2":
                return {
                    "agents": [],
                    "tmux_session": "session2"
                }
            return None
        
        self.mock_manager.get_context.side_effect = mock_get_context
        
        contexts = self.service.list_contexts()
        
        assert len(contexts) == 2
        assert "context1" in contexts
        assert "context2" in contexts
        assert contexts["context1"].tmux_session == "session1"
    
    def test_delete_context_success(self):
        """Test successful context deletion"""
        self.mock_manager.delete_context.return_value = None
        
        result = self.service.delete_context("test-context")
        
        assert result is True
        self.mock_manager.delete_context.assert_called_once_with("test-context")
    
    def test_delete_context_failure(self):
        """Test context deletion failure"""
        self.mock_manager.delete_context.side_effect = Exception("Delete failed")
        
        result = self.service.delete_context("test-context")
        
        assert result is False
    
    def test_export_context(self):
        """Test exporting context"""
        # Set up mock context
        self.mock_manager.get_context.return_value = {
            "agents": [
                {"name": "Lead", "container": "ccbox-lead", "model": "opus", "pane_index": 0}
            ],
            "tmux_session": "test-session",
            "created_at": "2024-01-01T00:00:00"
        }
        
        export_data = self.service.export_context("test-context")
        
        assert export_data is not None
        assert export_data["context_name"] == "test-context"
        assert "export_date" in export_data
        assert len(export_data["agents"]) == 1
        assert export_data["tmux_session"] == "test-session"
    
    def test_export_context_not_found(self):
        """Test exporting non-existent context"""
        self.mock_manager.get_context.return_value = None
        
        export_data = self.service.export_context("nonexistent")
        assert export_data is None
    
    def test_import_context_success(self):
        """Test importing context"""
        import_data = {
            "context_name": "imported-context",
            "agents": [
                {"name": "Lead", "container": "ccbox-lead", "model": "opus", "pane_index": 0}
            ],
            "tmux_session": "imported-session",
            "metadata": {"source": "backup"}
        }
        
        self.mock_manager.get_context.return_value = None  # Not exists
        self.mock_manager.create_context.return_value = None
        
        result = self.service.import_context(import_data)
        
        assert result is True
        # Verify create was called with correct agents
        call_args = self.mock_manager.create_context.call_args
        assert call_args[1]["context_name"] == "imported-context"
        assert len(call_args[1]["agents"]) == 1
    
    def test_import_context_already_exists(self):
        """Test importing context that already exists"""
        import_data = {"context_name": "existing-context"}
        
        self.mock_manager.get_context.return_value = {"exists": True}
        
        result = self.service.import_context(import_data, skip_existing=True)
        
        assert result is False
        self.mock_manager.create_context.assert_not_called()
    
    def test_save_to_file(self):
        """Test saving context to file"""
        self.mock_manager.get_context.return_value = {
            "agents": [],
            "tmux_session": "test-session"
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test-context.json"
            
            result = self.service.save_to_file("test-context", file_path)
            
            assert result is True
            assert Path(file_path).exists()
            
            # Verify content
            with open(file_path) as f:
                data = json.load(f)
                assert data["context_name"] == "test-context"
    
    def test_load_from_file(self):
        """Test loading context from file"""
        test_data = {
            "context_name": "loaded-context",
            "agents": [],
            "tmux_session": "loaded-session"
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test-context.json"
            
            # Write test file
            with open(file_path, 'w') as f:
                json.dump(test_data, f)
            
            self.mock_manager.get_context.return_value = None
            self.mock_manager.create_context.return_value = None
            
            result = self.service.load_from_file(file_path)
            
            assert result is True
            self.mock_manager.create_context.assert_called_once()
    
    def test_update_context_metadata_merge(self):
        """Test updating context metadata with merge"""
        self.mock_manager.get_context.return_value = {
            "agents": [],
            "existing": "value",
            "to_update": "old"
        }
        
        result = self.service.update_context_metadata(
            "test-context",
            {"to_update": "new", "additional": "data"},
            merge=True
        )
        
        assert result is True
        # Check that save was called
        self.mock_manager._save_registry.assert_called_once()
        
        # Verify data was updated correctly
        context_data = self.mock_manager.get_context.return_value
        assert context_data["existing"] == "value"
        assert context_data["to_update"] == "new"
        assert context_data["additional"] == "data"
    
    def test_update_context_metadata_replace(self):
        """Test updating context metadata with replace"""
        self.mock_manager.get_context.return_value = {
            "agents": [],
            "tmux_session": "session",
            "created_at": "2024-01-01",
            "old_metadata": "remove_me"
        }
        
        result = self.service.update_context_metadata(
            "test-context",
            {"new_metadata": "keep_me"},
            merge=False
        )
        
        assert result is True
        
        # Verify old metadata was removed and new added
        context_data = self.mock_manager.get_context.return_value
        assert "old_metadata" not in context_data
        assert context_data["new_metadata"] == "keep_me"
        # Core fields should remain
        assert "agents" in context_data
        assert "tmux_session" in context_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])