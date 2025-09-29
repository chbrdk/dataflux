package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// WeaviateConfig holds Weaviate configuration
type WeaviateConfig struct {
	URL     string
	Timeout time.Duration
}

// WeaviateClient handles Weaviate operations
type WeaviateClient struct {
	config     WeaviateConfig
	httpClient *http.Client
}

// NewWeaviateClient creates a new Weaviate client
func NewWeaviateClient(url string) *WeaviateClient {
	return &WeaviateClient{
		config: WeaviateConfig{
			URL:     url,
			Timeout: 30 * time.Second,
		},
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// HealthCheck checks if Weaviate is healthy
func (w *WeaviateClient) HealthCheck() bool {
	resp, err := w.httpClient.Get(w.config.URL + "/v1/meta")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200
}

// SearchRequest represents a search request to Weaviate
type SearchRequest struct {
	Class    string                 `json:"class"`
	Query    string                 `json:"query,omitempty"`
	Vector   []float64              `json:"vector,omitempty"`
	Limit    int                    `json:"limit"`
	Offset   int                    `json:"offset"`
	Where    map[string]interface{} `json:"where,omitempty"`
	Hybrid   bool                   `json:"hybrid,omitempty"`
}

// SearchResponse represents a search response from Weaviate
type SearchResponse struct {
	Data struct {
		Get map[string][]WeaviateObject `json:"Get"`
	} `json:"data"`
}

// WeaviateObject represents an object in Weaviate
type WeaviateObject struct {
	Additional struct {
		ID       string  `json:"id"`
		Distance float64 `json:"distance"`
		Score    float64 `json:"score"`
	} `json:"_additional"`
	EntityID         string                 `json:"entity_id"`
	Filename         string                 `json:"filename"`
	MimeType         string                 `json:"mime_type"`
	FileSize         int64                  `json:"file_size"`
	ProcessingStatus string                 `json:"processing_status"`
	CreatedAt        string                 `json:"created_at"`
	Metadata         map[string]interface{} `json:"metadata"`
	Tags             []string               `json:"tags"`
	CollectionID     string                 `json:"collection_id"`
}

// SearchSimilarAssets searches for similar assets using vector similarity
func (w *WeaviateClient) SearchSimilarAssets(queryVector []float64, limit int, collectionID string) ([]WeaviateObject, error) {
	whereFilter := make(map[string]interface{})
	if collectionID != "" {
		whereFilter = map[string]interface{}{
			"path":     []string{"collection_id"},
			"operator": "Equal",
			"valueString": collectionID,
		}
	}

	searchReq := SearchRequest{
		Class:  "Asset",
		Vector: queryVector,
		Limit:  limit,
		Where:  whereFilter,
	}

	return w.performSearch(searchReq)
}

// HybridSearch performs hybrid search (text + vector)
func (w *WeaviateClient) HybridSearch(queryText string, queryVector []float64, limit int) ([]WeaviateObject, error) {
	searchReq := SearchRequest{
		Class:  "Asset",
		Query:  queryText,
		Vector: queryVector,
		Limit:  limit,
		Hybrid: true,
	}

	return w.performSearch(searchReq)
}

// TextSearch performs text-only search
func (w *WeaviateClient) TextSearch(queryText string, limit int) ([]WeaviateObject, error) {
	searchReq := SearchRequest{
		Class: "Asset",
		Query: queryText,
		Limit: limit,
	}

	return w.performSearch(searchReq)
}

// performSearch executes a search request
func (w *WeaviateClient) performSearch(req SearchRequest) ([]WeaviateObject, error) {
	// Build GraphQL query
	query := w.buildGraphQLQuery(req)
	
	// Create request body
	requestBody := map[string]interface{}{
		"query":     query,
		"variables": req,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	// Make HTTP request
	resp, err := w.httpClient.Post(
		w.config.URL+"/v1/graphql",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %v", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	// Parse response
	var searchResp SearchResponse
	if err := json.Unmarshal(body, &searchResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %v", err)
	}

	// Extract results
	if assets, exists := searchResp.Data.Get[req.Class]; exists {
		return assets, nil
	}

	return []WeaviateObject{}, nil
}

// buildGraphQLQuery builds a GraphQL query for Weaviate
func (w *WeaviateClient) buildGraphQLQuery(req SearchRequest) string {
	var queryParts []string
	
	// Base query structure
	query := fmt.Sprintf(`
		query($class: String!, $query: String, $vector: [Float], $limit: Int, $offset: Int, $where: WhereFilter) {
			Get {
				%s(
					limit: $limit
					offset: $offset`, req.Class)

	// Add search parameters
	if req.Query != "" {
		query += `
					bm25: {query: $query}`
	}
	
	if len(req.Vector) > 0 {
		query += `
					nearVector: {vector: $vector}`
	}
	
	if req.Where != nil {
		query += `
					where: $where`
	}

	// Close query and add fields
	query += fmt.Sprintf(`
				) {
					_additional {
						id
						distance
						score
					}
					... on %s {
						entity_id
						filename
						mime_type
						file_size
						processing_status
						created_at
						metadata
						tags
						collection_id
					}
				}
			}
		}`, req.Class)

	return query
}

// GetObject retrieves an object by ID
func (w *WeaviateClient) GetObject(objectID string) (*WeaviateObject, error) {
	resp, err := w.httpClient.Get(w.config.URL + "/v1/objects/" + objectID)
	if err != nil {
		return nil, fmt.Errorf("failed to get object: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("object not found: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	var obj WeaviateObject
	if err := json.Unmarshal(body, &obj); err != nil {
		return nil, fmt.Errorf("failed to unmarshal object: %v", err)
	}

	return &obj, nil
}

// CreateObject creates a new object in Weaviate
func (w *WeaviateClient) CreateObject(class string, properties map[string]interface{}, vector []float64) (string, error) {
	objData := map[string]interface{}{
		"class":      class,
		"properties": properties,
	}

	if len(vector) > 0 {
		objData["vector"] = vector
	}

	jsonData, err := json.Marshal(objData)
	if err != nil {
		return "", fmt.Errorf("failed to marshal object: %v", err)
	}

	resp, err := w.httpClient.Post(
		w.config.URL+"/v1/objects",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return "", fmt.Errorf("failed to create object: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("failed to create object: %d - %s", resp.StatusCode, string(body))
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("failed to decode response: %v", err)
	}

	if id, exists := result["id"]; exists {
		return id.(string), nil
	}

	return "", fmt.Errorf("no ID returned from Weaviate")
}

// UpdateObject updates an existing object
func (w *WeaviateClient) UpdateObject(objectID string, properties map[string]interface{}, vector []float64) error {
	objData := map[string]interface{}{
		"properties": properties,
	}

	if len(vector) > 0 {
		objData["vector"] = vector
	}

	jsonData, err := json.Marshal(objData)
	if err != nil {
		return fmt.Errorf("failed to marshal update: %v", err)
	}

	req, err := http.NewRequest("PATCH", w.config.URL+"/v1/objects/"+objectID, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := w.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to update object: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to update object: %d - %s", resp.StatusCode, string(body))
	}

	return nil
}

// DeleteObject deletes an object by ID
func (w *WeaviateClient) DeleteObject(objectID string) error {
	req, err := http.NewRequest("DELETE", w.config.URL+"/v1/objects/"+objectID, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}

	resp, err := w.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to delete object: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("failed to delete object: %d", resp.StatusCode)
	}

	return nil
}

// Mock implementation for testing
type MockWeaviateClient struct {
	objects map[string]WeaviateObject
}

func NewMockWeaviateClient() *MockWeaviateClient {
	return &MockWeaviateClient{
		objects: make(map[string]WeaviateObject),
	}
}

func (m *MockWeaviateClient) HealthCheck() bool {
	return true
}

func (m *MockWeaviateClient) SearchSimilarAssets(queryVector []float64, limit int, collectionID string) ([]WeaviateObject, error) {
	// Mock implementation - return empty results
	return []WeaviateObject{}, nil
}

func (m *MockWeaviateClient) HybridSearch(queryText string, queryVector []float64, limit int) ([]WeaviateObject, error) {
	// Mock implementation - return empty results
	return []WeaviateObject{}, nil
}

func (m *MockWeaviateClient) TextSearch(queryText string, limit int) ([]WeaviateObject, error) {
	// Mock implementation - return empty results
	return []WeaviateObject{}, nil
}

func (m *MockWeaviateClient) GetObject(objectID string) (*WeaviateObject, error) {
	if obj, exists := m.objects[objectID]; exists {
		return &obj, nil
	}
	return nil, fmt.Errorf("object not found")
}

func (m *MockWeaviateClient) CreateObject(class string, properties map[string]interface{}, vector []float64) (string, error) {
	objectID := fmt.Sprintf("mock_%d", len(m.objects))
	obj := WeaviateObject{
		EntityID:         objectID,
		Filename:         properties["filename"].(string),
		MimeType:         properties["mime_type"].(string),
		FileSize:         int64(properties["file_size"].(int)),
		ProcessingStatus: properties["processing_status"].(string),
		CreatedAt:        properties["created_at"].(string),
		Tags:             properties["tags"].([]string),
		CollectionID:     properties["collection_id"].(string),
	}
	m.objects[objectID] = obj
	return objectID, nil
}

func (m *MockWeaviateClient) UpdateObject(objectID string, properties map[string]interface{}, vector []float64) error {
	if obj, exists := m.objects[objectID]; exists {
		// Update properties
		if filename, ok := properties["filename"].(string); ok {
			obj.Filename = filename
		}
		m.objects[objectID] = obj
		return nil
	}
	return fmt.Errorf("object not found")
}

func (m *MockWeaviateClient) DeleteObject(objectID string) error {
	if _, exists := m.objects[objectID]; exists {
		delete(m.objects, objectID)
		return nil
	}
	return fmt.Errorf("object not found")
}
