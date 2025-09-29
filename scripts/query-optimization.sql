-- Query Optimization Scripts for DataFlux
-- Advanced query optimization and performance tuning

-- ==============================================
-- QUERY OPTIMIZATION FUNCTIONS
-- ==============================================

-- Function to analyze query performance
CREATE OR REPLACE FUNCTION analyze_query_performance(query_text TEXT)
RETURNS TABLE(
    plan_type TEXT,
    cost NUMERIC,
    rows BIGINT,
    width INTEGER,
    startup_cost NUMERIC,
    total_cost NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    EXECUTE 'EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) ' || query_text;
END;
$$ LANGUAGE plpgsql;

-- Function to get slow queries
CREATE OR REPLACE FUNCTION get_slow_queries(min_duration_ms INTEGER DEFAULT 1000)
RETURNS TABLE(
    query TEXT,
    calls BIGINT,
    total_time NUMERIC,
    mean_time NUMERIC,
    rows BIGINT,
    shared_blks_hit BIGINT,
    shared_blks_read BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pg_stat_statements.query,
        pg_stat_statements.calls,
        pg_stat_statements.total_exec_time,
        pg_stat_statements.mean_exec_time,
        pg_stat_statements.rows,
        pg_stat_statements.shared_blks_hit,
        pg_stat_statements.shared_blks_read
    FROM pg_stat_statements
    WHERE pg_stat_statements.mean_exec_time > min_duration_ms
    ORDER BY pg_stat_statements.mean_exec_time DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get table statistics
CREATE OR REPLACE FUNCTION get_table_stats()
RETURNS TABLE(
    table_name TEXT,
    row_count BIGINT,
    table_size TEXT,
    index_size TEXT,
    total_size TEXT,
    last_analyze TIMESTAMP,
    last_autoanalyze TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname||'.'||tablename as table_name,
        n_tup_ins - n_tup_del as row_count,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as table_size,
        pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
        last_analyze,
        last_autoanalyze
    FROM pg_stat_user_tables
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get index usage statistics
CREATE OR REPLACE FUNCTION get_index_usage_stats()
RETURNS TABLE(
    table_name TEXT,
    index_name TEXT,
    index_scans BIGINT,
    tuples_read BIGINT,
    tuples_fetched BIGINT,
    index_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname||'.'||tablename as table_name,
        indexname as index_name,
        idx_scan as index_scans,
        idx_tup_read as tuples_read,
        idx_tup_fetch as tuples_fetched,
        pg_size_pretty(pg_relation_size(indexrelid)) as index_size
    FROM pg_stat_user_indexes
    ORDER BY idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- OPTIMIZED QUERIES FOR COMMON OPERATIONS
-- ==============================================

-- Optimized asset search query
CREATE OR REPLACE FUNCTION search_assets_optimized(
    search_query TEXT DEFAULT '',
    collection_id UUID DEFAULT NULL,
    mime_type_filter TEXT DEFAULT NULL,
    limit_count INTEGER DEFAULT 50,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE(
    asset_id UUID,
    file_name TEXT,
    mime_type TEXT,
    file_size BIGINT,
    created_at TIMESTAMP WITH TIME ZONE,
    thumbnail_path TEXT,
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    WITH search_results AS (
        SELECT 
            a.asset_id,
            a.file_name,
            a.mime_type,
            a.file_size,
            a.created_at,
            a.thumbnail_path,
            CASE 
                WHEN search_query = '' THEN 1.0
                ELSE ts_rank(
                    to_tsvector('english', a.file_name || ' ' || COALESCE(a.description, '') || ' ' || COALESCE(array_to_string(a.tags, ' '), '')),
                    plainto_tsquery('english', search_query)
                )
            END as similarity_score
        FROM assets a
        WHERE a.is_active = true
        AND (collection_id IS NULL OR a.collection_id = collection_id)
        AND (mime_type_filter IS NULL OR a.mime_type LIKE mime_type_filter)
        AND (
            search_query = '' OR
            to_tsvector('english', a.file_name || ' ' || COALESCE(a.description, '') || ' ' || COALESCE(array_to_string(a.tags, ' '), ''))
            @@ plainto_tsquery('english', search_query)
        )
    )
    SELECT 
        sr.asset_id,
        sr.file_name,
        sr.mime_type,
        sr.file_size,
        sr.created_at,
        sr.thumbnail_path,
        sr.similarity_score
    FROM search_results sr
    ORDER BY sr.similarity_score DESC, sr.created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Optimized asset statistics query
CREATE OR REPLACE FUNCTION get_asset_statistics_optimized(
    collection_id UUID DEFAULT NULL,
    date_from TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    date_to TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS TABLE(
    total_assets BIGINT,
    total_size BIGINT,
    avg_size NUMERIC,
    mime_type_counts JSONB,
    size_distribution JSONB,
    upload_timeline JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH asset_stats AS (
        SELECT 
            COUNT(*) as total_assets,
            SUM(file_size) as total_size,
            AVG(file_size) as avg_size
        FROM assets
        WHERE is_active = true
        AND (collection_id IS NULL OR collection_id = collection_id)
        AND (date_from IS NULL OR created_at >= date_from)
        AND (date_to IS NULL OR created_at <= date_to)
    ),
    mime_type_stats AS (
        SELECT jsonb_object_agg(mime_type, count) as mime_type_counts
        FROM (
            SELECT mime_type, COUNT(*) as count
            FROM assets
            WHERE is_active = true
            AND (collection_id IS NULL OR collection_id = collection_id)
            AND (date_from IS NULL OR created_at >= date_from)
            AND (date_to IS NULL OR created_at <= date_to)
            GROUP BY mime_type
            ORDER BY count DESC
        ) t
    ),
    size_distribution_stats AS (
        SELECT jsonb_build_object(
            'small', COUNT(*) FILTER (WHERE file_size < 1024 * 1024),
            'medium', COUNT(*) FILTER (WHERE file_size >= 1024 * 1024 AND file_size < 100 * 1024 * 1024),
            'large', COUNT(*) FILTER (WHERE file_size >= 100 * 1024 * 1024)
        ) as size_distribution
        FROM assets
        WHERE is_active = true
        AND (collection_id IS NULL OR collection_id = collection_id)
        AND (date_from IS NULL OR created_at >= date_from)
        AND (date_to IS NULL OR created_at <= date_to)
    ),
    upload_timeline_stats AS (
        SELECT jsonb_object_agg(date_trunc('day', created_at)::text, count) as upload_timeline
        FROM (
            SELECT date_trunc('day', created_at) as day, COUNT(*) as count
            FROM assets
            WHERE is_active = true
            AND (collection_id IS NULL OR collection_id = collection_id)
            AND (date_from IS NULL OR created_at >= date_from)
            AND (date_to IS NULL OR created_at <= date_to)
            GROUP BY date_trunc('day', created_at)
            ORDER BY day DESC
            LIMIT 30
        ) t
    )
    SELECT 
        ast.total_assets,
        ast.total_size,
        ast.avg_size,
        mts.mime_type_counts,
        sds.size_distribution,
        uts.upload_timeline
    FROM asset_stats ast
    CROSS JOIN mime_type_stats mts
    CROSS JOIN size_distribution_stats sds
    CROSS JOIN upload_timeline_stats uts;
END;
$$ LANGUAGE plpgsql;

-- Optimized segment search query
CREATE OR REPLACE FUNCTION search_segments_optimized(
    asset_id UUID DEFAULT NULL,
    segment_type TEXT DEFAULT NULL,
    min_confidence REAL DEFAULT 0.5,
    limit_count INTEGER DEFAULT 100
)
RETURNS TABLE(
    segment_id UUID,
    asset_id UUID,
    segment_type TEXT,
    start_time NUMERIC,
    end_time NUMERIC,
    confidence_score REAL,
    segment_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.segment_id,
        s.asset_id,
        s.segment_type,
        s.start_time,
        s.end_time,
        s.confidence_score,
        s.segment_data
    FROM segments s
    WHERE s.is_active = true
    AND (asset_id IS NULL OR s.asset_id = asset_id)
    AND (segment_type IS NULL OR s.segment_type = segment_type)
    AND s.confidence_score >= min_confidence
    ORDER BY s.confidence_score DESC, s.start_time ASC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Optimized relationship traversal query
CREATE OR REPLACE FUNCTION get_related_assets_optimized(
    source_asset_id UUID,
    relationship_type TEXT DEFAULT NULL,
    max_depth INTEGER DEFAULT 2,
    limit_count INTEGER DEFAULT 50
)
RETURNS TABLE(
    target_asset_id UUID,
    relationship_type TEXT,
    confidence_score REAL,
    depth INTEGER,
    path TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE relationship_path AS (
        -- Base case: direct relationships
        SELECT 
            r.target_entity_id::UUID as target_asset_id,
            r.relationship_type,
            r.confidence_score,
            1 as depth,
            ARRAY[r.source_entity_id::TEXT, r.target_entity_id::TEXT] as path
        FROM relationships r
        WHERE r.source_entity_id = source_asset_id
        AND r.is_active = true
        AND (relationship_type IS NULL OR r.relationship_type = relationship_type)
        
        UNION ALL
        
        -- Recursive case: indirect relationships
        SELECT 
            r.target_entity_id::UUID as target_asset_id,
            r.relationship_type,
            r.confidence_score,
            rp.depth + 1,
            rp.path || r.target_entity_id::TEXT
        FROM relationships r
        JOIN relationship_path rp ON r.source_entity_id::UUID = rp.target_asset_id
        WHERE rp.depth < max_depth
        AND r.is_active = true
        AND (relationship_type IS NULL OR r.relationship_type = relationship_type)
        AND NOT (r.target_entity_id::TEXT = ANY(rp.path))  -- Avoid cycles
    )
    SELECT DISTINCT
        rp.target_asset_id,
        rp.relationship_type,
        rp.confidence_score,
        rp.depth,
        rp.path
    FROM relationship_path rp
    ORDER BY rp.confidence_score DESC, rp.depth ASC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- PERFORMANCE MONITORING VIEWS
-- ==============================================

-- View for monitoring query performance
CREATE OR REPLACE VIEW query_performance_monitor AS
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows,
    shared_blks_hit,
    shared_blks_read,
    shared_blks_written,
    local_blks_hit,
    local_blks_read,
    local_blks_written,
    temp_blks_read,
    temp_blks_written,
    blk_read_time,
    blk_write_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC;

-- View for monitoring table performance
CREATE OR REPLACE VIEW table_performance_monitor AS
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    vacuum_count,
    autovacuum_count,
    analyze_count,
    autoanalyze_count
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;

-- View for monitoring index performance
CREATE OR REPLACE VIEW index_performance_monitor AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- ==============================================
-- MAINTENANCE FUNCTIONS
-- ==============================================

-- Function to update table statistics
CREATE OR REPLACE FUNCTION update_table_statistics()
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
        RAISE NOTICE 'Analyzed table: %', table_record.tablename;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to vacuum tables
CREATE OR REPLACE FUNCTION vacuum_tables()
RETURNS void AS $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'VACUUM ANALYZE ' || table_record.tablename;
        RAISE NOTICE 'Vacuumed table: %', table_record.tablename;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to reindex tables
CREATE OR REPLACE FUNCTION reindex_tables()
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
        RAISE NOTICE 'Reindexed index: %', index_record.indexname;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- PERFORMANCE CONFIGURATION
-- ==============================================

-- Enable query plan caching
-- ALTER SYSTEM SET plan_cache_mode = 'force_custom_plan';

-- Set work_mem for better performance
-- ALTER SYSTEM SET work_mem = '256MB';

-- Set shared_buffers
-- ALTER SYSTEM SET shared_buffers = '1GB';

-- Set effective_cache_size
-- ALTER SYSTEM SET effective_cache_size = '4GB';

-- Set random_page_cost for SSD
-- ALTER SYSTEM SET random_page_cost = 1.1;

-- Set seq_page_cost for SSD
-- ALTER SYSTEM SET seq_page_cost = 1.0;

-- Enable parallel queries
-- ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
-- ALTER SYSTEM SET max_parallel_workers = 8;

-- Set maintenance_work_mem
-- ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- ==============================================
-- EXAMPLE USAGE
-- ==============================================

-- Example: Search assets with optimization
-- SELECT * FROM search_assets_optimized('video', NULL, 'video/%', 20, 0);

-- Example: Get asset statistics
-- SELECT * FROM get_asset_statistics_optimized();

-- Example: Search segments
-- SELECT * FROM search_segments_optimized(NULL, 'scene', 0.7, 50);

-- Example: Get related assets
-- SELECT * FROM get_related_assets_optimized('asset-uuid-here', 'similar', 2, 30);

-- Example: Monitor performance
-- SELECT * FROM query_performance_monitor LIMIT 10;
-- SELECT * FROM table_performance_monitor LIMIT 10;
-- SELECT * FROM index_performance_monitor LIMIT 10;

-- Example: Maintenance
-- SELECT update_table_statistics();
-- SELECT vacuum_tables();
-- SELECT reindex_tables();
