# JWT Authentication Middleware for DataFlux Services
# Reusable authentication middleware for FastAPI services

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, List, Dict, Any
import httpx
import os
from enum import Enum
import asyncio
import aioredis
from datetime import datetime, timedelta

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8006")

# Security scheme
security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    ANALYST = "analyst"

class Permission(str, Enum):
    READ_ASSETS = "read:assets"
    WRITE_ASSETS = "write:assets"
    DELETE_ASSETS = "delete:assets"
    READ_ANALYTICS = "read:analytics"
    WRITE_ANALYTICS = "write:analytics"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"

# Models
class UserInfo:
    def __init__(self, user_id: str, username: str, email: str, role: UserRole, permissions: List[Permission]):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.permissions = permissions

class AuthCache:
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = 300  # 5 minutes
        
    async def init_redis(self):
        """Initialize Redis connection for caching"""
        self.redis_client = aioredis.from_url(
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '2002')}",
            password=os.getenv("REDIS_PASSWORD", "dataflux_pass"),
            decode_responses=True
        )
    
    async def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """Get user info from cache"""
        if not self.redis_client:
            return None
            
        try:
            cached_data = await self.redis_client.get(f"user_info:{user_id}")
            if cached_data:
                import json
                data = json.loads(cached_data)
                return UserInfo(
                    user_id=data["user_id"],
                    username=data["username"],
                    email=data["email"],
                    role=UserRole(data["role"]),
                    permissions=[Permission(p) for p in data["permissions"]]
                )
        except Exception:
            pass
        return None
    
    async def cache_user_info(self, user_info: UserInfo):
        """Cache user info"""
        if not self.redis_client:
            return
            
        try:
            import json
            data = {
                "user_id": user_info.user_id,
                "username": user_info.username,
                "email": user_info.email,
                "role": user_info.role.value,
                "permissions": [p.value for p in user_info.permissions]
            }
            await self.redis_client.setex(
                f"user_info:{user_info.user_id}", 
                self.cache_ttl, 
                json.dumps(data)
            )
        except Exception:
            pass

# Global auth cache instance
auth_cache = AuthCache()

class JWTAuth:
    def __init__(self):
        self.auth_service_url = AUTH_SERVICE_URL
        
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def get_user_info_from_auth_service(self, user_id: str) -> Optional[UserInfo]:
        """Get user info from auth service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.auth_service_url}/auth/user/{user_id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return UserInfo(
                        user_id=data["user_id"],
                        username=data["username"],
                        email=data["email"],
                        role=UserRole(data["role"]),
                        permissions=[Permission(p) for p in data.get("permissions", [])]
                    )
        except Exception:
            pass
        return None
    
    async def get_user_permissions_from_auth_service(self, user_id: str) -> List[Permission]:
        """Get user permissions from auth service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.auth_service_url}/auth/permissions",
                    headers={"Authorization": f"Bearer {user_id}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return [Permission(p) for p in data.get("permissions", [])]
        except Exception:
            pass
        return []

# Global JWT auth instance
jwt_auth = JWTAuth()

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Get current authenticated user"""
    token = credentials.credentials
    
    # Verify token
    payload = jwt_auth.verify_token(token)
    user_id = payload.get("user_id")
    username = payload.get("sub")
    
    if not user_id or not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Try to get user info from cache first
    user_info = await auth_cache.get_user_info(user_id)
    
    if not user_info:
        # Get from auth service
        user_info = await jwt_auth.get_user_info_from_auth_service(user_id)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Cache user info
        await auth_cache.cache_user_info(user_info)
    
    return user_info

# Dependency to check permissions
def require_permission(resource: str, action: str):
    """Decorator to require specific permission"""
    async def permission_checker(current_user: UserInfo = Depends(get_current_user)):
        # Check if user has required permission
        required_permission = None
        
        # Map resource/action to permission
        permission_map = {
            ("assets", "read"): Permission.READ_ASSETS,
            ("assets", "write"): Permission.WRITE_ASSETS,
            ("assets", "delete"): Permission.DELETE_ASSETS,
            ("analytics", "read"): Permission.READ_ANALYTICS,
            ("analytics", "write"): Permission.WRITE_ANALYTICS,
            ("users", "admin"): Permission.ADMIN_USERS,
            ("system", "admin"): Permission.ADMIN_SYSTEM,
        }
        
        required_permission = permission_map.get((resource, action))
        
        if not required_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown permission: {action} on {resource}"
            )
        
        # Admin users have all permissions
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Check if user has the required permission
        if required_permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {action} on {resource}"
            )
        
        return current_user
    return permission_checker

# Dependency to require admin role
def require_admin(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user

# Dependency to require specific role
def require_role(required_role: UserRole):
    """Require specific role"""
    async def role_checker(current_user: UserInfo = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{required_role.value} role required"
            )
        return current_user
    return role_checker

# Optional authentication (for public endpoints that can benefit from user context)
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[UserInfo]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

# Service-to-service authentication
class ServiceAuth:
    def __init__(self):
        self.service_tokens = {
            "ingestion-service": os.getenv("INGESTION_SERVICE_TOKEN", "ingestion-token"),
            "query-service": os.getenv("QUERY_SERVICE_TOKEN", "query-token"),
            "analysis-service": os.getenv("ANALYSIS_SERVICE_TOKEN", "analysis-token"),
            "mcp-server": os.getenv("MCP_SERVICE_TOKEN", "mcp-token"),
        }
    
    def verify_service_token(self, token: str) -> Optional[str]:
        """Verify service token and return service name"""
        for service_name, service_token in self.service_tokens.items():
            if token == service_token:
                return service_name
        return None

# Global service auth instance
service_auth = ServiceAuth()

# Dependency for service-to-service authentication
def require_service_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Require service authentication"""
    token = credentials.credentials
    service_name = service_auth.verify_service_token(token)
    
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return service_name

# Utility functions
async def init_auth_cache():
    """Initialize auth cache"""
    await auth_cache.init_redis()

def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from token without full verification"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        return payload.get("user_id")
    except JWTError:
        return None

def get_username_from_token(token: str) -> Optional[str]:
    """Extract username from token without full verification"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        return payload.get("sub")
    except JWTError:
        return None

# Example usage in FastAPI endpoints:
"""
from fastapi import FastAPI, Depends
from auth_middleware import get_current_user, require_permission, UserInfo

app = FastAPI()

@app.get("/protected")
async def protected_endpoint(current_user: UserInfo = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}"}

@app.get("/admin-only")
async def admin_endpoint(current_user: UserInfo = Depends(require_admin)):
    return {"message": "Admin access granted"}

@app.get("/assets")
async def get_assets(current_user: UserInfo = Depends(require_permission("assets", "read"))):
    return {"assets": []}

@app.post("/assets")
async def create_asset(current_user: UserInfo = Depends(require_permission("assets", "write"))):
    return {"message": "Asset created"}
"""
