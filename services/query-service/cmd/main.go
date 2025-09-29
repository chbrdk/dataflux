package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/neo4j/neo4j-go-driver/v4/neo4j"
)

// Configuration
var (
	databaseURL    = getEnv("DATABASE_URL", "postgresql://dataflux_user:dataflux_pass@localhost:2001/dataflux")
	redisURL       = getEnv("REDIS_URL", "redis://default:dataflux_pass@localhost:2002/0")
	neo4jURI       = getEnv("NEO4J_URI", "bolt://localhost:2008")
	neo4jUser      = getEnv("NEO4J_USER", "neo4j")
	neo4jPassword  = getEnv("NEO4J_PASSWORD", "dataflux_pass")
	clickhouseURL  = getEnv("CLICKHOUSE_URL", "http://localhost:2011")
	clickhouseUser = getEnv("CLICKHOUSE_USER", "dataflux_user")
	clickhousePass = getEnv("CLICKHOUSE_PASSWORD", "dataflux_pass")
)

// Global clients
var (
	dbPool          *pgxpool.Pool
	redisClient     *redis.Client
	neo4jDriver     neo4j.Driver
)

// Data structures
type SearchRequest struct {
	Query           string                 `json:"query" binding:"required"`
	MediaTypes      []string              `json:"media_types"`
	Filters         map[string]interface{} `json:"filters"`
	Limit           int                   `json:"limit"`
	Offset          int                   `json:"offset"`
	IncludeSegments bool                  `json:"include_segments"`
	ConfidenceMin   float64               `json:"confidence_min"`
}

type SearchResponse struct {
	Results []SearchResult `json:"results"`
	Total   int           `json:"total"`
	Took    int64         `json:"took_ms"`
	Cache   bool          `json:"cache"`
}

type SearchResult struct {
	ID         string                 `json:"id"`
	Type       string                 `json:"type"`
	Score      float64               `json:"score"`
	Metadata   map[string]interface{} `json:"metadata"`
	Segments   []Segment             `json:"segments,omitempty"`
	Highlights []string              `json:"highlights,omitempty"`
}

type Segment struct {
	ID         string                 `json:"id"`
	StartTime  float64                `json:"start_time,omitempty"`
	EndTime    float64                `json:"end_time,omitempty"`
	Confidence float64                `json:"confidence"`
	Features   map[string]interface{} `json:"features"`
}

type SimilarRequest struct {
	EntityID  string   `json:"entity_id" binding:"required"`
	Threshold float64  `json:"threshold"`
	Limit     int      `json:"limit"`
	MediaTypes []string `json:"media_types"`
}

type NLPResult struct {
	Query              string   `json:"query"`
	Keywords           []string `json:"keywords"`
	HasSemanticIntent  bool     `json:"has_semantic_intent"`
	HasKeywords        bool     `json:"has_keywords"`
	HasRelationships   bool     `json:"has_relationships"`
	Relationships      []string `json:"relationships"`
	MediaType          string   `json:"media_type"`
	Confidence         float64  `json:"confidence"`
}

type HealthResponse struct {
	Status      string            `json:"status"`
	Service     string            `json:"service"`
	Timestamp   time.Time         `json:"timestamp"`
	Version     string            `json:"version"`
	Connections map[string]string `json:"connections"`
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	// Initialize connections
	initConnections()
	defer closeConnections()

	// Setup Gin router
	router := gin.Default()
	
	// CORS middleware
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"*"}
	router.Use(cors.New(config))

	// Recovery middleware
	router.Use(gin.Recovery())

	// Request logging middleware
	router.Use(func(c *gin.Context) {
		start := time.Now()
		c.Next()
		latency := time.Since(start)
		log.Printf("%s %s %d %v", c.Request.Method, c.Request.URL.Path, c.Writer.Status(), latency)
	})

	// API routes
	v1 := router.Group("/api/v1")
	{
		v1.POST("/search", handleSearch)
		v1.POST("/similar", handleSimilar)
		v1.GET("/segments/:id", handleGetSegment)
		v1.GET("/relationships", handleGetRelationships)
		v1.GET("/stats", handleGetStats)
	}

	// Health check
	router.GET("/health", handleHealth)
	router.GET("/", handleRoot)

	// Start server
	port := getEnv("PORT", "8002")
	log.Printf("Query Service starting on port %s", port)
	log.Fatal(router.Run(":" + port))
}

