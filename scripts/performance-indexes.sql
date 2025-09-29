-- Advanced Database Indexes for DataFlux Performance Optimization
-- Comprehensive indexing strategy for optimal query performance

-- ==============================================
-- PRIMARY KEY INDEXES (already exist, but documented)
-- ==============================================
-- These are automatically created by PostgreSQL
-- entities: PRIMARY KEY (entity_id)
-- assets: PRIMARY KEY (asset_id)
-- segments: PRIMARY KEY (segment_id)
-- features: PRIMARY KEY (feature_id)
-- embeddings: PRIMARY KEY (embedding_id)
-- relationships: PRIMARY KEY (relationship_id)
-- collections: PRIMARY KEY (collection_id)
-- users: PRIMARY KEY (user_id)

-- ==============================================
-- UNIQUE INDEXES
-- ==============================================

-- Asset hash uniqueness (for deduplication)
CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_file_hash_unique 
ON assets(file_hash) 
WHERE file_hash IS NOT NULL;

-- User uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique 
ON users(username);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique 
ON users(email);

-- Collection uniqueness per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_collections_name_user_unique 
ON collections(name, created_by) 
WHERE is_active = true;

-- ==============================================
-- PERFORMANCE INDEXES FOR QUERIES
-- ==============================================

-- Asset queries by collection and status
CREATE INDEX IF NOT EXISTS idx_assets_collection_status 
ON assets(collection_id, status) 
WHERE is_active = true;

-- Asset queries by MIME type and size
CREATE INDEX IF NOT EXISTS idx_assets_mime_type_size 
ON assets(mime_type, file_size) 
WHERE is_active = true;

-- Asset queries by creation date (for time-based queries)
CREATE INDEX IF NOT EXISTS idx_assets_created_at 
ON assets(created_at DESC) 
WHERE is_active = true;

-- Asset queries by file name (for search)
CREATE INDEX IF NOT EXISTS idx_assets_file_name_gin 
ON assets USING gin(to_tsvector('english', file_name));

-- Asset queries by metadata (JSONB)
CREATE INDEX IF NOT EXISTS idx_assets_metadata_gin 
ON assets USING gin(metadata);

-- Asset queries by tags (array)
CREATE INDEX IF NOT EXISTS idx_assets_tags_gin 
ON assets USING gin(tags);

-- Segment queries by asset
CREATE INDEX IF NOT EXISTS idx_segments_asset_id 
ON segments(asset_id) 
WHERE is_active = true;

-- Segment queries by type and confidence
CREATE INDEX IF NOT EXISTS idx_segments_type_confidence 
ON segments(segment_type, confidence_score) 
WHERE is_active = true AND confidence_score > 0.5;

-- Segment queries by time range
CREATE INDEX IF NOT EXISTS idx_segments_time_range 
ON segments(start_time, end_time) 
WHERE is_active = true;

-- Feature queries by segment
CREATE INDEX IF NOT EXISTS idx_features_segment_id 
ON features(segment_id) 
WHERE is_active = true;

-- Feature queries by type and confidence
CREATE INDEX IF NOT EXISTS idx_features_type_confidence 
ON features(feature_type, confidence_score) 
WHERE is_active = true AND confidence_score > 0.5;

-- Embedding queries by asset
CREATE INDEX IF NOT EXISTS idx_embeddings_asset_id 
ON embeddings(asset_id) 
WHERE is_active = true;

-- Embedding queries by segment
CREATE INDEX IF NOT EXISTS idx_embeddings_segment_id 
ON embeddings(segment_id) 
WHERE is_active = true AND segment_id IS NOT NULL;

-- Embedding queries by model and dimension
CREATE INDEX IF NOT EXISTS idx_embeddings_model_dimension 
ON embeddings(model_name, dimension) 
WHERE is_active = true;

-- Relationship queries by source entity
CREATE INDEX IF NOT EXISTS idx_relationships_source_entity 
ON relationships(source_entity_id, relationship_type) 
WHERE is_active = true;

-- Relationship queries by target entity
CREATE INDEX IF NOT EXISTS idx_relationships_target_entity 
ON relationships(target_entity_id, relationship_type) 
WHERE is_active = true;

-- Relationship queries by type and confidence
CREATE INDEX IF NOT EXISTS idx_relationships_type_confidence 
ON relationships(relationship_type, confidence_score) 
WHERE is_active = true AND confidence_score > 0.5;

-- Collection queries by user
CREATE INDEX IF NOT EXISTS idx_collections_created_by 
ON collections(created_by) 
WHERE is_active = true;

-- Collection queries by name (for search)
CREATE INDEX IF NOT EXISTS idx_collections_name_gin 
ON collections USING gin(to_tsvector('english', name));

