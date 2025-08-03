#!/usr/bin/env python3
"""
Enhanced Team MCP Demo - Team collaboration with intelligent message delivery

Features:
- Agent state monitoring (busy/idle detection)
- Intelligent message delivery (queues messages when agents are busy)
- Non-vim mode support for direct input
- Configurable model selection
- Debug mode disabled by default
"""

import sys
import os
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
from src.session_manager import SessionManager, AgentInfo


# Team member prompts - Updated to NOT tell agents to check messages regularly
LEADER_PROMPT = """You are the Leader agent in a collaborative AI team.

MCP tools available:
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- broadcast_message: Message all agents (param: message)
- check_messages: Read your inbox

Your role:
1. Coordinate the team
2. Delegate tasks to specialists
3. Synthesize results

IMPORTANT RULES:
- You must ONLY use the MCP tools provided above
- Do NOT use Bash, Read, Write, or any file system tools
- Do NOT try to debug, fix, or run any Python scripts
- Do NOT attempt to install packages or modify the system
- If MCP tools are not working, simply report the issue and wait

Start by using list_agents to see your team, then delegate a task to the Researcher.
"""

RESEARCHER_PROMPT = """You are the Researcher agent - a specialist in finding information.

MCP tools available:
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Your role:
1. Research topics when asked
2. Provide detailed, accurate information
3. Report findings back to the Leader

IMPORTANT RULES:
- You must ONLY use the MCP tools provided above
- Do NOT use Bash, Read, Write, or any file system tools
- Do NOT try to debug, fix, or run any Python scripts
- Do NOT attempt to install packages or modify the system
- If MCP tools are not working, simply report the issue and wait
"""

WRITER_PROMPT = """You are the Writer agent - a specialist in creating content.

MCP tools available:
- list_agents: See all team members
- send_message: Communicate with specific agents (params: to, message)
- check_messages: Read your inbox

Your role:
1. Create content based on requests
2. Edit and refine text
3. Report completed work back to the Leader

IMPORTANT RULES:
- You must ONLY use the MCP tools provided above
- Do NOT use Bash, Read, Write, or any file system tools
- Do NOT try to debug, fix, or run any Python scripts
- Do NOT attempt to install packages or modify the system
- If MCP tools are not working, simply report the issue and wait
"""


