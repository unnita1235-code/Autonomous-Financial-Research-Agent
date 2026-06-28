import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
VALID_API_KEYS = set(k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip())

security = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_minutes: int = 60) -> str:
    try:
        from jose import jwt
        payload = dict(data)
        payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    except ImportError:
        return secrets.token_urlsafe(32)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not REQUIRE_AUTH:
        return {"sub": "anonymous"}
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = credentials.credentials
    if token in VALID_API_KEYS:
        return {"sub": "api_key_user"}
    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
