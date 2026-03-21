import sys
import os

# ensure parent directory (workspace root) is on path so utilities package is visible
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import asyncio
import os
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

# load environment variables from .env (endpoint, key, deployment, version)
load_dotenv()

# require deployment and version to be set
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
if not azure_deployment:
    raise RuntimeError("AZURE_OPENAI_DEPLOYMENT must be set in .env")

api_version = os.getenv("AZURE_OPENAI_API_VERSION")
if not api_version:
    raise RuntimeError("AZURE_OPENAI_API_VERSION must be set in .env")

# instantiate Azure chat model
llm = AzureChatOpenAI(
    azure_deployment=azure_deployment,
    api_version=api_version,
    # additional params like temperature, max_tokens are optional
    temperature=0.1
)


async def setup_async_graph():
    
    # Initialize SQLite checkpointer for conversation persistence with async support
    conn = await aiosqlite.connect("checkpoints.sqlite")
    saver = AsyncSqliteSaver(conn=conn)

    CLIENT_CONFIG = {
       "run_node_test": {
            "transport": "stdio",
            "command": "python", 
            "args": ["Q:\\mcp\\server.py"] 
        }
    }

    # 1. Instantiate directly. No more 'async with'!
    mcp_client = MultiServerMCPClient(CLIENT_CONFIG)
    
    # 2. Fetch tools. The client handles the connection temporarily under the hood.
    tools = await mcp_client.get_tools()
    
    # Build the agent
    return create_agent(llm, tools, checkpointer=saver)

async def run_test():
    print("Initializing Multi-Server MCP Client...")

    
    try:
        chatbot = await setup_async_graph()
            
        while True:

            user_input = input("\n You: ")

            if user_input.strip().lower() in ["bye", "exit", "quit"]:
                break

            final_state = await chatbot.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config={"configurable": {"thread_id": "test_mdjcdjc87i8jdch654647554"}}
            )

            final_ai_text = final_state["messages"][-1]
            print(f"AI: {final_ai_text}")

        print("\n\n[Stream finished successfully!]")
        
    finally:
        print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(run_test())

