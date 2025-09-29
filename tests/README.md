# DataFlux Testing Suite

## 🧪 Overview

This directory contains comprehensive tests for the DataFlux platform.

## 📁 Structure

```
tests/
├── unit/                  # Unit tests
│   ├── services/         # Service-specific unit tests
│   │   ├── ingestion/    # Ingestion service tests
│   │   ├── query/        # Query service tests
│   │   ├── analysis/     # Analysis service tests
│   │   └── mcp/          # MCP server tests
│   └── shared/           # Shared utility tests
├── integration/          # Integration tests
│   ├── services/         # Service integration tests
│   ├── database/         # Database integration tests
│   └── api/              # API integration tests
├── e2e/                  # End-to-end tests
│   ├── workflows/        # Complete workflow tests
│   ├── performance/      # Performance tests
│   └── security/         # Security tests
└── fixtures/             # Test data and fixtures
    ├── media/            # Sample media files
    ├── data/             # Test data sets
    └── configs/          # Test configurations
```

## 🚀 Running Tests

### Unit Tests
```bash
# Python services
cd services/ingestion-service && python -m pytest tests/

# Go services
cd services/query-service && go test ./...

# Node.js services
cd services/mcp-server && npm test
```

### Integration Tests
```bash
# Start test environment
docker-compose -f docker/docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/

# Cleanup
docker-compose -f docker/docker-compose.test.yml down
```

### End-to-End Tests
```bash
# Install Playwright
npm install -g playwright
playwright install

# Run E2E tests
playwright test tests/e2e/
```

## 📊 Test Coverage

- **Unit Tests**: > 80% coverage
- **Integration Tests**: All critical paths
- **E2E Tests**: Complete user workflows

## 🔧 Test Configuration

### Environment Variables
```bash
# Test database
TEST_DATABASE_URL=postgresql://test:test@localhost:5432/dataflux_test

# Test Redis
TEST_REDIS_URL=redis://localhost:6379/1

# Test Kafka
TEST_KAFKA_BROKERS=localhost:9092
```

### Test Data
- Use fixtures for consistent test data
- Clean up after each test
- Use transactions for database tests
- Mock external services

## 📝 Writing Tests

### Unit Test Guidelines
- Test one function/method at a time
- Use descriptive test names
- Mock external dependencies
- Test edge cases and error conditions

### Integration Test Guidelines
- Test service interactions
- Use real databases (test instances)
- Test API endpoints
- Verify data consistency

### E2E Test Guidelines
- Test complete user workflows
- Use realistic test data
- Test error scenarios
- Verify UI interactions

## 🐛 Debugging Tests

### Common Issues
- Database connection failures
- Port conflicts
- Missing test data
- Timeout issues

### Debug Commands
```bash
# Run with verbose output
pytest -v tests/

# Run specific test
pytest tests/unit/services/ingestion/test_upload.py::test_upload_asset

# Run with coverage
pytest --cov=src tests/

# Debug mode
pytest --pdb tests/
```

## 📈 Performance Testing

### Load Testing
```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz | tar xvz

# Run load tests
k6 run tests/e2e/performance/load-test.js
```

### Benchmark Tests
```bash
# Run benchmarks
go test -bench=. ./services/query-service/
python -m pytest tests/unit/benchmarks/
```

## 🔒 Security Testing

### Security Test Suite
- SQL injection tests
- Authentication tests
- Authorization tests
- Input validation tests
- Rate limiting tests

### Running Security Tests
```bash
# Run security tests
pytest tests/e2e/security/

# Run with security scanner
bandit -r services/ingestion-service/src/
gosec ./services/query-service/...
```

## 📋 Test Checklist

- [ ] Unit tests for all services
- [ ] Integration tests for APIs
- [ ] E2E tests for workflows
- [ ] Performance tests
- [ ] Security tests
- [ ] Test coverage > 80%
- [ ] All tests passing in CI
- [ ] Documentation updated
