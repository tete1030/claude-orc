# Multi-Channel Communication Design

## Communication Channels Overview

Our system supports multiple communication channels with different priorities and use cases:

### 1. Normal Interactive Input (Most Common)
- **Mechanism**: Agent completes task and waits for input via tmux
- **Use Case**: Standard task completion and awaiting next instruction
- **Format**: Uses identity prefix `[FROM: Agent Name]`
- **Example**: Developer finishes feature, waits for next task

### 2. Direct Interrupts (High Priority)
- **Mechanism**: ESC command via tmux to pause ongoing process
- **Use Case**: Emergency situations requiring immediate attention
- **Authority**: Primarily from Master Agent
- **Example**: Critical error detected, stop all work immediately

### 3. Mailbox System (Asynchronous)
- **Mechanism**: Agents poll/query their mailbox for messages
- **Types**:
  - Direct messages to specific agent
  - Broadcast messages to all agents
  - Event notifications
- **Agent Response**: Optional - agent decides whether to respond or act
- **Implementation**: File-based message queue per agent

### 4. Hook-Based Status Updates (Continuous)
- **Mechanism**: Claude-code hook system presents info continuously
- **Information Displayed**:
  - Current mailbox status (new messages indicator)
  - Global system status bulletin
  - Agent-specific status info
- **Visibility**: Always visible to agent without interrupting work

## Detailed Design

### 1. Interrupt System

```python
class InterruptManager:
    def send_interrupt(self, target_agent: str, reason: str):
        """Send ESC interrupt to pause agent's current operation"""
        # Log interrupt for audit trail
        self.log_interrupt(target_agent, reason)
        
        # Send ESC via tmux
        tmux_cmd = f"send-keys -t {target_agent} C-["  # ESC key
        subprocess.run(["tmux", tmux_cmd])
        
        # Follow up with high-priority message
        self.send_urgent_message(target_agent, f"[INTERRUPT] {reason}")
```

**Interrupt Protocol**:
- Only Master Agent should issue interrupts (except system emergencies)
- Must be followed by explanation message
- Agent should acknowledge interrupt and await instructions

### 2. Mailbox System Design

```
mailboxes/
├── master_agent/
│   ├── inbox/
│   │   ├── msg_001.json
│   │   └── msg_002.json
│   └── outbox/
├── developer_agent/
│   ├── inbox/
│   └── outbox/
└── global_bulletin/
    └── status.json
```

**Message Format**:
```json
{
    "id": "msg_001",
    "timestamp": "2024-01-27T10:30:00Z",
    "from": "master_agent",
    "to": ["developer_agent"],  // or ["*"] for broadcast
    "priority": "normal",  // urgent, normal, low
    "type": "instruction",  // instruction, query, notification, status
    "content": "Please review the error handling in module X",
    "requires_response": true,
    "correlation_id": "task_123"
}
```

**Agent Mailbox Behavior**:
```python
class AgentMailbox:
    def check_messages(self):
        """Agent actively checks for new messages"""
        new_messages = self.get_unread_messages()
        
        for msg in new_messages:
            # Agent decides how to handle each message
            if msg['type'] == 'instruction' and msg['priority'] == 'urgent':
                # Likely to act on urgent instructions
                self.process_instruction(msg)
            elif msg['type'] == 'notification':
                # May just acknowledge or ignore
                self.mark_as_read(msg)
            # Agent has autonomy to ignore messages
```

### 3. Hook-Based Status Display

**Claude-Code Hook Configuration**:
```bash
# Hook that runs before each prompt display
claude-hook pre-prompt "python show_agent_status.py"
```

**Status Display Script**:
```python
# show_agent_status.py
def display_agent_status(agent_name):
    # Check mailbox
    unread_count = get_unread_message_count(agent_name)
    urgent_count = get_urgent_message_count(agent_name)
    
    # Get global status
    global_status = read_global_bulletin()
    
    # Format status line
    status_line = f"""
╔════════════════════════════════════════════════════════╗
║ 📬 Mailbox: {unread_count} new ({urgent_count} urgent) | 🌐 Global: {global_status} ║
╚════════════════════════════════════════════════════════╝
"""
    print(status_line)
```

