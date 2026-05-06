import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set in .env")
        return
        
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    try:
        engine = create_engine(database_url)
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS reports (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    query TEXT NOT NULL,
                    ticker VARCHAR(5) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'queued',
                    synthesis_quality FLOAT,
                    markdown TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS findings (
                    id UUID PRIMARY KEY,
                    report_id UUID REFERENCES reports(id),
                    metric_name VARCHAR(50),
                    value FLOAT,
                    source VARCHAR(30),
                    confidence FLOAT,
                    conflict_flagged BOOLEAN DEFAULT false,
                    period VARCHAR(20)
                );
            """))
            
        print("Migration successful")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
