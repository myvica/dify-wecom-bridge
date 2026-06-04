CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_key VARCHAR(191) UNIQUE NOT NULL,
    channel_type VARCHAR(50) NOT NULL,
    corp_id VARCHAR(32) NOT NULL,
    agent_id VARCHAR(32) NOT NULL,
    external_user_id VARCHAR(64) NOT NULL,
    chat_id VARCHAR(64) NOT NULL,
    chat_type VARCHAR(20) NOT NULL,
    dify_conversation_id VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_message_at DATETIME,
    message_count INT DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    INDEX idx_conversations_lookup (corp_id, agent_id, external_user_id, chat_id),
    INDEX idx_conversations_updated (updated_at)
) DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_key VARCHAR(191) NOT NULL,
    dify_message_id VARCHAR(191) UNIQUE,
    wecom_msg_id VARCHAR(255),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    raw_content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_messages_conversation (session_key),
    INDEX idx_messages_created (created_at)
) DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS api_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    endpoint VARCHAR(245) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_body TEXT,
    response_body TEXT,
    status_code INT,
    duration_ms INT,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_api_logs_endpoint (endpoint),
    INDEX idx_api_logs_created (created_at)
) DEFAULT CHARSET=utf8mb4;
