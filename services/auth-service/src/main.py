# JWT Authentication Service for DataFlux
# Centralized authentication and authorization service

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncpg
import aioredis
import os
from enum import Enum
import uuid

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[UserRole] = None
    permissions: List[Permission] = []

class PermissionCheck(BaseModel):
    resource: str
    action: str
    user_id: str

class AuthService:
    def __init__(self):
        self.db_pool = None
        self.redis_client = None
        
    async def init_db(self):
        """Initialize database connection"""
        self.db_pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "2001")),
            user=os.getenv("POSTGRES_USER", "dataflux_user"),
            password=os.getenv("POSTGRES_PASSWORD", "dataflux_pass"),
            database=os.getenv("POSTGRES_DB", "dataflux"),
            min_size=5,
            max_size=20
        )
        
    async def init_redis(self):
        """Initialize Redis connection"""
        self.redis_client = aioredis.from_url(
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '2002')}",
            password=os.getenv("REDIS_PASSWORD", "dataflux_pass"),
            decode_responses=True
        )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            role: str = payload.get("role")
            permissions: List[str] = payload.get("permissions", [])
            
            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(
                username=username,
                user_id=user_id,
                role=UserRole(role) if role else None,
                permissions=[Permission(p) for p in permissions]
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, username, email, full_name, role, is_active, created_at, last_login FROM users WHERE username = $1",
                username
            )
            if row:
                return UserResponse(
                    user_id=row["user_id"],
                    username=row["username"],
                    email=row["email"],
                    full_name=row["full_name"],
                    role=UserRole(row["role"]),
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    last_login=row["last_login"]
                )
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, username, email, full_name, role, is_active, created_at, last_login FROM users WHERE user_id = $1",
                user_id
            )
            if row:
                return UserResponse(
                    user_id=row["user_id"],
                    username=row["username"],
                    email=row["email"],
                    full_name=row["full_name"],
                    role=UserRole(row["role"]),
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    last_login=row["last_login"]
                )
            return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[UserResponse]:
        """Authenticate a user"""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash FROM users WHERE username = $1",
                username
            )
            if not row or not self.verify_password(password, row["password_hash"]):
                return None
        
        # Update last login
        await self.update_last_login(user.user_id)
        return user
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        password_hash = self.get_password_hash(user_data.password)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, username, email, password_hash, full_name, role, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                user_id, user_data.username, user_data.email, password_hash,
                user_data.full_name, user_data.role.value, True, datetime.utcnow()
            )
        
        return await self.get_user_by_id(user_id)
    
    async def update_last_login(self, user_id: str):
        """Update user's last login time"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = $1 WHERE user_id = $2",
                datetime.utcnow(), user_id
            )
    
    async def get_user_permissions(self, user_id: str) -> List[Permission]:
        """Get user permissions based on role"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return []
        
        # Role-based permissions
        role_permissions = {
            UserRole.ADMIN: [
                Permission.READ_ASSETS, Permission.WRITE_ASSETS, Permission.DELETE_ASSETS,
                Permission.READ_ANALYTICS, Permission.WRITE_ANALYTICS,
                Permission.ADMIN_USERS, Permission.ADMIN_SYSTEM
            ],
            UserRole.ANALYST: [
                Permission.READ_ASSETS, Permission.WRITE_ASSETS,
                Permission.READ_ANALYTICS, Permission.WRITE_ANALYTICS
            ],
            UserRole.USER: [
                Permission.READ_ASSETS, Permission.WRITE_ASSETS
            ],
            UserRole.VIEWER: [
                Permission.READ_ASSETS, Permission.READ_ANALYTICS
            ]
        }
        
        return role_permissions.get(user.role, [])
    
    async def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has permission for resource/action"""
        permissions = await self.get_user_permissions(user_id)
        
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
        return required_permission in permissions if required_permission else False
    
    async def cache_token(self, token: str, user_id: str, expires_in: int):
        """Cache token in Redis"""
        await self.redis_client.setex(f"token:{token}", expires_in, user_id)
    
    async def revoke_token(self, token: str):
        """Revoke a token"""
        await self.redis_client.delete(f"token:{token}")
    
    async def is_token_revoked(self, token: str) -> bool:
        """Check if token is revoked"""
        result = await self.redis_client.get(f"token:{token}")
        return result is None

# Global auth service instance
auth_service = AuthService()

# FastAPI app
app = FastAPI(
    title="DataFlux Authentication Service",
    description="Centralized authentication and authorization for DataFlux",
    version="1.0.0"
)

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """Get current authenticated user"""
    token = credentials.credentials
    
    # Check if token is revoked
    if await auth_service.is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = auth_service.verify_token(token)
    user = await auth_service.get_user_by_id(token_data.user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

# Dependency to check permissions
def require_permission(resource: str, action: str):
    """Decorator to require specific permission"""
    async def permission_checker(current_user: UserResponse = Depends(get_current_user)):
        has_permission = await auth_service.check_permission(current_user.user_id, resource, action)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {action} on {resource}"
            )
        return current_user
    return permission_checker

# API Endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    # Check if user already exists
    existing_user = await auth_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    return await auth_service.create_user(user_data)

@app.post("/auth/login", response_model=Token)
async def login(login_data: UserLogin):
    """Login user and return tokens"""
    user = await auth_service.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = auth_service.create_access_token(
        data={"sub": user.username, "user_id": user.user_id, "role": user.role.value}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.username, "user_id": user.user_id}
    )
    
    # Cache access token
    await auth_service.cache_token(access_token, user.user_id, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.post("/auth/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    token_data = auth_service.verify_token(refresh_token)
    if token_data.username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await auth_service.get_user_by_username(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    access_token = auth_service.create_access_token(
        data={"sub": user.username, "user_id": user.user_id, "role": user.role.value}
    )
    
    # Cache new token
    await auth_service.cache_token(access_token, user.user_id, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.post("/auth/logout")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """Logout user and revoke token"""
    # In a real implementation, you'd need to pass the token to revoke it
    # For now, we'll just return success
    return {"message": "Successfully logged out"}

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@app.get("/auth/permissions")
async def get_user_permissions(current_user: UserResponse = Depends(get_current_user)):
    """Get current user permissions"""
    permissions = await auth_service.get_user_permissions(current_user.user_id)
    return {"permissions": [p.value for p in permissions]}

@app.post("/auth/check-permission")
async def check_permission(
    permission_check: PermissionCheck,
    current_user: UserResponse = Depends(get_current_user)
):
    """Check if user has specific permission"""
    has_permission = await auth_service.check_permission(
        current_user.user_id, permission_check.resource, permission_check.action
    )
    return {"has_permission": has_permission}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-service"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await auth_service.init_db()
    await auth_service.init_redis()

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if auth_service.db_pool:
        await auth_service.db_pool.close()
    if auth_service.redis_client:
        await auth_service.redis_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
