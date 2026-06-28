"""
app/database.py
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def get_db_engine() -> Engine | None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL env var is not set.")
        return None

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    try:
        engine = create_engine(
            database_url,
            pool_size=2,
            max_overflow=3,
            pool_timeout=10,
            pool_pre_ping=True
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
        return engine
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None
