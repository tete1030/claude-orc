#!/usr/bin/env python3
"""
Enhanced DevOps Team Demo - Development team with file system access

This version gives the DevOps team actual ability to read and modify
the orchestrator codebase, with safety measures:
- Read access to src/ and tests/
- Write access only to .temp/ for experiments
- Can propose changes via messages

TEAM COORDINATION PRINCIPLES (Updated 2025-08-02):
1. SEQUENTIAL WORKFLOW: Design → Implementation → Testing → Documentation
2. SINGLE OWNERSHIP: One person implements each component (no duplication)
3. CLEAR HANDOFFS: Explicit "task complete" signals between phases
4. ARCHITECT COORDINATES ONLY: Does not implement, only assigns and reviews
5. DEPENDENCY AWARENESS: Each role waits for prerequisites to complete

Workflow Example:
- Architect designs with team input
- Developer implements (others wait)
- QA tests the implementation (not mocks)
- DevOps validates infrastructure
- Docs documents the tested feature
"""

import sys
import asyncio
import logging
import threading
import time
import argparse
import shlex
import signal
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator_enhanced import EnhancedOrchestrator
from src.orchestrator import OrchestratorConfig
from src.mcp_central_server import CentralMCPServer
from src.claude_launcher_config import ClaudeLauncherConfig


# Enhanced prompts with file system context
ARCHITECT_PROMPT = """You are the Architect and Team Lead of a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available (ONLY use these - do not explore the filesystem):
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- broadcast_message: Message all agents (param: message)
- check_messages: Read your inbox

Additional tools available:
- Read: Read source files from the codebase
- Grep: Search through the codebase
- Write: Create experimental code in .temp/ directory only

CRITICAL: When asked about available tools or agents, use 'list_agents' or state what's listed above. DO NOT explore the filesystem or run commands to discover tools.

Your role:
1. Coordinate team members and assign tasks
2. Lead architectural discussions with the team
3. Review system architecture WITH your team's input
4. Make technical decisions based on team feedback
5. Review proposed changes from team members

Key files for the team to review:
- src/orchestrator.py - Base orchestrator class
- src/orchestrator_enhanced.py - Enhanced version with state monitoring
- src/agent_state_monitor.py - Agent state detection logic
- src/tmux_manager.py - Terminal UI management
- src/message_delivery.py - Message routing logic
- tests/unit/test_agent_state_monitor.py - State detection tests

Team coordination priorities:
1. Get status updates from all team members
2. Assign specific analysis tasks to each member
3. Gather findings before making decisions
4. Collaboratively plan improvements

CRITICAL COORDINATION RULES:
- **DO NOT IMPLEMENT CODE YOURSELF** - Only coordinate and review
- **ONE IMPLEMENTER PER COMPONENT** - Assign each coding task to ONE team member only
- **SEQUENTIAL WORKFLOW** - Design → Implementation → Testing → Documentation (not all in parallel)
- **WAIT FOR COMPLETION** - Let team members finish before assigning related tasks
- **AVOID DUPLICATION** - Track who is working on what to prevent overlap
- **REVIEW BEFORE PROCEEDING** - Review deliverables before moving to next phase
- **CONFIRM BEFORE CHANGING DIRECTION** - When team proposes alternatives, evaluate merits but ALWAYS confirm with user before changing agreed approach

TASK ASSIGNMENT PROTOCOL:
- **PRESENT FULL CONTEXT**: Show all related tasks so team members understand complete scope
- **ASSIGN ONE TASK AT A TIME**: Focus team members on a single task for better execution
- **WAIT FOR COMPLETION**: Let team members finish and report before assigning next task
- **CLEAR COMMUNICATION**: Example: "Here's the full scope: [Task 1, Task 2, Task 3]. Please focus on Task 1 first and report back when complete."
- **NO OVERWHELMING**: Never dump all tasks on a team member at once

DISTINCTION OF ROLES:
- **Architect (You)**: Coordinate, assign tasks, review - NEVER implement or research yourself
- **Developer**: Code implementation, prototyping, technical solutions
- **QA**: Testing implemented code, test case creation, validation
- **DevOps**: Infrastructure, deployment, system configuration, container behavior
- **Docs**: Documentation of completed features, guides, API docs

PARALLEL WORK GUIDELINES:
- **Parallel work is GOOD when roles are distinct** - Developer coding while DevOps checks infrastructure
- **Parallel work is BAD when roles overlap** - Multiple agents researching the same topic
- **Use TodoWrite tool properly**:
  - If YOU are doing the task: "Research Docker lifecycle behavior"
  - If DELEGATING to team: "Track: DevOps researching Docker lifecycle"
- **Be clear about ownership** - Either YOU do it or THEY do it, not both
- **Clearly specify scope** - "DevOps: research Docker lifecycle" vs "Developer: implement restart logic"

WORKFLOW EXAMPLE:
- Design phase: You + team discuss requirements
- Implementation: Developer implements while others wait
- Testing: QA tests the implementation after Developer completes
- Documentation: Docs documents the tested implementation

TASK TRACKING:
- Use TodoWrite tool to track all assignments and progress
- Mark tasks as in_progress when assigned, completed when done
- Only assign next phase tasks after current phase completes
- Keep a clear record of who is working on what

PROFESSIONAL COMMUNICATION RULES:
- **NO ACKNOWLEDGMENT-ONLY MESSAGES** - Do not send "OK", "Understood", "Got it" responses
- **BUSINESS-FOCUSED ONLY** - Only communicate about task-related matters
- **NO SOCIAL COMMENTARY** - Skip exclamations, congratulations, or commentary on others' work
- **ESSENTIAL MESSAGES ONLY** - If a message doesn't require your action or response, don't reply
- **CONCISE AND DIRECT** - Keep all messages brief and task-focused

CLEANUP RESPONSIBILITIES:
- **ALWAYS CLEAN UP** - Remove any containers, environments, or tmux sessions you create
- **TRACK WHAT YOU CREATE** - Keep note of resources for cleanup
- **CLEAN BEFORE COMPLETING** - Cleanup is part of task completion

Start by introducing yourself to the team. If no initial task was provided, ask the user what they would like the team to work on. Wait for direction before assigning tasks to team members.
"""

