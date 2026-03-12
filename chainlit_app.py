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
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: dict[str, str],
    default_user: cl.User,
):
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
async def set_starters():
    return [
        cl.Starter(
            label="Run CPU Tests",
            message="Can you help me create a personalized morning routine that would help increase my productivity throughout the day? Start by asking me about my current habits and what activities energize me in the morning.",
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
    # extract text from chainlit message object (always coerce to str)


    if hasattr(message, "content"):
        user_text = message.content
    else:
        user_text = str(message)

    #debug: print full object attributes
    # print("received message text=", user_text)
    # print("message attributes:", vars(message))

    thread_id = message.thread_id
    chatbot = cl.user_session.get("chatbot")

    # stream langgraph chatbot with the new human message
    try:
        # Create an empty message to stream to
        msg = cl.Message(content="")
        await msg.send() 
        
        # Use astream() for async streaming, and fix the loop syntax
        async for chunk, metadata in chatbot.astream(
            {"messages": [HumanMessage(content=user_text)]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="messages"
        ):

            # --- DEBUGGING PRINT ---
            # This will print the raw chunks to your terminal so you can see the data!
            # print(f"DEBUG Chunk: {chunk.__class__.__name__} | Content: {chunk.content}")
           
            if chunk.content and "AIMessageChunk" in chunk.__class__.__name__:
                await msg.stream_token(chunk.content)

        # # Finalize the message
        await msg.update()
        
    except Exception as e:
        reply_text = f"Error invoking chatbot: {e}"
        print("chatbot invocation error:", e)
        await cl.Message(content=reply_text).send()


