# Central Orchestration Service Design

## Overview

A central service that manages all agent interactions, tmux sessions, and communication routing. Agents never directly control tmux or communicate with each other - everything goes through the orchestrator.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 ORCHESTRATION SERVICE                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │            Command Parser & Validator            │   │
│  │         Parses <orc-command> directives         │   │
│  └────────────────┬────────────────────────────────┘   │
│                   │                                      │
│  ┌────────────────▼────────────────────────────────┐   │
│  │              Command Executor                    │   │
│  │  - Tmux Management (create/destroy panes)       │   │
│  │  - Message Routing (with rule enforcement)      │   │
│  │  - Session Control (pause/resume/reset)         │   │
│  │  - State Management (agent status tracking)     │   │
│  └────────────────┬────────────────────────────────┘   │
│                   │                                      │
│  ┌────────────────▼────────────────────────────────┐   │
│  │            Monitoring & Logging                  │   │
│  │  - Session file watching                        │   │
│  │  - Command audit trail                          │   │
│  │  - Performance metrics                          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
                           │ Controls
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Tmux Sessions                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Master     │  │  Developer   │  │   Reviewer   │ │
│  │   Agent      │  │    Agent     │  │    Agent     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Agent Communication Protocol

### Command Format

Agents communicate with the orchestrator using special formatted commands:

```xml
<orc-command type="send_message">
  <from>developer_agent</from>
  <to>reviewer_agent</to>
  <title>Code review request for login feature</title>
  <content>
    I've completed the login feature implementation.
    Files changed: src/auth/login.py, tests/test_login.py
  </content>
</orc-command>
```

### Available Commands

#### 1. Send Message
```xml
<orc-command type="send_message">
  <from>agent_name</from>
  <to>target_agent</to>
  <title>Brief description</title>
  <content>Detailed message content</content>
  <priority>normal|high|urgent</priority>
</orc-command>
```

#### 2. Query Mailbox
```xml
<orc-command type="query_mailbox">
  <agent>agent_name</agent>
  <filter>unread|all|urgent</filter>
</orc-command>
```

#### 3. Update Status
```xml
<orc-command type="update_status">
  <agent>agent_name</agent>
  <status>idle|working|blocked|completed</status>
  <current_task>Brief description of current work</current_task>
</orc-command>
```

#### 4. Request Action
```xml
<orc-command type="request_action">
  <from>agent_name</from>
  <action>spawn_agent|terminate_agent|reset_session</action>
  <target>target_agent_name</target>
  <reason>Why this action is needed</reason>
</orc-command>
```

#### 5. Query System State
```xml
<orc-command type="query_state">
  <query>active_agents|communication_log|global_status</query>
  <filter>last_10_minutes|specific_agent|all</filter>
</orc-command>
```

## Implementation Details

### Command Detection

The orchestrator monitors agent session files for commands:

```python
class CommandDetector:
    def __init__(self):
        self.command_pattern = re.compile(
            r'<orc-command.*?>(.*?)</orc-command>', 
            re.DOTALL
        )
    
    def extract_commands(self, session_content):
        """Extract orchestrator commands from session content"""
        commands = []
        for match in self.command_pattern.finditer(session_content):
            cmd_xml = match.group(0)
            commands.append(self.parse_command(cmd_xml))
        return commands
    
    def parse_command(self, xml_string):
        """Parse XML command into structured data"""
        # Parse XML and validate structure
        root = ET.fromstring(xml_string)
        command_type = root.get('type')
        
        command = {
            'type': command_type,
            'timestamp': datetime.now(),
            'raw': xml_string
        }
        
        # Extract fields based on command type
        for child in root:
            command[child.tag] = child.text
        
        return command
```

### Command Execution

