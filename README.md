# Multi-Agent AI Platform with MCP Integration

A production-ready, fully asynchronous **agentic AI platform** built with
**LangGraph**, **Chainlit**, and the **Model Context Protocol (MCP)**,
powered by **OpenAI**.

Unlike a traditional chatbot, this platform runs a stateful LangGraph
agent that can autonomously plan, call external tools via MCP, and
pause for human review before executing sensitive operations — all
through a polished web UI with Google authentication.

The platform supports:

-   Google OAuth authentication (with account picker + consent screen)
-   Persistent chat history
-   LangGraph checkpoint memory
-   Real-time streaming responses
-   Multi-user safe conversations
-   MCP (Model Context Protocol) tool integration
-   Human-in-the-Loop (HITL) approval for sensitive tool calls

Each conversation thread is persisted and restored automatically,
allowing users to switch between chats while maintaining memory.

------------------------------------------------------------------------

# Tech Stack

## Frontend / UI

-   Chainlit 2.x — conversational UI, authentication, and chat history

## Agent Logic / Backend

-   LangGraph — stateful agent execution and checkpointing
-   LangChain — LLM interface and agent construction
-   `langchain-mcp-adapters` — MCP tool integration

## LLM Provider

-   OpenAI (`gpt-4o-mini` via `ChatOpenAI`)

## MCP Server

-   FastMCP — exposes tools (e.g. `run_node_test`) over stdio transport

## Persistence Layers

Two independent databases are used:

| Component    | Database                  | Purpose                          |
|--------------|---------------------------|----------------------------------|
| Chainlit UI  | `chainlit_ui_history.db`  | Chat history, threads, steps     |
| LangGraph    | `checkpoints.sqlite`      | Conversation memory / agent state |

## Other Tools

-   SQLite / aiosqlite
-   python-dotenv
-   LangSmith (optional observability)

------------------------------------------------------------------------

# Features

## Google OAuth Authentication

Users authenticate with Google before accessing the chatbot.

Authentication uses Chainlit's OAuth callback system. The login flow is
configured to always show the **account picker and consent screen** so
users can choose which Google account to use each time.

Each authenticated user receives isolated chat threads.

------------------------------------------------------------------------

## Persistent Chat History

All conversations are stored in the Chainlit SQLite database.

Users can:
-   Switch between conversations
-   Resume previous chats
-   Continue conversations later

The sidebar automatically displays saved threads.

------------------------------------------------------------------------

## LangGraph Memory Persistence

Conversation memory is stored using LangGraph's async SQLite checkpointer.

Each conversation thread maps to a unique checkpoint state.

Example flow:

    Chainlit Thread ID
    → LangGraph thread_id
    → SQLite checkpoints.sqlite

This ensures that when a chat is resumed, the model retains full context.

------------------------------------------------------------------------

## MCP Tool Integration

The backend connects to an MCP server (`server.py`) over stdio transport
using `MultiServerMCPClient`. Tools exposed by the MCP server are
automatically discovered and made available to the LangGraph agent.

Current MCP tools:

| Tool            | Description                                      |
|-----------------|--------------------------------------------------|
| `run_node_test` | Runs a probation test (CPU/Memory/Network) on a server node |

The agent collects required parameters (`node_id`, `test_type`) from the
user before invoking any tool.

------------------------------------------------------------------------

## Human-in-the-Loop (HITL) Approval

Sensitive tools (e.g. `write_db`) require explicit user approval before
execution. When the agent wants to call such a tool, the UI pauses and
presents the user with action buttons:

-   **✅ Approve** — executes the tool as-is
-   **✏️ Edit** — lets the user modify the tool arguments (supports any
    number of args via JSON editing) before approving
-   **❌ Reject** — cancels the tool call with an optional reason

After the user's decision, the graph resumes and streams the continued
response. Chained interrupts (multiple tools requiring approval in the
same turn) are handled recursively.

------------------------------------------------------------------------

## Real-Time Streaming Responses

The chatbot streams responses token-by-token using:

```python
astream(stream_mode="messages")
```

This produces a typewriter-style response in the UI.

------------------------------------------------------------------------

## Fully Asynchronous Pipeline

The entire stack runs asynchronously:

    User
    → Chainlit UI
    → LangGraph Execution
    → OpenAI API
    → MCP Server (stdio)
    → SQLite Checkpoint Storage

All components use `async/await` to prevent blocking.

------------------------------------------------------------------------

## Multi-User Safe Architecture

The server runs a single shared LangGraph instance.

Conversation isolation is maintained using thread IDs:

    User A → thread_id = T1
    User B → thread_id = T2
    User C → thread_id = T3

Checkpoint state is stored separately per thread, allowing multiple
users to chat simultaneously without memory overlap.

