import asyncio
import os
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
# from mcp.client.sse import sse_client # If available in the SDK, otherwise we stick to stdio for now as per Docker config

from loguru import logger

class MCPClientManager:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}
        self.tools: List[Dict[str, Any]] = []
        self.tool_map: Dict[str, str] = {} # tool_name -> server_name

    async def connect_stdio(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """Connect to an MCP server via stdio."""
        try:
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            # We use the context manager manually to keep connections alive
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            
            await session.initialize()
            self.sessions[name] = session
            logger.info(f"Connected to MCP server: {name}")
            
            # Discover tools
            await self._refresh_tools(name)
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {name}: {e}")

    async def _refresh_tools(self, server_name: str):
        """Fetch tools from a connected server."""
        session = self.sessions.get(server_name)
        if not session:
            return

        try:
            result = await session.list_tools()
            for tool in result.tools:
                # Adapt tool definition to Claude's expected format if needed
                # MCP tool definition: name, description, inputSchema
                tool_def = {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                self.tools.append(tool_def)
                self.tool_map[tool.name] = server_name
                logger.debug(f"Registered tool {tool.name} from {server_name}")
                
        except Exception as e:
            logger.error(f"Failed to list tools from {server_name}: {e}")

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the appropriate server."""
        server_name = self.tool_map.get(name)
        if not server_name:
            raise ValueError(f"Unknown tool: {name}")
            
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")
            
        try:
            logger.info(f"Executing tool {name} on {server_name}")
            result = await session.call_tool(name, arguments)
            
            # Format result for LLM
            # MCP CallToolResult has content list (TextContent or ImageContent)
            output = []
            for content in result.content:
                if content.type == "text":
                    output.append(content.text)
                elif content.type == "image":
                    output.append(f"[Image: {content.mimeType}]") # Placeholder for now
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error: {str(e)}"

    async def cleanup(self):
        """Close all connections."""
        await self.exit_stack.aclose()
