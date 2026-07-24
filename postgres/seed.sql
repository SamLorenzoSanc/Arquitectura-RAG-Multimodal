CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-------------------------------------------------------------
-- ORGANIZACIONES
-------------------------------------------------------------

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    logo TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- DEPARTAMENTOS
-------------------------------------------------------------

CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    UNIQUE(organization_id, name)
);

-------------------------------------------------------------
-- TENANTS
-------------------------------------------------------------

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    api_key UUID DEFAULT gen_random_uuid(),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, name)
);

-------------------------------------------------------------
-- ROLES
-------------------------------------------------------------

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID
        REFERENCES organizations(id)
        ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    UNIQUE(organization_id, name)
);

-------------------------------------------------------------
-- USUARIOS
-------------------------------------------------------------

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- MIEMBROS DE ORGANIZACIÓN
-------------------------------------------------------------

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id)
        ON DELETE CASCADE,
    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,
    department_id UUID
        REFERENCES departments(id),
    role_id UUID
        REFERENCES roles(id),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, user_id)
);

-------------------------------------------------------------
-- BASES DE CONOCIMIENTO
-------------------------------------------------------------

CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL
        REFERENCES tenants(id)
        ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    chroma_collection VARCHAR(100) UNIQUE NOT NULL,
    created_by UUID
        REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- PERMISOS
-------------------------------------------------------------

CREATE TABLE knowledge_base_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID
        REFERENCES knowledge_bases(id)
        ON DELETE CASCADE,
    member_id UUID
        REFERENCES organization_members(id)
        ON DELETE CASCADE,
    permission VARCHAR(20) NOT NULL,
    UNIQUE(knowledge_base_id, member_id)
);

-------------------------------------------------------------
-- DOCUMENTOS
-------------------------------------------------------------

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID
        REFERENCES tenants(id),
    knowledge_base_id UUID
        REFERENCES knowledge_bases(id),
    owner_id UUID
        REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    mime_type VARCHAR(100),
    storage_path TEXT NOT NULL,
    size BIGINT,
    current_version INTEGER DEFAULT 1,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- VERSIONES
-------------------------------------------------------------

CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID
        REFERENCES documents(id)
        ON DELETE CASCADE,
    version INTEGER NOT NULL,
    filename VARCHAR(255),
    storage_path TEXT,
    uploaded_by UUID
        REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, version)
);

-------------------------------------------------------------
-- TAGS
-------------------------------------------------------------

CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE document_tags (
    document_id UUID
        REFERENCES documents(id)
        ON DELETE CASCADE,
    tag_id UUID
        REFERENCES tags(id)
        ON DELETE CASCADE,
    PRIMARY KEY(document_id, tag_id)
);

-------------------------------------------------------------
-- PROCESAMIENTO
-------------------------------------------------------------

CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID
        REFERENCES tenants(id),
    document_id UUID
        REFERENCES documents(id)
        ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    error_message TEXT,
    chunks_generated INTEGER DEFAULT 0,
    embedding_model VARCHAR(100),
    llm_model VARCHAR(100)
);

-------------------------------------------------------------
-- CONVERSACIONES
-------------------------------------------------------------

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID
        REFERENCES tenants(id),
    user_id UUID
        REFERENCES users(id),
    knowledge_base_id UUID
        REFERENCES knowledge_bases(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- MENSAJES
-------------------------------------------------------------

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID
        REFERENCES conversations(id)
        ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- FUENTES UTILIZADAS
-------------------------------------------------------------

CREATE TABLE message_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID
        REFERENCES messages(id)
        ON DELETE CASCADE,
    document_id UUID
        REFERENCES documents(id),
    chunk_id VARCHAR(100),
    similarity_score REAL
);

-------------------------------------------------------------
-- TOKENS REVOCADOS
-------------------------------------------------------------

CREATE TABLE revoked_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- LOGS API
-------------------------------------------------------------

CREATE TABLE api_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID
        REFERENCES users(id),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    execution_time_ms INTEGER,
    status_code INTEGER,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-------------------------------------------------------------
-- API-KEYS
-------------------------------------------------------------
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL
        REFERENCES tenants(id)
        ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    api_key UUID DEFAULT gen_random_uuid(),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);


CREATE TABLE department_members (
    department_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role_id UUID NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (department_id, user_id),

    CONSTRAINT fk_department
        FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_role
        FOREIGN KEY (role_id)
        REFERENCES roles(id)
        ON DELETE SET NULL
);


CREATE TABLE evaluations_results (
    id UUID PRIMARY KEY,
    question TEXT,
    category TEXT,
    reference_answer TEXT,
    system_answer TEXT,
    accuracy_score FLOAT, -- Calificación del 1 al 5
    retrieval_score FLOAT, -- Éxito en encontrar el chunk (0 o 1)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_tenants (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'MEMBER', -- 'OWNER', 'ADMIN', 'MEMBER', 'VIEWER'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tenant_id)
);

CREATE TABLE shipments (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    product VARCHAR(100),
    container_id VARCHAR(50),
    origin_name VARCHAR(255),
    origin_lat FLOAT,
    origin_lng FLOAT,
    destination_name VARCHAR(255),
    destination_lat FLOAT,
    destination_lng FLOAT,
    vessel_name VARCHAR(100),
    departure_date TIMESTAMP,
    eta TIMESTAMP,
    current_step INT,
    temperature_threshold FLOAT
);
-------------------------------------------------------------
-- ÍNDICES
-------------------------------------------------------------

CREATE INDEX idx_users_email
ON users(email);
CREATE INDEX idx_members_user
ON organization_members(user_id);
CREATE INDEX idx_members_org
ON organization_members(organization_id);
CREATE INDEX idx_departments_org
ON departments(organization_id);
CREATE INDEX idx_tenants_org
ON tenants(organization_id);
CREATE INDEX idx_documents_owner
ON documents(owner_id);
CREATE INDEX idx_documents_tenant
ON documents(tenant_id);
CREATE INDEX idx_documents_kb
ON documents(knowledge_base_id);
CREATE INDEX idx_conversations_user
ON conversations(user_id);
CREATE INDEX idx_conversations_tenant
ON conversations(tenant_id);
CREATE INDEX idx_messages_conversation
ON messages(conversation_id);
CREATE INDEX idx_jobs_document
ON processing_jobs(document_id);
CREATE INDEX idx_logs_user
ON api_logs(user_id);
CREATE INDEX idx_permissions_member
ON knowledge_base_permissions(member_id);
CREATE INDEX idx_department_members_department
ON department_members(department_id);
CREATE INDEX idx_department_members_user
ON department_members(user_id);
 