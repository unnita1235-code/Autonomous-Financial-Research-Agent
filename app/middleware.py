import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .logging_service import log_request

logger = logging.getLogger(__name__)

class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log every request to the database for auditing and security tracking.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        # Capture request body if possible (be careful with large bodies)
        payload = None
        if request.method in ["POST", "PUT"]:
            try:
                # This can be tricky with large streams, but for small API requests it's fine
                # body = await request.body()
                # payload = json.loads(body) if body else None
                pass # Skipping body capture for now to avoid stream issues
            except Exception:
                pass

        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id

        # Async logging to DB
        await log_request(
            path=request.url.path,
            method=request.method,
            ip_address=request.client.host if request.client else "unknown",
            status_code=response.status_code,
            payload=payload,
            request_id=request_id
        )

        return response
