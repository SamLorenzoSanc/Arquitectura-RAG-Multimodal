CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workspaces (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    logo TEXT,
    api_key VARCHAR(255) UNIQUE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_workspace_owner
    FOREIGN KEY(owner_id)
    REFERENCES users(id)
);

CREATE TABLE knowledge_bases (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    icon VARCHAR(100),
    scope VARCHAR(100),
    embedding_model VARCHAR(150),
    llm_model VARCHAR(150),
    chunk_size INTEGER DEFAULT 100,
    chunk_overlap INTEGER DEFAULT 20,
    top_k INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.75,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_kb_workspace
    FOREIGN KEY(workspace_id)
    REFERENCES workspaces(id)
);

CREATE TABLE knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    summary TEXT,
    markdown TEXT,
    tags JSONB DEFAULT '[]',
    source_name VARCHAR(255),
    source_type VARCHAR(100),
    page INTEGER,
    ocr_text TEXT,
    status VARCHAR(50)
    DEFAULT 'processed',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_knowledge_base
    FOREIGN KEY(knowledge_base_id)
    REFERENCES knowledge_bases(id)
);

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    headline VARCHAR(255),
    content TEXT NOT NULL,
    tokens INTEGER,
    embedding VECTOR(4096),
    embedding_model VARCHAR(150),
    provider VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_embedding_knowledge
    FOREIGN KEY(knowledge_id)
    REFERENCES knowledge(id)
    ON DELETE CASCADE
);



CREATE INDEX embeddings_vector_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE conversations (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    user_id UUID,
    knowledge_base_id UUID,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources JSONB,
    retrieved_chunks JSONB,
    llm_model VARCHAR(150),
    embedding_model VARCHAR(150),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms INTEGER,
    evaluation JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(workspace_id)
    REFERENCES workspaces(id),
    FOREIGN KEY(user_id)
    REFERENCES users(id),
    FOREIGN KEY(knowledge_base_id)
    REFERENCES knowledge_bases(id)

);