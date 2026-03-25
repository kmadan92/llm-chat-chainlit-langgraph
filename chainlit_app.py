import sys
import os
from dotenv import load_dotenv
load_dotenv()

# ensure parent directory (workspace root) is on path so backend package is visible
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

import chainlit as cl
from backend.chatbot import setup_async_graph
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.errors import GraphInterrupt
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

cl_data._data_layer = SQLAlchemyDataLayer(conninfo="sqlite+aiosqlite:///./chainlit_ui_history.db")

graph = None

async def get_graph():
    global graph
    if graph is None:
        graph = await setup_async_graph()
    return graph

# --- NEW: Real Google OAuth Authentication ---
@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: dict[str, str],
    default_user: cl.User,
    id_token: str | None = None,
) -> cl.User | None:
    # Chainlit automatically handles the Google login flow.
    # This function just confirms the login was successful and returns the user object.
    if provider_id == "google":
        return cl.User(
            identifier=default_user.identifier,
            metadata={
                "name": raw_user_data.get("name"),
                "image": raw_user_data.get("picture")
            }
        )
    return None
# ---------------------------------------------

@cl.set_starters
async def set_starters(user: cl.User | None = None, app_language: str | None = None):
    return [
        cl.Starter(
            label="Run Probation Test",
            message="Run Probation Test",
            icon="/public/idea.svg",
        ),

        cl.Starter(
            label="Run Memory Tests",
            message="Explain superconductors like I'm five years old.",
            icon="/public/learn.svg",
        ),
        cl.Starter(
            label="Run Disk Tests",
            message="Write a script to automate sending daily email reports in Python, and walk me through how I would set it up.",
            icon="/public/terminal.svg",
            command="code",
        ),
        cl.Starter(
            label="Holistic Stress - CPU+Memory+Disk",
            message="Write a text asking a friend to be my plus-one at a wedding next month. I want to keep it super short and casual, and offer an out.",
            icon="/public/write.svg",
        )
    ]


@cl.on_chat_start
async def start_chat():

    # 1. Initialize the async graph and database connection
    chatbot = await get_graph()
    
    # 2. Store this specific chatbot instance in the user's session
    cl.user_session.set("chatbot", chatbot)


@cl.on_chat_resume
async def on_chat_resume(thread):
    chatbot = await get_graph()
    cl.user_session.set("chatbot", chatbot)
    cl.user_session.set("thread_id", thread.get("id"))

@cl.on_message
async def main(message):
    user_text = message.content if hasattr(message, "content") else str(message)
    thread_id = message.thread_id
    chatbot = cl.user_session.get("chatbot")
    if chatbot is None:
        await cl.Message(content="Session not ready. Please refresh and try again.").send()
        return
    config = {"configurable": {"thread_id": thread_id}, "run_name": thread_id}

    msg = cl.Message(content="")
    await msg.send()

    try:
        async for chunk, metadata in chatbot.astream(
            {"messages": [HumanMessage(content=user_text)]},
            config=config,
            stream_mode="messages"
        ):
            if chunk.content and "AIMessageChunk" in chunk.__class__.__name__:
                await msg.stream_token(chunk.content)
        await msg.update()

        # Check for HITL interrupt after streaming completes
        snapshot = await chatbot.aget_state(config)
        if snapshot.interrupts:
            #print(snapshot)
            await _handle_interrupt(chatbot, config, snapshot)

    except Exception as e:
        print("chatbot invocation error:", e)
        await cl.Message(content=f"Error invoking chatbot: {e}").send()


async def _handle_interrupt(chatbot, config, snapshot):
    """Show Approve / Edit / Reject UI and resume the graph with the user's decision."""
    interrupt_val = snapshot.interrupts[0].value
    action = interrupt_val["action_requests"][0]
    allowed = interrupt_val["review_configs"][0]["allowed_decisions"]

    action_name = action.get("name", "unknown")
    description = action.get("description", "The AI wants to perform an action.")
    args = action.get("args", {})

    # Build buttons based on what is allowed for this tool
    buttons = []
    if "approve" in allowed:
        buttons.append(cl.Action(name="approve", payload={"value": "approve"}, label="✅ Approve"))
    if "edit" in allowed:
        buttons.append(cl.Action(name="edit", payload={"value": "edit"}, label="✏️ Edit"))
    if "reject" in allowed:
        buttons.append(cl.Action(name="reject", payload={"value": "reject"}, label="❌ Reject"))

    action_res = await cl.AskActionMessage(
        content=(
            f"**Approval Required**\n\n"
            f"🔧 Tool: `{action_name}`\n"
            f"📋 Args: `{args}`\n\n"
        ),
        actions=buttons,
    ).send()

    decision = action_res["payload"]["value"] if action_res else "reject"

    if decision == "edit":
        edit_res = await cl.AskUserMessage(
            content=f"✏️ **Edit value for `{action_name}` in the text field below**\n\nCurrent value is: `{args}`\n\nEnter new value:",
            timeout=120,
        ).send()
        new_message = (edit_res.get("output") or "").strip() if edit_res else args.get("message", "")
        resume_decision = {
            "type": "edit",
            "edited_action": {
                "name": action_name,
                "args": {"message": new_message},
            },
        }
    elif decision == "reject":
        reason_res = await cl.AskUserMessage(
            content="❌ Enter a reason for rejection (optional — press Enter to skip):",
            timeout=60,
        ).send()
        resume_decision = {"type": "reject"}
        if reason_res and (reason_res.get("output") or "").strip():
            resume_decision["message"] = reason_res.get("output", "").strip()
    else:
        resume_decision = {"type": "approve"}

    # Resume the graph and stream the continued response
    msg = cl.Message(content="")
    await msg.send()
    async for chunk, metadata in chatbot.astream(
        Command(resume={"decisions": [resume_decision]}),
        config=config,
        stream_mode="messages",
    ):
        if chunk.content and "AIMessageChunk" in chunk.__class__.__name__:
            await msg.stream_token(chunk.content)
    await msg.update()

    # Handle chained interrupts (another tool may need approval in the same turn)
    snapshot = await chatbot.aget_state(config)
    if snapshot.interrupts:
        await _handle_interrupt(chatbot, config, snapshot)


