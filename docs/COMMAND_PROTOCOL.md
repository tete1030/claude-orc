# Command Protocol Specification

## Overview

The orchestrator uses an XML-based command protocol for inter-agent communication. Commands are embedded in agent responses and extracted by the monitoring system.

## Protocol Design Principles

1. **Human-Readable**: XML format that's easy to understand and debug
2. **Flexible**: Supports multiple formats for backward compatibility  
3. **Extensible**: Easy to add new command types
4. **Robust**: Handles variations in formatting and case

## Command Format

### Modern Format (Recommended)

```xml
<orc-command name="command_type" param1="value1" param2="value2">
    Content if needed
</orc-command>
```

**Attributes in opening tag:**
- Cleaner and more concise
- Easier to parse
- Better for simple commands

### Legacy Format (Supported)

```xml
<orc-command type="command_type">
    <param1>value1</param1>
    <param2>value2</param2>
    <content>Content if needed</content>
</orc-command>
```

**Nested XML elements:**
- More verbose but clearer structure
- Better for complex data
- Original format from early versions

## Command Types

### 1. send_message

Sends a message from one agent to another.

**Modern Format:**
```xml
<orc-command name="send_message" from="SenderAgent" to="ReceiverAgent" title="Message Title" priority="normal">
    This is the message content.
    It can be multiple lines.
</orc-command>
```

**Legacy Format:**
```xml
<orc-command type="send_message">
    <from>SenderAgent</from>
    <to>ReceiverAgent</to>
    <title>Message Title</title>
    <content>This is the message content.</content>
    <priority>normal</priority>
</orc-command>
```

**Parameters:**
- `from` (required): Name of sending agent
- `to` (required): Name of receiving agent  
- `title` (optional): Message subject/title
- `priority` (optional): "normal" or "high" (default: "normal")
- Content: The message body

**Example Usage:**
```python
system_prompt = """When you need to send a task to the Worker agent:
<orc-command name="send_message" from="Master" to="Worker" title="New Task">
Describe the task here
</orc-command>"""
```

### 2. mailbox_check

Retrieves all pending messages for the requesting agent.

**Format:**
```xml
<orc-command name="mailbox_check"></orc-command>
```

**No parameters needed** - agent identity is determined from context.

**Response:** The orchestrator will send all queued messages to the agent's pane.

**Example Usage:**
```python
system_prompt = """To check your messages:
<orc-command name="mailbox_check"></orc-command>"""
```

### 3. list_agents (Planned)

Lists all currently active agents.

**Format:**
```xml
<orc-command name="list_agents"></orc-command>
```

**Response:** List of agent names and their status.

### 4. context_status (Planned)

Reports context usage statistics.

**Format:**
```xml
<orc-command name="context_status"></orc-command>
```

**Response:** Lines used, estimated tokens, warnings if near limit.

## Command Parsing

### Regular Expression

The orchestrator uses this regex pattern:

```python
pattern = re.compile(
    r'<orc-command\s+(?:name|type)=["\']([^"\']+)["\'](?:\s+[^>]+)?>(.*?)</orc-command>',
    re.DOTALL | re.IGNORECASE
)
```

**Breakdown:**
- `<orc-command\s+`: Opening tag with whitespace
- `(?:name|type)=`: Either "name" or "type" attribute
- `["\']([^"\']+)["\']`: Quoted command type (captured)
- `(?:\s+[^>]+)?`: Optional additional attributes
- `>(.*?)</orc-command>`: Content and closing tag (captured)

### Attribute Parsing

For modern format attributes:

```python
# Extract attributes from tag
attr_pattern = re.compile(r'(\w+)=["\']([^"\']+)["\']')
attributes = dict(attr_pattern.findall(tag_text))
```

## Message Routing

### Agent Name Resolution

The orchestrator uses case-insensitive matching:

```python
# Direct match first
target_agent = self.agents.get(cmd.to_agent)

# Fall back to case-insensitive
if not target_agent:
    for agent_name, agent in self.agents.items():
        if agent_name.lower() == cmd.to_agent.lower():
            target_agent = agent
            break
```

### Mailbox System

Messages are queued until retrieved:

```python
# Add to mailbox
self.mailbox[agent_name].append(formatted_message)

# Retrieve from mailbox
messages = self.mailbox[agent_name]
self.mailbox[agent_name] = []  # Clear after retrieval
```

## Command Examples

### Basic Communication Flow

