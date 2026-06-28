import logging
import os
import sys

def configure_logging():
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    fmt = os.getenv("LOG_FORMAT", "text")
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        try:
            from pythonjsonlogger import jsonlogger
            handler.setFormatter(jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S"
            ))
        except ImportError:
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s"))
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s", "%H:%M:%S"))
    root.addHandler(handler)
    for noisy in ("httpx", "httpcore", "faiss", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
