-- DataFlux PostgreSQL Schema
-- Universal AI-native database for media content

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- =================================
-- Core Tables
-- =================================

-- Base entity table for all content
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL, -- 'asset', 'segment', 'collection'
    parent_id UUID REFERENCES entities(id),
    version INTEGER DEFAULT 1,
    version_of UUID REFERENCES entities(id), -- Points to original
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_latest BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT valid_entity_type CHECK (entity_type IN ('asset', 'segment', 'collection'))
);

-- Assets (files)
CREATE TABLE assets (
    id UUID PRIMARY KEY REFERENCES entities(id),
    filename TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    storage_path TEXT NOT NULL,
    upload_context TEXT,
    processing_status VARCHAR(20) DEFAULT 'queued',
    processing_priority INTEGER DEFAULT 5,
    confidence_score FLOAT DEFAULT 0.0,
    thumbnail_path TEXT,
    proxy_path TEXT,
    
    CONSTRAINT valid_processing_status CHECK (processing_status IN ('queued', 'processing', 'completed', 'failed')),
    CONSTRAINT valid_priority CHECK (processing_priority BETWEEN 1 AND 10),
    CONSTRAINT valid_confidence CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    UNIQUE(file_hash)
);

-- Universal segments
CREATE TABLE segments (
    id UUID PRIMARY KEY REFERENCES entities(id),
    asset_id UUID NOT NULL REFERENCES assets(id),
    segment_type VARCHAR(50) NOT NULL, -- 'scene', 'paragraph', 'region', 'frame'
    sequence_number INTEGER NOT NULL,
    start_marker JSONB NOT NULL, -- {time: 1.5} or {page: 1, line: 10}
    end_marker JSONB NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    duration FLOAT, -- Duration in seconds for time-based segments
    
    CONSTRAINT valid_segment_type CHECK (segment_type IN ('scene', 'paragraph', 'region', 'frame', 'chunk')),
    CONSTRAINT valid_confidence CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    CONSTRAINT valid_duration CHECK (duration IS NULL OR duration > 0)
);

-- Features extracted from segments
CREATE TABLE features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    segment_id UUID NOT NULL REFERENCES segments(id),
    feature_domain VARCHAR(50) NOT NULL, -- 'visual', 'semantic', 'style', 'technical', 'audio'
    feature_type VARCHAR(100) NOT NULL, -- 'object_detection', 'sentiment', etc.
    feature_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    analyzer_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_feature_domain CHECK (feature_domain IN ('visual', 'semantic', 'style', 'technical', 'audio', 'text')),
    CONSTRAINT valid_feature_confidence CHECK (confidence BETWEEN 0.0 AND 1.0)
);

-- Embeddings for vector search
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES entities(id),
    embedding_type VARCHAR(50) NOT NULL, -- 'visual', 'text', 'audio', 'multimodal'
    model_name VARCHAR(100) NOT NULL,
    vector_id VARCHAR(100) NOT NULL, -- Reference to vector DB
    dimensions INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_embedding_type CHECK (embedding_type IN ('visual', 'text', 'audio', 'multimodal')),
    CONSTRAINT valid_dimensions CHECK (dimensions > 0)
);

-- Relationships between entities
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES entities(id),
    target_id UUID NOT NULL REFERENCES entities(id),
    relationship_type VARCHAR(50) NOT NULL, -- 'similar_to', 'derived_from', 'contains', 'part_of'
    strength FLOAT NOT NULL DEFAULT 0.0, -- 0.0 to 1.0
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_relationship_type CHECK (relationship_type IN ('similar_to', 'derived_from', 'contains', 'part_of', 'related_to')),
    CONSTRAINT valid_strength CHECK (strength BETWEEN 0.0 AND 1.0),
    CONSTRAINT no_self_relationship CHECK (source_id != target_id)
);

-- Collections for grouping assets
CREATE TABLE collections (
    id UUID PRIMARY KEY REFERENCES entities(id),
    name TEXT NOT NULL,
    description TEXT,
    auto_generated BOOLEAN DEFAULT false,
    asset_count INTEGER DEFAULT 0,
    
    CONSTRAINT valid_name CHECK (LENGTH(name) > 0)
);

-- User permissions
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    entity_id UUID REFERENCES entities(id),
    permission_type VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    granted_by UUID,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_permission_type CHECK (permission_type IN ('read', 'write', 'delete', 'share', 'admin')),
    UNIQUE(user_id, entity_id, permission_type)
);

-- Feedback for learning
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    entity_id UUID NOT NULL REFERENCES entities(id),
    feedback_type VARCHAR(50) NOT NULL,
    feedback_value BOOLEAN NOT NULL, -- true = positive, false = negative
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_feedback_type CHECK (feedback_type IN ('relevance', 'accuracy', 'quality', 'usefulness'))
);

-- =================================
-- Indexes for Performance
-- =================================

-- Entity indexes
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_parent ON entities(parent_id);
CREATE INDEX idx_entities_version ON entities(version_of);
CREATE INDEX idx_entities_created ON entities(created_at DESC);
CREATE INDEX idx_entities_latest ON entities(is_latest) WHERE is_latest = true;

-- Asset indexes
CREATE INDEX idx_assets_hash ON assets(file_hash);
CREATE INDEX idx_assets_mime_type ON assets(mime_type);
CREATE INDEX idx_assets_status ON assets(processing_status);
CREATE INDEX idx_assets_priority ON assets(processing_priority);
CREATE INDEX idx_assets_created ON assets(created_at DESC);
CREATE INDEX idx_assets_filename_trgm ON assets USING gin(filename gin_trgm_ops);