**Master Agent:**
```
I'll assign a calculation task to the Worker.

<orc-command name="send_message" from="Master" to="Worker" title="Calculate">
Please calculate the sum of 15 and 27 and report back.
</orc-command>
```

**Worker Agent receives notification and checks:**
```
I have a new message. Let me check my mailbox.

<orc-command name="mailbox_check"></orc-command>
```

**Worker Agent responds:**
```
I've calculated the sum. Let me send the result back.

<orc-command name="send_message" from="Worker" to="Master" title="Result">
The sum of 15 and 27 is 42.
</orc-command>
```

### High-Priority Message

```xml
<orc-command name="send_message" from="Monitor" to="Master" title="Alert" priority="high">
System resources are running low. Please take action.
</orc-command>
```

## Best Practices

### 1. Command Placement

**DO:** Place commands in natural conversation flow
```
I'll send this task to the Worker agent now.

<orc-command name="send_message" from="Master" to="Worker">
Please process the attached data.
</orc-command>

The task has been sent successfully.
```

**DON'T:** Place commands in code blocks
```markdown
Here's how to send a message:
```xml
<orc-command name="send_message">  <!-- This won't be processed -->
</orc-command>
```
```

### 2. Error Handling

Always include clear instructions in system prompts:

```python
system_prompt = """If a message fails to send, you'll see an error.
In that case, check the agent name and try again.

Valid agents: Master, Worker, Monitor"""
```

### 3. Message Formatting

For complex messages, use clear structure:

```xml
<orc-command name="send_message" from="Analyst" to="Reporter" title="Analysis Results">
Summary: Processing completed successfully

Details:
- Processed 1,543 records
- Found 23 anomalies  
- Execution time: 4.2 seconds

Recommendations:
1. Review anomalies in dataset
2. Adjust threshold parameters
3. Re-run analysis tomorrow
</orc-command>
```

## Extending the Protocol

### Adding New Command Types

1. **Define command structure:**
```xml
<orc-command name="new_command" param1="value1">
    Optional content
</orc-command>
```

2. **Update command parser:**
```python
def extract_commands(self, messages):
    # ... existing parsing ...
    
    if command_type == "new_command":
        command.param1 = attributes.get("param1")
```

3. **Add command handler:**
```python
def _handle_new_command(self, agent_name: str, command: Command):
    # Implementation
    pass

# Register handler
self.command_handlers["new_command"] = self._handle_new_command
```

### Adding Parameters

For backward compatibility, support both formats:

```python
# Modern format: from attribute
from_agent = attributes.get("from")

# Legacy format: from nested element
if not from_agent and legacy_content:
    from_match = re.search(r'<from>([^<]+)</from>', legacy_content)
    if from_match:
        from_agent = from_match.group(1)
```

## Security Considerations

### Input Validation

Always validate command parameters:

```python
def _handle_send_message(self, agent_name: str, command: Command):
    # Validate agent exists
    if command.to_agent not in self.agents:
        logger.warning(f"Unknown recipient: {command.to_agent}")
        return
    
    # Validate sender matches
    if command.from_agent != agent_name:
        logger.warning(f"Agent {agent_name} spoofing as {command.from_agent}")
        return
```

### Content Sanitization

Consider sanitizing message content:

```python
def sanitize_content(content: str) -> str:
    # Remove potential security risks
    # But preserve necessary formatting
    return content.strip()
```

## Debugging Commands

### Enable Command Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In SessionMonitor
logger.debug(f"Extracted command: {command.command_type} from {agent_name}")
```

### Test Command Extraction

```python
# Test regex manually
import re

test_content = '''<orc-command name="send_message" from="A" to="B">Test</orc-command>'''
pattern = re.compile(r'<orc-command\s+(?:name|type)=["\']([^"\']+)["\'](?:\s+[^>]+)?>(.*?)</orc-command>', re.DOTALL)

match = pattern.search(test_content)
if match:
    print(f"Type: {match.group(1)}")
    print(f"Content: {match.group(2)}")
```

### Common Issues

1. **Commands not detected:**
   - Check not in code blocks
   - Verify XML is well-formed
   - Ensure quotes are standard ASCII

2. **Routing failures:**
   - Verify agent names (case-insensitive)
   - Check agent is registered
   - Confirm mailbox exists

3. **Malformed XML:**
   - Missing closing tags
   - Mismatched quotes
   - Special characters not escaped