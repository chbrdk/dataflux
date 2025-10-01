-- DataFlux Schema Migration
-- Update existing schema to support multi-media features

-- Step 1: Add asset_id column to features table
ALTER TABLE features ADD COLUMN asset_id UUID REFERENCES assets(id);

-- Step 2: Make segment_id nullable
ALTER TABLE features ALTER COLUMN segment_id DROP NOT NULL;

-- Step 3: Add constraint to ensure features belong to either asset or segment
ALTER TABLE features ADD CONSTRAINT feature_must_belong_to_asset_or_segment CHECK (
    (asset_id IS NOT NULL AND segment_id IS NULL) OR 
    (asset_id IS NOT NULL AND segment_id IS NOT NULL)
);

-- Step 4: Add index for asset_id
CREATE INDEX IF NOT EXISTS idx_features_asset ON features(asset_id);

-- Step 5: Create asset_features view
CREATE OR REPLACE VIEW asset_features AS
SELECT 
    a.id,
    a.filename,
    a.file_hash,
    a.file_size,
    a.mime_type,
    a.storage_path,
    a.upload_context,
    a.processing_status,
    a.processing_priority,
    a.confidence_score,
    a.thumbnail_path,
    a.proxy_path,
    e.created_at,
    e.updated_at,
    COUNT(f.id) as feature_count,
    AVG(f.confidence) as avg_feature_confidence,
    ARRAY_AGG(DISTINCT f.feature_domain) as feature_domains,
    ARRAY_AGG(DISTINCT f.feature_type) as feature_types
FROM assets a
JOIN entities e ON a.id = e.id
LEFT JOIN features f ON a.id = f.asset_id AND f.segment_id IS NULL
GROUP BY a.id, a.filename, a.file_hash, a.file_size, a.mime_type, a.storage_path, a.upload_context, a.processing_status, a.processing_priority, a.confidence_score, a.thumbnail_path, a.proxy_path, e.created_at, e.updated_at;

-- Step 6: Update existing features to have asset_id (if they don't have it)
UPDATE features 
SET asset_id = (
    SELECT s.asset_id 
    FROM segments s 
    WHERE s.id = features.segment_id
)
WHERE asset_id IS NULL AND segment_id IS NOT NULL;

-- Step 7: Add comment
COMMENT ON COLUMN features.asset_id IS 'Direct reference to asset for asset-level features (images, documents)';
COMMENT ON COLUMN features.segment_id IS 'Optional reference to segment for segment-level features (videos, audio)';
