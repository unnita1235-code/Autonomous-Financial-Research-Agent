import logging
import os

logger = logging.getLogger(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Agent Evaluation Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { color: #38bdf8; border-bottom: 2px solid #1e293b; padding-bottom: 10px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; margin-top: 30px; }
        .metric-card { background: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #10b981; }
        .metric-name { color: #94a3b8; font-size: 0.9em; text-transform: uppercase; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Autonomous Financial Agent - Performance Metrics</h1>
        <div class="metrics-grid">
            {% for name, value in metrics.items() %}
            <div class="metric-card">
                <div class="metric-value">{{ "%.2f"|format(value) }}</div>
                <div class="metric-name">{{ name.replace('_', ' ') }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

def generate_dashboard(metrics: dict, output_path: str = "evaluation/dashboard.html"):
    """
    Generates an HTML dashboard for evaluation metrics.
    """
    try:
        from jinja2 import Template
        template = Template(DASHBOARD_HTML)
        html = template.render(metrics=metrics)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"Dashboard generated at {output_path}")
    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}")
