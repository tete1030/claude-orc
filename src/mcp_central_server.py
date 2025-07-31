#!/usr/bin/env python3
"""
Central MCP Server for Orchestrator
This is the ONE server that handles ALL agents
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List
from datetime import datetime

try:
    from mcp.server.fastmcp import FastMCP
    from aiohttp import web
except ImportError:
    print("Required packages not installed.")
    print("Install with: pip install 'mcp[cli]' aiohttp")
    raise


class CentralMCPServer:
    """The ONE MCP server that handles all agents"""
    
    def __init__(self, orchestrator, port: int = 8765):
        self.orchestrator = orchestrator
        self.port = port
        self.app = web.Application()
        self.logger = logging.getLogger(__name__)
        
        # Create MCP instance
        self.mcp = FastMCP(
            "OrchestratorCentral",
            description="Central MCP server for all agents"
        )
        
        # Setup HTTP routes
        self._setup_routes()
        
        # Setup MCP tools
        self._setup_tools()
        
    def _setup_routes(self):
        """Setup HTTP routes"""
        # MCP endpoints - SSE requires GET for event stream, POST for messages
        # OAuth discovery endpoints (for SSE auth)
        self.app.router.add_get('/.well-known/oauth-protected-resource', self.handle_oauth_discovery)
        self.app.router.add_get('/.well-known/oauth-authorization-server', self.handle_oauth_server_discovery)
        self.app.router.add_post('/register', self.handle_client_registration)
        self.app.router.add_get('/authorize', self.handle_authorize)
        self.app.router.add_post('/token', self.handle_token)
        
        self.app.router.add_get('/mcp/{agent_name}', self.handle_sse_connect)
        self.app.router.add_post('/mcp/{agent_name}', self.handle_mcp_request)
        self.app.router.add_post('/mcp/{agent_name}/messages', self.handle_sse_message)
    
    async def handle_oauth_discovery(self, request: web.Request) -> web.Response:
        """Handle OAuth protected resource discovery"""
        # Tell Claude this resource uses OAuth
        return web.json_response({
            "authorization_server": f"{request.scheme}://{request.host}/.well-known/oauth-authorization-server"
        })
    
    async def handle_oauth_server_discovery(self, request: web.Request) -> web.Response:
        """Handle OAuth server discovery"""
        # Full OAuth server metadata required by Claude
        base_url = f"{request.scheme}://{request.host}"
        return web.json_response({
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "registration_endpoint": f"{base_url}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"]
        })
    
    async def handle_client_registration(self, request: web.Request) -> web.Response:
        """Handle dynamic client registration"""
        # Accept any registration and return client credentials
        data = await request.json()
        client_id = f"client_{id(data)}"
        
        # Extract redirect_uris from request or use default
        redirect_uris = data.get("redirect_uris", ["http://localhost"])
        
        return web.json_response({
            "client_id": client_id,
            "client_id_issued_at": int(time.time()),
            "grant_types": ["authorization_code", "client_credentials"],
            "token_endpoint_auth_method": "none",
            "redirect_uris": redirect_uris,
            "response_types": ["code"]
        })
    
    async def handle_authorize(self, request: web.Request) -> web.Response:
        """Handle authorization endpoint - redirect with code"""
        # For SSE MCP, we can use a simplified flow
        client_id = request.query.get('client_id', 'unknown')
        redirect_uri = request.query.get('redirect_uri', '')
        state = request.query.get('state', '')
        
        # Generate a simple auth code
        auth_code = f"code_{int(time.time())}"
        
        # Redirect back with code
        if redirect_uri:
            separator = '&' if '?' in redirect_uri else '?'
            redirect_url = f"{redirect_uri}{separator}code={auth_code}&state={state}"
            raise web.HTTPFound(redirect_url)
        
        return web.json_response({"code": auth_code})
    
    async def handle_token(self, request: web.Request) -> web.Response:
        """Handle token endpoint - return access token"""
        # Accept any token request and return a token
        try:
            data = await request.json()
        except:
            data = await request.post()
        
        # Return a simple access token
        return web.json_response({
            "access_token": f"token_{int(time.time())}",
            "token_type": "Bearer",
            "expires_in": 3600
        })
        
    async def handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle MCP requests from agents - supports both regular and streaming"""
        agent_name = request.match_info['agent_name']
        
        # Check if this is a streaming request
        if request.headers.get('Accept') == 'text/event-stream':
            return await self.handle_mcp_stream(request, agent_name)
        
        try:
            # Get JSON-RPC request
            data = await request.json()
            
            # Log the request
            self.logger.info(f"MCP request from {agent_name}: {data.get('method')}")
            
            # Route to appropriate handler based on agent
            response = await self._process_request(agent_name, data)
            
            return web.json_response(response)
            
        except Exception as e:
            self.logger.error(f"Error handling request from {agent_name}: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": data.get("id") if 'data' in locals() else None
            })
    
    async def handle_mcp_stream(self, request: web.Request, agent_name: str) -> web.StreamResponse:
        """Handle streaming MCP requests"""
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        await response.prepare(request)
        
        try:
            # Read streaming requests
            async for line in request.content:
                if not line:
                    continue
                    
                try:
                    # Parse JSON-RPC request
                    data = json.loads(line.decode().strip())
                    
                    # Process request
                    result = await self._process_request(agent_name, data)
                    
                    # Send response
                    await response.write(json.dumps(result).encode() + b'\n')
                    
                except json.JSONDecodeError:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    }
                    await response.write(json.dumps(error_response).encode() + b'\n')
                    
        except Exception as e:
            self.logger.error(f"Stream error for {agent_name}: {e}")
        
        return response
    
    async def handle_sse_connect(self, request: web.Request) -> web.StreamResponse:
        """Handle SSE connection from agent"""
        agent_name = request.match_info['agent_name']
        
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['Access-Control-Allow-Origin'] = '*'
        await response.prepare(request)
        
        # Send initial connection event
        await response.write(b'event: connected\ndata: {"message": "Connected to MCP server"}\n\n')
        
        # Keep connection alive
        try:
            while not response.task.done():
                await asyncio.sleep(30)  # Send keepalive every 30 seconds
                await response.write(b':keepalive\n\n')
        except Exception as e:
            self.logger.error(f"SSE connection error for {agent_name}: {e}")
            
        return response
    
    async def handle_sse_message(self, request: web.Request) -> web.Response:
        """Handle POST messages in SSE mode"""
        agent_name = request.match_info['agent_name']
        
        try:
            data = await request.json()
            self.logger.info(f"SSE message from {agent_name}: {data.get('method')}")
            
            # Process the request
            response = await self._process_request(agent_name, data)
            
            return web.json_response(response)
            
        except Exception as e:
            self.logger.error(f"SSE message error from {agent_name}: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": data.get("id") if 'data' in locals() else None
            })
    
    async def _process_request(self, agent_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON-RPC request for specific agent"""
        method = request.get("method")
        params = request.get("params", {})
        msg_id = request.get("id")
        
        # Handle standard MCP methods
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "OrchestratorCentral",
                        "version": "1.0.0"
                    }
                },
                "id": msg_id
            }
            
        elif method == "tools/list":
            # Return tools specific to this agent
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": self._get_tools_for_agent(agent_name)
                },
                "id": msg_id
            }
            
        elif method == "tools/call":
            # Invoke tool with agent context
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            result = await self._invoke_tool(agent_name, tool_name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                },
                "id": msg_id
            }
            
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": "Method not found"
                },
                "id": msg_id
            }
    
    def _get_tools_for_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get tools available for specific agent"""
        # All agents get the same communication tools
        return [
            {
                "name": "send_message",
                "description": "Send a message to another agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient agent"},
                        "message": {"type": "string", "description": "Message content"}
                    },
                    "required": ["to", "message"]
                }
            },
            {
                "name": "check_messages",
                "description": "Check your mailbox",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 10}
                    }
                }
            },
            {
                "name": "list_agents",
                "description": "List all available agents",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "broadcast_message",
                "description": "Send message to all agents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    },
                    "required": ["message"]
                }
            }
        ]
    
    async def _invoke_tool(self, agent_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Invoke tool on behalf of agent"""
        # Route to orchestrator methods
        if tool_name == "send_message":
            to_agent = arguments.get("to", "")
            message = arguments.get("message", "")
            if not to_agent or not message:
                return "Error: 'to' and 'message' are required parameters"
            return self._send_message(agent_name, to_agent, message)
        elif tool_name == "check_messages":
            return self._check_messages(agent_name, arguments.get("limit", 10))
        elif tool_name == "list_agents":
            return self._list_agents()
        elif tool_name == "broadcast_message":
            message = arguments.get("message", "")
            if not message:
                return "Error: 'message' is required parameter"
            return self._broadcast_message(agent_name, message)
        else:
            return f"Unknown tool: {tool_name}"
    
    def _send_message(self, from_agent: str, to_agent: str, message: str) -> str:
        """Send message through orchestrator"""
        if to_agent not in self.orchestrator.agents:
            return f"Error: Agent '{to_agent}' not found"
        
        # Use the enhanced message delivery system if available
        if hasattr(self.orchestrator, 'send_message_to_agent'):
            # This will handle notifications and queueing
            success = self.orchestrator.send_message_to_agent(
                to_agent, from_agent, message, priority="normal"
            )
            if success:
                return f"Message sent to {to_agent}"
            else:
                return f"Failed to send message to {to_agent}"
        else:
            # Fallback to old behavior
            with self.orchestrator._mailbox_lock:
                msg_data = {
                    "from": from_agent,
                    "to": to_agent,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                self.orchestrator.mailbox[to_agent].append(msg_data)
                
            self.logger.info(f"Message: {from_agent} -> {to_agent}")
            return f"Message sent to {to_agent}"
    
    def _check_messages(self, agent_name: str, limit: int) -> str:
        """Check messages for agent"""
        with self.orchestrator._mailbox_lock:
            messages = list(self.orchestrator.mailbox.get(agent_name, []))[-limit:]
            self.orchestrator.mailbox[agent_name] = []
            
        if not messages:
            return "No new messages"
            
        result = f"You have {len(messages)} message(s):\n"
        for i, msg in enumerate(messages, 1):
            result += f"{i}. From: {msg['from']} - {msg['message']} [{msg['timestamp']}]\n"
            
        return result.strip()
    
    def _list_agents(self) -> str:
        """List all agents"""
        with self.orchestrator._agents_lock:
            agents = list(self.orchestrator.agents.keys())
            
        if not agents:
            return "No agents registered"
            
        return f"Available agents ({len(agents)}): {', '.join(sorted(agents))}"
    
    def _broadcast_message(self, from_agent: str, message: str) -> str:
        """Broadcast to all agents"""
        count = 0
        with self.orchestrator._mailbox_lock:
            for agent_name in self.orchestrator.agents:
                if agent_name != from_agent:
                    msg_data = {
                        "from": from_agent,
                        "to": "all",
                        "message": f"[BROADCAST] {message}",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.orchestrator.mailbox[agent_name].append(msg_data)
                    count += 1
                    
        return f"Broadcast sent to {count} agents"
    
    def _setup_tools(self):
        """Setup MCP tools (for potential direct FastMCP usage)"""
        # These would be used if we could get FastMCP to work with HTTP
        pass
    
    async def start(self):
        """Start the central MCP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        self.logger.info(f"Central MCP server started on http://localhost:{self.port}")
        
    async def run_forever(self):
        """Run the server forever"""
        await self.start()
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour