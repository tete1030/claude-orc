# Team Configuration Guide

The Claude Multi-Agent Orchestrator supports team-based configuration files that define groups of agents with specific roles, workflows, and coordination rules. This guide covers how to create, configure, and launch custom teams.

## Overview

Team configuration isolation allows you to:
- Define reusable team structures with specific agent roles
- Set team-wide defaults for models, sessions, and orchestration settings
- Establish workflow patterns and communication rules
- Launch complete teams with a single command
- Override individual settings when needed

The system searches for team configurations in:
1. `teams/` directory
2. `examples/teams/` directory

## Configuration Format

Team configurations are stored in YAML or JSON format with the following structure:

### Basic YAML Structure

```yaml
team:
  name: "Your Team Name"
  description: "Brief description of the team's purpose"

agents:
  - name: "Agent Name"
    role: "Agent Role Description"
    model: "sonnet"  # Optional, uses team default if not specified
    # prompt_file: "agent_name.md"  # Optional, defaults to name-based file

settings:
  default_context_name: "team-session"
  default_model: "sonnet"
  orchestrator_type: "enhanced"  # "base" or "enhanced"
  poll_interval: 0.5
  mcp_port: 8766
  debug: false
  container_mode: "isolated"  # "isolated" or "shared"

# Optional workflow documentation
workflow:
  coordination_rules:
    - "Rule 1: Description of coordination pattern"
    - "Rule 2: Another coordination pattern"
  
  communication_patterns:
    - "Pattern 1: How team members communicate"
    - "Pattern 2: Information flow patterns"
```

### JSON Format Example

```json
{
  "team": {
    "name": "Development Team",
    "description": "Software development team"
  },
  "agents": [
    {
      "name": "Architect",
      "role": "System Design Lead",
      "model": "sonnet"
    },
    {
      "name": "Developer", 
      "role": "Implementation Engineer",
      "model": "sonnet"
    }
  ],
  "settings": {
    "default_context_name": "dev-team",
    "default_model": "sonnet",
    "orchestrator_type": "enhanced"
  }
}
```

## Usage Guide

### List Available Teams

View all configured teams:

```bash
ccorc teams list
```

Example output:
```
Team Name            Config Name               Agents   Directory      
---------------------------------------------------------------------------
DevOps Team          devops-team               5        examples/teams 
Security Team        security-team             4        examples/teams 
Data Engineering Team data-team                4        examples/teams 
```

### Launch a Team

Basic team launch:

```bash
ccorc launch --team devops-team
```

### CLI Override Options

Override team settings during launch:

**Session Name Override:**
```bash
ccorc launch --team devops-team --session my-session
```

**Global Model Override:**
```bash
ccorc launch --team devops-team --model opus
```

**Agent-Specific Model Overrides:**
```bash
ccorc launch --team devops-team --agent-model "Architect=opus" --agent-model "Developer=sonnet"
```

**Force Kill Existing Session:**
```bash
ccorc launch --team devops-team --force
```

**Debug Mode:**
```bash
ccorc launch --team devops-team --debug
```

**Combined Options:**
```bash
ccorc launch --team devops-team --session custom-session --model sonnet --debug --force
```

### Team Context Management

List active team contexts:
```bash
ccorc list
```

Get detailed information about a team context:
```bash
ccorc info team-session-name
```

Check team health:
```bash
ccorc health team-session-name
```

Clean up a team context:
```bash
ccorc clean team-session-name
```

## Creating Custom Teams

### Directory Structure

To create a custom team, organize files as follows:

```
teams/your-team/
├── team.yaml              # Main configuration file
├── architect.md            # Agent prompt file (optional)
├── developer.md            # Agent prompt file (optional)
└── qa.md                   # Agent prompt file (optional)
```

Or place configuration directly in search paths:
```
teams/
├── your-team.yaml          # Configuration file
├── architect.md            # Prompt files in same directory
├── developer.md
└── qa.md
```

### Required Files

**team.yaml** (or team.json):
- Main configuration file with team structure
- Must include `team`, `agents`, and `settings` sections
- At least one agent is required

**Agent Prompt Files** (optional):
- Markdown files containing agent-specific prompts
- Default naming: `{agent_name_lowercase_with_underscores}.md`
- Can be overridden with `prompt_file` property in agent config

### Configuration Options

#### Team Settings

