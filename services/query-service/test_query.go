package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Test data structures
type SearchRequest struct {
	Query           string                 `json:"query"`
	MediaTypes      []string              `json:"media_types"`
	Filters         map[string]interface{} `json:"filters"`
	Limit           int                   `json:"limit"`
	Offset          int                   `json:"offset"`
	IncludeSegments bool                  `json:"include_segments"`
	ConfidenceMin   float64               `json:"confidence_min"`
}

type SimilarRequest struct {
	EntityID   string   `json:"entity_id"`
	Threshold  float64  `json:"threshold"`
	Limit      int      `json:"limit"`
	MediaTypes []string `json:"media_types"`
}

const baseURL = "http://localhost:8002"

func main() {
	fmt.Println("DataFlux Query Service Tests")
	fmt.Println("=" * 40)

	// Test health check
	if !testHealth() {
		fmt.Println("❌ Health check failed")
		return
	}
	fmt.Println("✅ Health check passed")

	// Test search
	if !testSearch() {
		fmt.Println("❌ Search test failed")
		return
	}
	fmt.Println("✅ Search test passed")

	// Test similar search
	if !testSimilar() {
		fmt.Println("❌ Similar search test failed")
		return
	}
	fmt.Println("✅ Similar search test passed")

	// Test stats
	if !testStats() {
		fmt.Println("❌ Stats test failed")
		return
	}
	fmt.Println("✅ Stats test passed")

	fmt.Println("\n🎉 All tests passed!")
}

func testHealth() bool {
	resp, err := http.Get(baseURL + "/health")
	if err != nil {
		fmt.Printf("Health check error: %v\n", err)
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Health check status: %d\n", resp.StatusCode)
		return false
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Health check read error: %v\n", err)
		return false
	}

	fmt.Printf("Health response: %s\n", string(body))
	return true
}

func testSearch() bool {
	searchReq := SearchRequest{
		Query:           "find videos with cars",
		MediaTypes:      []string{"video"},
		Limit:           10,
		IncludeSegments: true,
		ConfidenceMin:   0.7,
	}

	jsonData, err := json.Marshal(searchReq)
	if err != nil {
		fmt.Printf("Search request marshal error: %v\n", err)
		return false
	}

	resp, err := http.Post(baseURL+"/api/v1/search", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Printf("Search request error: %v\n", err)
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Search status: %d\n", resp.StatusCode)
		return false
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Search response read error: %v\n", err)
		return false
	}

	fmt.Printf("Search response: %s\n", string(body))
	return true
}

func testSimilar() bool {
	similarReq := SimilarRequest{
		EntityID:  "test-entity-123",
		Threshold: 0.75,
		Limit:     5,
		MediaTypes: []string{"video", "image"},
	}

	jsonData, err := json.Marshal(similarReq)
	if err != nil {
		fmt.Printf("Similar request marshal error: %v\n", err)
		return false
	}

	resp, err := http.Post(baseURL+"/api/v1/similar", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Printf("Similar request error: %v\n", err)
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Similar search status: %d\n", resp.StatusCode)
		return false
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Similar response read error: %v\n", err)
		return false
	}

	fmt.Printf("Similar response: %s\n", string(body))
	return true
}

func testStats() bool {
	resp, err := http.Get(baseURL + "/api/v1/stats")
	if err != nil {
		fmt.Printf("Stats request error: %v\n", err)
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Stats status: %d\n", resp.StatusCode)
		return false
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Stats response read error: %v\n", err)
		return false
	}

	fmt.Printf("Stats response: %s\n", string(body))
	return true
}
