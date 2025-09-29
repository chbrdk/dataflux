package neo4j

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Neo4jConfig holds Neo4j configuration
type Neo4jConfig struct {
	URL      string
	Username string
	Password string
	Timeout  time.Duration
}

// Neo4jClient handles Neo4j operations
type Neo4jClient struct {
	config     Neo4jConfig
	httpClient *http.Client
}

// NewNeo4jClient creates a new Neo4j client
func NewNeo4jClient(url, username, password string) *Neo4jClient {
	return &Neo4jClient{
		config: Neo4jConfig{
			URL:      url,
			Username: username,
			Password: password,
			Timeout:  30 * time.Second,
		},
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// HealthCheck checks if Neo4j is healthy
func (n *Neo4jClient) HealthCheck() bool {
	req, err := http.NewRequest("GET", n.config.URL+"/db/data/", nil)
	if err != nil {
		return false
	}
	req.SetBasicAuth(n.config.Username, n.config.Password)

	resp, err := n.httpClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == 200
}

// CypherRequest represents a Cypher request
type CypherRequest struct {
	Statement  string                 `json:"statement"`
	Parameters map[string]interface{} `json:"parameters"`
}

// CypherResponse represents a Cypher response
type CypherResponse struct {
	Results []struct {
		Columns []string `json:"columns"`
		Data    []struct {
			Row []interface{} `json:"row"`
		} `json:"data"`
	} `json:"results"`
	Errors []struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"errors"`
}

// ExecuteCypher executes a Cypher query
func (n *Neo4jClient) ExecuteCypher(query string, parameters map[string]interface{}) (*CypherResponse, error) {
	url := n.config.URL + "/db/data/transaction/commit"

	payload := map[string]interface{}{
		"statements": []CypherRequest{
			{
				Statement:  query,
				Parameters: parameters,
			},
		},
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}
	req.SetBasicAuth(n.config.Username, n.config.Password)
	req.Header.Set("Content-Type", "application/json")

	resp, err := n.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	var cypherResp CypherResponse
	if err := json.Unmarshal(body, &cypherResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %v", err)
	}

	if len(cypherResp.Errors) > 0 {
		return nil, fmt.Errorf("cypher error: %s", cypherResp.Errors[0].Message)
	}

	return &cypherResp, nil
}

// Asset represents an asset node
type Asset struct {
	EntityID         string                 `json:"entity_id"`
	AssetID          string                 `json:"asset_id"`
	Filename         string                 `json:"filename"`
	MimeType         string                 `json:"mime_type"`
	FileSize         int64                  `json:"file_size"`
	ProcessingStatus string                 `json:"processing_status"`
	CreatedAt        string                 `json:"created_at"`
	UpdatedAt        string                 `json:"updated_at"`
	Metadata         map[string]interface{} `json:"metadata"`
	Tags             []string               `json:"tags"`
	CollectionID     string                 `json:"collection_id"`
}

// Segment represents a segment node
type Segment struct {
	EntityID          string                 `json:"entity_id"`
	SegmentID         string                 `json:"segment_id"`
	AssetID           string                 `json:"asset_id"`
	SegmentType       string                 `json:"segment_type"`
	SequenceNumber    int                    `json:"sequence_number"`
	StartTime         float64                `json:"start_time"`
	EndTime           float64                `json:"end_time"`
	ConfidenceScore   float64                `json:"confidence_score"`
	ContentDescription string                `json:"content_description"`
	DetectedObjects   []string               `json:"detected_objects"`
	DetectedText      string                 `json:"detected_text"`
	CreatedAt         string                 `json:"created_at"`
	UpdatedAt         string                 `json:"updated_at"`
}

// SimilarAsset represents a similar asset result
type SimilarAsset struct {
	AssetID         string  `json:"asset_id"`
	Filename        string  `json:"filename"`
	MimeType        string  `json:"mime_type"`
	SimilarityScore float64 `json:"similarity_score"`
}

// Recommendation represents a content recommendation
type Recommendation struct {
	AssetID         string   `json:"asset_id"`
	Filename        string   `json:"filename"`
	MimeType        string   `json:"mime_type"`
	Tags            []string `json:"tags"`
	SimilarityScore float64  `json:"similarity_score"`
	SimilarityType  string   `json:"similarity_type"`
}

// CreateAsset creates an asset node
func (n *Neo4jClient) CreateAsset(asset Asset) error {
	query := `
		CREATE (a:Asset:Entity {
			entity_id: $entity_id,
			asset_id: $asset_id,
			filename: $filename,
			mime_type: $mime_type,
			file_size: $file_size,
			processing_status: $processing_status,
			created_at: $created_at,
			updated_at: $updated_at,
			metadata: $metadata,
			tags: $tags,
			collection_id: $collection_id
		})
		RETURN a
	`

	parameters := map[string]interface{}{
		"entity_id":         asset.EntityID,
		"asset_id":          asset.AssetID,
		"filename":          asset.Filename,
		"mime_type":         asset.MimeType,
		"file_size":         asset.FileSize,
		"processing_status": asset.ProcessingStatus,
		"created_at":        asset.CreatedAt,
		"updated_at":        asset.UpdatedAt,
		"metadata":          asset.Metadata,
		"tags":              asset.Tags,
		"collection_id":     asset.CollectionID,
	}

	_, err := n.ExecuteCypher(query, parameters)
	return err
}

// CreateSegment creates a segment node
func (n *Neo4jClient) CreateSegment(segment Segment) error {
	query := `
		CREATE (s:Segment:Entity {
			entity_id: $entity_id,
			segment_id: $segment_id,
			asset_id: $asset_id,
			segment_type: $segment_type,
			sequence_number: $sequence_number,
			start_time: $start_time,
			end_time: $end_time,
			confidence_score: $confidence_score,
			content_description: $content_description,
			detected_objects: $detected_objects,
			detected_text: $detected_text,
			created_at: $created_at,
			updated_at: $updated_at
		})
		RETURN s
	`

	parameters := map[string]interface{}{
		"entity_id":           segment.EntityID,
		"segment_id":          segment.SegmentID,
		"asset_id":            segment.AssetID,
		"segment_type":        segment.SegmentType,
		"sequence_number":     segment.SequenceNumber,
		"start_time":          segment.StartTime,
		"end_time":            segment.EndTime,
		"confidence_score":    segment.ConfidenceScore,
		"content_description": segment.ContentDescription,
		"detected_objects":    segment.DetectedObjects,
		"detected_text":       segment.DetectedText,
		"created_at":          segment.CreatedAt,
		"updated_at":          segment.UpdatedAt,
	}

	_, err := n.ExecuteCypher(query, parameters)
	return err
}

// CreateAssetSegmentRelationship creates a relationship between asset and segment
func (n *Neo4jClient) CreateAssetSegmentRelationship(assetID, segmentID string, sequence int) error {
	query := `
		MATCH (a:Asset {asset_id: $asset_id}), (s:Segment {segment_id: $segment_id})
		CREATE (a)-[:CONTAINS {
			relationship_type: 'contains',
			sequence: $sequence,
			created_at: datetime()
		}]->(s)
		RETURN a, s
	`

	parameters := map[string]interface{}{
		"asset_id":  assetID,
		"segment_id": segmentID,
		"sequence":  sequence,
	}

	_, err := n.ExecuteCypher(query, parameters)
	return err
}

// CreateSimilarityRelationship creates a similarity relationship between assets
func (n *Neo4jClient) CreateSimilarityRelationship(asset1ID, asset2ID string, score float64, similarityType string) error {
	query := `
		MATCH (a1:Asset {asset_id: $asset1_id}), (a2:Asset {asset_id: $asset2_id})
		CREATE (a1)-[:SIMILAR_TO {
			similarity_score: $score,
			similarity_type: $type,
			created_at: datetime(),
			metadata: '{"algorithm": "content_similarity"}'
		}]->(a2)
		RETURN a1, a2
	`

	parameters := map[string]interface{}{
		"asset1_id": asset1ID,
		"asset2_id": asset2ID,
		"score":     score,
		"type":      similarityType,
	}

	_, err := n.ExecuteCypher(query, parameters)
	return err
}

// FindSimilarAssets finds assets similar to a given asset
func (n *Neo4jClient) FindSimilarAssets(assetID string, threshold float64, limit int) ([]SimilarAsset, error) {
	query := `
		MATCH (a1:Asset {asset_id: $asset_id})-[r:SIMILAR_TO]->(a2:Asset)
		WHERE r.similarity_score >= $threshold
		RETURN a2.asset_id, a2.filename, a2.mime_type, r.similarity_score
		ORDER BY r.similarity_score DESC
		LIMIT $limit
	`

	parameters := map[string]interface{}{
		"asset_id":  assetID,
		"threshold": threshold,
		"limit":     limit,
	}

	resp, err := n.ExecuteCypher(query, parameters)
	if err != nil {
		return nil, err
	}

	var similarAssets []SimilarAsset
	if len(resp.Results) > 0 && len(resp.Results[0].Data) > 0 {
		for _, row := range resp.Results[0].Data {
			if len(row.Row) >= 4 {
				similarAssets = append(similarAssets, SimilarAsset{
					AssetID:         row.Row[0].(string),
					Filename:        row.Row[1].(string),
					MimeType:        row.Row[2].(string),
					SimilarityScore: row.Row[3].(float64),
				})
			}
		}
	}

	return similarAssets, nil
}

// GetRecommendations gets content recommendations based on similarity
func (n *Neo4jClient) GetRecommendations(assetID string, limit int) ([]Recommendation, error) {
	query := `
		MATCH (a1:Asset {asset_id: $asset_id})-[r:SIMILAR_TO]->(a2:Asset)
		WHERE r.similarity_score >= 0.6
		RETURN a2.asset_id, a2.filename, a2.mime_type, a2.tags,
		       r.similarity_score, r.similarity_type
		ORDER BY r.similarity_score DESC
		LIMIT $limit
	`

	parameters := map[string]interface{}{
		"asset_id": assetID,
		"limit":    limit,
	}

	resp, err := n.ExecuteCypher(query, parameters)
	if err != nil {
		return nil, err
	}

	var recommendations []Recommendation
	if len(resp.Results) > 0 && len(resp.Results[0].Data) > 0 {
		for _, row := range resp.Results[0].Data {
			if len(row.Row) >= 6 {
				tags := []string{}
				if tagsInterface, ok := row.Row[3].([]interface{}); ok {
					for _, tag := range tagsInterface {
						if tagStr, ok := tag.(string); ok {
							tags = append(tags, tagStr)
						}
					}
				}

				recommendations = append(recommendations, Recommendation{
					AssetID:         row.Row[0].(string),
					Filename:        row.Row[1].(string),
					MimeType:        row.Row[2].(string),
					Tags:            tags,
					SimilarityScore: row.Row[4].(float64),
					SimilarityType:  row.Row[5].(string),
				})
			}
		}
	}

	return recommendations, nil
}

// FindObjectsInSegments finds segments containing specific objects
func (n *Neo4jClient) FindObjectsInSegments(objectName string, limit int) ([]map[string]interface{}, error) {
	query := `
		MATCH (s:Segment)
		WHERE $object_name IN s.detected_objects
		MATCH (a:Asset)-[:CONTAINS]->(s)
		RETURN s.segment_id, s.content_description, s.detected_objects,
		       a.asset_id, a.filename
		ORDER BY s.confidence_score DESC
		LIMIT $limit
	`

	parameters := map[string]interface{}{
		"object_name": objectName,
		"limit":       limit,
	}

	resp, err := n.ExecuteCypher(query, parameters)
	if err != nil {
		return nil, err
	}

	var results []map[string]interface{}
	if len(resp.Results) > 0 && len(resp.Results[0].Data) > 0 {
		for _, row := range resp.Results[0].Data {
			if len(row.Row) >= 5 {
				detectedObjects := []string{}
				if objectsInterface, ok := row.Row[2].([]interface{}); ok {
					for _, obj := range objectsInterface {
						if objStr, ok := obj.(string); ok {
							detectedObjects = append(detectedObjects, objStr)
						}
					}
				}

				results = append(results, map[string]interface{}{
					"segment_id":         row.Row[0].(string),
					"content_description": row.Row[1].(string),
					"detected_objects":   detectedObjects,
					"asset_id":           row.Row[3].(string),
					"filename":           row.Row[4].(string),
				})
			}
		}
	}

	return results, nil
}

// GetAssetSegments gets all segments of an asset
func (n *Neo4jClient) GetAssetSegments(assetID string) ([]map[string]interface{}, error) {
	query := `
		MATCH (a:Asset {asset_id: $asset_id})-[:CONTAINS]->(s:Segment)
		RETURN s.segment_id, s.segment_type, s.sequence_number,
		       s.start_time, s.end_time, s.content_description
		ORDER BY s.sequence_number
	`

	parameters := map[string]interface{}{
		"asset_id": assetID,
	}

	resp, err := n.ExecuteCypher(query, parameters)
	if err != nil {
		return nil, err
	}

	var segments []map[string]interface{}
	if len(resp.Results) > 0 && len(resp.Results[0].Data) > 0 {
		for _, row := range resp.Results[0].Data {
			if len(row.Row) >= 6 {
				segments = append(segments, map[string]interface{}{
					"segment_id":          row.Row[0].(string),
					"segment_type":        row.Row[1].(string),
					"sequence_number":     row.Row[2].(int),
					"start_time":          row.Row[3].(float64),
					"end_time":            row.Row[4].(float64),
					"content_description": row.Row[5].(string),
				})
			}
		}
	}

	return segments, nil
}

// GetGraphStatistics gets graph database statistics
func (n *Neo4jClient) GetGraphStatistics() (map[string]interface{}, error) {
	query := `
		MATCH (n)
		OPTIONAL MATCH (n)-[r]->()
		RETURN 
			labels(n)[0] as label,
			count(n) as count,
			count(r) as relationships
		ORDER BY count DESC
	`

	resp, err := n.ExecuteCypher(query, nil)
	if err != nil {
		return nil, err
	}

	stats := map[string]interface{}{
		"total_nodes":       0,
		"total_relationships": 0,
		"by_label":          map[string]interface{}{},
	}

	if len(resp.Results) > 0 && len(resp.Results[0].Data) > 0 {
		for _, row := range resp.Results[0].Data {
			if len(row.Row) >= 3 {
				label := row.Row[0].(string)
				count := row.Row[1].(int)
				relationships := row.Row[2].(int)

				stats["total_nodes"] = stats["total_nodes"].(int) + count
				stats["total_relationships"] = stats["total_relationships"].(int) + relationships

				byLabel := stats["by_label"].(map[string]interface{})
				byLabel[label] = map[string]interface{}{
					"nodes":        count,
					"relationships": relationships,
				}
			}
		}
	}

	return stats, nil
}

// Mock implementation for testing
type MockNeo4jClient struct {
	assets      map[string]Asset
	segments    map[string]Segment
	similarities []map[string]interface{}
}

func NewMockNeo4jClient() *MockNeo4jClient {
	return &MockNeo4jClient{
		assets:      make(map[string]Asset),
		segments:    make(map[string]Segment),
		similarities: []map[string]interface{}{},
	}
}

func (m *MockNeo4jClient) HealthCheck() bool {
	return true
}

func (m *MockNeo4jClient) ExecuteCypher(query string, parameters map[string]interface{}) (*CypherResponse, error) {
	// Mock implementation - return empty results
	return &CypherResponse{
		Results: []struct {
			Columns []string `json:"columns"`
			Data    []struct {
				Row []interface{} `json:"row"`
			} `json:"data"`
		}{},
		Errors: []struct {
			Code    string `json:"code"`
			Message string `json:"message"`
		}{},
	}, nil
}

func (m *MockNeo4jClient) CreateAsset(asset Asset) error {
	m.assets[asset.AssetID] = asset
	return nil
}

func (m *MockNeo4jClient) CreateSegment(segment Segment) error {
	m.segments[segment.SegmentID] = segment
	return nil
}

func (m *MockNeo4jClient) CreateSimilarityRelationship(asset1ID, asset2ID string, score float64, similarityType string) error {
	m.similarities = append(m.similarities, map[string]interface{}{
		"asset1": asset1ID,
		"asset2": asset2ID,
		"score":  score,
		"type":   similarityType,
	})
	return nil
}

func (m *MockNeo4jClient) FindSimilarAssets(assetID string, threshold float64, limit int) ([]SimilarAsset, error) {
	// Mock implementation - return empty results
	return []SimilarAsset{}, nil
}

func (m *MockNeo4jClient) GetRecommendations(assetID string, limit int) ([]Recommendation, error) {
	// Mock implementation - return empty results
	return []Recommendation{}, nil
}
