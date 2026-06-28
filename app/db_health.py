import logging
from sqlalchemy import text
from app.database import get_db_engine

logger = logging.getLogger(__name__)

def check_db_health() -> dict:
    engine = get_db_engine()
    if not engine:
        return {"status": "unavailable", "message": "DATABASE_URL not set or connection failed"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database reachable"}
    except Exception as e:
        logger.warning(f"DB health check failed: {e}")
        return {"status": "error", "message": str(e)}