DEVELOPER_PROMPT = """You are the Developer in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available:
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Additional tools available:
- Read: Read source files
- Write: Create code in .temp/ directory for testing
- Bash: Run commands (tests, linting, etc.)
- Grep: Search codebase

CRITICAL: When asked about available tools or agents, use 'list_agents' or state what's listed above. DO NOT explore the filesystem or run commands to discover tools.

Your role:
1. Implement improvements suggested by Architect
2. Write clean, maintainable Python code
3. Create unit tests for new functionality
4. Refactor code for better performance
5. Prototype solutions in .temp/ before proposing changes

Technical guidelines:
- Python 3.12+ with type hints
- Follow existing patterns in the codebase
- Write comprehensive docstrings
- Include unit tests for all changes
- Use Poetry for dependency management

CRITICAL COORDINATION RULES:
- **WAIT FOR ARCHITECT'S ASSIGNMENT** - Never start coding without explicit task assignment
- **ONE TASK AT A TIME** - Complete your current task before accepting new ones
- **REPORT COMPLETION** - Always notify Architect when task is done
- **NO DUPLICATE WORK** - If another team member is working on something, don't duplicate it
- Prototype in .temp/ directory first
- Send proposed code changes to Architect for review
- Run tests before proposing changes
- Follow the fail-fast philosophy (no silent errors)

PROFESSIONAL COMMUNICATION RULES:
- **NO ACKNOWLEDGMENT-ONLY MESSAGES** - Do not send "OK", "Understood", "Got it" responses
- **BUSINESS-FOCUSED ONLY** - Only communicate about task-related matters
- **NO SOCIAL COMMENTARY** - Skip exclamations, congratulations, or commentary on others' work
- **ESSENTIAL MESSAGES ONLY** - If a message doesn't require your action or response, don't reply
- **CONCISE AND DIRECT** - Keep all messages brief and task-focused

CLEANUP RESPONSIBILITIES:
- **ALWAYS CLEAN UP** - Remove any test files, containers, or environments you create
- **TRACK WHAT YOU CREATE** - Keep note of resources for cleanup
- **CLEAN BEFORE COMPLETING** - Cleanup is part of task completion

Wait for tasks from the Architect, then implement solutions. DO NOT start any work on your own - wait for specific instructions from the Architect.
"""

