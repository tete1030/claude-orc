# Communication Rules and Master Oversight

## Core Principles

1. **Normal Interactive Input is Primary**: Most communication happens when agents complete tasks and wait for input
2. **Master Sees All**: Every message has a title/summary visible to master
3. **Configurable Rules**: Which agents can communicate is policy-driven
4. **Progressive Detail**: Master sees titles by default, queries for details when needed

## Communication Authorization System

### Rule Processing Order
1. Check if communication is explicitly forbidden
2. Check if sender is allowed to send to recipient
3. Check if recipient is allowed to receive from sender
4. Default: DENY (if not explicitly allowed)

### Configuration Structure

```python
class CommunicationRules:
    def __init__(self, config_file="communication_rules.yaml"):
        self.rules = self.load_rules(config_file)
    
    def is_allowed(self, from_agent: str, to_agent: str) -> tuple[bool, str]:
        """Check if communication is allowed between agents"""
        # Check forbidden rules first
        for rule in self.rules.get('forbidden_interactions', []):
            if rule['from'] == from_agent and rule['to'] == to_agent:
                return False, rule.get('reason', 'Forbidden by policy')
        
        # Check allowed rules
        allowed_to = self.rules['allowed_interactions'][from_agent]['can_send_to']
        allowed_from = self.rules['allowed_interactions'][to_agent]['can_receive_from']
        
        if ("*" in allowed_to or to_agent in allowed_to) and \
           ("*" in allowed_from or from_agent in allowed_from):
            return True, "Allowed by policy"
        
        return False, "Not explicitly allowed"
```

## Master Agent Dashboard

### Overview Display
```
╔══════════════════════════════════════════════════════════════════╗
║                    AGENT COMMUNICATION LOG                        ║
╠══════════════════════════════════════════════════════════════════╣
║ Time     From        To          Title                    Status  ║
║ 10:30    Developer   waiting      Feature X complete       ✓      ║
║ 10:32    Master      Reviewer     Review feature X         ✓      ║
║ 10:35    Reviewer    Developer    Found 3 issues           ✓      ║
║ 10:36    Tester      Reviewer     Test results ready       ✗      ║
║          └─ BLOCKED: Should go through developer first           ║
╚══════════════════════════════════════════════════════════════════╝

[Q]uery message | [F]ilter by agent | [D]etailed view | [R]efresh
```

### Master Query Commands
- `query msg_001` - Show full content of specific message
- `query developer-reviewer last 5` - Show last 5 messages between agents
- `query all reviewer` - Show all messages to/from reviewer
- `query blocked` - Show all blocked communications

## Implementation Details

### Message Routing with Titles

```python
class MessageRouter:
    def send_message(self, from_agent: str, to_agent: str, title: str, content: str):
        # Check authorization
        allowed, reason = self.rules.is_allowed(from_agent, to_agent)
        
        if not allowed:
            # Log blocked attempt for master
            self.log_blocked_message(from_agent, to_agent, title, reason)
            # Notify sender
            self.notify_sender(from_agent, f"Message blocked: {reason}")
            return False
        
        # Create message with required title
        message = {
            "id": self.generate_id(),
            "timestamp": datetime.now().isoformat(),
            "from": from_agent,
            "to": to_agent,
            "title": title,  # REQUIRED for master oversight
            "content": content,
            "status": "delivered"
        }
        
        # Log for master oversight (title only)
        self.log_for_master(message, title_only=True)
        
        # Deliver to recipient
        self.deliver_to_agent(to_agent, message)
        
        return True
```

### Agent Communication Interface

Agents must provide titles when communicating:

```python
# In agent prompt/training:
"""
When sending messages to other agents, you MUST provide a brief title:

Format: [FROM: Your Agent Name] [TITLE: Brief description] Detailed message...

Examples:
[FROM: Developer Agent] [TITLE: Code review request] I've completed the login feature...
[FROM: Reviewer Agent] [TITLE: Found security issue] The password validation needs...
"""
```

## Common Communication Patterns

### 1. Task Completion Pattern
```
Developer: [TITLE: Feature complete] → Master
Master: [TITLE: Assign review] → Reviewer
Reviewer: [TITLE: Review complete] → Master
Master: [TITLE: Deploy approved] → Developer
```

### 2. Clarification Pattern
```
Developer: [TITLE: Architecture question] → Master
Master: [TITLE: Consult architect] → Architect
Architect: [TITLE: Architecture guidance] → Developer (via Master)
```

### 3. Issue Escalation Pattern
```
Tester: [TITLE: Critical bug found] → Developer
Developer: [TITLE: Need assistance] → Master
Master: [TITLE: Emergency fix needed] → Senior Developer
```

## Benefits

1. **Controlled Communication**: Prevents chaotic cross-talk
2. **Master Awareness**: Nothing happens without potential oversight
3. **Flexible Policy**: Easy to adjust rules as team evolves
4. **Audit Trail**: Complete history with summaries
5. **Scalable**: Works with any number of agents