CREATE TABLE user (
    user_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255)
    -- Add other user columns here (e.g., name, email, etc.)
);

CREATE TABLE chat (
    chat_id INT AUTO_INCREMENT PRIMARY KEY,
    explore_key VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

CREATE TABLE message (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT,
    chat_id INT,
    is_user_message BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_possitive_feedback BOOLEAN,
    feedback_message_id INT,
    FOREIGN KEY (chat_id) REFERENCES chat(chat_id)
);

CREATE TABLE feedback (
    feedback_message_id INT AUTO_INCREMENT PRIMARY KEY,
    feedback_message TEXT,
    is_possitive BOOLEAN
);