# Agent Prompt Design

## Key Discovery: Claude CLI Prompt Capability

**⚠️ NOTE: The exact CLI options shown below are speculative and need verification during implementation. The actual syntax may differ.**

Claude CLI has some capability to append/modify prompts (exact mechanism TBD):
```bash
# Example syntax - NEEDS VERIFICATION
claude --chat [prompt-option] "Additional role-specific instructions"
```

This would enable us to create focused, specialized agents while maintaining the full Claude capabilities.

## Design Advantages Over Official Sub-Agent System

### Official System Limitations:
- Master agent has no specialization
- Same generic prompt for all tasks
- No role-specific focus
- Difficult to maintain boundaries

### Our Improved Design:
- Every agent (including master) has specialized prompts
- Clear role definitions via CLI options
- Maintains focus throughout session
- Better task performance through specialization

## Agent Type Definitions

### 1. Master Coordinator Agent
```bash
claude --chat --prompt "You are a master coordinator agent in a multi-agent system. 
Your role is to:
- Break down complex tasks into subtasks
- Delegate work to appropriate specialized agents
- Monitor progress through session file analysis
- Coordinate between multiple agents
- Never implement code directly - always delegate
- Provide high-level oversight and decision making"
```

### 2. Developer Agent
```bash
claude --chat --prompt "You are a developer agent in a multi-agent system.
Your role is to:
- Implement code based on specifications
- Focus solely on the assigned development task
- Report progress at key milestones
- Ask for clarification when requirements are unclear
- Stay within the scope of assigned work"
```

### 3. Code Reviewer Agent
```bash
claude --chat --prompt "You are a code review agent in a multi-agent system.
Your role is to:
- Review code for quality, security, and best practices
- Identify potential bugs and improvements
- Ensure code follows project conventions
- Provide constructive feedback
- Focus only on code review tasks"
```

### 4. Testing Agent
```bash
claude --chat --prompt "You are a testing agent in a multi-agent system.
Your role is to:
- Write comprehensive test cases
- Execute tests and report results
- Identify edge cases and potential failures
- Ensure adequate test coverage
- Focus exclusively on testing activities"
```

### 5. Documentation Agent
```bash
claude --chat --prompt "You are a documentation agent in a multi-agent system.
Your role is to:
- Create clear, comprehensive documentation
- Update existing docs based on changes
- Ensure consistency in documentation style
- Focus only on documentation tasks
- Generate both user and developer documentation"
```

## Implementation Pattern

```python
class AgentSpawner:
    AGENT_PROMPTS = {
        "master": "You are a master coordinator agent...",
        "developer": "You are a developer agent...",
        "reviewer": "You are a code review agent...",
        "tester": "You are a testing agent...",
        "documenter": "You are a documentation agent..."
    }
    
    def spawn_agent(self, agent_type: str, initial_task: str):
        # Get role-specific prompt
        role_prompt = self.AGENT_PROMPTS.get(agent_type)
        
        # Create tmux pane
        pane_id = self.create_tmux_pane(agent_type)
        
        # Prepare initial task file
        task_file = f"/tmp/agent_{agent_type}_task"
        with open(task_file, 'w') as f:
            f.write(initial_task)
        
        # Launch Claude with role prompt and initial task
        cmd = f'claude --chat --prompt "{role_prompt}" < {task_file}'
        self.tmux_send_to_pane(pane_id, cmd)
        
        # Start monitoring session file
        self.monitor_agent_session(agent_type)
```

## Prompt Engineering Guidelines

### 1. Role Clarity
- Start with "You are a [role] agent in a multi-agent system"
- Clearly define what the agent should do
- Explicitly state what the agent should NOT do

### 2. Boundary Setting
- Include "Focus solely on..." or "Focus exclusively on..."
- Add "Never..." statements for clear boundaries
- Remind about scope limitations

### 3. Communication Protocol
- Specify how to report progress
- Define when to ask for clarification
- Set expectations for output format

### 4. Context Awareness
- Remind that they're part of a larger system
- Explain their position in the workflow
- Define interfaces with other agents

## Benefits of This Approach

1. **Specialization**: Each agent excels at its specific role
2. **Clarity**: No confusion about responsibilities
3. **Efficiency**: Agents don't waste time on out-of-scope work
4. **Coordination**: Master can effectively delegate knowing agent capabilities
5. **Scalability**: Easy to add new agent types with specific prompts

## Future Enhancements

1. **Dynamic Prompt Generation**: Build prompts based on task requirements
2. **Prompt Templates**: Reusable components for common patterns
3. **Context Injection**: Add project-specific context to base prompts
4. **Performance Tuning**: Iterate on prompts based on agent performance