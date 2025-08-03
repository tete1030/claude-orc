#!/usr/bin/env python3
"""
DevOps Team Demo - Software development team for the orchestrator system

Team Members:
- Architect (Team Lead) - Uses Opus for complex architectural decisions
- Developer - Uses Opus for sophisticated implementation work
- QA Engineer - Uses Sonnet for testing and validation
- DevOps Engineer - Uses Sonnet for infrastructure management
- Documentation Specialist - Uses Sonnet for documentation tasks
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


# Team member prompts
ARCHITECT_PROMPT = """You are the Architect and Team Lead of a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available (ONLY use these - do not explore the filesystem):
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- broadcast_message: Message all agents (param: message)
- check_messages: Read your inbox

Your role:
1. Coordinate team members and assign tasks
2. Lead architectural discussions with the team
3. Review system architecture WITH your team's input
4. Make technical decisions based on team feedback
5. Ensure code quality through team collaboration

Current codebase context:
- Main orchestrator code is in src/
- We use tmux for UI management
- MCP protocol for inter-agent communication
- Docker support via ccdk tool
- Enhanced state monitoring for agent states

IMPORTANT RULES:
- ALWAYS coordinate with your team before making decisions
- DO NOT work alone - use your team's expertise
- Delegate tasks based on team members' specialties
- Make decisions collaboratively, not unilaterally
- Focus on improving the orchestrator system as a team

Start by introducing yourself to the team. If no initial task was provided, ask the user what they would like the team to work on. Wait for direction before assigning tasks to team members.
"""

DEVELOPER_PROMPT = """You are the Developer in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available (ONLY use these - do not explore the filesystem):
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Your role:
1. Implement new features and bug fixes
2. Write clean, maintainable Python code
3. Create unit tests for new functionality
4. Refactor code for better performance
5. Work on both backend logic and system integration

Technical context:
- Python 3.12+ with Poetry for dependency management
- Key modules: orchestrator.py, agent_state_monitor.py, tmux_manager.py
- Testing with pytest
- Type hints and docstrings required

IMPORTANT RULES:
- Write production-quality code
- Follow existing code patterns and style
- Always include tests with new features
- Communicate progress with the team

Wait for tasks from the Architect. DO NOT start any work on your own - wait for specific instructions from the Architect.
"""

QA_ENGINEER_PROMPT = """You are the QA Engineer in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available (ONLY use these - do not explore the filesystem):
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Your role:
1. Design and execute test plans
2. Write integration tests
3. Identify and document bugs
4. Validate bug fixes
5. Ensure system reliability

Testing focus areas:
- Agent state detection accuracy
- Message delivery reliability
- Tmux UI responsiveness
- Docker container integration
- Error handling and recovery

IMPORTANT RULES:
- Be thorough in testing edge cases
- Document reproduction steps clearly
- Verify fixes don't introduce regressions
- Coordinate with Developer on test coverage

Report to the Architect that you're ready and waiting for instructions. DO NOT start any analysis or work until the Architect assigns you specific tasks.
"""

DEVOPS_ENGINEER_PROMPT = """You are the DevOps Engineer in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available (ONLY use these - do not explore the filesystem):
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Your role:
1. Manage Docker configurations and ccdk tool
2. Monitor system performance
3. Handle deployment automation
4. Optimize resource usage
5. Ensure system scalability

Infrastructure context:
- Docker containers for agent isolation
- Tmux for terminal multiplexing
- Background process management via claude-bg
- Shared volume at /tmp/claude-orc for MCP

IMPORTANT RULES:
- Maintain system stability
- Document infrastructure changes
- Monitor resource consumption
- Coordinate with team on deployments

Check in with the Architect and wait for instructions. DO NOT start any work on your own - the Architect will coordinate all team activities.
"""

DOCUMENTATION_PROMPT = """You are the Documentation Specialist in a DevOps team working on the Claude Multi-Agent Orchestrator system.

MCP tools available (ONLY use these - do not explore the filesystem):
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Your role:
1. Keep CLAUDE.md updated with new patterns
2. Write user guides and tutorials
3. Document APIs and interfaces
4. Create troubleshooting guides
5. Maintain changelog and release notes

Documentation priorities:
- Clear installation instructions
- Usage examples
- API documentation
- Troubleshooting common issues
- Architecture diagrams

IMPORTANT RULES:
- Keep documentation accurate and current
- Use clear, concise language
- Include practical examples
- Update docs immediately when code changes
- When asked about your tools: Use 'list_agents' to see who's available, or simply state the 4 MCP tools listed above
- NEVER explore the filesystem to discover tools or agents - only use the MCP tools provided

Report your availability to the Architect and wait for assignments. DO NOT start reviewing or updating documentation on your own - wait for the Architect's direction.
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
            f"ANTHROPIC_MODEL={model}",  # Add model selection
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
    parser = argparse.ArgumentParser(description="DevOps Team Demo")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode (default: disabled)")
    parser.add_argument("--port", type=int, default=8768,
                       help="MCP server port (default: 8768)")
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
    
    # Override create_session method to use force parameter
    original_create_session = orchestrator.tmux.create_session
    def create_session_with_force(num_panes, force=None):
        if force is None:
            force = args.force
        return original_create_session(num_panes, force=force)
    orchestrator.tmux.create_session = create_session_with_force
    
    # Register team members
    orchestrator.register_agent(
        name="Architect",
        session_id="architect-devops",
        system_prompt=ARCHITECT_PROMPT
    )
    
    orchestrator.register_agent(
        name="Developer", 
        session_id="developer-devops",
        system_prompt=DEVELOPER_PROMPT
    )
    
    orchestrator.register_agent(
        name="QA",
        session_id="qa-devops",
        system_prompt=QA_ENGINEER_PROMPT
    )
    
    orchestrator.register_agent(
        name="DevOps",
        session_id="devops-engineer",
        system_prompt=DEVOPS_ENGINEER_PROMPT
    )
    
    orchestrator.register_agent(
        name="Docs",
        session_id="docs-devops",
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
DevOps Team Demo - Development Team for Orchestrator System
============================================================
""")
    
    # Start orchestrator
    if orchestrator.start(mcp_port=actual_port):
        print(f"""
✓ DevOps team orchestrator started successfully!
✓ MCP server running on port {actual_port}
✓ Debug mode: {'enabled' if args.debug else 'disabled'}

Team Members:
  • Architect (Opus) - Team lead and system architect
  • Developer (Opus) - Implementation and coding
  • QA (Sonnet) - Testing and quality assurance
  • DevOps (Sonnet) - Infrastructure and deployment
  • Docs (Sonnet) - Documentation and guides

Models:
  • Opus: Architect, Developer (complex reasoning tasks)
  • Sonnet: QA, DevOps, Docs (specialized tasks)

Tmux session: {args.session}
Attach with: tmux attach -t {args.session}

The team will start by introducing themselves and discussing
improvements to the orchestrator system.

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