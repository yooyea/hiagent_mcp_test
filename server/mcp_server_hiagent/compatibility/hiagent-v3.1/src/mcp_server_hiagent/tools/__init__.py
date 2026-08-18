"""Business-domain tool registration for HiAgent MCP Server."""

from mcp_server_hiagent.tools._common import OpenAPIClient
from mcp_server_hiagent.tools.dataset import register_dataset_tools
from mcp_server_hiagent.tools.knowledge import register_knowledge_tools


__all__ = [
    "OpenAPIClient",
    "register_dataset_tools",
    "register_knowledge_tools",
]
