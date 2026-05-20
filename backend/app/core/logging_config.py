"""Logging setup for the backend. Set LOG_LEVEL=DEBUG in .env for verbose agent output."""

from __future__ import annotations

import logging
import os
import sys


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = "[%(asctime)s] %(levelname)-8s %(name)s | %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers.clear()
        root.addHandler(handler)

    # Quiet noisy third-party libs
    for noisy in ("httpx", "httpcore", "uvicorn.access", "langgraph", "langchain"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
