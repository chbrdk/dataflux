-- Authentication and Authorization Schema for DataFlux
-- Extends the existing schema with user management and permissions

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user', 'viewer', 'analyst')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE
);

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    access_token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address INET,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- User permissions table (for custom permissions beyond role-based)
CREATE TABLE IF NOT EXISTS user_permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    granted_by UUID REFERENCES users(user_id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE(user_id, resource, action)
);

-- Collections permissions (inheritance from collections)
CREATE TABLE IF NOT EXISTS collection_permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL REFERENCES collections(collection_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    permission_type VARCHAR(20) NOT NULL CHECK (permission_type IN ('read', 'write', 'admin')),
    granted_by UUID REFERENCES users(user_id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE(collection_id, user_id, permission_type)
);

-- API keys for service-to-service authentication
CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    permissions TEXT[] NOT NULL DEFAULT '{}',
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Audit log for authentication events
CREATE TABLE IF NOT EXISTS auth_audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active);

CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_resource ON user_permissions(resource);
CREATE INDEX IF NOT EXISTS idx_user_permissions_active ON user_permissions(is_active);

CREATE INDEX IF NOT EXISTS idx_collection_permissions_collection_id ON collection_permissions(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_permissions_user_id ON collection_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_collection_permissions_active ON collection_permissions(is_active);

CREATE INDEX IF NOT EXISTS idx_api_keys_service_name ON api_keys(service_name);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

CREATE INDEX IF NOT EXISTS idx_auth_audit_log_user_id ON auth_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_log_event_type ON auth_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_auth_audit_log_created_at ON auth_audit_log(created_at);

-- Functions for permission checking
CREATE OR REPLACE FUNCTION check_user_permission(
    p_user_id UUID,
    p_resource VARCHAR(100),
    p_action VARCHAR(50)
) RETURNS BOOLEAN AS $$
DECLARE
    user_role VARCHAR(20);
    has_permission BOOLEAN := FALSE;
BEGIN
    -- Get user role
    SELECT role INTO user_role FROM users WHERE user_id = p_user_id AND is_active = true;
    
    IF user_role IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check role-based permissions
    CASE user_role
        WHEN 'admin' THEN
            has_permission := TRUE; -- Admins have all permissions
        WHEN 'analyst' THEN
            has_permission := (p_resource = 'assets' AND p_action IN ('read', 'write')) OR
                             (p_resource = 'analytics' AND p_action IN ('read', 'write'));
        WHEN 'user' THEN
            has_permission := (p_resource = 'assets' AND p_action IN ('read', 'write'));
        WHEN 'viewer' THEN
            has_permission := (p_resource = 'assets' AND p_action = 'read') OR
                             (p_resource = 'analytics' AND p_action = 'read');
    END CASE;
    
    -- If role-based permission exists, return true
    IF has_permission THEN
        RETURN TRUE;
    END IF;
    
    -- Check custom user permissions
    SELECT EXISTS(
        SELECT 1 FROM user_permissions 
        WHERE user_id = p_user_id 
        AND resource = p_resource 
        AND action = p_action 
        AND is_active = true
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- Function to check collection permissions
CREATE OR REPLACE FUNCTION check_collection_permission(
    p_user_id UUID,
    p_collection_id UUID,
    p_permission_type VARCHAR(20)
) RETURNS BOOLEAN AS $$
DECLARE
    user_role VARCHAR(20);
    has_permission BOOLEAN := FALSE;
BEGIN
    -- Get user role
    SELECT role INTO user_role FROM users WHERE user_id = p_user_id AND is_active = true;
    
    IF user_role IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Admins have all permissions
    IF user_role = 'admin' THEN
        RETURN TRUE;
    END IF;
    
    -- Check collection-specific permissions
    SELECT EXISTS(
        SELECT 1 FROM collection_permissions 
        WHERE collection_id = p_collection_id 
        AND user_id = p_user_id 
        AND permission_type = p_permission_type
        AND is_active = true
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- Function to get user permissions
CREATE OR REPLACE FUNCTION get_user_permissions(p_user_id UUID)
RETURNS TABLE(resource VARCHAR(100), action VARCHAR(50)) AS $$
DECLARE
    user_role VARCHAR(20);
BEGIN
    -- Get user role
    SELECT role INTO user_role FROM users WHERE user_id = p_user_id AND is_active = true;
    
    IF user_role IS NULL THEN
        RETURN;
    END IF;
    
    -- Return role-based permissions
    CASE user_role
        WHEN 'admin' THEN
            RETURN QUERY VALUES 
                ('assets', 'read'), ('assets', 'write'), ('assets', 'delete'),
                ('analytics', 'read'), ('analytics', 'write'),
                ('users', 'admin'), ('system', 'admin');
        WHEN 'analyst' THEN
            RETURN QUERY VALUES 
                ('assets', 'read'), ('assets', 'write'),
                ('analytics', 'read'), ('analytics', 'write');
        WHEN 'user' THEN
            RETURN QUERY VALUES 
                ('assets', 'read'), ('assets', 'write');
        WHEN 'viewer' THEN
            RETURN QUERY VALUES 
                ('assets', 'read'), ('analytics', 'read');
    END CASE;
    
    -- Add custom permissions
    RETURN QUERY
    SELECT up.resource, up.action
    FROM user_permissions up
    WHERE up.user_id = p_user_id 
    AND up.is_active = true
    AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, full_name, role, is_active) 
VALUES (
    'admin', 
    'admin@dataflux.local', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Qz8K2C', -- admin123
    'System Administrator', 
    'admin', 
    true
) ON CONFLICT (username) DO NOTHING;

-- Insert default test users
INSERT INTO users (username, email, password_hash, full_name, role, is_active) 
VALUES 
    (
        'testuser', 
        'test@dataflux.local', 
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Qz8K2C', -- admin123
        'Test User', 
        'user', 
        true
    ),
    (
        'analyst', 
        'analyst@dataflux.local', 
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Qz8K2C', -- admin123
        'Data Analyst', 
        'analyst', 
        true
    ),
    (
        'viewer', 
        'viewer@dataflux.local', 
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Qz8K2C', -- admin123
        'Viewer User', 
        'viewer', 
        true
    )
ON CONFLICT (username) DO NOTHING;

-- Create default collection permissions for admin
INSERT INTO collection_permissions (collection_id, user_id, permission_type, granted_by)
SELECT 
    c.collection_id,
    u.user_id,
    'admin',
    u.user_id
FROM collections c, users u
WHERE u.username = 'admin'
AND c.name = 'default'
ON CONFLICT (collection_id, user_id, permission_type) DO NOTHING;
