from fastmcp import FastMCP

# Initialize your MCP Server
mcp = FastMCP("LLM App")

@mcp.tool()
async def run_node_test(node_id: list[str], test_type: str) -> str:
    """
    Executes a probation test on a server node for given NodeId or NodeIds and Test Type.
    
    CRITICAL INSTRUCTIONS FOR AI:
    You MUST have both node_id' or  list of node ids and a 'test_type' (e.g., CPU, Memory, Network) to call this tool.
    
    If you are missing any of these details, DO NOT CALL THIS TOOL. Instead, you must collect the missing information. Ask for EXACTLY ONE QUESTION AT A TIME:
    1. First, check if you have the 'node_id'. If you do not, ask the user ONLY for the Node ID or list of Node IDs and stop. Wait for their reply.
    2. Once you have the 'node_id', check if you have the 'test_type'. If you do not, ask the user ONLY for the test type to select any one from type from CPU, Memory, Network and stop. Wait for their reply.
    3. 'test_type' should always be one either from CPU, Memory or Network. If user provides anything other than this then ask him to select one out of CPU, Network or Memory
    3. NEVER ask for both the Node ID and the Test Type in the same message.
    """
    
    return f"Tests failed for {node_id}"

@mcp.tool()
async def write_db(message: str) -> str:
    """
    Saves user-provided details to the database.
    
    Call this tool when the user asks to save, store, or write any information to the DB or database.
    
    Args:
        message: The details or information the user wants to save to the database.
    """
    return f"Write operation of user message {message} is successful."

# Run the MCP server
if __name__ == "__main__":
    mcp.run()