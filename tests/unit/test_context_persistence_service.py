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
from tests.unit.mock_helpers import create_mock_team_context


class TestContextPersistenceService:
    """Test the context persistence service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_manager = Mock()
        self.service = ContextPersistenceService(self.mock_manager)
        
        # Sample agents
        self.agents = [
            TeamContextAgentInfo(name="Lead", role="Team Lead", model="opus", pane_index=0),
            TeamContextAgentInfo(name="Dev", role="Developer", model="sonnet", pane_index=1),
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
            tmux_session="test-session",
            working_dir=None
        )
    
    def test_create_context_failure(self):
        """Test context creation failure"""
        self.mock_manager.create_context.side_effect = Exception("Creation failed")
        
        with pytest.raises(Exception, match="Creation failed"):
            self.service.create_context("test-context", self.agents)
    
    def test_get_context_exists(self):
        """Test getting existing context"""
        # Use proper TeamContext object instead of dict
        self.mock_manager.get_context.return_value = create_mock_team_context(
            context_name="test-context",
            agents=[
                {"name": "Lead", "role": "Team Lead", "model": "opus", "pane_index": 0, "session_id": "lead-session-123"}
            ],
            tmux_session="test-session",
            created_at="2024-01-01T00:00:00",
            custom_field="value"  # Extra field goes to metadata
        )
        
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
        
        # Mock get_context to return proper TeamContext objects
        def mock_get_context(name):
            if name == "context1":
                return create_mock_team_context(
                    context_name="context1",
                    agents=[],
                    tmux_session="session1"
                )
            elif name == "context2":
                return create_mock_team_context(
                    context_name="context2",
                    agents=[],
                    tmux_session="session2"
                )
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
        # Set up mock context with proper TeamContext
        self.mock_manager.get_context.return_value = create_mock_team_context(
            context_name="test-context",
            agents=[
                {"name": "Lead", "role": "Team Lead", "model": "opus", "pane_index": 0, "session_id": "lead-session-123"}
            ],
            tmux_session="test-session",
            created_at="2024-01-01T00:00:00"
        )
        
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
                {"name": "Lead", "role": "Team Lead", "model": "opus", "pane_index": 0, "session_id": "lead-session-123"}
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
        
        # Use proper TeamContext object
        self.mock_manager.get_context.return_value = create_mock_team_context(
            context_name="existing-context",
            agents=[],
            tmux_session="existing-session"
        )
        
        result = self.service.import_context(import_data, skip_existing=True)
        
        assert result is False
        self.mock_manager.create_context.assert_not_called()
    
    def test_save_to_file(self):
        """Test saving context to file"""
        self.mock_manager.get_context.return_value = create_mock_team_context(
            context_name="test-context",
            agents=[],
            tmux_session="test-session"
        )
        
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
        # Mock the context object
        mock_context = Mock()
        mock_context.metadata = {
            "existing": "value",
            "to_update": "old"
        }
        self.mock_manager.update_context.return_value = mock_context
        
        result = self.service.update_context_metadata(
            "test-context",
            {"to_update": "new", "additional": "data"},
            merge=True
        )
        
        assert result is True
        # Check that update_context was called with the right parameters
        self.mock_manager.update_context.assert_called_once()
        call_args = self.mock_manager.update_context.call_args[1]
        assert "orchestrator_config" in call_args
        assert call_args["orchestrator_config"]["to_update"] == "new"
        assert call_args["orchestrator_config"]["additional"] == "data"
    
    def test_update_context_metadata_replace(self):
        """Test updating context metadata with replace"""
        # Mock the context object
        mock_context = Mock()
        mock_context.metadata = {
            "old_metadata": "remove_me"
        }
        self.mock_manager.update_context.return_value = mock_context
        
        result = self.service.update_context_metadata(
            "test-context",
            {"new_metadata": "keep_me"},
            merge=False
        )
        
        assert result is True
        # Check that update_context was called
        self.mock_manager.update_context.assert_called_once()
        call_args = self.mock_manager.update_context.call_args[1]
        assert "orchestrator_config" in call_args
        assert call_args["orchestrator_config"]["new_metadata"] == "keep_me"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])