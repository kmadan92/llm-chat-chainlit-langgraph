from mcp.server.fastmcp import FastMCP
from langgraph.types import Command
from backend.hitl import setup_async_graph
import uuid

# Initialize your MCP Server
mcp = FastMCP("LLM App")

@mcp.tool()
async def run_node_test(node_id: str, test_type: str) -> str:
    """
    Executes a probation test on a server node.
    
    CRITICAL INSTRUCTIONS FOR AI:
    You MUST have both a 'node_id' and a 'test_type' (e.g., CPU, Memory, Network) to call this tool.
    If the user asks to run a test but does NOT provide these details, DO NOT CALL THIS TOOL. 
    Instead, stop and ask the user to provide the missing 'node_id' and 'test_type'.
    """
    
    return "Tests failed"

# Run the MCP server (typically handled by your specific MCP runner/transport)
if __name__ == "__main__":
    mcp.run()