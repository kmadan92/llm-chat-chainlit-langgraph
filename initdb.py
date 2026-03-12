from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///chainlit_ui_history.db")

schema = [

"""
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    identifier TEXT UNIQUE,
    metadata TEXT,
    createdAt TEXT
)
""",

"""
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    createdAt TEXT,
    updatedAt TEXT,
    deletedAt TEXT,
    name TEXT,
    userId TEXT,
    userIdentifier TEXT,
    tags TEXT,
    metadata TEXT,
    FOREIGN KEY(userId) REFERENCES users(id)
)
""",

"""
CREATE TABLE steps (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    threadId TEXT NOT NULL,
    parentId TEXT,
    streaming BOOLEAN,
    waitForAnswer BOOLEAN,
    isError BOOLEAN,
    metadata TEXT,
    tags TEXT,
    input TEXT,
    output TEXT,
    createdAt TEXT,
    command TEXT,
    start TEXT,
    end TEXT,
    generation TEXT,
    showInput TEXT,
    language TEXT,
    indent INTEGER,
    defaultOpen BOOLEAN,
    autoCollapse BOOLEAN,
    disableFeedback BOOLEAN,
    hideOutput BOOLEAN,
    feedback TEXT,
    FOREIGN KEY(threadId) REFERENCES threads(id)
)
""",

"""
CREATE TABLE elements (
    id TEXT PRIMARY KEY,
    threadId TEXT,
    type TEXT,
    url TEXT,
    chainlitKey TEXT,
    name TEXT,
    display TEXT,
    objectKey TEXT,
    size TEXT,
    page INTEGER,
    language TEXT,
    forId TEXT,
    mime TEXT,
    props TEXT,
    createdAt TEXT,
    updatedAt TEXT,
    FOREIGN KEY(threadId) REFERENCES threads(id)
)
""",

"""
CREATE TABLE feedbacks (
    id TEXT PRIMARY KEY,
    forId TEXT,
    threadId TEXT,
    value INTEGER,
    comment TEXT,
    FOREIGN KEY(threadId) REFERENCES threads(id)
)
"""
]

with engine.begin() as conn:
    for stmt in schema:
        conn.execute(text(stmt))

print("Chainlit database initialized successfully.")