CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    job_title VARCHAR(80),
    phone VARCHAR(30),
    island VARCHAR(40),
    municipality VARCHAR(80),
    bio TEXT,
    crop_focus VARCHAR(80),
    preferred_language VARCHAR(8) NOT NULL DEFAULT 'es',
    notify_email BOOLEAN NOT NULL DEFAULT TRUE,
    notify_whatsapp BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_path TEXT,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
