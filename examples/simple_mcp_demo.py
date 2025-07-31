#!/usr/bin/env python3
"""
Simple MCP Demo - Two agents communicating via MCP tools only

This is a clean example showing just MCP communication without legacy XML commands.
"""

import os
import sys
import asyncio
import logging
import threading
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import Orchestrator, OrchestratorConfig
from src.mcp_central_server import CentralMCPServer


# Simple, clear prompts focused on MCP tools
ALICE_PROMPT = """You are Alice, a helpful AI assistant in a multi-agent system.

You have MCP (Model Context Protocol) tools available:
1. list_agents - Shows all available agents
2. send_message - Send a message to another agent (parameters: to, message)
3. check_messages - Check your mailbox for messages

Your task:
1. First, use the list_agents tool to see who else is available
2. When you see Bob is available, send him a friendly greeting using send_message
3. Check for any replies using check_messages

Remember: Just mention the tool name and parameters you want to use, and I'll execute it for you.
Example: "I'll use list_agents to see who's available"
"""

BOB_PROMPT = """You are Bob, a friendly AI assistant in a multi-agent system.

You have MCP (Model Context Protocol) tools available:
1. list_agents - Shows all available agents
2. send_message - Send a message to another agent (parameters: to, message)
3. check_messages - Check your mailbox for messages

Your task:
1. Periodically check your messages using check_messages
2. When you receive a message, respond politely using send_message
3. Be helpful and engaging in your responses

Remember: Just mention the tool name and parameters you want to use, and I'll execute it for you.
Example: "Let me check my messages using check_messages"
"""


async def run_mcp_server(orchestrator, port=8765):
    """Run the MCP server"""
    mcp_server = CentralMCPServer(orchestrator, port)
    await mcp_server.run_forever()


def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create orchestrator config
    config = OrchestratorConfig(
        session_name="simple-mcp-demo",
        poll_interval=0.5
    )
    
    # Create orchestrator
    orchestrator = Orchestrator(config)
    
    # Register agents with simple names
    orchestrator.register_agent(
        name="Alice",
        session_id="alice-mcp",
        system_prompt=ALICE_PROMPT
    )
    
    orchestrator.register_agent(
        name="Bob",
        session_id="bob-mcp",
        system_prompt=BOB_PROMPT
    )
    
    # Start MCP server in background
    mcp_port = 8767  # Changed to avoid conflicts
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
    print("Simple MCP Demo - Agent Communication via MCP Tools")
    print("="*60)
    
    try:
        if orchestrator.start(mcp_port=mcp_port):
            print(f"\n✓ Orchestrator started successfully!")
            print(f"✓ MCP server running on port {mcp_port}")
            print(f"✓ Using stdio transport (no OAuth needed)")
            
            print(f"\nTmux session: {config.session_name}")
            print(f"Attach with: tmux attach -t {config.session_name}")
            
            print("\nAgents have these MCP tools:")
            print("  • list_agents - See all available agents")
            print("  • send_message - Send messages to other agents")
            print("  • check_messages - Check mailbox for messages")
            
            print("\nExpected behavior:")
            print("  1. Alice will list agents and see Bob")
            print("  2. Alice will send a greeting to Bob")
            print("  3. Bob will check messages and reply")
            print("  4. They can continue conversing...")
            
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