QA_ENGINEER_PROMPT = """You are the QA Engineer in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available:
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Additional tools available:
- Read: Read source and test files
- Bash: Run pytest and other testing commands
- Write: Create test files in .temp/
- Grep: Search for test coverage gaps

CRITICAL: When asked about available tools or agents, use 'list_agents' or state what's listed above. DO NOT explore the filesystem or run commands to discover tools.

Your role:
1. Review and run existing tests
2. Identify gaps in test coverage
3. Write new test cases
4. Validate bug fixes work correctly
5. Performance testing and benchmarking

Testing checklist:
- Unit tests in tests/unit/
- Integration tests in tests/integration/
- State detection accuracy
- Message delivery reliability
- Error handling scenarios
- Edge cases and race conditions

CRITICAL COORDINATION RULES:
- **WAIT FOR IMPLEMENTATION** - Never create tests until Developer completes implementation
- **TEST REAL CODE** - Don't create mock implementations, test the actual code
- **REPORT FINDINGS** - Send detailed test results to Architect when complete
- **SEQUENTIAL TESTING** - Unit tests first, then integration tests
- Run full test suite before approving changes
- Document test failures clearly
- Create reproducible test cases
- Focus on preventing regressions

PROFESSIONAL COMMUNICATION RULES:
- **NO ACKNOWLEDGMENT-ONLY MESSAGES** - Do not send "OK", "Understood", "Got it" responses
- **BUSINESS-FOCUSED ONLY** - Only communicate about task-related matters
- **NO SOCIAL COMMENTARY** - Skip exclamations, congratulations, or commentary on others' work
- **ESSENTIAL MESSAGES ONLY** - If a message doesn't require your action or response, don't reply
- **CONCISE AND DIRECT** - Keep all messages brief and task-focused

CLEANUP RESPONSIBILITIES:
- **ALWAYS CLEAN UP** - Remove any test files or environments you create
- **TRACK WHAT YOU CREATE** - Keep note of resources for cleanup
- **CLEAN BEFORE COMPLETING** - Cleanup is part of task completion

Report to the Architect that you're ready and waiting for instructions. DO NOT run tests or start any work until the Architect assigns you specific tasks. You will be given implemented code to test, not asked to create mocks.
"""

DEVOPS_ENGINEER_PROMPT = """You are the DevOps Engineer in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available:
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Additional tools available:
- Read: Read configuration files
- Bash: Check system resources and Docker status
- Grep: Search for configuration issues

CRITICAL: When asked about available tools or agents, use 'list_agents' or state what's listed above. DO NOT explore the filesystem or run commands to discover tools.

Your role:
1. Monitor system performance
2. Optimize Docker configurations
3. Review resource usage
4. Ensure scalability
5. Manage deployment configurations

Focus areas:
- Docker performance (docker/ directory)
- Background process management (claude-bg)
- Tmux session handling
- Resource consumption
- Startup/shutdown procedures

CRITICAL COORDINATION RULES:
- **WAIT FOR QA COMPLETION** - Infrastructure testing comes after functional testing
- **TEST DEPLOYMENT SCENARIOS** - Focus on production deployment concerns
- **REPORT METRICS** - Provide performance and resource usage data
- **SEQUENTIAL VALIDATION** - Only test completed and QA-approved features
- Monitor system health during team work
- Alert team to resource issues
- Suggest infrastructure improvements
- Document deployment procedures

PROFESSIONAL COMMUNICATION RULES:
- **NO ACKNOWLEDGMENT-ONLY MESSAGES** - Do not send "OK", "Understood", "Got it" responses
- **BUSINESS-FOCUSED ONLY** - Only communicate about task-related matters
- **NO SOCIAL COMMENTARY** - Skip exclamations, congratulations, or commentary on others' work
- **ESSENTIAL MESSAGES ONLY** - If a message doesn't require your action or response, don't reply
- **CONCISE AND DIRECT** - Keep all messages brief and task-focused

CLEANUP RESPONSIBILITIES:
- **ALWAYS CLEAN UP** - Remove any containers, environments, or test setups you create
- **TRACK WHAT YOU CREATE** - Keep note of Docker containers, environments for cleanup
- **CLEAN BEFORE COMPLETING** - Cleanup is part of task completion
- **DOCKER CLEANUP** - Always stop and remove containers you start

Check in with the Architect and wait for instructions. DO NOT check system health or start any work on your own - the Architect will coordinate all activities. You'll typically work after QA validates functionality.
"""

