/**
 * DataFlux E2E Tests with Playwright
 * End-to-end testing for the complete DataFlux system
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';

// Test configuration
const BASE_URL = 'http://localhost:3000';
const API_BASE_URL = 'http://localhost:2013';

// Test data
const TEST_FILES = {
  image: {
    name: 'test-image.jpg',
    content: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=',
    mimeType: 'image/jpeg'
  },
  video: {
    name: 'test-video.mp4',
    content: 'data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAAt1tZGF0AQAAARo=',
    mimeType: 'video/mp4'
  },
  document: {
    name: 'test-document.pdf',
    content: 'data:application/pdf;base64,JVBERi0xLjQKJcOkw7zDtsO8CjIgMCBvYmoKPDwKL0xlbmd0aCAzIDAgUgo+PgpzdHJlYW0K',
    mimeType: 'application/pdf'
  }
};

// Helper functions
async function uploadFile(page: Page, fileData: typeof TEST_FILES.image) {
  // Navigate to upload page
  await page.goto(`${BASE_URL}/upload`);
  
  // Wait for upload component to load
  await page.waitForSelector('[data-testid="file-upload"]');
  
  // Create a file input and upload
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles({
    name: fileData.name,
    mimeType: fileData.mimeType,
    buffer: Buffer.from(fileData.content.split(',')[1], 'base64')
  });
  
  // Fill in metadata
  await page.fill('[data-testid="context-input"]', 'E2E test upload');
  await page.selectOption('[data-testid="priority-select"]', '5');
  
  // Submit upload
  await page.click('[data-testid="upload-button"]');
  
  // Wait for upload to complete
  await page.waitForSelector('[data-testid="upload-success"]', { timeout: 30000 });
  
  // Get the asset ID from success message
  const successMessage = await page.textContent('[data-testid="upload-success"]');
  const assetIdMatch = successMessage?.match(/Asset ID: ([a-f0-9-]+)/);
  return assetIdMatch ? assetIdMatch[1] : null;
}

async function searchAssets(page: Page, query: string) {
  // Navigate to search page
  await page.goto(`${BASE_URL}/search`);
  
  // Wait for search component to load
  await page.waitForSelector('[data-testid="search-input"]');
  
  // Enter search query
  await page.fill('[data-testid="search-input"]', query);
  
  // Select media type
  await page.selectOption('[data-testid="media-type-select"]', 'all');
  
  // Submit search
  await page.click('[data-testid="search-button"]');
  
  // Wait for results
  await page.waitForSelector('[data-testid="search-results"]', { timeout: 10000 });
  
  // Get results
  const results = await page.locator('[data-testid="search-result"]').all();
  return results;
}

async function viewAssetDetails(page: Page, assetId: string) {
  // Navigate to asset details
  await page.goto(`${BASE_URL}/assets/${assetId}`);
  
  // Wait for asset details to load
  await page.waitForSelector('[data-testid="asset-details"]');
  
  // Get asset information
  const assetInfo = {
    filename: await page.textContent('[data-testid="asset-filename"]'),
    mimeType: await page.textContent('[data-testid="asset-mime-type"]'),
    fileSize: await page.textContent('[data-testid="asset-file-size"]'),
    status: await page.textContent('[data-testid="asset-status"]')
  };
  
  return assetInfo;
}

// Test suites
test.describe('DataFlux E2E Tests', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test.describe('Web UI Navigation', () => {
    test('should load the main dashboard', async () => {
      await page.goto(BASE_URL);
      
      // Check if dashboard loads
      await expect(page).toHaveTitle(/DataFlux/);
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
      
      // Check navigation elements
      await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
      await expect(page.locator('[data-testid="header"]')).toBeVisible();
    });

    test('should navigate between different sections', async () => {
      await page.goto(BASE_URL);
      
      // Test navigation to upload page
      await page.click('[data-testid="nav-upload"]');
      await expect(page).toHaveURL(/.*\/upload/);
      await expect(page.locator('[data-testid="upload-page"]')).toBeVisible();
      
      // Test navigation to search page
      await page.click('[data-testid="nav-search"]');
      await expect(page).toHaveURL(/.*\/search/);
      await expect(page.locator('[data-testid="search-page"]')).toBeVisible();
      
      // Test navigation to assets page
      await page.click('[data-testid="nav-assets"]');
      await expect(page).toHaveURL(/.*\/assets/);
      await expect(page.locator('[data-testid="assets-page"]')).toBeVisible();
      
      // Test navigation to analytics page
      await page.click('[data-testid="nav-analytics"]');
      await expect(page).toHaveURL(/.*\/analytics/);
      await expect(page.locator('[data-testid="analytics-page"]')).toBeVisible();
    });

    test('should display system status correctly', async () => {
      await page.goto(BASE_URL);
      
      // Check system status indicators
      await expect(page.locator('[data-testid="system-status"]')).toBeVisible();
      
      // Check service status
      const serviceStatuses = await page.locator('[data-testid="service-status"]').all();
      expect(serviceStatuses.length).toBeGreaterThan(0);
      
      // All services should be healthy
      for (const status of serviceStatuses) {
        await expect(status).toHaveClass(/healthy/);
      }
    });
  });

  test.describe('File Upload Workflow', () => {
    test('should upload an image file successfully', async () => {
      const assetId = await uploadFile(page, TEST_FILES.image);
      expect(assetId).toBeTruthy();
      
      // Verify asset appears in assets list
      await page.goto(`${BASE_URL}/assets`);
      await page.waitForSelector('[data-testid="assets-list"]');
      
      const assetElement = page.locator(`[data-testid="asset-${assetId}"]`);
      await expect(assetElement).toBeVisible();
    });

    test('should upload a video file successfully', async () => {
      const assetId = await uploadFile(page, TEST_FILES.video);
      expect(assetId).toBeTruthy();
      
      // Verify asset details
      const assetInfo = await viewAssetDetails(page, assetId);
      expect(assetInfo.filename).toBe(TEST_FILES.video.name);
      expect(assetInfo.mimeType).toBe(TEST_FILES.video.mimeType);
    });

    test('should upload a document file successfully', async () => {
      const assetId = await uploadFile(page, TEST_FILES.document);
      expect(assetId).toBeTruthy();
      
      // Verify asset appears in search results
      const results = await searchAssets(page, 'test-document');
      expect(results.length).toBeGreaterThan(0);
    });

    test('should handle upload errors gracefully', async () => {
      await page.goto(`${BASE_URL}/upload`);
      
      // Try to upload without selecting a file
      await page.click('[data-testid="upload-button"]');
      
      // Should show error message
      await expect(page.locator('[data-testid="upload-error"]')).toBeVisible();
    });

    test('should validate file types', async () => {
      await page.goto(`${BASE_URL}/upload`);
      
      // Try to upload an invalid file type
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'test.exe',
        mimeType: 'application/x-executable',
        buffer: Buffer.from('invalid content')
      });
      
      // Should show validation error
      await expect(page.locator('[data-testid="file-type-error"]')).toBeVisible();
    });
  });

  test.describe('Search Functionality', () => {
    test.beforeEach(async () => {
      // Upload test files before each search test
      await uploadFile(page, TEST_FILES.image);
      await uploadFile(page, TEST_FILES.video);
      await uploadFile(page, TEST_FILES.document);
    });

    test('should search for assets by filename', async () => {
      const results = await searchAssets(page, 'test-image');
      expect(results.length).toBeGreaterThan(0);
      
      // Check that results contain the expected file
      const firstResult = results[0];
      await expect(firstResult.locator('[data-testid="result-filename"]')).toContainText('test-image');
    });

    test('should search for assets by media type', async () => {
      // Search for video files only
      await page.goto(`${BASE_URL}/search`);
      await page.fill('[data-testid="search-input"]', 'test');
      await page.selectOption('[data-testid="media-type-select"]', 'video');
      await page.click('[data-testid="search-button"]');
      
      await page.waitForSelector('[data-testid="search-results"]');
      const results = await page.locator('[data-testid="search-result"]').all();
      
      // All results should be video files
      for (const result of results) {
        await expect(result.locator('[data-testid="result-mime-type"]')).toContainText('video/');
      }
    });

    test('should perform similarity search', async () => {
      // First upload a reference image
      const referenceAssetId = await uploadFile(page, TEST_FILES.image);
      
      // Navigate to similarity search
      await page.goto(`${BASE_URL}/search`);
      await page.click('[data-testid="similarity-search-tab"]');
      
      // Enter reference asset ID
      await page.fill('[data-testid="reference-asset-input"]', referenceAssetId);
      await page.click('[data-testid="similarity-search-button"]');
      
      // Wait for results
      await page.waitForSelector('[data-testid="similarity-results"]');
      const results = await page.locator('[data-testid="similarity-result"]').all();
      
      expect(results.length).toBeGreaterThan(0);
    });

    test('should handle empty search results', async () => {
      const results = await searchAssets(page, 'nonexistent-file-xyz');
      expect(results.length).toBe(0);
      
      // Should show "no results" message
      await expect(page.locator('[data-testid="no-results-message"]')).toBeVisible();
    });

    test('should paginate search results', async () => {
      // Upload multiple files to test pagination
      for (let i = 0; i < 15; i++) {
        await uploadFile(page, {
          ...TEST_FILES.image,
          name: `test-image-${i}.jpg`
        });
      }
      
      // Search and check pagination
      await page.goto(`${BASE_URL}/search`);
      await page.fill('[data-testid="search-input"]', 'test-image');
      await page.click('[data-testid="search-button"]');
      
      await page.waitForSelector('[data-testid="search-results"]');
      
      // Check pagination controls
      await expect(page.locator('[data-testid="pagination"]')).toBeVisible();
      await expect(page.locator('[data-testid="next-page"]')).toBeVisible();
    });
  });

  test.describe('Asset Management', () => {
    let testAssetId: string;

    test.beforeEach(async () => {
      testAssetId = await uploadFile(page, TEST_FILES.image);
    });

    test('should view asset details', async () => {
      const assetInfo = await viewAssetDetails(page, testAssetId);
      
      expect(assetInfo.filename).toBe(TEST_FILES.image.name);
      expect(assetInfo.mimeType).toBe(TEST_FILES.image.mimeType);
      expect(assetInfo.status).toBe('processed');
    });

    test('should display asset metadata', async () => {
      await page.goto(`${BASE_URL}/assets/${testAssetId}`);
      
      // Check metadata sections
      await expect(page.locator('[data-testid="asset-metadata"]')).toBeVisible();
      await expect(page.locator('[data-testid="asset-segments"]')).toBeVisible();
      await expect(page.locator('[data-testid="asset-features"]')).toBeVisible();
    });

    test('should show asset processing status', async () => {
      await page.goto(`${BASE_URL}/assets/${testAssetId}`);
      
      // Check processing status
      const statusElement = page.locator('[data-testid="processing-status"]');
      await expect(statusElement).toBeVisible();
      
      // Status should eventually become "processed"
      await expect(statusElement).toContainText('processed', { timeout: 30000 });
    });

    test('should allow asset deletion', async () => {
      await page.goto(`${BASE_URL}/assets/${testAssetId}`);
      
      // Click delete button
      await page.click('[data-testid="delete-asset-button"]');
      
      // Confirm deletion
      await page.click('[data-testid="confirm-delete"]');
      
      // Should redirect to assets list
      await expect(page).toHaveURL(/.*\/assets/);
      
      // Asset should not appear in list
      await expect(page.locator(`[data-testid="asset-${testAssetId}"]`)).not.toBeVisible();
    });

    test('should bulk select and delete assets', async () => {
      // Upload multiple assets
      const assetIds = [];
      for (let i = 0; i < 3; i++) {
        const assetId = await uploadFile(page, {
          ...TEST_FILES.image,
          name: `bulk-test-${i}.jpg`
        });
        assetIds.push(assetId);
      }
      
      // Navigate to assets list
      await page.goto(`${BASE_URL}/assets`);
      await page.waitForSelector('[data-testid="assets-list"]');
      
      // Select multiple assets
      for (const assetId of assetIds) {
        await page.check(`[data-testid="asset-checkbox-${assetId}"]`);
      }
      
      // Click bulk delete
      await page.click('[data-testid="bulk-delete-button"]');
      await page.click('[data-testid="confirm-bulk-delete"]');
      
      // Verify assets are deleted
      for (const assetId of assetIds) {
        await expect(page.locator(`[data-testid="asset-${assetId}"]`)).not.toBeVisible();
      }
    });
  });

  test.describe('Analytics Dashboard', () => {
    test('should display analytics charts', async () => {
      await page.goto(`${BASE_URL}/analytics`);
      
      // Check for chart components
      await expect(page.locator('[data-testid="upload-stats-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="storage-usage-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="processing-stats-chart"]')).toBeVisible();
    });

    test('should show system metrics', async () => {
      await page.goto(`${BASE_URL}/analytics`);
      
      // Check system metrics
      await expect(page.locator('[data-testid="total-assets"]')).toBeVisible();
      await expect(page.locator('[data-testid="total-storage"]')).toBeVisible();
      await expect(page.locator('[data-testid="processing-queue"]')).toBeVisible();
    });

    test('should update metrics in real-time', async () => {
      await page.goto(`${BASE_URL}/analytics`);
      
      // Get initial metrics
      const initialAssets = await page.textContent('[data-testid="total-assets"]');
      
      // Upload a new asset
      await uploadFile(page, TEST_FILES.image);
      
      // Check that metrics updated
      await page.waitForFunction(
        (initial) => {
          const current = document.querySelector('[data-testid="total-assets"]')?.textContent;
          return current && parseInt(current) > parseInt(initial);
        },
        initialAssets,
        { timeout: 10000 }
      );
    });
  });

  test.describe('API Integration', () => {
    test('should handle API errors gracefully', async () => {
      // Mock API error
      await page.route('**/api/v1/assets', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal server error' })
        });
      });
      
      await page.goto(`${BASE_URL}/upload`);
      
      // Try to upload
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'test.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('test')
      });
      
      await page.click('[data-testid="upload-button"]');
      
      // Should show error message
      await expect(page.locator('[data-testid="api-error"]')).toBeVisible();
    });

    test('should retry failed requests', async () => {
      let requestCount = 0;
      
      await page.route('**/api/v1/search', route => {
        requestCount++;
        if (requestCount < 3) {
          route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Temporary error' })
          });
        } else {
          route.continue();
        }
      });
      
      await page.goto(`${BASE_URL}/search`);
      await page.fill('[data-testid="search-input"]', 'test');
      await page.click('[data-testid="search-button"]');
      
      // Should eventually succeed after retries
      await page.waitForSelector('[data-testid="search-results"]', { timeout: 15000 });
      expect(requestCount).toBe(3);
    });
  });

  test.describe('Performance Tests', () => {
    test('should load pages within acceptable time', async () => {
      const pages = ['/', '/upload', '/search', '/assets', '/analytics'];
      
      for (const pagePath of pages) {
        const start = Date.now();
        await page.goto(`${BASE_URL}${pagePath}`);
        await page.waitForLoadState('networkidle');
        const loadTime = Date.now() - start;
        
        expect(loadTime).toBeLessThan(3000); // Should load within 3 seconds
      }
    });

    test('should handle large file uploads', async () => {
      // Create a large file (simulate)
      const largeFile = {
        name: 'large-file.mp4',
        content: 'data:video/mp4;base64,' + 'A'.repeat(1000000), // ~750KB
        mimeType: 'video/mp4'
      };
      
      const start = Date.now();
      const assetId = await uploadFile(page, largeFile);
      const uploadTime = Date.now() - start;
      
      expect(assetId).toBeTruthy();
      expect(uploadTime).toBeLessThan(30000); // Should upload within 30 seconds
    });

    test('should handle concurrent operations', async () => {
      // Start multiple operations simultaneously
      const operations = [
        page.goto(`${BASE_URL}/search`),
        page.goto(`${BASE_URL}/assets`),
        page.goto(`${BASE_URL}/analytics`)
      ];
      
      const start = Date.now();
      await Promise.all(operations);
      const totalTime = Date.now() - start;
      
      expect(totalTime).toBeLessThan(5000); // All operations should complete within 5 seconds
    });
  });

  test.describe('Accessibility Tests', () => {
    test('should be keyboard navigable', async () => {
      await page.goto(BASE_URL);
      
      // Test keyboard navigation
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toBeVisible();
      
      // Continue tabbing through elements
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');
        await expect(page.locator(':focus')).toBeVisible();
      }
    });

    test('should have proper ARIA labels', async () => {
      await page.goto(`${BASE_URL}/upload`);
      
      // Check for ARIA labels on form elements
      await expect(page.locator('[data-testid="file-upload"]')).toHaveAttribute('aria-label');
      await expect(page.locator('[data-testid="context-input"]')).toHaveAttribute('aria-label');
      await expect(page.locator('[data-testid="upload-button"]')).toHaveAttribute('aria-label');
    });

    test('should support screen readers', async () => {
      await page.goto(BASE_URL);
      
      // Check for proper heading structure
      const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();
      expect(headings.length).toBeGreaterThan(0);
      
      // Check for alt text on images
      const images = await page.locator('img').all();
      for (const img of images) {
        await expect(img).toHaveAttribute('alt');
      }
    });
  });
});