-- Segment indexes
CREATE INDEX idx_segments_asset ON segments(asset_id);
CREATE INDEX idx_segments_type ON segments(segment_type);
CREATE INDEX idx_segments_sequence ON segments(sequence_number);
CREATE INDEX idx_segments_confidence ON segments(confidence_score DESC);

-- Feature indexes
CREATE INDEX idx_features_segment ON features(segment_id);
CREATE INDEX idx_features_domain_type ON features(feature_domain, feature_type);
CREATE INDEX idx_features_confidence ON features(confidence DESC);
CREATE INDEX idx_features_created ON features(created_at DESC);

-- Embedding indexes
CREATE INDEX idx_embeddings_entity ON embeddings(entity_id);
CREATE INDEX idx_embeddings_type ON embeddings(embedding_type);
CREATE INDEX idx_embeddings_model ON embeddings(model_name);

-- Relationship indexes
CREATE INDEX idx_relationships_source ON relationships(source_id);
CREATE INDEX idx_relationships_target ON relationships(target_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
CREATE INDEX idx_relationships_strength ON relationships(strength DESC);

-- Permission indexes
CREATE INDEX idx_permissions_user ON permissions(user_id);
CREATE INDEX idx_permissions_entity ON permissions(entity_id);
CREATE INDEX idx_permissions_type ON permissions(permission_type);

-- Feedback indexes
CREATE INDEX idx_feedback_entity ON feedback(entity_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);
CREATE INDEX idx_feedback_created ON feedback(created_at DESC);

-- JSONB indexes for metadata
CREATE INDEX idx_entities_metadata ON entities USING gin(metadata);
CREATE INDEX idx_features_data ON features USING gin(feature_data);
CREATE INDEX idx_relationships_metadata ON relationships USING gin(metadata);

-- =================================
-- Views for Common Queries
-- =================================

-- Asset details with segment count
CREATE VIEW asset_details AS
SELECT 
    a.*,
    e.created_at,
    e.updated_at,
    e.metadata as entity_metadata,
    COUNT(s.id) as segment_count,
    AVG(s.confidence_score) as avg_segment_confidence
FROM assets a
JOIN entities e ON a.id = e.id
LEFT JOIN segments s ON a.id = s.asset_id
GROUP BY a.id, e.created_at, e.updated_at, e.metadata, a.filename, a.file_hash, a.file_size, a.mime_type, a.storage_path, a.upload_context, a.processing_status, a.processing_priority, a.confidence_score, a.thumbnail_path, a.proxy_path;

-- Segment details with features
CREATE VIEW segment_details AS
SELECT 
    s.*,
    a.filename,
    a.mime_type,
    COUNT(f.id) as feature_count,
    AVG(f.confidence) as avg_feature_confidence
FROM segments s
JOIN assets a ON s.asset_id = a.id
LEFT JOIN features f ON s.id = f.segment_id
GROUP BY s.id, a.filename, a.mime_type;

-- Collection statistics
CREATE VIEW collection_stats AS
SELECT 
    c.*,
    COUNT(a.id) as actual_asset_count,
    AVG(a.confidence_score) as avg_confidence
FROM collections c
JOIN entities e ON c.id = e.id
LEFT JOIN assets a ON e.id = a.id
GROUP BY c.id, c.name, c.description, c.auto_generated, c.asset_count;

-- =================================
-- Functions and Triggers
-- =================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to entities
CREATE TRIGGER update_entities_updated_at 
    BEFORE UPDATE ON entities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply updated_at trigger to assets
CREATE TRIGGER update_assets_updated_at 
    BEFORE UPDATE ON assets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update asset count in collections
CREATE OR REPLACE FUNCTION update_collection_asset_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE collections 
        SET asset_count = asset_count + 1 
        WHERE id = NEW.parent_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE collections 
        SET asset_count = asset_count - 1 
        WHERE id = OLD.parent_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

-- Apply asset count trigger
CREATE TRIGGER update_collection_count_on_asset_insert
    AFTER INSERT ON assets
    FOR EACH ROW EXECUTE FUNCTION update_collection_asset_count();

CREATE TRIGGER update_collection_count_on_asset_delete
    AFTER DELETE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_collection_asset_count();

-- =================================
-- Initial Data
-- =================================

-- Create default collection
INSERT INTO entities (id, entity_type, metadata) 
VALUES (uuid_generate_v4(), 'collection', '{"name": "Default Collection", "description": "Default collection for all assets"}');

INSERT INTO collections (id, name, description, auto_generated)
SELECT id, 'Default Collection', 'Default collection for all assets', false
FROM entities 
WHERE entity_type = 'collection' 
ORDER BY created_at DESC 
LIMIT 1;

-- =================================
-- Comments
-- =================================

COMMENT ON TABLE entities IS 'Base table for all content entities (assets, segments, collections)';
COMMENT ON TABLE assets IS 'Media files with metadata and processing status';
COMMENT ON TABLE segments IS 'Segmented parts of assets (scenes, paragraphs, regions)';
COMMENT ON TABLE features IS 'AI-extracted features from segments';
COMMENT ON TABLE embeddings IS 'Vector embeddings for similarity search';
COMMENT ON TABLE relationships IS 'Relationships between entities';
COMMENT ON TABLE collections IS 'Groupings of related assets';
COMMENT ON TABLE permissions IS 'User permissions for entities';
COMMENT ON TABLE feedback IS 'User feedback for learning and improvement';