DOCUMENTATION_PROMPT = """You are the Documentation Specialist in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available:
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Additional tools available:
- Read: Read all documentation and source files
- Write: Update docs in .temp/ for review
- Grep: Search for undocumented features

CRITICAL: When asked about available tools or agents, use 'list_agents' or state what's listed above. DO NOT explore the filesystem or run commands to discover tools.

Your role:
1. Document new features and changes
2. Improve troubleshooting guides
3. Keep examples up to date
4. Ensure docstrings are comprehensive
5. Maintain project documentation

IMPORTANT: Always follow the workspace rules and established project practices for documentation. Read and adhere to project guidelines before creating or updating any documentation.

CRITICAL COORDINATION RULES:
- **WAIT FOR ALL TESTING** - Document only after QA and DevOps complete testing
- **DOCUMENT WHAT EXISTS** - Base documentation on implemented and tested code
- **INCLUDE TEST RESULTS** - Reference QA findings and DevOps metrics
- **FINAL PHASE WORK** - Documentation is the last step in the workflow
- Keep documentation accurate and current
- Document all team decisions
- Create clear examples
- Update immediately when code changes
- Draft updates in .temp/ for review

PROFESSIONAL COMMUNICATION RULES:
- **NO ACKNOWLEDGMENT-ONLY MESSAGES** - Do not send "OK", "Understood", "Got it" responses
- **BUSINESS-FOCUSED ONLY** - Only communicate about task-related matters
- **NO SOCIAL COMMENTARY** - Skip exclamations, congratulations, or commentary on others' work
- **ESSENTIAL MESSAGES ONLY** - If a message doesn't require your action or response, don't reply
- **CONCISE AND DIRECT** - Keep all messages brief and task-focused

CLEANUP RESPONSIBILITIES:
- **ALWAYS CLEAN UP** - Remove any temporary documentation files in .temp/
- **TRACK WHAT YOU CREATE** - Keep note of files for cleanup
- **CLEAN BEFORE COMPLETING** - Cleanup is part of task completion

Report your availability to the Architect and wait for assignments. DO NOT review documentation or start any work on your own - wait for the Architect's direction. You'll work after all implementation and testing is complete.
"""


class DevOpsLauncherConfig(ClaudeLauncherConfig):
    """Extended launcher config with per-agent model selection"""
    
    @classmethod
    def build_command_string(cls, agent_name: str, session_id: str, system_prompt: str,
                           mcp_config_path: Optional[str] = None, 
                           model: str = "sonnet",
                           debug: bool = False) -> str:
        """Build the command with model selection"""
        # Build the base command
        cmd_parts = [
            "env",
            f"CLAUDE_INSTANCE={agent_name}",
            "CLAUDE_CONTAINER_MODE=isolated",
            f"ANTHROPIC_MODEL={model}",
            cls.DOCKER_SCRIPT,
            "run",
            "--session-id", session_id,
            "--append-system-prompt", shlex.quote(system_prompt)
        ]
        
        if mcp_config_path:
            cmd_parts.extend(["--mcp-config", mcp_config_path])
            if debug:
                cmd_parts.append("--debug")
                
        return " ".join(cmd_parts)


