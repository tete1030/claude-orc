#!/usr/bin/env python3
"""
Unit tests for session persistence data model changes.

Tests the TeamContextAgentInfo with session_id field and
serialization/deserialization functionality.
"""

import pytest
import json
from dataclasses import asdict

from src.team_context_manager import TeamContextAgentInfo, TeamContext


class TestTeamContextAgentInfo:
    """Test TeamContextAgentInfo with session_id field"""
    
    def test_create_agent_with_session_id(self):
        """Test creating agent info with session ID"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer",
            model="sonnet",
            pane_index=0,
            session_id="test-session-123"
        )
        
        assert agent.name == "TestAgent"
        assert agent.role == "Developer"
        assert agent.model == "sonnet"
        assert agent.pane_index == 0
        assert agent.session_id == "test-session-123"
    
    def test_create_agent_without_session_id(self):
        """Test creating agent info without session ID (defaults to None)"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer"
        )
        
        assert agent.name == "TestAgent"
        assert agent.role == "Developer"
        assert agent.model == "sonnet"  # Default value
        assert agent.pane_index is None
        assert agent.session_id is None
    
    def test_agent_serialization_with_session_id(self):
        """Test serializing agent info with session ID"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="Developer",
            model="opus",
            pane_index=1,
            session_id="abc-def-123"
        )
        
        agent_dict = asdict(agent)
        
        assert agent_dict == {
            "name": "TestAgent",
            "role": "Developer",
            "model": "opus",
            "pane_index": 1,
            "session_id": "abc-def-123"
        }
        
        # Ensure it's JSON serializable
        json_str = json.dumps(agent_dict)
        assert isinstance(json_str, str)
    
    def test_agent_serialization_with_none_session_id(self):
        """Test serializing agent info with None session ID"""
        agent = TeamContextAgentInfo(
            name="TestAgent",
            role="QA",
            session_id=None
        )
        
        agent_dict = asdict(agent)
        
        assert agent_dict["session_id"] is None
        
        # Ensure None is properly serialized to JSON
        json_str = json.dumps(agent_dict)
        loaded = json.loads(json_str)
        assert loaded["session_id"] is None
    
    def test_agent_deserialization_with_session_id(self):
        """Test deserializing agent info from dict with session ID"""
        agent_data = {
            "name": "TestAgent",
            "role": "Architect",
            "model": "sonnet",
            "pane_index": 2,
            "session_id": "xyz-789"
        }
        
        agent = TeamContextAgentInfo(**agent_data)
        
        assert agent.name == "TestAgent"
        assert agent.role == "Architect"
        assert agent.model == "sonnet"
        assert agent.pane_index == 2
        assert agent.session_id == "xyz-789"
    
    def test_agent_deserialization_missing_session_id(self):
        """Test deserializing agent info when session_id is missing"""
        agent_data = {
            "name": "TestAgent",
            "role": "DevOps",
            "model": "sonnet",
            "pane_index": 3
            # session_id intentionally omitted
        }
        
        agent = TeamContextAgentInfo(**agent_data)
        
        assert agent.name == "TestAgent"
        assert agent.role == "DevOps"
        assert agent.session_id is None  # Should default to None


class TestTeamContextWithSessionIds:
    """Test TeamContext with agents having session IDs"""
    
    def test_team_context_serialization(self):
        """Test serializing team context with agents having session IDs"""
        agents = [
            TeamContextAgentInfo(
                name="Lead",
                role="Team Lead",
                session_id="lead-session-123"
            ),
            TeamContextAgentInfo(
                name="Dev",
                role="Developer",
                session_id="dev-session-456"
            ),
            TeamContextAgentInfo(
                name="QA",
                role="Quality Assurance",
                session_id=None  # Mix of None and actual IDs
            )
        ]
        
        context = TeamContext(
            context_name="test-team",
            tmux_session="test-tmux",
            created_at="2025-01-01T00:00:00",
            agents=agents
        )
        
        context_dict = asdict(context)
        
        # Verify structure
        assert context_dict["context_name"] == "test-team"
        assert context_dict["tmux_session"] == "test-tmux"
        assert len(context_dict["agents"]) == 3
        
        # Verify agent session IDs
        assert context_dict["agents"][0]["session_id"] == "lead-session-123"
        assert context_dict["agents"][1]["session_id"] == "dev-session-456"
        assert context_dict["agents"][2]["session_id"] is None
        
        # Ensure full JSON serialization works
        json_str = json.dumps(context_dict)
        loaded = json.loads(json_str)
        
        assert loaded["agents"][0]["session_id"] == "lead-session-123"
        assert loaded["agents"][1]["session_id"] == "dev-session-456"
        assert loaded["agents"][2]["session_id"] is None
    
    def test_team_context_deserialization(self):
        """Test deserializing team context from JSON with session IDs"""
        json_data = {
            "context_name": "test-team",
            "tmux_session": "test-tmux",
            "created_at": "2025-01-01T00:00:00",
            "agents": [
                {
                    "name": "Architect",
                    "role": "System Architect",
                    "model": "opus",
                    "pane_index": 0,
                    "session_id": "arch-session-999"
                },
                {
                    "name": "Developer",
                    "role": "Backend Developer",
                    "model": "sonnet",
                    "pane_index": 1,
                    "session_id": None
                }
            ],
            "updated_at": None,
            "orchestrator_config": {}
        }
        
        # Convert agent dicts to TeamContextAgentInfo objects
        agents = [TeamContextAgentInfo(**agent) for agent in json_data["agents"]]
        json_data["agents"] = agents
        
        context = TeamContext(**json_data)
        
        assert context.context_name == "test-team"
        assert len(context.agents) == 2
        assert context.agents[0].session_id == "arch-session-999"
        assert context.agents[1].session_id is None
    
    def test_backward_compatibility(self):
        """Test that old data without session_id still works"""
        # Simulate old data format without session_id
        old_agent_data = {
            "name": "OldAgent",
            "role": "Legacy Role",
            "model": "sonnet",
            "pane_index": 0
            # No session_id field at all
        }
        
        # Should still deserialize correctly
        agent = TeamContextAgentInfo(**old_agent_data)
        
        assert agent.name == "OldAgent"
        assert agent.role == "Legacy Role"
        assert agent.session_id is None  # Defaults to None
        
        # Should serialize with session_id as None
        serialized = asdict(agent)
        assert "session_id" in serialized
        assert serialized["session_id"] is None