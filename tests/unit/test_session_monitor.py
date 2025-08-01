"""Unit tests for SessionMonitor"""

import unittest
import json
import tempfile
import os
from src.session_monitor import SessionMonitor, Message, Command


class TestSessionMonitor(unittest.TestCase):
    """Test cases for SessionMonitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        self.temp_file.close()
        self.monitor = SessionMonitor(self.temp_file.name, "test_agent")
        
    def tearDown(self):
        """Clean up test fixtures"""
        os.unlink(self.temp_file.name)
        
    def test_get_new_messages_empty_file(self):
        """Test reading from empty file"""
        messages = self.monitor.get_new_messages()
        self.assertEqual(len(messages), 0)
        
    def test_get_new_messages_user_message(self):
        """Test reading user message"""
        # Write a user message to file
        msg_data = {
            "uuid": "test-uuid-1",
            "sessionId": "session-123",
            "type": "user",
            "timestamp": 1234567890,
            "message": {
                "role": "user",
                "content": "Hello, this is a test message"
            }
        }
        
        with open(self.temp_file.name, 'w') as f:
            f.write(json.dumps(msg_data) + '\n')
            
        messages = self.monitor.get_new_messages()
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].uuid, "test-uuid-1")
        self.assertEqual(messages[0].type, "user")
        self.assertEqual(messages[0].content, "Hello, this is a test message")
        
    def test_get_new_messages_assistant_message(self):
        """Test reading assistant message with content blocks"""
        msg_data = {
            "uuid": "test-uuid-2",
            "sessionId": "session-123",
            "type": "assistant",
            "timestamp": 1234567890,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "This is the response"
                    },
                    {
                        "type": "thinking",
                        "text": "This should be ignored"
                    }
                ]
            }
        }
        
        with open(self.temp_file.name, 'w') as f:
            f.write(json.dumps(msg_data) + '\n')
            
        messages = self.monitor.get_new_messages()
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].type, "assistant")
        self.assertEqual(messages[0].content, "This is the response")
        
    def test_incremental_reading(self):
        """Test that only new messages are read"""
        # Write first message
        msg1 = {
            "uuid": "uuid-1",
            "sessionId": "session-123",
            "type": "user",
            "message": {"content": "First message"}
        }
        
        with open(self.temp_file.name, 'w') as f:
            f.write(json.dumps(msg1) + '\n')
            
        # Read first time
        messages = self.monitor.get_new_messages()
        self.assertEqual(len(messages), 1)
        
        # Write second message
        msg2 = {
            "uuid": "uuid-2",
            "sessionId": "session-123",
            "type": "user",
            "message": {"content": "Second message"}
        }
        
        with open(self.temp_file.name, 'a') as f:
            f.write(json.dumps(msg2) + '\n')
            
        # Read second time - should only get new message
        messages = self.monitor.get_new_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].uuid, "uuid-2")
        
    def test_extract_commands_from_user_message(self):
        """Test extracting commands from user message"""
        message = Message(
            uuid="test-uuid",
            session_id="session-123",
            type="user",
            timestamp=1234567890,
            content='''Here is a command:
<orc-command type="send_message">
  <from>master_agent</from>
  <to>worker_agent</to>
  <title>Test Task</title>
  <content>Please do something</content>
</orc-command>''',
            raw_data={}
        )
        
        commands = self.monitor.extract_commands([message])
        
        self.assertEqual(len(commands), 1)
        cmd = commands[0]
        self.assertEqual(cmd.command_type, "send_message")
        self.assertEqual(cmd.from_agent, "master_agent")
        self.assertEqual(cmd.to_agent, "worker_agent")
        self.assertEqual(cmd.title, "Test Task")
        self.assertEqual(cmd.content, "Please do something")
        
    def test_extract_commands_with_single_quotes(self):
        """Test extracting commands with single quotes in type attribute"""
        message = Message(
            uuid="test-uuid",
            session_id="session-123",
            type="user",
            timestamp=1234567890,
            content='''<orc-command type='send_message'>
  <from>agent1</from>
  <to>agent2</to>
  <title>Test</title>
  <content>Test content</content>
</orc-command>''',
            raw_data={}
        )
        
        commands = self.monitor.extract_commands([message])
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].command_type, "send_message")
        
    def test_extract_multiple_commands(self):
        """Test extracting multiple commands from one message"""
        message = Message(
            uuid="test-uuid",
            session_id="session-123",
            type="user",
            timestamp=1234567890,
            content='''First command:
<orc-command type="send_message">
  <from>agent1</from>
  <to>agent2</to>
  <title>Command 1</title>
</orc-command>

Second command:
<orc-command type="send_message">
  <from>agent2</from>
  <to>agent1</to>
  <title>Command 2</title>
</orc-command>''',
            raw_data={}
        )
        
        commands = self.monitor.extract_commands([message])
        
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0].title, "Command 1")
        self.assertEqual(commands[1].title, "Command 2")
        
    def test_reset_monitor(self):
        """Test resetting monitor state"""
        # Add some processed UUIDs
        self.monitor.processed_uuids.add("uuid-1")
        self.monitor.processed_uuids.add("uuid-2")
        self.monitor.last_position = 100
        
        # Reset
        self.monitor.reset()
        
        self.assertEqual(len(self.monitor.processed_uuids), 0)
        self.assertEqual(self.monitor.last_position, 0)
        
    def test_get_file_size(self):
        """Test getting file size"""
        # Write some data
        with open(self.temp_file.name, 'w') as f:
            f.write("test content\n")
            
        size = self.monitor.get_file_size()
        self.assertGreater(size, 0)
        
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON lines"""
        with open(self.temp_file.name, 'w') as f:
            f.write("not json\n")
            f.write(json.dumps({"uuid": "valid", "type": "user", 
                               "message": {"content": "valid message"}}) + "\n")
            
        messages = self.monitor.get_new_messages()
        
        # Should skip malformed line and read valid one
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].uuid, "valid")


if __name__ == '__main__':
    unittest.main()