```python
class CommandExecutor:
    def __init__(self, tmux_manager, rule_engine, message_router):
        self.tmux = tmux_manager
        self.rules = rule_engine
        self.router = message_router
    
    def execute(self, command):
        """Execute orchestrator command"""
        cmd_type = command['type']
        
        if cmd_type == 'send_message':
            return self.handle_send_message(command)
        elif cmd_type == 'query_mailbox':
            return self.handle_query_mailbox(command)
        elif cmd_type == 'update_status':
            return self.handle_update_status(command)
        elif cmd_type == 'request_action':
            return self.handle_request_action(command)
        elif cmd_type == 'query_state':
            return self.handle_query_state(command)
        else:
            return {'error': f'Unknown command type: {cmd_type}'}
    
    def handle_send_message(self, command):
        """Route message between agents with rule checking"""
        from_agent = command['from']
        to_agent = command['to']
        
        # Check communication rules
        allowed, reason = self.rules.is_allowed(from_agent, to_agent)
        if not allowed:
            # Notify sender of blocked message
            self.send_notification(from_agent, 
                f"Message blocked: {reason}")
            return {'status': 'blocked', 'reason': reason}
        
        # Route the message
        message_id = self.router.deliver(command)
        
        # Log for master oversight
        self.log_communication(command, message_id)
        
        return {'status': 'delivered', 'message_id': message_id}
```

## Agent Integration

### How Agents Use the Service

In agent prompts, we train them to use orchestrator commands:

```
When you need to communicate with other agents or the system, use orchestrator commands:

To send a message to another agent:
<orc-command type="send_message">
  <from>your_agent_name</from>
  <to>target_agent_name</to>
  <title>Brief description</title>
  <content>Your detailed message</content>
</orc-command>

To check your mailbox:
<orc-command type="query_mailbox">
  <agent>your_agent_name</agent>
  <filter>unread</filter>
</orc-command>

To update your status:
<orc-command type="update_status">
  <agent>your_agent_name</agent>
  <status>working</status>
  <current_task>Implementing login feature</current_task>
</orc-command>
```

### Response Handling

The orchestrator sends responses back through tmux:

```python
def send_response(self, agent_name, response):
    """Send command response back to agent"""
    formatted_response = f"""
[ORCHESTRATOR RESPONSE]
Command: {response['command_type']}
Status: {response['status']}
Result: {response.get('result', 'Command executed')}
Details: {json.dumps(response.get('details', {}), indent=2)}
[END ORCHESTRATOR RESPONSE]
"""
    self.tmux.send_to_agent(agent_name, formatted_response)
```

## Benefits of Central Service

1. **Single Point of Control**: All agent interactions go through one service
2. **Rule Enforcement**: Communication rules checked centrally
3. **Complete Audit Trail**: Every command logged and traceable
4. **Clean Separation**: Agents focus on tasks, not infrastructure
5. **Easy Monitoring**: One service to monitor instead of many agents
6. **Flexible Protocol**: Easy to add new command types
7. **Error Handling**: Central place for error management

## Alternative Protocols Considered

### Shell Script Approach
```bash
# Agent would call scripts like:
./orc send-message --from developer --to reviewer --title "Review request"
./orc query-mailbox --agent developer --filter unread
```

**Pros**: Simple, Unix philosophy
**Cons**: Harder to parse in agent output, less structured

### JSON Protocol
```json
{"orc_command": {
  "type": "send_message",
  "from": "developer_agent",
  "to": "reviewer_agent",
  "title": "Review request",
  "content": "Please review..."
}}
```

**Pros**: Structured, easy to parse
**Cons**: Less readable in agent conversation, JSON escaping issues

### Chosen: XML Protocol
**Pros**: 
- Human readable in conversation
- Clear boundaries with tags
- Supports multi-line content naturally
- Easy to parse and validate

## Security Considerations

1. **Command Validation**: All commands validated before execution
2. **Permission Checking**: Agents can only perform allowed actions
3. **Rate Limiting**: Prevent command flooding
4. **Audit Logging**: Complete trace of all commands
5. **Isolation**: Agents can't directly control tmux or filesystem