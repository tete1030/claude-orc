#!/usr/bin/env python3
"""
Pure MCP Team Demo - Demonstrates clean MCP-only multi-agent system

This example shows:
- No XML commands at all
- Pure MCP tool-based communication
- Minimal orchestrator for MCP-only operation
- Team collaboration: Leader, Researcher, and Writer agents
- Session persistence support
"""

import sys
import os
import asyncio
import logging
import threading
import time
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import Orchestrator, OrchestratorConfig
from src.mcp_central_server import CentralMCPServer
from src.session_manager import SessionManager, AgentInfo


# Team member prompts
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

IMPORTANT: You must use the MCP tools provided. Do not try to use other tools or commands.

Start by:
1. Use list_agents to see your team
2. Use send_message to assign a simple research task to the Researcher
3. Use check_messages periodically to see responses
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

IMPORTANT: You must use the MCP tools provided. Do not try to use other tools or commands.

Start by using check_messages to see if you have any research requests.
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

IMPORTANT: You must use the MCP tools provided. Do not try to use other tools or commands.

Start by using check_messages to see if you have any writing tasks.
"""


async def run_mcp_server(orchestrator, port=8765):
    """Run the MCP server"""
    mcp_server = CentralMCPServer(orchestrator, port)
    await mcp_server.run_forever()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Team MCP Demo")
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
    logging.basicConfig(
        level=logging.INFO,
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
    
    # Create orchestrator config
    config = OrchestratorConfig(
        session_name=args.session,
        poll_interval=0.5
    )
    
    # Create orchestrator
    orchestrator = Orchestrator(config)
    
    # Override launcher to set container names if session provided
    if args.session_name:
        from src.claude_launcher_config import ClaudeLauncherConfig
        original_build = ClaudeLauncherConfig.build_command_string
        def patched_build(agent_name, session_id, system_prompt, mcp_config_path=None):
            # Set container name based on session
            container_suffix = agent_name.lower().replace(" ", "-")
            os.environ['CLAUDE_INSTANCE'] = f"{args.session_name}-{container_suffix}"
            return original_build(agent_name, session_id, system_prompt, mcp_config_path)
        ClaudeLauncherConfig.build_command_string = patched_build
    
    # Override create_session method to use force parameter
    original_create_session = orchestrator.tmux.create_session
    def create_session_with_force(num_panes, force=None):
        if force is None:
            force = args.force
        return original_create_session(num_panes, force=force)
    orchestrator.tmux.create_session = create_session_with_force
    
    # Register team members
    # Update session IDs if using named session
    leader_id = f"{args.session_name}-leader" if args.session_name else "leader-01"
    researcher_id = f"{args.session_name}-researcher" if args.session_name else "researcher-01"
    writer_id = f"{args.session_name}-writer" if args.session_name else "writer-01"
    
    # Container mode always isolated for this demo
    os.environ['CLAUDE_CONTAINER_MODE'] = 'isolated'
    
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
    
    # Start MCP server in background
    mcp_port = 8766  # Changed from 8765 to avoid conflicts
    mcp_server_loop = None
    
    def run_mcp_in_thread():
        nonlocal mcp_server_loop
        mcp_server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(mcp_server_loop)
        try:
            mcp_server_loop.run_until_complete(run_mcp_server(orchestrator, mcp_port))
        except asyncio.CancelledError:
            pass
    
    mcp_thread = threading.Thread(target=run_mcp_in_thread, daemon=True)
    mcp_thread.start()
    
    # Give MCP server time to start
    time.sleep(2)
    
    # Start orchestrator with MCP
    print("\n" + "="*60)
    print("Team MCP Demo - Collaborative AI Agents")
    print("="*60)
    
    try:
        if orchestrator.start(mcp_port=mcp_port):
            # Register session if session name provided and not resuming
            if args.session_name and not args.resume:
                # Build agent info list
                container_prefix = "ccbox-" + args.session_name
                agents_info = [
                    AgentInfo(
                        name="Leader",
                        container=f"{container_prefix}-leader",
                        model="sonnet",
                        container_mode="isolated"
                    ),
                    AgentInfo(
                        name="Researcher",
                        container=f"{container_prefix}-researcher",
                        model="sonnet",
                        container_mode="isolated"
                    ),
                    AgentInfo(
                        name="Writer",
                        container=f"{container_prefix}-writer",
                        model="sonnet",
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
                        "mcp_port": mcp_port
                    }
                )
                print(f"\n✓ Session '{args.session_name}' registered with {len(agents_info)} agents")
            
            print(f"\n✓ Orchestrator started successfully!")
            print(f"✓ MCP server running on port {mcp_port}")
            print(f"✓ 3 agents: Leader, Researcher, Writer")
            if args.session_name:
                print(f"✓ Session: {args.session_name}")
            
            print(f"\nTmux session: {args.session}")
            print(f"Attach with: tmux attach -t {args.session}")
            
            print("\nAgent Team:")
            print("  • Leader - Coordinates the team")
            print("  • Researcher - Finds information")
            print("  • Writer - Creates content")
            
            print("\nMCP Tools Available:")
            print("  • list_agents - See all team members")
            print("  • send_message - Send messages to specific agents")
            print("  • check_messages - Check mailbox for messages")
            print("  • broadcast_message - Message all agents")
            
            print("\nExpected behavior:")
            print("  1. Leader will list agents and see the team")
            print("  2. Leader will delegate a research task")
            print("  3. Researcher will complete the task and report back")
            print("  4. Leader may ask Writer to create content based on research")
            
            # Send initial prompts to kickstart the team
            print("\nSending initial prompts to team members...")
            time.sleep(3)  # Wait for agents to initialize
            
            # Send welcome message to Leader
            orchestrator.send_to_agent("Leader", 
                "Welcome Leader! Your team is ready. Use the list_agents tool to see who's available, " +
                "then assign a simple research task to the Researcher.")
            
            # Send ready messages to other agents
            orchestrator.send_to_agent("Researcher", 
                "Welcome Researcher! You're part of a team. Use check_messages regularly to see if you have tasks.")
            
            orchestrator.send_to_agent("Writer", 
                "Welcome Writer! You're part of a team. Use check_messages regularly to see if you have tasks.")
            
            print("✓ Initial prompts sent")
            
            print("\nPress Ctrl+C to stop\n")
            
            while True:
                time.sleep(1)
        else:
            print("Failed to start orchestrator!")
            return 1
            
    except KeyboardInterrupt:
        # Clean shutdown without stack trace
        print("\n\nShutting down gracefully...")
    finally:
        # Always clean up
        orchestrator.stop()
        if mcp_server_loop:
            mcp_server_loop.call_soon_threadsafe(mcp_server_loop.stop)
        print("✓ Cleanup complete")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Catch any remaining KeyboardInterrupt to prevent stack trace
        sys.exit(0)