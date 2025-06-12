#!/usr/bin/env python3

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from mcp import Server, types
from mcp.server import stdio
from dotenv import load_dotenv

from handlers.mcp_handler import MCPHandler
from handlers.fallback_handler import FallbackHandler
from config.settings import Settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LookerMCPServer:
    def __init__(self):
        self.settings = Settings()
        self.mcp_handler = MCPHandler(self.settings)
        self.fallback_handler = FallbackHandler(self.settings)
        self.server = Server("looker-explore-assistant")
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available tools"""
            return await self.mcp_handler.list_tools()
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            return await self.mcp_handler.call_tool(name, arguments)
        
        @self.server.list_resources()
        async def list_resources() -> List[types.Resource]:
            """List available resources"""
            return await self.mcp_handler.list_resources()
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource content"""
            return await self.mcp_handler.read_resource(uri)
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Looker MCP Server...")
        logger.info(f"Target API URL: {self.settings.looker_api_url}")
        
        async with stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream, 
                self.server.create_initialization_options()
            )

async def main():
    """Main entry point"""
    server = LookerMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())