-- Collection queries by description (for search)
CREATE INDEX IF NOT EXISTS idx_collections_description_gin 
ON collections USING gin(to_tsvector('english', description));

-- ==============================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ==============================================

-- Asset search by collection, type, and date range
CREATE INDEX IF NOT EXISTS idx_assets_collection_type_date 
ON assets(collection_id, mime_type, created_at DESC) 
WHERE is_active = true;

-- Asset search by collection, status, and size
CREATE INDEX IF NOT EXISTS idx_assets_collection_status_size 
ON assets(collection_id, status, file_size) 
WHERE is_active = true;

-- Segment search by asset and type
CREATE INDEX IF NOT EXISTS idx_segments_asset_type 
ON segments(asset_id, segment_type) 
WHERE is_active = true;

-- Feature search by segment and type
CREATE INDEX IF NOT EXISTS idx_features_segment_type 
ON features(segment_id, feature_type) 
WHERE is_active = true;

-- Embedding search by asset and model
CREATE INDEX IF NOT EXISTS idx_embeddings_asset_model 
ON embeddings(asset_id, model_name) 
WHERE is_active = true;

-- Relationship search by source and type
CREATE INDEX IF NOT EXISTS idx_relationships_source_type 
ON relationships(source_entity_id, relationship_type) 
WHERE is_active = true;

-- ==============================================
-- PARTIAL INDEXES FOR SPECIFIC CONDITIONS
-- ==============================================

-- Active assets only
CREATE INDEX IF NOT EXISTS idx_assets_active 
ON assets(asset_id) 
WHERE is_active = true;

-- High confidence segments only
CREATE INDEX IF NOT EXISTS idx_segments_high_confidence 
ON segments(segment_id, confidence_score) 
WHERE is_active = true AND confidence_score > 0.8;

-- High confidence features only
CREATE INDEX IF NOT EXISTS idx_features_high_confidence 
ON features(feature_id, confidence_score) 
WHERE is_active = true AND confidence_score > 0.8;

-- Recent assets (last 30 days)
CREATE INDEX IF NOT EXISTS idx_assets_recent 
ON assets(created_at DESC) 
WHERE is_active = true AND created_at > NOW() - INTERVAL '30 days';

-- Large files only (> 100MB)
CREATE INDEX IF NOT EXISTS idx_assets_large_files 
ON assets(file_size DESC) 
WHERE is_active = true AND file_size > 100 * 1024 * 1024;

-- Video files only
CREATE INDEX IF NOT EXISTS idx_assets_video_files 
ON assets(asset_id, file_size) 
WHERE is_active = true AND mime_type LIKE 'video/%';

-- Image files only
CREATE INDEX IF NOT EXISTS idx_assets_image_files 
ON assets(asset_id, file_size) 
WHERE is_active = true AND mime_type LIKE 'image/%';

-- Audio files only
CREATE INDEX IF NOT EXISTS idx_assets_audio_files 
ON assets(asset_id, file_size) 
WHERE is_active = true AND mime_type LIKE 'audio/%';

-- ==============================================
-- COVERING INDEXES (INCLUDE COLUMNS)
-- ==============================================

-- Asset list query covering index
CREATE INDEX IF NOT EXISTS idx_assets_list_covering 
ON assets(collection_id, created_at DESC) 
INCLUDE (asset_id, file_name, mime_type, file_size, status);

-- Segment list query covering index
CREATE INDEX IF NOT EXISTS idx_segments_list_covering 
ON segments(asset_id, start_time) 
INCLUDE (segment_id, segment_type, confidence_score, end_time);

-- Feature list query covering index
CREATE INDEX IF NOT EXISTS idx_features_list_covering 
ON features(segment_id, feature_type) 
INCLUDE (feature_id, confidence_score, feature_data);

-- ==============================================
-- EXPRESSION INDEXES
-- ==============================================

-- Asset queries by file extension
CREATE INDEX IF NOT EXISTS idx_assets_file_extension 
ON assets((regexp_replace(file_name, '.*\.', ''))) 
WHERE is_active = true;

-- Asset queries by file size category
CREATE INDEX IF NOT EXISTS idx_assets_size_category 
ON assets(
    CASE 
        WHEN file_size < 1024 * 1024 THEN 'small'
        WHEN file_size < 100 * 1024 * 1024 THEN 'medium'
        ELSE 'large'
    END
) 
WHERE is_active = true;

-- Asset queries by creation month
CREATE INDEX IF NOT EXISTS idx_assets_creation_month 
ON assets(date_trunc('month', created_at)) 
WHERE is_active = true;

-- ==============================================
-- FULL-TEXT SEARCH INDEXES
-- ==============================================