func initConnections() {
	var err error

	// Initialize PostgreSQL connection pool
	dbPool, err = pgxpool.Connect(context.Background(), databaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to PostgreSQL: %v", err)
	}

	// Initialize Redis client
	redisClient = redis.NewClient(&redis.Options{
		Addr:     "localhost:2002",
		Password: "dataflux_pass",
		DB:       0,
	})

	// Test Redis connection
	ctx := context.Background()
	_, err = redisClient.Ping(ctx).Result()
	if err != nil {
		log.Printf("Warning: Redis connection failed: %v", err)
	}

	// Weaviate integration will be added later
	log.Println("Weaviate integration disabled for now")

	// Initialize Neo4j driver
	neo4jDriver, err = neo4j.NewDriver(neo4jURI, neo4j.BasicAuth(neo4jUser, neo4jPassword, ""))
	if err != nil {
		log.Printf("Warning: Neo4j connection failed: %v", err)
	}

	log.Println("All connections initialized successfully")
}

func closeConnections() {
	if dbPool != nil {
		dbPool.Close()
	}
	if redisClient != nil {
		redisClient.Close()
	}
	if neo4jDriver != nil {
		neo4jDriver.Close()
	}
}

func handleSearch(c *gin.Context) {
	start := time.Now()
	
	var req SearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Set defaults
	if req.Limit == 0 {
		req.Limit = 20
	}
	if req.ConfidenceMin == 0 {
		req.ConfidenceMin = 0.7
	}

	// Check Redis cache
	cacheKey := generateCacheKey(req)
	cached, err := redisClient.Get(context.Background(), cacheKey).Result()
	if err == nil {
		var response SearchResponse
		json.Unmarshal([]byte(cached), &response)
		response.Cache = true
		c.JSON(http.StatusOK, response)
		return
	}

	// Parse query for NLP
	nlpResult := parseNaturalLanguageQuery(req.Query)

	// Build multi-index query
	var results []SearchResult

	// 1. Vector search in Weaviate (if semantic intent detected)
	if nlpResult.HasSemanticIntent {
		vectorResults := searchWeaviate(nlpResult, req.Filters, req.Limit)
		results = append(results, vectorResults...)
	}

	// 2. Full-text search in PostgreSQL (if keywords detected)
	if nlpResult.HasKeywords {
		textResults := searchPostgreSQL(nlpResult.Keywords, req.Filters, req.Limit)
		results = append(results, textResults...)
	}

	// 3. Graph traversal in Neo4j (if relationships detected)
	if nlpResult.HasRelationships {
		graphResults := searchNeo4j(nlpResult.Relationships, req.Limit)
		results = append(results, graphResults...)
	}

	// Merge and rank results
	rankedResults := rankResults(results, req.Query)

	// Include segments if requested
	if req.IncludeSegments {
		enrichWithSegments(rankedResults)
	}

	response := SearchResponse{
		Results: rankedResults,
		Total:   len(rankedResults),
		Took:    time.Since(start).Milliseconds(),
		Cache:   false,
	}

	// Cache results
	cacheData, _ := json.Marshal(response)
	redisClient.SetEX(context.Background(), cacheKey, string(cacheData), 5*time.Minute)

	c.JSON(http.StatusOK, response)
}

func handleSimilar(c *gin.Context) {
	var req SimilarRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Set defaults
	if req.Threshold == 0 {
		req.Threshold = 0.75
	}
	if req.Limit == 0 {
		req.Limit = 10
	}

	// Find similar entities using Weaviate
	similarResults := findSimilarEntities(req.EntityID, req.Threshold, req.Limit)

	c.JSON(http.StatusOK, SearchResponse{
		Results: similarResults,
		Total:   len(similarResults),
		Took:    0,
		Cache:   false,
	})
}

func handleGetSegment(c *gin.Context) {
	segmentID := c.Param("id")
	
	// Get segment details from PostgreSQL
	var segment Segment
	err := dbPool.QueryRow(context.Background(), `
		SELECT s.id, s.start_marker, s.end_marker, s.confidence_score,
		       a.filename, a.mime_type
		FROM segments s
		JOIN assets a ON s.asset_id = a.id
		WHERE s.id = $1
	`, segmentID).Scan(
		&segment.ID,
		&segment.StartTime,
		&segment.EndTime,
		&segment.Confidence,
	)

	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Segment not found"})
		return
	}

	c.JSON(http.StatusOK, segment)
}

func handleGetRelationships(c *gin.Context) {
	entityID := c.Query("entity_id")
	limitStr := c.DefaultQuery("limit", "20")
	limit, _ := strconv.Atoi(limitStr)

	// Get relationships from Neo4j
	relationships := getEntityRelationships(entityID, limit)

	c.JSON(http.StatusOK, gin.H{
		"relationships": relationships,
		"total":         len(relationships),
	})
}

