from pydantic import BaseModel, Field
from typing import Dict, Optional

class MCPServerConfig(BaseModel):
    """
    Configuration for a single MCP server.
    """
    url: str
    transport: str = Field(default="sse", pattern="^(sse|stdio)$")
    timeout: int = Field(default=30, ge=1)
    rate_limit: int = Field(default=10, description="Requests per minute")

class MCPConfig(BaseModel):
    """
    Global MCP configuration.
    """
    servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)

    @classmethod
    def default(cls):
        return cls(
            servers={
                "filesystem": MCPServerConfig(url="http://localhost:8001/sse"),
                "github": MCPServerConfig(url="http://localhost:8002/sse"),
                "web_search": MCPServerConfig(url="http://localhost:8003/sse"),
                "log_parser": MCPServerConfig(url="http://localhost:8004/sse"),
            }
        )

# Global instance
mcp_config = MCPConfig.default()