class EnhancedClaudeLauncherConfig(ClaudeLauncherConfig):
    """Extended launcher config with model selection and debug control"""
    
    @classmethod
    def build_command_string(cls, agent_name: str, session_id: str, system_prompt: str,
                           mcp_config_path: Optional[str] = None, 
                           model: str = "sonnet",
                           debug: bool = False) -> str:
        """Build the command with model selection and debug control"""
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
    parser = argparse.ArgumentParser(description="Enhanced Team MCP Demo")
    parser.add_argument("--model", default="sonnet",
                       help="Claude model to use (default: Sonnet)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode (default: disabled)")
    parser.add_argument("--port", type=int, default=8766,
                       help="MCP server port (default: 8766)")
    parser.add_argument("--force", action="store_true",
                       help="Force kill existing tmux session if it exists")
    parser.add_argument("--session", type=str, default="team-mcp-demo",
                       help="Tmux session name (default: team-mcp-demo)")
    parser.add_argument("--session-name", type=str,
                       help="Name for this team session (for container tracking)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume an existing session with persistent containers")
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize session manager
    session_manager = SessionManager()
    team_session = None
    
    # Handle session resume or creation
    if args.resume and args.session_name:
        print(f"Resuming session: {args.session_name}")
        try:
            team_session = session_manager.resume_session(args.session_name)
            # Override settings from saved session
            args.session = team_session.tmux_session
            print(f"Resumed session with tmux: {args.session}")
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    elif args.resume and not args.session_name:
        print("ERROR: --resume requires --session-name")
        sys.exit(1)
    
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
    
    # Override the launcher config
    original_build = ClaudeLauncherConfig.build_command_string
    def patched_build(agent_name, session_id, system_prompt, mcp_config_path=None):
        # Set container name based on session if provided
        if args.session_name:
            container_suffix = agent_name.lower().replace(" ", "-")
            os.environ['CLAUDE_INSTANCE'] = f"{args.session_name}-{container_suffix}"
        
        return EnhancedClaudeLauncherConfig.build_command_string(
            agent_name, session_id, system_prompt, mcp_config_path,
            model=args.model, debug=args.debug
        )
    ClaudeLauncherConfig.build_command_string = patched_build
    
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
    # Update session IDs if using named session
    leader_id = f"{args.session_name}-leader" if args.session_name else "leader-mcp"
    researcher_id = f"{args.session_name}-researcher" if args.session_name else "researcher-mcp"
    writer_id = f"{args.session_name}-writer" if args.session_name else "writer-mcp"
    
    orchestrator.register_agent(
        name="Leader",
        session_id=leader_id,
        system_prompt=LEADER_PROMPT
    )
    
    orchestrator.register_agent(
        name="Researcher", 
        session_id=researcher_id,
        system_prompt=RESEARCHER_PROMPT
    )
    
    orchestrator.register_agent(
        name="Writer",
        session_id=writer_id, 
        system_prompt=WRITER_PROMPT
    )
    
    # Start MCP server in background with automatic port adjustment
    mcp_server_loop = None
    mcp_thread = None
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
Enhanced Team MCP Demo - Collaborative AI Agents
============================================================
""")
    
    # Start orchestrator
    if orchestrator.start(mcp_port=actual_port):
        # Register session if session name provided and not resuming
        if args.session_name and not args.resume:
            # Build agent info list for basic demo
            container_prefix = "ccbox-" + args.session_name
            agents_info = [
                AgentInfo(
                    name="Leader",
                    container=f"{container_prefix}-leader",
                    model=args.model,
                    container_mode="isolated"
                ),
                AgentInfo(
                    name="Researcher",
                    container=f"{container_prefix}-researcher",
                    model=args.model,
                    container_mode="isolated"
                ),
                AgentInfo(
                    name="Writer",
                    container=f"{container_prefix}-writer",
                    model=args.model,
                    container_mode="isolated"
                )
            ]
            
            # Create session in registry
            team_session = session_manager.create_session(
                session_name=args.session_name,
                agents=agents_info,
                tmux_session=args.session,
                orchestrator_config={
                    "poll_interval": config.poll_interval,
                    "mcp_port": actual_port,
                    "debug": args.debug,
                    "model": args.model
                }
            )
            print(f"\n✓ Session '{args.session_name}' registered with {len(agents_info)} agents")
        
        print(f"""
✓ Enhanced orchestrator started successfully!
✓ MCP server running on port {actual_port}
✓ Model: {args.model}
✓ Debug mode: {'enabled' if args.debug else 'disabled'}
✓ Agent state monitoring: enabled
✓ Intelligent message delivery: enabled
{f"✓ Session: {args.session_name}" if args.session_name else ""}

Team Members:
  • Leader - Coordinates the team
  • Researcher - Finds information  
  • Writer - Creates content

Tmux session: {args.session}
Attach with: tmux attach -t {args.session}

Enhanced Features:
  • Messages are queued when agents are busy
  • Agents are notified when they become idle
  • Direct input support (non-vim mode)
  • Real-time state monitoring

To send a test message from orchestrator:
  1. Wait for agents to initialize
  2. Run: orchestrator.send_direct_input("Leader", "list_agents")
  3. Or: orchestrator.send_message_to_agent("Researcher", "Leader", "Please research AI trends")

Press Ctrl+C to stop
""")
        
        # Demo: Show agent states periodically
        def show_states():
            while orchestrator.running:
                time.sleep(10)
                states = orchestrator.get_all_agent_states()
                if states:
                    print(f"\nAgent States: {states}")
                    
        state_thread = threading.Thread(target=show_states, daemon=True)
        state_thread.start()
        
        try:
            # Keep running until shutdown
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