### 4. Global Status Bulletin

**Purpose**: Shared awareness across all agents

**Content Examples**:
```json
{
    "system_status": "normal",  // normal, degraded, maintenance
    "active_agents": ["master", "developer", "reviewer"],
    "current_phase": "implementation",
    "warnings": [],
    "shared_resources": {
        "database": "locked_by: developer_agent",
        "api_server": "available"
    }
}
```

## Master Agent Oversight

### Communication Visibility
- **Master sees all**: Every inter-agent message is logged with title/summary
- **Overview mode**: Master sees message titles for high-level monitoring
- **Detail access**: Master can query full message content when needed

### Message Format with Title
```json
{
    "id": "msg_001",
    "timestamp": "2024-01-27T10:30:00Z",
    "from": "developer_agent",
    "to": ["reviewer_agent"],
    "title": "Code review request for login feature",  // REQUIRED
    "priority": "normal",
    "type": "request",
    "content": "Full details of the code changes...",  // Can be queried
    "requires_response": true
}
```

### Communication Rules Configuration

```yaml
# communication_rules.yaml
allowed_interactions:
  master_agent:
    can_send_to: ["*"]  # Master can communicate with all
    can_receive_from: ["*"]
  
  developer_agent:
    can_send_to: ["master_agent", "reviewer_agent", "tester_agent"]
    can_receive_from: ["master_agent", "reviewer_agent"]
  
  reviewer_agent:
    can_send_to: ["master_agent", "developer_agent"]
    can_receive_from: ["master_agent", "developer_agent"]
  
  tester_agent:
    can_send_to: ["master_agent", "developer_agent"]
    can_receive_from: ["master_agent", "developer_agent"]

forbidden_interactions:
  # Explicit denial rules (override allows)
  - from: "tester_agent"
    to: "reviewer_agent"
    reason: "Should go through developer first"
```

## Communication Flow Examples

### Example 1: Normal Interactive Flow
```
1. Developer completes feature implementation
2. Developer sends: "[FROM: Developer Agent] Feature X complete, awaiting review"
3. Master sees log: "Developer → waiting | Title: Feature X complete"
4. Master assigns: "[FROM: Master Agent] Reviewer, please review feature X"
5. Reviewer begins work
```

### Example 2: Direct Agent Communication
```
1. Developer needs clarification from Reviewer
2. System checks: developer_agent → reviewer_agent (ALLOWED)
3. Developer sends: "[FROM: Developer Agent] Question about code style"
4. Master sees: "Developer → Reviewer | Title: Question about code style"
5. Master can query full message if concerned
```

### Example 3: Forbidden Communication Attempt
```
1. Tester tries to message Reviewer directly
2. System checks: tester_agent → reviewer_agent (FORBIDDEN)
3. Message blocked, Tester notified: "Please route through Developer"
4. Master sees: "BLOCKED: Tester → Reviewer | Reason: Should go through developer"
```

### Example 4: Master Oversight Query
```
1. Master sees multiple messages between Developer and Reviewer
2. Master concerned about lengthy discussion
3. Master queries: "Show full content of messages 5-8"
4. System displays detailed conversation
5. Master intervenes if needed
```

## Agent Autonomy Principles

1. **Interrupts are rare**: Reserved for true emergencies
2. **Mailbox is advisory**: Agents can choose to ignore messages
3. **Status is informational**: Not all status changes require action
4. **Response is optional**: Unless explicitly required
5. **Timing is flexible**: Agents check messages when appropriate

## Implementation Benefits

1. **Non-intrusive**: Normal work flow isn't constantly interrupted
2. **Scalable**: Agents can work independently most of the time
3. **Flexible**: Multiple communication patterns supported
4. **Auditable**: All communications logged for analysis
5. **Autonomous**: Agents maintain decision-making capability