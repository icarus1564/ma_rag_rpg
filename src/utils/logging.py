"""Structured logging utilities."""

import structlog
import logging
import sys
from typing import Any, Dict, Optional, Literal
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_format: Literal["json", "text"] = "json",
    log_file: Optional[str] = None
) -> None:
    """Setup structured logging with configurable format and output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Log format type - "json" for structured JSON, "text" for human-readable
        log_file: Optional path to log file. If None, logs to console/stdout
    """
    # Determine output stream
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        output_stream = open(log_path, "a", encoding="utf-8")
    else:
        output_stream = sys.stdout
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=output_stream,
        level=getattr(logging, log_level.upper()),
        force=True,  # Force reconfiguration if already configured
    )
    
    # Build processors based on format
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add renderer based on format
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:  # text format
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)

