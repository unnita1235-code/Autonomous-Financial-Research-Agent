"""
reports/db_writer.py
"""

import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import text
from app.database import get_db_engine

logger = logging.getLogger(__name__)

def save_report(report: Dict[str, Any]) -> Optional[str]:
    """
    Persist a report to PostgreSQL.
    """
    engine = get_db_engine()
    if not engine:
        return None
        
    report_id = report.get("id") or report.get("report_id") or str(uuid.uuid4())
    if not report.get("query") or not report.get("ticker"):
        logger.error("Report dict missing required fields 'query' or 'ticker'")
        return None

    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO reports (
                        id, query, ticker, status, 
                        synthesis_quality, markdown
                    ) VALUES (
                        :id, :query, :ticker, :status, 
                        :synthesis_quality, :markdown
                    )
                """),
                {
                    "id": report_id,
                    "query": report.get("query"),
                    "ticker": report.get("ticker"),
                    "status": report.get("status", "queued"),
                    "synthesis_quality": report.get("synthesis_quality"),
                    "markdown": report.get("markdown"),
                }
            )
            logger.info("Inserted report row: %s", report_id)
        return str(report_id)
    except Exception as exc:
        logger.error("Failed to save report %s to database: %s", report_id, exc)
        return None

def save_findings(report_id: str, metrics: Dict[str, Any]) -> Optional[bool]:
    """
    Persist findings to PostgreSQL.
    """
    engine = get_db_engine()
    if not engine:
        return None
        
    try:
        with engine.begin() as conn:
            for metric_name, data in metrics.items():
                if not isinstance(data, dict):
                    continue
                    
                finding_id = str(uuid.uuid4())
                
                value = data.get("value")
                metric_value = None
                if isinstance(value, (int, float)):
                    metric_value = float(value)
                elif isinstance(value, str):
                    try:
                        metric_value = float(value.replace(",", "").replace("$", ""))
                    except ValueError:
                        pass
                
                conn.execute(
                    text("""
                        INSERT INTO findings (
                            id, report_id, metric_name,
                            value, source, confidence,
                            conflict_flagged, period
                        ) VALUES (
                            :id, :report_id, :metric_name,
                            :value, :source, :confidence,
                            :conflict_flagged, :period
                        )
                    """),
                    {
                        "id": finding_id,
                        "report_id": report_id,
                        "metric_name": metric_name,
                        "value": metric_value,
                        "source": data.get("winning_source") or data.get("source"),
                        "confidence": data.get("confidence"),
                        "conflict_flagged": data.get("conflict", False) or data.get("conflict_flagged", False),
                        "period": data.get("period"),
                    }
                )
            logger.info("Inserted findings for report %s", report_id)
        return True
    except Exception as exc:
        logger.error("Failed to save findings for report %s: %s", report_id, exc)
        return None
