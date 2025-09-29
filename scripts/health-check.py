#!/usr/bin/env python3
"""
DataFlux Health Check System
Comprehensive health monitoring for all DataFlux services
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class HealthCheckResult:
    """Health check result"""
    service: str
    status: str  # healthy, unhealthy, degraded
    response_time: float
    timestamp: datetime
    details: Dict[str, Any]
    error: Optional[str] = None

class DataFluxHealthChecker:
    """Comprehensive health checker for DataFlux services"""
    
    def __init__(self):
        self.services = {
            "ingestion-service": {
                "url": "http://localhost:8002/health",
                "timeout": 5,
                "expected_status": 200
            },
            "query-service": {
                "url": "http://localhost:8003/health",
                "timeout": 5,
                "expected_status": 200
            },
            "analysis-service": {
                "url": "http://localhost:8004/health",
                "timeout": 5,
                "expected_status": 200
            },
            "mcp-server": {
                "url": "http://localhost:2015/health",
                "timeout": 5,
                "expected_status": 200
            },
            "web-ui": {
                "url": "http://localhost:3000",
                "timeout": 5,
                "expected_status": 200
            },
            "api-gateway": {
                "url": "http://localhost:2013/health",
                "timeout": 5,
                "expected_status": 200
            },
            "postgres": {
                "url": "http://localhost:2001",
                "timeout": 5,
                "expected_status": 200
            },
            "redis": {
                "url": "http://localhost:2002",
                "timeout": 5,
                "expected_status": 200
            },
            "kafka": {
                "url": "http://localhost:2009",
                "timeout": 5,
                "expected_status": 200
            },
            "minio": {
                "url": "http://localhost:2003/minio/health/live",
                "timeout": 5,
                "expected_status": 200
            },
            "weaviate": {
                "url": "http://localhost:2005/v1/meta",
                "timeout": 5,
                "expected_status": 200
            },
            "neo4j": {
                "url": "http://localhost:2007/db/data/",
                "timeout": 5,
                "expected_status": 200
            },
            "clickhouse": {
                "url": "http://localhost:2011/ping",
                "timeout": 5,
                "expected_status": 200
            },
            "prometheus": {
                "url": "http://localhost:2020/-/healthy",
                "timeout": 5,
                "expected_status": 200
            },
            "grafana": {
                "url": "http://localhost:2021/api/health",
                "timeout": 5,
                "expected_status": 200
            }
        }
    
    async def check_service_health(self, service_name: str, config: Dict[str, Any]) -> HealthCheckResult:
        """Check health of a single service"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config["url"],
                    timeout=aiohttp.ClientTimeout(total=config["timeout"])
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == config["expected_status"]:
                        status = "healthy"
                        error = None
                    else:
                        status = "unhealthy"
                        error = f"Unexpected status code: {response.status}"
                    
                    # Try to get response details
                    try:
                        details = await response.json()
                    except:
                        details = {"status_code": response.status}
                    
                    return HealthCheckResult(
                        service=service_name,
                        status=status,
                        response_time=response_time,
                        timestamp=datetime.now(),
                        details=details,
                        error=error
                    )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service=service_name,
                status="unhealthy",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                details={},
                error="Request timeout"
            )
        
        except Exception as e:
            return HealthCheckResult(
                service=service_name,
                status="unhealthy",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                details={},
                error=str(e)
            )
    
    async def check_all_services(self) -> List[HealthCheckResult]:
        """Check health of all services"""
        tasks = []
        
        for service_name, config in self.services.items():
            task = self.check_service_health(service_name, config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to HealthCheckResult
        health_results = []
        for result in results:
            if isinstance(result, HealthCheckResult):
                health_results.append(result)
            else:
                # Handle exceptions
                health_results.append(HealthCheckResult(
                    service="unknown",
                    status="unhealthy",
                    response_time=0,
                    timestamp=datetime.now(),
                    details={},
                    error=str(result)
                ))
        
        return health_results
    
    def generate_health_report(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Generate a comprehensive health report"""
        total_services = len(results)
        healthy_services = len([r for r in results if r.status == "healthy"])
        unhealthy_services = len([r for r in results if r.status == "unhealthy"])
        degraded_services = len([r for r in results if r.status == "degraded"])
        
        # Calculate average response time
        avg_response_time = sum(r.response_time for r in results) / total_services if total_services > 0 else 0
        
        # Group services by status
        by_status = {
            "healthy": [r for r in results if r.status == "healthy"],
            "unhealthy": [r for r in results if r.status == "unhealthy"],
            "degraded": [r for r in results if r.status == "degraded"]
        }
        
        # Overall system health
        if unhealthy_services == 0 and degraded_services == 0:
            overall_status = "healthy"
        elif unhealthy_services == 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": unhealthy_services,
                "degraded_services": degraded_services,
                "health_percentage": (healthy_services / total_services) * 100 if total_services > 0 else 0,
                "average_response_time": avg_response_time
            },
            "services_by_status": by_status,
            "detailed_results": [
                {
                    "service": r.service,
                    "status": r.status,
                    "response_time": r.response_time,
                    "timestamp": r.timestamp.isoformat(),
                    "details": r.details,
                    "error": r.error
                }
                for r in results
            ]
        }
    
    def print_health_report(self, report: Dict[str, Any]):
        """Print a formatted health report"""
        print("🏥 DataFlux Health Check Report")
        print("=" * 50)
        
        # Overall status
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌"
        }
        
        print(f"Overall Status: {status_emoji.get(report['overall_status'], '❓')} {report['overall_status'].upper()}")
        print(f"Timestamp: {report['timestamp']}")
        print()
        
        # Summary
        summary = report["summary"]
        print("📊 Summary:")
        print(f"  Total Services: {summary['total_services']}")
        print(f"  Healthy: {summary['healthy_services']} ({summary['health_percentage']:.1f}%)")
        print(f"  Unhealthy: {summary['unhealthy_services']}")
        print(f"  Degraded: {summary['degraded_services']}")
        print(f"  Avg Response Time: {summary['average_response_time']:.3f}s")
        print()
        
        # Services by status
        for status, services in report["services_by_status"].items():
            if services:
                print(f"{status_emoji.get(status, '❓')} {status.upper()} Services:")
                for service in services:
                    print(f"  - {service.service}: {service.response_time:.3f}s")
                    if service.error:
                        print(f"    Error: {service.error}")
                print()

# Mock implementation for testing
class MockDataFluxHealthChecker:
    """Mock health checker for testing"""
    
    def __init__(self):
        self.mock_results = [
            HealthCheckResult(
                service="ingestion-service",
                status="healthy",
                response_time=0.05,
                timestamp=datetime.now(),
                details={"status": "ok", "version": "1.0.0"}
            ),
            HealthCheckResult(
                service="query-service",
                status="healthy",
                response_time=0.03,
                timestamp=datetime.now(),
                details={"status": "ok", "version": "1.0.0"}
            ),
            HealthCheckResult(
                service="analysis-service",
                status="degraded",
                response_time=2.1,
                timestamp=datetime.now(),
                details={"status": "slow", "version": "1.0.0"}
            ),
            HealthCheckResult(
                service="postgres",
                status="unhealthy",
                response_time=5.0,
                timestamp=datetime.now(),
                details={},
                error="Connection refused"
            )
        ]
    
    async def check_all_services(self) -> List[HealthCheckResult]:
        """Mock check all services"""
        await asyncio.sleep(0.1)  # Simulate async operation
        return self.mock_results
    
    def generate_health_report(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Generate a comprehensive health report"""
        total_services = len(results)
        healthy_services = len([r for r in results if r.status == "healthy"])
        unhealthy_services = len([r for r in results if r.status == "unhealthy"])
        degraded_services = len([r for r in results if r.status == "degraded"])
        
        # Calculate average response time
        avg_response_time = sum(r.response_time for r in results) / total_services if total_services > 0 else 0
        
        # Group services by status
        by_status = {
            "healthy": [r for r in results if r.status == "healthy"],
            "unhealthy": [r for r in results if r.status == "unhealthy"],
            "degraded": [r for r in results if r.status == "degraded"]
        }
        
        # Overall system health
        if unhealthy_services == 0 and degraded_services == 0:
            overall_status = "healthy"
        elif unhealthy_services == 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": unhealthy_services,
                "degraded_services": degraded_services,
                "health_percentage": (healthy_services / total_services) * 100 if total_services > 0 else 0,
                "average_response_time": avg_response_time
            },
            "services_by_status": by_status,
            "detailed_results": [
                {
                    "service": r.service,
                    "status": r.status,
                    "response_time": r.response_time,
                    "timestamp": r.timestamp.isoformat(),
                    "details": r.details,
                    "error": r.error
                }
                for r in results
            ]
        }
    
    def print_health_report(self, report: Dict[str, Any]):
        """Print a formatted health report"""
        print("🏥 DataFlux Health Check Report")
        print("=" * 50)
        
        # Overall status
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌"
        }
        
        print(f"Overall Status: {status_emoji.get(report['overall_status'], '❓')} {report['overall_status'].upper()}")
        print(f"Timestamp: {report['timestamp']}")
        print()
        
        # Summary
        summary = report["summary"]
        print("📊 Summary:")
        print(f"  Total Services: {summary['total_services']}")
        print(f"  Healthy: {summary['healthy_services']} ({summary['health_percentage']:.1f}%)")
        print(f"  Unhealthy: {summary['unhealthy_services']}")
        print(f"  Degraded: {summary['degraded_services']}")
        print(f"  Avg Response Time: {summary['average_response_time']:.3f}s")
        print()
        
        # Services by status
        for status, services in report["services_by_status"].items():
            if services:
                print(f"{status_emoji.get(status, '❓')} {status.upper()} Services:")
                for service in services:
                    print(f"  - {service.service}: {service.response_time:.3f}s")
                    if service.error:
                        print(f"    Error: {service.error}")
                print()

# Test function
async def test_health_checker():
    """Test the health checker"""
    print("🧪 Testing DataFlux Health Checker")
    print("=" * 40)
    
    # Use mock implementation for testing
    checker = MockDataFluxHealthChecker()
    
    # Check all services
    results = await checker.check_all_services()
    
    # Generate report
    report = checker.generate_health_report(results)
    
    # Print report
    checker.print_health_report(report)
    
    print("\n🎉 Health checker test completed!")

if __name__ == "__main__":
    asyncio.run(test_health_checker())