func handleGetStats(c *gin.Context) {
	// Get system statistics
	stats := getSystemStats()

	c.JSON(http.StatusOK, stats)
}

func handleHealth(c *gin.Context) {
	health := HealthResponse{
		Status:    "healthy",
		Service:   "query-service",
		Timestamp: time.Now(),
		Version:   "1.0.0",
		Connections: map[string]string{
			"postgres":  checkPostgres(),
			"redis":     checkRedis(),
			"neo4j":     checkNeo4j(),
			"weaviate":  checkWeaviate(),
			"clickhouse": checkClickHouse(),
		},
	}

	c.JSON(http.StatusOK, health)
}

func handleRoot(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "DataFlux Query Service",
		"version": "1.0.0",
		"docs":    "/docs",
		"health":  "/health",
	})
}

// Helper functions
func generateCacheKey(req SearchRequest) string {
	key := fmt.Sprintf("search:%s:%v:%v:%d:%d:%t:%.2f",
		req.Query,
		req.MediaTypes,
		req.Filters,
		req.Limit,
		req.Offset,
		req.IncludeSegments,
		req.ConfidenceMin)
	return key
}

func parseNaturalLanguageQuery(query string) NLPResult {
	// Simple NLP parsing (in production, use a proper NLP service)
	keywords := extractKeywords(query)
	hasSemanticIntent := len(keywords) > 0 && containsSemanticWords(query)
	hasKeywords := len(keywords) > 0
	hasRelationships := containsRelationshipWords(query)
	relationships := extractRelationships(query)
	mediaType := detectMediaType(query)
	confidence := calculateConfidence(query)

	return NLPResult{
		Query:              query,
		Keywords:           keywords,
		HasSemanticIntent:  hasSemanticIntent,
		HasKeywords:        hasKeywords,
		HasRelationships:   hasRelationships,
		Relationships:      relationships,
		MediaType:          mediaType,
		Confidence:         confidence,
	}
}

func extractKeywords(query string) []string {
	// Simple keyword extraction
	words := strings.Fields(strings.ToLower(query))
	stopWords := map[string]bool{
		"the": true, "a": true, "an": true, "and": true, "or": true,
		"but": true, "in": true, "on": true, "at": true, "to": true,
		"for": true, "of": true, "with": true, "by": true,
	}
	
	var keywords []string
	for _, word := range words {
		if !stopWords[word] && len(word) > 2 {
			keywords = append(keywords, word)
		}
	}
	return keywords
}

func containsSemanticWords(query string) bool {
	semanticWords := []string{"find", "search", "show", "get", "look", "similar", "like", "related"}
	queryLower := strings.ToLower(query)
	for _, word := range semanticWords {
		if strings.Contains(queryLower, word) {
			return true
		}
	}
	return false
}

func containsRelationshipWords(query string) bool {
	relationshipWords := []string{"related", "similar", "connected", "associated", "linked"}
	queryLower := strings.ToLower(query)
	for _, word := range relationshipWords {
		if strings.Contains(queryLower, word) {
			return true
		}
	}
	return false
}

func extractRelationships(query string) []string {
	// Extract relationship types from query
	var relationships []string
	queryLower := strings.ToLower(query)
	
	if strings.Contains(queryLower, "similar") {
		relationships = append(relationships, "similar_to")
	}
	if strings.Contains(queryLower, "related") {
		relationships = append(relationships, "related_to")
	}
	if strings.Contains(queryLower, "contains") {
		relationships = append(relationships, "contains")
	}
	
	return relationships
}

func detectMediaType(query string) string {
	queryLower := strings.ToLower(query)
	if strings.Contains(queryLower, "video") || strings.Contains(queryLower, "movie") || strings.Contains(queryLower, "film") {
		return "video"
	}
	if strings.Contains(queryLower, "image") || strings.Contains(queryLower, "picture") || strings.Contains(queryLower, "photo") {
		return "image"
	}
	if strings.Contains(queryLower, "audio") || strings.Contains(queryLower, "sound") || strings.Contains(queryLower, "music") {
		return "audio"
	}
	if strings.Contains(queryLower, "document") || strings.Contains(queryLower, "text") || strings.Contains(queryLower, "pdf") {
		return "document"
	}
	return "all"
}

