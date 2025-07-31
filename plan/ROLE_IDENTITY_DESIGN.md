# Role Identity and Communication Design

## The Identity Problem

In Claude's conversation model:
- All input appears as coming from "user" role
- Claude responds as "assistant" role
- No built-in concept of multiple participants

In our multi-agent system:
- Input could come from: human user, master agent, or other sub-agents
- Each agent has its own role (developer, reviewer, tester, etc.)
- Agents need to understand who they're talking to

## Critical Design Challenge

**Claude's View:**
```
user: "Please implement the login feature"
assistant: "I'll implement that..."
```

**Our System Reality:**
```
[Master Agent via 'user' role]: "Please implement the login feature"
[Developer Agent as 'assistant']: "I'll implement that..."

[Developer Agent via 'user' role]: "I've completed the login feature"
[Master Agent as 'assistant']: "Good, now let me assign the reviewer..."
```

The same "user" role represents different agents at different times!

## Proposed Solution: Identity Prefixing

### 1. Message Format Convention
Every message sent between agents includes an identity prefix:

```
[FROM: Master Agent] Please implement the login feature with the following requirements...

[FROM: Developer Agent] I've completed the implementation. The login feature now includes...

[FROM: Reviewer Agent] I've found 3 issues in the code that need addressing...
```

### 2. Agent Prompt Instructions
Each agent's initial prompt must include:

```
You are a [ROLE] agent in a multi-agent system. 

CRITICAL COMMUNICATION PROTOCOL:
- All messages you receive will start with [FROM: Agent Name]
- Always start your responses with [FROM: Your Role Agent]
- The "user" you see in the interface may be different agents
- Pay attention to WHO is communicating with you

Example:
If you see: "[FROM: Master Agent] Please review this code"
You respond: "[FROM: Reviewer Agent] I'll review the code now..."
```

### 3. Implementation Pattern

```python
class AgentCommunicator:
    def send_message(self, from_agent: str, to_agent: str, message: str):
        # Format message with sender identity
        formatted_message = f"[FROM: {from_agent}] {message}"
        
        # Send via tmux to target agent
        self.tmux_send_to_agent(to_agent, formatted_message)
        
    def parse_message(self, raw_message: str):
        # Extract sender identity and actual message
        pattern = r"\[FROM: (.*?)\] (.*)"
        match = re.match(pattern, raw_message)
        
        if match:
            sender = match.group(1)
            content = match.group(2)
            return {"sender": sender, "content": content}
        else:
            # Handle messages without proper formatting
            return {"sender": "Unknown", "content": raw_message}
```

## Alternative Approaches Considered

### 1. Session Context Injection
- Modify each agent's context with current conversation partner
- Problem: Context gets complex with multiple interactions

### 2. Separate Conversation Threads
- Each agent pair gets its own conversation
- Problem: Loses shared context and coordination ability

### 3. Custom Metadata Fields
- Try to inject metadata outside the message
- Problem: Claude only sees the message content

## Benefits of Identity Prefixing

1. **Simple**: Easy to implement and understand
2. **Visible**: Agents can see in plain text who they're talking to
3. **Flexible**: Works with any number of agents
4. **Debuggable**: Human operators can follow conversations
5. **Robust**: Doesn't rely on hidden state or complex routing

## Communication Patterns

### 1. Direct Communication
```
[FROM: Master Agent] Developer, please implement feature X
[FROM: Developer Agent] Master, I'll implement feature X now
```

### 2. Broadcast Messages
```
[FROM: Master Agent] ALL AGENTS: Project deadline has moved to Friday
[FROM: Developer Agent] Master, acknowledged the deadline change
[FROM: Tester Agent] Master, acknowledged the deadline change
```

### 3. Handoff Pattern
```
[FROM: Master Agent] Developer, implement feature X then notify Reviewer
[FROM: Developer Agent] Reviewer, I've completed feature X at path/to/code
[FROM: Reviewer Agent] Developer, I found issues at lines 23-25
```

## Edge Cases to Handle

1. **Missing Identity Prefix**: Assume it's from human operator
2. **Multiple Recipients**: Use "TO: Agent1, Agent2" in addition to FROM
3. **System Messages**: Use "[FROM: System]" for automation messages
4. **Context Resets**: Re-establish identity after session resets

## Implementation Notes

1. Master controller must enforce identity prefixing
2. Agents should be trained (via prompt) to always use prefixes
3. Monitor compliance and correct when needed
4. Consider visual indicators in tmux panes showing current conversation partners