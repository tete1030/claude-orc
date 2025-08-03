# Claude Multi-Agent Orchestrator - Comprehensive Refactor Plan

## Current State Analysis: A Complete Mess

The current `ccorc` launch system is a nightmare of accumulated patches, monkey-patching, and workarounds:

### Critical Problems Identified

1. **1173-line monolithic CLI file** with 28 methods in a single class
2. **Launch method is 200+ lines** of spaghetti code with multiple responsibilities  
3. **Monkey-patching everywhere**: `orchestrator.tmux.create_session = create_session_with_layout`
4. **Runtime string replacement**: `cmd.replace("ccdk", f"ccdk --model {model}", 1)`
5. **Global state manipulation**: `ClaudeLauncherConfig.build_command_string = patched_build`
6. **Nested functions with closure variables**: `create_session_with_layout`, `patched_build`, `signal_handler`
7. **Thread management mixed with business logic**
8. **No separation of concerns**: CLI, orchestration, configuration, lifecycle all mixed
9. **Inconsistent error handling**: Some exceptions, some print statements, some boolean returns
10. **No testable units**: Everything is tightly coupled
11. **🚨 CRITICAL: Hardcoded DevOps team assumptions throughout codebase**

### The Launch Process Disaster

The `launch_team` method is doing **everything**:
- Configuration loading/validation
- Context management
- Orchestrator creation/configuration  
- Method monkey-patching
- Port discovery
- MCP server lifecycle
- Agent registration with model resolution
- Task injection
- Signal handling setup
- Thread management
- Rich status output
- Context persistence

This is **completely unmaintainable**.

### 🚨 CRITICAL: DevOps Team Hardcoding Issues

The system is **hardcoded for DevOps teams only**, breaking its promise as a generic multi-agent orchestrator:

#### Hardcoded Model Assignment (lines 663, 667)
```python
# WRONG: Hardcoded role keywords
if any(keyword in agent_role.lower() or keyword in agent_name.lower() 
       for keyword in ["architect", "lead"]):
    return "opus"
elif any(keyword in agent_role.lower() or keyword in agent_name.lower() 
         for keyword in ["developer", "implementation", "coding"]):
    return "opus"
else:
    return "sonnet"
```

#### Hardcoded Task Injection (line 808)
```python
# WRONG: Assumes "architect" role exists
if task and agent_config.name.lower() == "architect":
    task_context = f"\n\nInitial task from user: {task}"
    prompt += task_context
```

#### Impact of Hardcoding
- **Breaks data science teams** (no "architect" role)
- **Breaks security teams** (different role structures)
- **Breaks research teams** (academic hierarchies)
- **Forces naming conventions** on users
- **Violates open/closed principle**

#### Examples of Broken Use Cases
- **Data Team**: DataScientist, MLEngineer, Analyst → All get "sonnet" incorrectly
- **Security Team**: SecurityLead, PentTester, Analyst → Wrong model assignments
- **Research Team**: PrincipalResearcher, ResearchAssociate → No coordinator role for tasks

## Refactor Strategy: Clean Architecture

### Phase 1: Separate Core Responsibilities

#### 1.1 Extract Domain Models
```
src/domain/
├── team_config.py          # Team configuration domain model
├── agent_config.py         # Agent configuration domain model  
├── launch_config.py        # Launch parameters domain model
└── team_context.py         # Team context domain model
```

#### 1.2 Extract Services (Single Responsibility)
```
src/services/
├── team_loader_service.py      # Load and validate team configs
├── model_resolver_service.py   # Intelligent model assignment
├── port_discovery_service.py   # Find available ports
├── layout_detection_service.py # Terminal layout detection
├── orchestrator_factory.py     # Create configured orchestrators
├── mcp_server_service.py       # MCP server lifecycle
├── context_persistence_service.py # Context CRUD operations
└── launcher_service.py         # Coordinate the launch process
```

#### 1.3 Extract Infrastructure
```
src/infrastructure/
├── docker_client.py        # Docker operations
├── tmux_client.py          # Tmux operations  
├── process_manager.py      # Background process management
└── signal_handler.py       # Graceful shutdown
```

#### 1.4 Clean CLI Layer
```
src/cli/
├── commands/
│   ├── launch_command.py   # Launch command handler
│   ├── list_command.py     # List command handler
│   ├── clean_command.py    # Clean command handler
│   └── health_command.py   # Health command handler
├── formatters/
│   ├── status_formatter.py # Rich status output
│   └── table_formatter.py  # Table output
└── cli_app.py              # Main CLI application
```

### Phase 2: Proper Dependency Injection

#### 2.1 Service Container
```python
# src/container.py
class ServiceContainer:
    def __init__(self):
        self._services = {}
        self._configure_services()
    
    def get(self, service_type: Type[T]) -> T:
        return self._services[service_type]
    
    def _configure_services(self):
        # Configure all service dependencies
        self._services[TeamLoaderService] = TeamLoaderService()
        self._services[ModelResolverService] = ModelResolverService()
        # etc.
```