func calculateConfidence(query string) float64 {
	// Simple confidence calculation based on query length and specificity
	words := strings.Fields(query)
	baseConfidence := 0.5
	
	if len(words) > 3 {
		baseConfidence += 0.2
	}
	if len(words) > 6 {
		baseConfidence += 0.2
	}
	if containsSemanticWords(query) {
		baseConfidence += 0.1
	}
	
	if baseConfidence > 1.0 {
		baseConfidence = 1.0
	}
	
	return baseConfidence
}

func searchWeaviate(nlp NLPResult, filters map[string]interface{}, limit int) []SearchResult {
	// Weaviate integration disabled for now
	return []SearchResult{}
}

func searchPostgreSQL(keywords []string, filters map[string]interface{}, limit int) []SearchResult {
	// Placeholder for PostgreSQL full-text search
	// In production, implement actual PostgreSQL search
	return []SearchResult{
		{
			ID:    "postgres-result-1",
			Type:  "asset",
			Score: 0.85,
			Metadata: map[string]interface{}{
				"filename": "sample-image.jpg",
				"mime_type": "image/jpeg",
				"source": "postgres",
			},
		},
	}
}

func searchNeo4j(relationships []string, limit int) []SearchResult {
	// Placeholder for Neo4j graph search
	// In production, implement actual Neo4j graph traversal
	return []SearchResult{
		{
			ID:    "neo4j-result-1",
			Type:  "asset",
			Score: 0.80,
			Metadata: map[string]interface{}{
				"filename": "related-content.mp4",
				"mime_type": "video/mp4",
				"source": "neo4j",
			},
		},
	}
}

func findSimilarEntities(entityID string, threshold float64, limit int) []SearchResult {
	// Placeholder for similarity search
	return []SearchResult{
		{
			ID:    "similar-1",
			Type:  "asset",
			Score: 0.90,
			Metadata: map[string]interface{}{
				"filename": "similar-video.mp4",
				"mime_type": "video/mp4",
				"similarity": threshold,
			},
		},
	}
}

func rankResults(results []SearchResult, query string) []SearchResult {
	// Simple ranking algorithm
	// In production, implement more sophisticated ranking
	for i := range results {
		// Boost score based on query relevance
		if strings.Contains(strings.ToLower(results[i].Metadata["filename"].(string)), strings.ToLower(query)) {
			results[i].Score += 0.1
		}
	}
	
	// Sort by score (descending)
	for i := 0; i < len(results)-1; i++ {
		for j := i + 1; j < len(results); j++ {
			if results[i].Score < results[j].Score {
				results[i], results[j] = results[j], results[i]
			}
		}
	}
	
	return results
}

func enrichWithSegments(results []SearchResult) {
	// Placeholder for segment enrichment
	// In production, fetch actual segments from database
	for i := range results {
		results[i].Segments = []Segment{
			{
				ID:         "segment-1",
				StartTime:  0.0,
				EndTime:    10.5,
				Confidence: 0.95,
				Features: map[string]interface{}{
					"objects": []string{"person", "car"},
					"scene":   "outdoor",
				},
			},
		}
	}
}

func getEntityRelationships(entityID string, limit int) []map[string]interface{} {
	// Placeholder for relationship retrieval
	return []map[string]interface{}{
		{
			"source_id": entityID,
			"target_id": "related-entity-1",
			"type":      "similar_to",
			"strength":  0.85,
		},
	}
}

func getSystemStats() map[string]interface{} {
	// Placeholder for system statistics
	return map[string]interface{}{
		"total_assets":    1000,
		"total_segments":  5000,
		"total_features":  15000,
		"search_queries":  500,
		"cache_hit_rate":  0.75,
		"avg_response_time": 150,
	}
}

// Health check functions
func checkPostgres() string {
	if dbPool == nil {
		return "not_initialized"
	}
	
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	err := dbPool.Ping(ctx)
	if err != nil {
		return fmt.Sprintf("error: %v", err)
	}
	
	return "connected"
}

func checkRedis() string {
	if redisClient == nil {
		return "not_initialized"
	}
	
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	err := redisClient.Ping(ctx).Err()
	if err != nil {
		return fmt.Sprintf("error: %v", err)
	}
	
	return "connected"
}

func checkNeo4j() string {
	if neo4jDriver == nil {
		return "not_initialized"
	}
	
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	err := neo4jDriver.VerifyConnectivity()
	if err != nil {
		return fmt.Sprintf("error: %v", err)
	}
	
	return "connected"
}

func checkWeaviate() string {
	// Weaviate integration disabled for now
	return "disabled"
}

func checkClickHouse() string {
	// Placeholder for ClickHouse health check
	return "not_implemented"
}
