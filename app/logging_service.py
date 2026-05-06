import logging
import json
from typing import Any, Dict, Optional
from sqlalchemy import text
from app.database import get_db_engine

logger = logging.getLogger(__name__)

async def log_request(
    path: str,
    method: str,
    ip_address: str,
    status_code: int,
    payload: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Logs an incoming API request to the audit_logs table.
    """
    engine = get_db_engine()
    if not engine:
        return

    try:
        # In a real async app, we'd use an async driver, 
        # but here we use the synchronous engine in a thread pool (via engine.begin)
        # For true performance, SQLAlchemy's async extension is preferred.
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO audit_logs (
                        request_id, path, method, 
                        ip_address, status_code, payload
                    ) VALUES (
                        :request_id, :path, :method, 
                        :ip_address, :status_code, :payload
                    )
                """),
                {
                    "request_id": request_id,
                    "path": path,
                    "method": method,
                    "ip_address": ip_address,
                    "status_code": status_code,
                    "payload": json.dumps(payload) if payload else None,
                }
            )
    except Exception as exc:
        logger.error(f"Failed to write audit log: {exc}")