#### 2.2 Eliminate Global State
- No more monkey-patching
- No more global configuration changes
- Everything injected through constructor

### Phase 3: Proper Configuration Management

#### 3.1 Typed Configuration Classes
```python
@dataclass
class LaunchConfig:
    team_name: str
    context_name: Optional[str]
    model_override: Optional[str]
    agent_model_overrides: Dict[str, str]
    force: bool
    debug: bool
    task: Optional[str]
    
    def validate(self) -> List[str]:
        # Proper validation logic
        pass
```

#### 3.2 Configuration Builder Pattern
```python
class LaunchConfigBuilder:
    def from_args(self, args: argparse.Namespace) -> LaunchConfig:
        # Build config from CLI args
        
    def with_defaults(self, team_config: TeamConfig) -> LaunchConfig:
        # Apply team defaults
```

### Phase 4: Proper Error Handling

#### 4.1 Domain Exceptions
```python
class TeamNotFoundError(Exception): pass
class ContextAlreadyExistsError(Exception): pass
class PortUnavailableError(Exception): pass
class OrchestrationError(Exception): pass
```

#### 4.2 Result Pattern
```python
@dataclass
class LaunchResult:
    success: bool
    context_name: Optional[str]
    tmux_session: Optional[str]
    error: Optional[str]
    warnings: List[str]
```

### Phase 5: Testable Architecture

#### 5.1 Interfaces for External Dependencies
```python
class IDockerClient(Protocol):
    def list_containers(self, filter: str) -> List[ContainerInfo]: ...

class ITmuxClient(Protocol):
    def create_session(self, name: str, layout: Layout) -> TmuxSession: ...
```

#### 5.2 Service Testing
Each service can be unit tested in isolation with mocked dependencies.

### Phase 6: Launch Process Redesign

#### 6.1 Clean Launch Orchestration
```python
class LaunchService:
    def __init__(
        self, 
        team_loader: TeamLoaderService,
        model_resolver: ModelResolverService,
        orchestrator_factory: OrchestratorFactory,
        context_service: ContextPersistenceService,
        mcp_service: MCPServerService
    ):
        self._team_loader = team_loader
        self._model_resolver = model_resolver
        # etc.
    
    def launch_team(self, config: LaunchConfig) -> LaunchResult:
        # 1. Load and validate team config
        team_config = self._team_loader.load_team(config.team_name)
        
        # 2. Resolve models for agents  
        resolved_agents = self._model_resolver.resolve_models(
            team_config.agents, 
            config.model_override,
            config.agent_model_overrides
        )
        
        # 3. Create orchestrator with proper configuration
        orchestrator = self._orchestrator_factory.create(
            team_config, 
            resolved_agents,
            config
        )
        
        # 4. Start MCP server
        mcp_server = self._mcp_service.start_server(orchestrator)
        
        # 5. Launch orchestrator
        result = orchestrator.launch()
        
        # 6. Persist context
        if result.success:
            self._context_service.save_context(result.context)
            
        return result
```

## Implementation Plan

### Step 1: Write Unit Tests for Current Behavior (1-2 days)
- Test current launch behavior end-to-end
- Test model resolution logic
- Test port discovery
- Test layout detection
- Create test fixtures for team configs

### Step 2: Extract Services (3-4 days)
- Create service interfaces
- Extract each service one by one
- Maintain backward compatibility
- Add service tests

### Step 3: Clean CLI Layer (2-3 days)  
- Extract command handlers
- Create proper CLI structure
- Remove business logic from CLI

### Step 4: Eliminate Monkey-Patching (2-3 days)
- Create proper factory pattern for orchestrator
- Remove global state manipulation
- Clean configuration injection

### Step 5: Integration Testing (1-2 days)
- Test complete launch flow
- Test error scenarios
- Performance testing

### Step 6: Documentation (1 day)
- Update architecture documentation
- Service documentation
- Migration guide

## Success Criteria

1. **No monkey-patching**: All configuration done through proper injection
2. **Testable services**: Each service can be unit tested in isolation  
3. **Single responsibility**: Each class has one clear purpose
4. **Clean CLI**: CLI layer only handles user interaction
5. **Proper error handling**: Domain exceptions and result patterns
6. **Maintainable**: Easy to add new features without modifying existing code
7. **Performance**: Same or better performance than current implementation

## Risk Mitigation

1. **Feature flags**: Keep old implementation available during transition
2. **Comprehensive testing**: Test both old and new implementations  
3. **Gradual migration**: Migrate one service at a time
4. **Rollback plan**: Ability to revert to old implementation if needed

This refactor will transform the current mess into a professional, maintainable, and extensible system.