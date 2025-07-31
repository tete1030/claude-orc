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
import asyncio
import logging
import threading
import time
import argparse
import shlex
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator_enhanced import EnhancedOrchestrator
from src.orchestrator import OrchestratorConfig
from src.mcp_central_server import CentralMCPServer
from src.claude_launcher_config import ClaudeLauncherConfig


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

IMPORTANT: You must use the MCP tools provided. Do not try to use other tools or commands.

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

IMPORTANT: You must use the MCP tools provided. Do not try to use other tools or commands.
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
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Override the launcher config
    original_build = ClaudeLauncherConfig.build_command_string
    def patched_build(agent_name, session_id, system_prompt, mcp_config_path=None):
        return EnhancedClaudeLauncherConfig.build_command_string(
            agent_name, session_id, system_prompt, mcp_config_path,
            model=args.model, debug=args.debug
        )
    ClaudeLauncherConfig.build_command_string = patched_build
    
    # Create orchestrator config
    config = OrchestratorConfig(
        session_name="team-mcp-demo",
        poll_interval=0.5
    )
    
    # Create enhanced orchestrator
    orchestrator = EnhancedOrchestrator(config)
    
    # Register team members
    orchestrator.register_agent(
        name="Leader",
        session_id="leader-mcp",
        system_prompt=LEADER_PROMPT
    )
    
    orchestrator.register_agent(
        name="Researcher", 
        session_id="researcher-mcp",
        system_prompt=RESEARCHER_PROMPT
    )
    
    orchestrator.register_agent(
        name="Writer",
        session_id="writer-mcp", 
        system_prompt=WRITER_PROMPT
    )
    
    # Start MCP server in background
    mcp_server_loop = None
    mcp_thread = None
    
    def run_mcp_in_thread():
        nonlocal mcp_server_loop
        mcp_server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(mcp_server_loop)
        try:
            mcp_server_loop.run_until_complete(run_mcp_server(orchestrator, args.port))
        except asyncio.CancelledError:
            pass
    
    mcp_thread = threading.Thread(target=run_mcp_in_thread, daemon=True)
    mcp_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    print(f"""
============================================================
Enhanced Team MCP Demo - Collaborative AI Agents
============================================================
""")
    
    # Start orchestrator
    if orchestrator.start(mcp_port=args.port):
        print(f"""
✓ Enhanced orchestrator started successfully!
✓ MCP server running on port {args.port}
✓ Model: {args.model}
✓ Debug mode: {'enabled' if args.debug else 'disabled'}
✓ Agent state monitoring: enabled
✓ Intelligent message delivery: enabled

Team Members:
  • Leader - Coordinates the team
  • Researcher - Finds information  
  • Writer - Creates content

Tmux session: team-mcp-demo
Attach with: tmux attach -t team-mcp-demo

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
            # Keep running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            
        # Cleanup
        orchestrator.stop()
        if mcp_server_loop:
            mcp_server_loop.call_soon_threadsafe(mcp_server_loop.stop)
            
    else:
        print("❌ Failed to start orchestrator")
        sys.exit(1)


if __name__ == "__main__":
    main()