------------------------------------------------------------------------

# Conversation Thread Flow

1.  User sends a message in Chainlit
2.  Chainlit assigns a thread ID
3.  The message carries `message.thread_id`
4.  LangGraph receives the same ID

```python
chatbot.astream(
    {"messages": [HumanMessage(content=user_text)]},
    config={"configurable": {"thread_id": message.thread_id}}
)
```

5.  LangGraph loads the checkpoint for that thread
6.  Model response is generated, streamed, and stored
7.  If a HITL interrupt fires, the UI shows Approve / Edit / Reject
8.  Graph resumes with the user's decision

------------------------------------------------------------------------

# Getting Started

## 1. Prerequisites

-   Python 3.10+
-   OpenAI API key
-   Google OAuth credentials (from [Google Cloud Console](https://console.cloud.google.com/))

------------------------------------------------------------------------

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## 3. Configure Environment Variables

A `.env.sample` file is included in the repository with all required
variables and instructions. Copy it and fill in your values:

```bash
cp .env.sample .env
```

Then edit `.env`:

```dotenv
# OpenAI
OPENAI_API_KEY="sk-..."

# Google OAuth
OAUTH_GOOGLE_CLIENT_ID="your_google_client_id"
OAUTH_GOOGLE_CLIENT_SECRET="your_google_secret"
OAUTH_GOOGLE_PROMPT="select_account consent"

# Chainlit auth
CHAINLIT_AUTH_SECRET="your_chainlit_secret"

# LangSmith (optional)
LANGSMITH_API_KEY="lsv2_..."
LANGSMITH_TRACING="true"
LANGSMITH_PROJECT="your-project"
```

------------------------------------------------------------------------

## 4. Initialise the Databases

SQLite database files are **not committed to the repository**. Before
running the app for the first time you must create the Chainlit UI
history database by running:

```bash
python initdb.py
```

This creates `chainlit_ui_history.db` with the correct schema
(`users`, `threads`, `steps`, `elements`, `feedbacks` tables).

> **Note:** `checkpoints.sqlite` (LangGraph memory) is created
> automatically by the app on first run — no manual step needed.

------------------------------------------------------------------------

## 5. Run the Application

```bash
chainlit run chainlit_app.py -w
```

The application will start at:

http://localhost:8000

------------------------------------------------------------------------

# Project Structure

```
project-root
│
├── chainlit_app.py        # Chainlit UI, auth, streaming, HITL frontend
├── server.py              # FastMCP server exposing tools
├── initdb.py              # One-time DB initialisation script (run before first launch)
├── requirements.txt
├── .env                   # Environment variables (never commit)
├── .env.sample            # Template — copy to .env and fill in values
├── .chainlit/
│   └── config.toml        # Chainlit UI configuration
│
├── backend/
│   └── chatbot.py         # LangGraph agent, OpenAI LLM, MCP client
│
├── utilities/
│   └── checkpointer.py    # SQLite checkpoint helpers
│
├── public/                # Static assets (icons etc.)
│
├── checkpoints.sqlite     # LangGraph memory (auto-created)
└── chainlit_ui_history.db # Chainlit chat history (auto-created)
```

## Key Files

### `chainlit_app.py`

Handles:
-   Chainlit UI lifecycle (`on_chat_start`, `on_message`, `on_chat_resume`)
-   Google OAuth login
-   Real-time token streaming
-   HITL interrupt detection and Approve / Edit / Reject UI

### `backend/chatbot.py`

Defines:
-   OpenAI `gpt-4o-mini` LLM instantiation
-   `MultiServerMCPClient` connecting to `server.py` over stdio
-   LangGraph agent with `HumanInTheLoopMiddleware`
-   Async SQLite checkpoint saver

### `server.py`

Defines:
-   FastMCP server
-   `run_node_test` tool (probation tests for server nodes)

### `initdb.py`

One-time setup script that creates `chainlit_ui_history.db` with the
full Chainlit schema. Must be run **once after cloning the repo** before
starting the application. SQLite `.db` and `.sqlite` files are excluded
from version control via `.gitignore`.

```bash
python initdb.py
```

------------------------------------------------------------------------

# Security

Sensitive files are excluded via `.gitignore`:

```
.env
*.sqlite
*.db
venv/
mcp/
__pycache__/
```

Never commit API keys or local databases.

------------------------------------------------------------------------

# Future Improvements

Planned enhancements:

-   PostgreSQL checkpoint storage for production
-   Vector memory for long-term recall
-   Additional MCP tools
-   Retrieval-Augmented Generation (RAG)
-   Rate limiting and usage tracking
-   Container or cloud deployment

------------------------------------------------------------------------

# License

MIT License
