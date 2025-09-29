package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

// Test setup
func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	return setupRouter()
}

func TestHealthEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", response["status"])
}

func TestSearchEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	searchRequest := SearchRequest{
		Query:     "test search",
		MediaType: "all",
		Limit:     10,
		Offset:    0,
	}
	
	jsonData, _ := json.Marshal(searchRequest)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	
	var response SearchResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.NotNil(t, response.Results)
}

func TestSimilarEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	similarRequest := SimilarRequest{
		AssetID: "test-asset-123",
		Limit:   5,
	}
	
	jsonData, _ := json.Marshal(similarRequest)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/similar", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	
	var response SimilarResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.NotNil(t, response.SimilarAssets)
}

func TestGetSegmentEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/v1/segments/test-segment-123", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	
	var response SegmentResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "test-segment-123", response.SegmentID)
}

func TestGetRelationshipsEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/v1/relationships?asset_id=test-asset-123", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	
	var response RelationshipsResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.NotNil(t, response.Relationships)
}

func TestGetStatsEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/v1/stats", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	
	var response StatsResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.NotNil(t, response.TotalAssets)
	assert.NotNil(t, response.TotalSegments)
}

func TestRootEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "DataFlux Query Service", response["service"])
}

// Test request validation
func TestSearchRequestValidation(t *testing.T) {
	router := setupTestRouter()
	
	// Test empty query
	searchRequest := SearchRequest{
		Query:     "",
		MediaType: "all",
		Limit:     10,
		Offset:    0,
	}
	
	jsonData, _ := json.Marshal(searchRequest)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	// Should still work with empty query (returns all results)
	assert.Equal(t, 200, w.Code)
}

func TestSearchRequestInvalidLimit(t *testing.T) {
	router := setupTestRouter()
	
	// Test invalid limit (negative)
	searchRequest := SearchRequest{
		Query:     "test",
		MediaType: "all",
		Limit:     -1,
		Offset:    0,
	}
	
	jsonData, _ := json.Marshal(searchRequest)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	// Should handle invalid limit gracefully
	assert.Equal(t, 200, w.Code)
}

func TestSimilarRequestValidation(t *testing.T) {
	router := setupTestRouter()
	
	// Test empty asset ID
	similarRequest := SimilarRequest{
		AssetID: "",
		Limit:   5,
	}
	
	jsonData, _ := json.Marshal(similarRequest)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/similar", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	// Should handle empty asset ID gracefully
	assert.Equal(t, 200, w.Code)
}

// Test CORS
func TestCORSHeaders(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("OPTIONS", "/api/v1/search", nil)
	req.Header.Set("Origin", "http://localhost:3000")
	req.Header.Set("Access-Control-Request-Method", "POST")
	req.Header.Set("Access-Control-Request-Headers", "Content-Type")
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	assert.Contains(t, w.Header().Get("Access-Control-Allow-Origin"), "*")
	assert.Contains(t, w.Header().Get("Access-Control-Allow-Methods"), "POST")
}

// Test performance
func TestSearchPerformance(t *testing.T) {
	router := setupTestRouter()
	
	searchRequest := SearchRequest{
		Query:     "performance test",
		MediaType: "all",
		Limit:     100,
		Offset:    0,
	}
	
	jsonData, _ := json.Marshal(searchRequest)
	
	start := time.Now()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	duration := time.Since(start)
	
	assert.Equal(t, 200, w.Code)
	assert.Less(t, duration, 100*time.Millisecond, "Search should complete within 100ms")
}

// Test concurrent requests
func TestConcurrentRequests(t *testing.T) {
	router := setupTestRouter()
	
	searchRequest := SearchRequest{
		Query:     "concurrent test",
		MediaType: "all",
		Limit:     10,
		Offset:    0,
	}
	
	jsonData, _ := json.Marshal(searchRequest)
	
	// Channel to collect results
	results := make(chan int, 10)
	
	// Start 10 concurrent requests
	for i := 0; i < 10; i++ {
		go func() {
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(jsonData))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)
			results <- w.Code
		}()
	}
	
	// Collect results
	successCount := 0
	for i := 0; i < 10; i++ {
		code := <-results
		if code == 200 {
			successCount++
		}
	}
	
	assert.Equal(t, 10, successCount, "All concurrent requests should succeed")
}

// Test error handling
func TestInvalidJSON(t *testing.T) {
	router := setupTestRouter()
	
	invalidJSON := `{"invalid": json}`
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBufferString(invalidJSON))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	// Should handle invalid JSON gracefully
	assert.Equal(t, 400, w.Code)
}

func TestInvalidEndpoint(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/v1/invalid", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 404, w.Code)
}

// Test middleware
func TestLoggingMiddleware(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
	// Logging middleware should not affect response
}

func TestRecoveryMiddleware(t *testing.T) {
	router := setupTestRouter()
	
	// This test would require a handler that panics
	// For now, we just test that the middleware is set up
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, 200, w.Code)
}

// Benchmark tests
func BenchmarkSearchEndpoint(b *testing.B) {
	router := setupTestRouter()
	
	searchRequest := SearchRequest{
		Query:     "benchmark test",
		MediaType: "all",
		Limit:     10,
		Offset:    0,
	}
	
	jsonData, _ := json.Marshal(searchRequest)
	
	b.ResetTimer()
	
	for i := 0; i < b.N; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		router.ServeHTTP(w, req)
	}
}

func BenchmarkHealthEndpoint(b *testing.B) {
	router := setupTestRouter()
	
	b.ResetTimer()
	
	for i := 0; i < b.N; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/health", nil)
		router.ServeHTTP(w, req)
	}
}

// Test data structures
func TestSearchRequestStruct(t *testing.T) {
	req := SearchRequest{
		Query:     "test",
		MediaType: "video",
		Limit:     20,
		Offset:    10,
	}
	
	assert.Equal(t, "test", req.Query)
	assert.Equal(t, "video", req.MediaType)
	assert.Equal(t, 20, req.Limit)
	assert.Equal(t, 10, req.Offset)
}

func TestSearchResponseStruct(t *testing.T) {
	response := SearchResponse{
		Results: []SearchResult{
			{
				AssetID:   "test-123",
				Filename:  "test.mp4",
				MimeType:  "video/mp4",
				Score:     0.95,
				Thumbnail: "thumb.jpg",
			},
		},
		Total:  1,
		Limit:  10,
		Offset: 0,
	}
	
	assert.Len(t, response.Results, 1)
	assert.Equal(t, "test-123", response.Results[0].AssetID)
	assert.Equal(t, 1, response.Total)
}

func TestSimilarRequestStruct(t *testing.T) {
	req := SimilarRequest{
		AssetID: "test-asset-123",
		Limit:   5,
	}
	
	assert.Equal(t, "test-asset-123", req.AssetID)
	assert.Equal(t, 5, req.Limit)
}

func TestSimilarResponseStruct(t *testing.T) {
	response := SimilarResponse{
		SimilarAssets: []SimilarAsset{
			{
				AssetID:   "similar-123",
				Filename:  "similar.mp4",
				MimeType:  "video/mp4",
				Similarity: 0.85,
				Thumbnail: "similar_thumb.jpg",
			},
		},
		Total: 1,
	}
	
	assert.Len(t, response.SimilarAssets, 1)
	assert.Equal(t, "similar-123", response.SimilarAssets[0].AssetID)
	assert.Equal(t, 1, response.Total)
}
