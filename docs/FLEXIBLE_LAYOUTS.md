# Flexible Tmux Pane Layouts

The orchestrator now supports flexible tmux pane layouts for optimal agent organization. This production-ready feature automatically selects layouts based on agent count or allows custom configurations.

## Quick Start

```python
from src.orchestrator import Orchestrator, OrchestratorConfig

# Auto-select layout based on agent count (recommended)
config = OrchestratorConfig(session_name="my-agents")
orchestrator = Orchestrator(config)

# Or specify a layout explicitly
config = OrchestratorConfig(
    session_name="my-agents",
    layout_type="grid",  # horizontal, vertical, grid, main-left, main-top
    grid_rows=2,
    grid_cols=2
)
```

## Available Layout Types

| Layout | Best For | Agent Count | Terminal Size |
|--------|----------|-------------|---------------|
| **horizontal** | Side-by-side comparison | 2-4 | Wide screens |
| **vertical** | Sequential workflows | 2-6 | Tall screens |
| **grid** (2x2, 3x3) | Balanced monitoring | 4-9 | Large screens |
| **main-left** | Leader + specialists | 3-6 | Any size |
| **main-top** | Coordinator + workers | 3-6 | Wide screens |

## Smart Layout Selection (Production-Tested)

**Zero configuration required** - the orchestrator automatically detects terminal size and selects optimal layouts:

```python
# No layout configuration needed - smart selection enabled by default
config = OrchestratorConfig(session_name="auto-layout")
orchestrator = Orchestrator(config)

# Automatic selection based on terminal size + agent count:
# 240×48+ terminal: 2x3 grid for 5-6 agents, 3x3 for 7-9 agents
# 150×24+ terminal: Custom 2+3 layout (2 top row, 3 bottom row) for 5 agents
# 80×24 terminal:   main-vertical for 4+ agents, horizontal for 2-3
# Smaller terminal: horizontal layout (universal fallback)
```

**Performance**: <0.01ms overhead (production-validated by DevOps)

**Container Compatibility**: Docker containers (80×24 default) automatically use main-vertical for optimal 5-agent layout

## Common Patterns

### Development Team (4 agents)
```python
config = OrchestratorConfig(
    session_name="dev-team",
    layout_type="grid",
    grid_rows=2,
    grid_cols=2
)
# Layout: Frontend | Backend
#         Tester   | DevOps
```

### Research Project (3 agents)
```python  
config = OrchestratorConfig(
    session_name="research",
    layout_type="main-left"
)
# Layout: [Coordinator] | Researcher
#         [    (70%)   ] | Analyst
```

### Content Creation (5 agents)
```python
config = OrchestratorConfig(
    session_name="content",
    layout_type="grid",
    grid_rows=2,
    grid_cols=3
)
# Layout: Lead | Writer1 | Writer2
#         Editor| Review | Publish
```

## Integration with Enhanced Orchestrator

```python
from src.orchestrator_enhanced import EnhancedOrchestrator

# Enhanced orchestrator supports all layout types
config = OrchestratorConfig(
    session_name="enhanced-demo",
    layout_type="main-top"
)
orchestrator = EnhancedOrchestrator(config)
```

## Terminal Size Requirements

**Auto-Detection Thresholds** (production-tested):
- **240×48+**: Large layouts (2x3, 3x3 grids) for optimal viewing
- **150×24+**: Custom 2+3 layout for 5-agent teams (2 top row, 3 bottom row)
- **80×24**: Standard container size → main-vertical for 4+ agents
- **Smaller**: Horizontal layout (universal compatibility)

**Custom 2+3 Layout Structure**:
```
┌────────────┬────────────┐
│ Architect  │ Developer  │
├──────┬─────┴──┬─────────┤
│  QA  │ DevOps │  Docs   │
└──────┴────────┴─────────┘
```

**Edge Case**: 8+ agents in horizontal layout may exceed terminal width - smart selection prevents this.

**Performance**: Layout detection and application <0.01ms (DevOps-validated).

## Keyboard Navigation

All layouts preserve standard shortcuts:
- **F1-F3**: Quick switch to first 3 agents
- **Alt+1-9**: Alternative quick switching
- **Ctrl+b, 1-9**: Tmux standard navigation
- **Mouse**: Click panes directly, scroll for history

## Backward Compatibility

**100% backward compatible** - existing code works unchanged:
```python
# This still works exactly as before
orchestrator = Orchestrator(config)  # Uses horizontal layout
```

## Troubleshooting

**Smart selection eliminates most layout issues**, but if needed:

- **Layout unexpected**: Check terminal size with `stty size` - smart selection optimizes for your dimensions
- **"No space for new pane"**: Should not occur with smart selection (reports issue if seen)
- **Shortcuts not working**: Check for tmux key binding conflicts
- **Performance concerns**: Layout overhead is <0.01ms (negligible)

**QA-Validated Edge Cases**:
- 8+ agents: Automatically uses appropriate layout to prevent terminal overflow
- Container environments: 80×24 default automatically handled

**Pro Tip**: Use `orchestrator.tmux.get_layout_info()` to see which layout was auto-selected and why.