| Setting | Description | Default | Options |
|---------|-------------|---------|---------|
| `default_context_name` | Session name if not overridden | "team-session" | Any string |
| `default_model` | Default model for all agents | "sonnet" | Valid Claude model names |
| `orchestrator_type` | Type of orchestrator to use | "enhanced" | "base", "enhanced" |
| `poll_interval` | State monitoring frequency (seconds) | 0.5 | Number |
| `mcp_port` | MCP server port | 8766 | Port number |
| `debug` | Enable debug mode | false | true, false |
| `container_mode` | Container isolation level | "isolated" | "isolated", "shared" |

#### Agent Configuration

| Property | Description | Required | Example |
|----------|-------------|----------|---------|
| `name` | Agent identifier | Yes | "Architect" |
| `role` | Agent role description | Yes | "System Design Lead" |
| `model` | Agent-specific model | No | "sonnet" |
| `prompt_file` | Custom prompt file name | No | "custom_prompt.md" |

#### Workflow Documentation (Optional)

The `workflow` section documents team patterns but doesn't affect functionality:

```yaml
workflow:
  coordination_rules:
    - "Architect leads design discussions"
    - "Sequential validation through QA"
  
  communication_patterns:
    - "Architect broadcasts decisions"
    - "QA reports test results"
```

### Validation

The system validates team configurations:

- Team name is required
- At least one agent is required
- Agent names must be unique
- Agent names and roles are required
- Orchestrator type must be "base" or "enhanced"

Validation errors are displayed when launching teams.

## Examples

### Example Teams

The system includes three reference team configurations:

#### DevOps Team (`examples/teams/devops-team/`)
- **Agents**: Architect, Developer, QA, DevOps, Docs
- **Focus**: Complete software development lifecycle
- **Session**: `devops-team`

#### Security Team (`examples/teams/security-team/`)
- **Agents**: Security Architect, Security Analyst, Developer, QA  
- **Focus**: Cybersecurity, threat analysis, secure development
- **Session**: `security-team`

#### Data Engineering Team (`examples/teams/data-team/`)
- **Agents**: Data Architect, Data Engineer, ML Engineer, Analyst
- **Focus**: Data pipelines, machine learning, analytics
- **Session**: `data-team`

### Creating a Simple Team

Create `teams/simple-team.yaml`:

```yaml
team:
  name: "Simple Team"
  description: "Basic two-agent team"

agents:
  - name: "Lead"
    role: "Team Lead"
    model: "opus"
    
  - name: "Assistant"
    role: "Assistant"
    model: "sonnet"

settings:
  default_context_name: "simple-session"
  orchestrator_type: "enhanced"
```

Launch the team:
```bash
ccorc launch --team simple-team
```

### Creating a Team with Custom Prompts

Create `teams/consulting-team/team.yaml`:

```yaml
team:
  name: "Consulting Team"
  description: "Client consulting team"

agents:
  - name: "Senior Consultant"
    role: "Strategic Advisor"
    prompt_file: "senior_consultant.md"
    
  - name: "Analyst"
    role: "Data Analyst" 
    prompt_file: "business_analyst.md"

settings:
  default_context_name: "consulting-session"
```

Create prompt files:
- `teams/consulting-team/senior_consultant.md`
- `teams/consulting-team/business_analyst.md`

## Best Practices

1. **Use Descriptive Names**: Choose clear, descriptive names for teams and agents
2. **Document Workflows**: Include coordination rules and communication patterns
3. **Set Appropriate Models**: Choose models based on agent complexity and cost requirements
4. **Test Configurations**: Validate team configs before deployment
5. **Version Control**: Keep team configurations in version control
6. **Environment-Specific Overrides**: Use CLI options for environment-specific settings

## Troubleshooting

**Configuration not found:**
- Verify file is in `teams/` or `examples/teams/` directory
- Check file extension (`.yaml`, `.yml`, or `.json`)
- Ensure proper file naming

**Validation errors:**
- Review required fields (team name, agents, roles)
- Check for duplicate agent names
- Verify orchestrator type is "base" or "enhanced"

**Launch failures:**
- Use `--force` flag if session already exists
- Check Docker and tmux are available
- Verify Claude CLI is properly configured

**Missing prompts:**
- Prompt files are optional - agents will work with role descriptions
- Check prompt file names match agent names (lowercase with underscores)
- Verify prompt files exist in the same directory as team config