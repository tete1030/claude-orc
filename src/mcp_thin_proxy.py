#!/usr/bin/env python3
"""
Thin MCP Proxy for Agents
Each agent launches this via --mcp-config
It forwards ALL requests to the central orchestrator MCP server
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp


class MCPThinProxy:
    """Thin proxy that forwards everything to central orchestrator"""
    
    def __init__(self, agent_name: str, orchestrator_url: str = "http://localhost:8765"):
        self.agent_name = agent_name
        self.orchestrator_url = orchestrator_url
        self.mcp_endpoint = f"{orchestrator_url}/mcp/{agent_name}"
        self.logger = logging.getLogger(f"MCPProxy.{agent_name}")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def start_session(self):
        """Start aiohttp session"""
        self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def forward_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Forward JSON-RPC request to central orchestrator"""
        if not self.session:
            await self.start_session()
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        
        try:
            async with self.session.post(self.mcp_endpoint, json=request) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "error" in data:
                        raise Exception(data["error"]["message"])
                    return data.get("result", {})
                else:
                    raise Exception(f"HTTP {resp.status}: {await resp.text()}")
        except aiohttp.ClientError as e:
            self.logger.error(f"Connection error: {e}")
            raise Exception(f"Cannot connect to orchestrator: {e}")
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single JSON-RPC request"""
        method = request_data.get("method")
        params = request_data.get("params", {})
        msg_id = request_data.get("id")
        
        try:
            # Forward to central server
            if not self.session:
                await self.start_session()
            
            async with self.session.post(self.mcp_endpoint, json=request_data) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"HTTP {resp.status} from orchestrator"
                        },
                        "id": msg_id
                    }
        
        except Exception as e:
            self.logger.error(f"Error forwarding request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": msg_id
            }
    
    async def run(self):
        """Run the proxy server using stdio"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        writer = sys.stdout
        
        try:
            await self.start_session()
            
            # Handle requests
            while True:
                try:
                    # Read line from stdin
                    line = await reader.readline()
                    if not line:
                        break
                    
                    # Parse request
                    request_data = json.loads(line.decode().strip())
                    
                    # Handle request
                    response = await self.handle_request(request_data)
                    
                    # Write response
                    writer.write(json.dumps(response) + "\n")
                    writer.flush()
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    }
                    writer.write(json.dumps(error_response) + "\n")
                    writer.flush()
                
                except Exception as e:
                    self.logger.error(f"Unexpected error: {e}")
                    break
        
        finally:
            await self.close_session()


def main():
    """Main entry point"""
    # Get agent name from environment
    agent_name = os.environ.get("AGENT_NAME")
    if not agent_name:
        print("Error: AGENT_NAME environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Get orchestrator URL from environment
    orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8765")
    
    # Setup logging
    log_file = f"/tmp/mcp_proxy_{agent_name}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    # Create and run proxy
    proxy = MCPThinProxy(agent_name, orchestrator_url)
    
    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