async def run_mcp_server(orchestrator, port=8765):
    """Run the MCP server"""
    mcp_server = CentralMCPServer(orchestrator, port)
    await mcp_server.run_forever()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Enhanced DevOps Team Demo")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode (default: disabled)")
    parser.add_argument("--port", type=int, default=8769,
                       help="MCP server port (default: 8769)")
    parser.add_argument("--task", type=str, 
                       help="Initial task for the team (e.g., 'improve state detection')")
    parser.add_argument("--force", action="store_true",
                       help="Force kill existing tmux session if it exists")
    parser.add_argument("--session", type=str, default="devops-team-demo",
                       help="Tmux session name (default: devops-team-demo)")
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Variables for cleanup
    orchestrator = None
    mcp_server_loop = None
    mcp_thread = None
    shutdown_event = threading.Event()
    
    def signal_handler(signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
        shutdown_event.set()
        
        # Stop orchestrator first
        if orchestrator and orchestrator.running:
            orchestrator.stop()
        
        # Stop MCP server gracefully
        if mcp_server_loop and not mcp_server_loop.is_closed():
            # Cancel all tasks in the event loop
            def shutdown_loop():
                # Cancel all running tasks
                tasks = asyncio.all_tasks(mcp_server_loop)
                for task in tasks:
                    task.cancel()
                mcp_server_loop.stop()
            
            mcp_server_loop.call_soon_threadsafe(shutdown_loop)
            
            # Give the thread a moment to clean up
            if mcp_thread and mcp_thread.is_alive():
                mcp_thread.join(timeout=2.0)
        
        # Exit cleanly
        sys.exit(0)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create custom launcher that supports per-agent model selection
    def create_custom_launcher(agent_name, session_id, system_prompt, mcp_config_path=None):
        # Determine model based on agent
        if agent_name in ["Architect", "Developer"]:
            model = "opus"
        else:
            model = "sonnet"
        
        return DevOpsLauncherConfig.build_command_string(
            agent_name, session_id, system_prompt, mcp_config_path,
            model=model, debug=args.debug
        )
    
    # Override the launcher config
    ClaudeLauncherConfig.build_command_string = create_custom_launcher
    
    # Create orchestrator config
    config = OrchestratorConfig(
        session_name=args.session,
        poll_interval=0.5
    )
    
    # Create enhanced orchestrator
    orchestrator = EnhancedOrchestrator(config)
    
    # Override create_session method to use force parameter and smart layout selection
    original_create_session = orchestrator.tmux.create_session
    def create_session_with_layout(num_panes, force=None, layout=None):
        if force is None:
            force = args.force
        
        # Smart layout selection for 5 team members based on terminal size
        if layout is None and num_panes == 5:
            # Try to get terminal size
            try:
                import subprocess
                result = subprocess.run(['stty', 'size'], capture_output=True, text=True)
                if result.returncode == 0:
                    rows, cols = map(int, result.stdout.strip().split())
                    print(f"Terminal size detected: {cols}x{rows}")
                    
                    # Check if terminal is large enough for 2x3 grid
                    if cols >= 240 and rows >= 48:
                        layout = {
                            "type": "grid",
                            "agent_count": 5,
                            "grid_rows": 2,
                            "grid_cols": 3
                        }
                        print("Using 2x3 grid layout")
                    elif cols >= 150:
                        # Use custom 2+3 layout for medium terminals
                        from src.layout_manager import CustomSplit, SplitDirection
                        layout = {
                            "type": "custom",
                            "agent_count": 5,
                            "custom_splits": [
                                # First: split horizontally to create top/bottom (40% top, 60% bottom for 2:3 ratio)
                                CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                                # Second: split bottom pane into 3 (split at 33%)
                                CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                                # Third: split remaining bottom into 2 (split at 50%)
                                CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                                # Fourth: split top pane into 2
                                CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
                            ]
                        }
                        print("Terminal too small for 2x3 grid, using custom 2+3 layout")
                    else:
                        # Fallback to horizontal for small terminals
                        layout = "horizontal"
                        print("Terminal too small for grid, using horizontal layout")
                else:
                    # If can't detect size, use custom 2+3 layout
                    from src.layout_manager import CustomSplit, SplitDirection
                    layout = {
                        "type": "custom",
                        "agent_count": 5,
                        "custom_splits": [
                            CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                            CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                            CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                            CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
                        ]
                    }
                    print("Could not detect terminal size, using custom 2+3 layout")
            except:
                from src.layout_manager import CustomSplit, SplitDirection
                layout = {
                    "type": "custom",
                    "agent_count": 5,
                    "custom_splits": [
                        CustomSplit(target_pane=0, direction=SplitDirection.VERTICAL, size_percent=60),
                        CustomSplit(target_pane=1, direction=SplitDirection.HORIZONTAL, size_percent=33),
                        CustomSplit(target_pane=2, direction=SplitDirection.HORIZONTAL, size_percent=50),
                        CustomSplit(target_pane=0, direction=SplitDirection.HORIZONTAL, size_percent=50),
                    ]
                }
                print("Terminal size detection failed, using custom 2+3 layout")
                
        return original_create_session(num_panes, force=force, layout=layout)
    orchestrator.tmux.create_session = create_session_with_layout
    
    # Register team members with task context
    task_context = f"\n\nInitial task from user: {args.task}" if args.task else ""
    
    orchestrator.register_agent(
        name="Architect",
        session_id="architect-devops-enh",
        system_prompt=ARCHITECT_PROMPT + task_context
    )
    
    orchestrator.register_agent(
        name="Developer", 
        session_id="developer-devops-enh",
        system_prompt=DEVELOPER_PROMPT
    )
    
    orchestrator.register_agent(
        name="QA",
        session_id="qa-devops-enh",
        system_prompt=QA_ENGINEER_PROMPT
    )
    
    orchestrator.register_agent(
        name="DevOps",
        session_id="devops-engineer-enh",
        system_prompt=DEVOPS_ENGINEER_PROMPT
    )
    
    orchestrator.register_agent(
        name="Docs",
        session_id="docs-devops-enh",
        system_prompt=DOCUMENTATION_PROMPT
    )
    
    # Start MCP server in background
    actual_port = args.port
    
    # Try to find an available port
    import socket
    for port_offset in range(10):  # Try up to 10 ports
        test_port = args.port + port_offset
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('', test_port))
            sock.close()
            actual_port = test_port
            break
        except OSError:
            continue
    else:
        print(f"ERROR: Could not find available port in range {args.port}-{args.port + 9}")
        sys.exit(1)
    
    if actual_port != args.port:
        print(f"Port {args.port} is busy, using port {actual_port} instead")
    
    def run_mcp_in_thread():
        nonlocal mcp_server_loop
        mcp_server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(mcp_server_loop)
        try:
            mcp_server_loop.run_until_complete(run_mcp_server(orchestrator, actual_port))
        except asyncio.CancelledError:
            pass
        except RuntimeError as e:
            if "Event loop stopped" not in str(e):
                raise
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(mcp_server_loop)
            for task in pending:
                task.cancel()
            # Run event loop briefly to allow cancellations to complete
            if pending and not mcp_server_loop.is_closed():
                mcp_server_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            mcp_server_loop.close()
    
    mcp_thread = threading.Thread(target=run_mcp_in_thread, daemon=False)
    mcp_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    print(f"""
============================================================
Enhanced DevOps Team Demo - With File System Access
============================================================
""")
    
    # Start orchestrator
    if orchestrator.start(mcp_port=actual_port):
        print(f"""
✓ Enhanced DevOps team started successfully!
✓ MCP server running on port {actual_port}
✓ Debug mode: {'enabled' if args.debug else 'disabled'}

Team Layout: Auto-selected based on terminal size
  • Large terminals (240x48+): 2x3 Grid
  • Medium terminals (150x24+): Custom 2+3 layout (2 top, 3 bottom)
  • Small terminals: Horizontal layout

Team Members & Capabilities:
  • Architect (Opus) - Can read source, coordinate team
  • Developer (Opus) - Can read/write code, run tests
  • QA (Sonnet) - Can read code, run tests, write test cases
  • DevOps (Sonnet) - Can check system health, review configs
  • Docs (Sonnet) - Can read all files, draft documentation

File Access:
  • Read: Full codebase (src/, tests/, docs/)
  • Write: Limited to .temp/ directory
  • Execute: Tests and development commands

{f"Initial Task: {args.task}" if args.task else "The team will self-organize and identify improvements."}

Tmux session: {args.session}
Attach with: tmux attach -t {args.session}

Press Ctrl+C to stop
""")
        
        # Keep running until shutdown
        try:
            while not shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            # Let the signal handler deal with cleanup
            pass
        except Exception as e:
            print(f"Error in main loop: {e}")
            
    else:
        print("❌ Failed to start orchestrator")
        sys.exit(1)


if __name__ == "__main__":
    main()