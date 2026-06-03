PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key TEXT UNIQUE NOT NULL,
    channel_type TEXT NOT NULL,
    corp_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    external_user_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    chat_type TEXT NOT NULL,
    dify_conversation_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_conversations_lookup
ON conversations(corp_id, agent_id, external_user_id, chat_id);

CREATE INDEX IF NOT EXISTS idx_conversations_updated
ON conversations(updated_at);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key TEXT NOT NULL,
    dify_message_id TEXT UNIQUE,
    wecom_msg_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    raw_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_key) REFERENCES conversations(session_key)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
ON messages(session_key);

CREATE INDEX IF NOT EXISTS idx_messages_created
ON messages(created_at);

CREATE TABLE IF NOT EXISTS api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    request_body TEXT,
    response_body TEXT,
    status_code INTEGER,
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint
ON api_logs(endpoint);

CREATE INDEX IF NOT EXISTS idx_api_logs_created
ON api_logs(created_at);
