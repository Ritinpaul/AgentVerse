"""
Structured JSON Logging & OpenTelemetry Config for Nuuvixx Services.
"""
from __future__ import annotations
import os
import sys
import logging
from pythonjsonlogger import jsonlogger


def setup_logging(service_name: str = "nuuvixx-service") -> logging.Logger:
    """
    Configure structured JSON logging for production or human-readable formatting for dev.
    Controlled via NUUVIXX_LOG_FORMAT="json" | "console"
    """
    log_format = os.getenv("NUUVIXX_LOG_FORMAT", "json").lower()
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)

    if log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
        )

    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    logger = logging.getLogger(service_name)
    logger.info(f"Structured logging initialized for service '{service_name}' [format={log_format}]")
    return logger