-- Asset full-text search
CREATE INDEX IF NOT EXISTS idx_assets_fulltext 
ON assets USING gin(
    to_tsvector('english', 
        COALESCE(file_name, '') || ' ' || 
        COALESCE(description, '') || ' ' || 
        COALESCE(array_to_string(tags, ' '), '')
    )
);

-- Collection full-text search
CREATE INDEX IF NOT EXISTS idx_collections_fulltext 
ON collections USING gin(
    to_tsvector('english', 
        COALESCE(name, '') || ' ' || 
        COALESCE(description, '')
    )
);

-- ==============================================
-- STATISTICS AND ANALYTICS INDEXES
-- ==============================================

-- Asset statistics by collection
CREATE INDEX IF NOT EXISTS idx_assets_stats_collection 
ON assets(collection_id, mime_type, file_size, created_at) 
WHERE is_active = true;

-- User activity statistics
CREATE INDEX IF NOT EXISTS idx_users_activity 
ON users(last_login, created_at) 
WHERE is_active = true;

-- Collection statistics
CREATE INDEX IF NOT EXISTS idx_collections_stats 
ON collections(created_by, created_at, asset_count) 
WHERE is_active = true;

-- ==============================================
-- MAINTENANCE AND MONITORING
-- ==============================================

-- Update table statistics
ANALYZE entities;
ANALYZE assets;
ANALYZE segments;
ANALYZE features;
ANALYZE embeddings;
ANALYZE relationships;
ANALYZE collections;
ANALYZE users;

-- ==============================================
-- INDEX USAGE MONITORING VIEWS
-- ==============================================

-- Create view to monitor index usage
CREATE OR REPLACE VIEW index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Create view to monitor slow queries
CREATE OR REPLACE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
WHERE mean_time > 1000  -- Queries taking more than 1 second on average
ORDER BY mean_time DESC;

-- ==============================================
-- PERFORMANCE CONFIGURATION
-- ==============================================

-- Set work_mem for better performance (adjust based on available RAM)
-- ALTER SYSTEM SET work_mem = '256MB';

-- Set shared_buffers (adjust based on available RAM)
-- ALTER SYSTEM SET shared_buffers = '1GB';

-- Set effective_cache_size (adjust based on available RAM)
-- ALTER SYSTEM SET effective_cache_size = '4GB';

-- Set random_page_cost for SSD storage
-- ALTER SYSTEM SET random_page_cost = 1.1;

-- Set seq_page_cost for SSD storage
-- ALTER SYSTEM SET seq_page_cost = 1.0;

-- Enable query plan caching
-- ALTER SYSTEM SET plan_cache_mode = 'force_custom_plan';

-- ==============================================
-- INDEX MAINTENANCE FUNCTIONS
-- ==============================================

-- Function to rebuild indexes
CREATE OR REPLACE FUNCTION rebuild_indexes()
RETURNS void AS $$
DECLARE
    index_record RECORD;
BEGIN
    FOR index_record IN 
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'REINDEX INDEX ' || index_record.indexname;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to analyze all tables
CREATE OR REPLACE FUNCTION analyze_all_tables()
RETURNS void AS $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ANALYZE ' || table_record.tablename;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to get index bloat information
CREATE OR REPLACE FUNCTION get_index_bloat()
RETURNS TABLE(
    index_name TEXT,
    table_name TEXT,
    index_size BIGINT,
    bloat_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.indexname::TEXT,
        i.tablename::TEXT,
        pg_relation_size(i.indexrelid) as index_size,
        CASE 
            WHEN pg_relation_size(i.indexrelid) > 0 THEN
                (pg_relation_size(i.indexrelid) - pg_relation_size(i.relid))::NUMERIC / 
                pg_relation_size(i.indexrelid)::NUMERIC * 100
            ELSE 0
        END as bloat_ratio
    FROM pg_stat_user_indexes i
    WHERE pg_relation_size(i.indexrelid) > 1024 * 1024  -- Only indexes larger than 1MB
    ORDER BY bloat_ratio DESC;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- PERFORMANCE MONITORING QUERIES
-- ==============================================

-- Query to find unused indexes
-- SELECT schemaname, tablename, indexname, idx_scan 
-- FROM pg_stat_user_indexes 
-- WHERE idx_scan = 0 
-- ORDER BY schemaname, tablename, indexname;

-- Query to find most used indexes
-- SELECT schemaname, tablename, indexname, idx_scan 
-- FROM pg_stat_user_indexes 
-- ORDER BY idx_scan DESC 
-- LIMIT 20;

-- Query to find largest indexes
-- SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid)) as size
-- FROM pg_stat_user_indexes 
-- ORDER BY pg_relation_size(indexrelid) DESC 
-- LIMIT 20;

-- Query to find slow queries
-- SELECT query, calls, total_time, mean_time 
-- FROM pg_stat_statements 
-- ORDER BY mean_time DESC 
-- LIMIT 20;
