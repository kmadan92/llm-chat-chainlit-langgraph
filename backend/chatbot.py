import sys
import os

# ensure parent directory (workspace root) is on path so utilities package is visible
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import asyncio
import os
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient

# load environment variables from .env (endpoint, key, deployment, version)
load_dotenv()

# instantiate Gemini model (API key loaded from GOOGLE_API_KEY in .env)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
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

    # Build the agent with HITL middleware — approve/reject before write_db runs
    return create_agent(
        llm,
        tools,
        checkpointer=saver,
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "write_db": {"allowed_decisions": ["approve", "reject"]},
                    "run_node_test": False,
                }
            ),
        ],
    )

async def run_test():
    print("Initializing Multi-Server MCP Client...")

    try:
        chatbot = await setup_async_graph()
        thread_id = "t7736r7ijfrgv75cjfncjjdch654647554"
        config = {"configurable": {"thread_id": thread_id},
                  "run_name": thread_id}

        while True:

            user_input = input("\n You: ")

            if user_input.strip().lower() in ["bye", "exit", "quit"]:
                break

            final_state = await chatbot.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )

            # Check state AFTER ainvoke to detect HITL interrupt
            snapshot = await chatbot.aget_state(config)

            if snapshot.interrupts:
                interrupt_val = snapshot.interrupts[0].value
                action = interrupt_val["action_requests"][0]
                allowed = interrupt_val["review_configs"][0]["allowed_decisions"]

                print(f"\n[APPROVAL REQUIRED]")
                print(f"  {action['description']}")
                print(f"  Enter one of: {allowed}")
                decision = input("  Your decision: ").strip().lower()

                final_state = await chatbot.ainvoke(
                Command(resume={"decisions": [{"type": decision}]}),
                config=config
                )

            # --- Graph State ---
            print("\n" + "="*50)
            print("GRAPH STATE:")
            print(f"  Total messages in thread : {len(final_state['messages'])}")
            for i, msg in enumerate(final_state["messages"]):
                role = msg.__class__.__name__.replace("Message", "")
                content_preview = str(msg.content)[:120] + ("..." if len(str(msg.content)) > 120 else "")
                print(f"  [{i}] {role}: {content_preview}")
            print("="*50)

            # --- AI Response ---
            final_ai_text = final_state["messages"][-1].content
            print(f"\nAI: {final_ai_text}\n")
            print(final_state)

        print("\n\n[Stream finished successfully!]")

    finally:
        print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(run_test())

