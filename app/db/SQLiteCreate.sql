CREATE TABLE IF NOT EXISTS users_tbl (
    user_no INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    user_name TEXT NOT NULL,
    user_passwd TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_tbl_user_id
ON users_tbl(user_id);

CREATE INDEX IF NOT EXISTS idx_users_tbl_user_name
ON users_tbl(user_name);

CREATE TABLE IF NOT EXISTS user_images_tbl (
    image_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_desc TEXT NOT NULL DEFAULT '',
    stored_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_ext TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users_tbl(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_images_tbl_user_id
ON user_images_tbl(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_images_tbl_stored_name
ON user_images_tbl(stored_name);

CREATE TABLE IF NOT EXISTS design_profile_tbl (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    ai_image_id INTEGER NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CONSTRAINT valid_json CHECK (json_valid(profile_json)),
    FOREIGN KEY (user_id) REFERENCES users_tbl(user_id),
    FOREIGN KEY (ai_image_id) REFERENCES user_images_tbl(image_id)
);

CREATE INDEX IF NOT EXISTS idx_design_profile_tbl_user_id
ON design_profile_tbl(user_id);
