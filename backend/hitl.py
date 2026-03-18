from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# 1. Define the State
class TestState(TypedDict):
    node_id: Optional[str]
    test_type: Optional[str]
    status: Optional[str]

# 2. Node: Check for Node ID
async def collect_node_id(state: TestState):
    if not state.get("node_id"):
        # Pauses graph execution and sends this string back to the caller (Chainlit/MCP)
        node_id = interrupt("Please provide a Node ID:")
        print(node_id)
        if node_id:
            return {"node_id": node_id}
        else: 
            return {"status": "cancelled"}
    return {}

# 3. Node: Check for Test Type
async def collect_test_type(state: TestState):

    # Short-circuit if cancelled in a previous step
    if state.get("status") == "cancelled":
        return {}

    if not state.get("test_type"):
        test_type = interrupt("Please select a Test Type (CPU, Memory, Network):")
        if test_type:
            return {"test_type": test_type}
        else: 
            return {"status": "cancelled"}
    return {}

# 4. Node: Final Confirmation
async def confirm_execution(state: TestState):
    if state.get("status") != "confirmed":
        decision = interrupt(f"Are you sure you want to run the {state['test_type']} test on node {state['node_id']}? (Y/N)")
        
        if decision.lower() in ['y', 'yes']:
            return {"status": "confirmed"}
        else:
            return {"status": "cancelled"}
    return {}

# 5. Node: Execute Test
async def execute_test(state: TestState):
    if state.get("status") == "cancelled":
        return {"status": "Execution aborted by user."}
    
    # --- Trigger your actual test script/API here ---
    
    return {"status": f"Successfully executed {state['test_type']} test on {state['node_id']}."}


builder = StateGraph(TestState)

builder.add_node("collect_node_id", collect_node_id)
builder.add_node("collect_test_type", collect_test_type)
builder.add_node("confirm_execution", confirm_execution)
builder.add_node("execute_test", execute_test)

# Linear flow: It will naturally progress through the nodes, stopping only if interrupted
builder.add_edge(START, "collect_node_id")
builder.add_edge("collect_node_id", "collect_test_type")
builder.add_edge("collect_test_type", "confirm_execution")
builder.add_edge("confirm_execution", "execute_test")
builder.add_edge("execute_test", END)

async def setup_async_graph():
    # Now we can safely use 'await' because we are inside an async function
    conn = await aiosqlite.connect("checkpoints.sqlite")
    saver = AsyncSqliteSaver(conn=conn)
    
    # Compile and return the chatbot
    return builder.compile(checkpointer=saver)