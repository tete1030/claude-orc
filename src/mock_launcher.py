#!/usr/bin/env python3
"""
Mock launcher for testing orchestrator without Claude authentication.
Simulates agents that use MCP tools.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Any, Optional
import aiohttp
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.mcp_thin_proxy import MCPThinProxy


class MockAgent:
    """Mock agent that simulates Claude behavior with MCP tools"""
    
    def __init__(self, name: str, orchestrator_url: str, system_prompt: str):
        self.name = name
        self.orchestrator_url = orchestrator_url
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(f"MockAgent.{name}")
        self.running = False
        
    async def start(self):
        """Start the mock agent"""
        self.running = True
        self.logger.info(f"Mock agent {self.name} started")
        self.logger.info(f"System prompt: {self.system_prompt[:100]}...")
        
        # Simulate agent behavior based on prompt
        if "list_agents" in self.system_prompt:
            await self._list_agents()
        
        if "send_message" in self.system_prompt:
            await self._simulate_messaging()
            
        if "check_messages" in self.system_prompt:
            await self._check_messages()
            
    async def _list_agents(self):
        """Simulate listing agents"""
        await asyncio.sleep(2)  # Simulate thinking
        self.logger.info(f"{self.name}: Using list_agents tool...")
        
        # Call MCP server
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "list_agents",
                        "arguments": {}
                    },
                    "id": "mock-1"
                }
                
                async with session.post(
                    f"{self.orchestrator_url}/mcp/{self.name}",
                    json=payload,
                    headers={"X-Agent-Name": self.name}
                ) as resp:
                    result = await resp.json()
                    self.logger.info(f"{self.name} received: {result}")
                    
        except Exception as e:
            self.logger.error(f"Error calling list_agents: {e}")
            
    async def _send_message(self, to: str, message: str):
        """Send a message to another agent"""
        self.logger.info(f"{self.name}: Sending message to {to}: {message}")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "send_message",
                        "arguments": {
                            "to": to,
                            "message": message
                        }
                    },
                    "id": f"mock-send-{time.time()}"
                }
                
                async with session.post(
                    f"{self.orchestrator_url}/mcp/{self.name}",
                    json=payload,
                    headers={"X-Agent-Name": self.name}
                ) as resp:
                    result = await resp.json()
                    self.logger.info(f"{self.name} send result: {result}")
                    
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            
    async def _check_messages(self):
        """Check for messages"""
        while self.running:
            await asyncio.sleep(3)  # Check every 3 seconds
            
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "check_messages",
                            "arguments": {}
                        },
                        "id": f"mock-check-{time.time()}"
                    }
                    
                    async with session.post(
                        f"{self.orchestrator_url}/mcp/{self.name}",
                        json=payload,
                        headers={"X-Agent-Name": self.name}
                    ) as resp:
                        result = await resp.json()
                        
                        # Check for messages in the content
                        if result.get("result", {}).get("content"):
                            content = result["result"]["content"]
                            if isinstance(content, list) and len(content) > 0:
                                text = content[0].get("text", "")
                                # Parse messages from text
                                if "messages" in text.lower() and ":" in text:
                                    self.logger.info(f"{self.name} received response: {text}")
                                    # Extract messages if they're formatted in the text
                                    if "from Alice" in text:
                                        self.logger.info(f"{self.name} received from Alice: Hello Bob! How are you today?")
                                        # Respond to Alice
                                        if self.name == "Bob":
                                            await self._send_message(
                                                "Alice",
                                                "Hello Alice! I'm doing well, thanks for asking. How can I help you today?"
                                            )
                            
                                        
            except Exception as e:
                self.logger.error(f"Error checking messages: {e}")
                
    async def _simulate_messaging(self):
        """Simulate agent messaging behavior"""
        if self.name == "Leader":
            # Leader delegates tasks
            await asyncio.sleep(3)
            await self._send_message("Researcher", "Please research MCP tools and their usage.")
            
            # Check for responses
            await self._check_messages()
            
        elif self.name == "Alice":
            # Simple demo behavior
            await asyncio.sleep(2)
            await self._send_message("Bob", "Hello Bob! How are you today?")
            await self._check_messages()
            
    def stop(self):
        """Stop the agent"""
        self.running = False
        self.logger.info(f"Mock agent {self.name} stopped")


class MockLauncher:
    """Launcher for mock agents"""
    
    def __init__(self):
        self.logger = logging.getLogger("MockLauncher")
        self.agents = {}
        
    async def launch_agent(
        self,
        agent_name: str,
        orchestrator_url: str,
        system_prompt: str
    ) -> MockAgent:
        """Launch a mock agent"""
        agent = MockAgent(agent_name, orchestrator_url, system_prompt)
        self.agents[agent_name] = agent
        
        # Start agent in background
        asyncio.create_task(agent.start())
        
        return agent
        
    def stop_all(self):
        """Stop all agents"""
        for agent in self.agents.values():
            agent.stop()


async def run_mock_agents(agents_config: list, orchestrator_url: str):
    """Run mock agents with given configuration"""
    launcher = MockLauncher()
    
    # Launch all agents
    for config in agents_config:
        await launcher.launch_agent(
            config["name"],
            orchestrator_url,
            config["prompt"]
        )
        
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        launcher.stop_all()


if __name__ == "__main__":
    # Test mock agents
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    agents = [
        {
            "name": "Alice",
            "prompt": "You are Alice. Use list_agents and send_message to Bob."
        },
        {
            "name": "Bob", 
            "prompt": "You are Bob. Use check_messages to receive messages."
        }
    ]
    
    asyncio.run(run_mock_agents(agents, "http://localhost:8767"))