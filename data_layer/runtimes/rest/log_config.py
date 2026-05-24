"""Logging setup for the REST runtime."""

from __future__ import annotations

import logging


def configure_logging(log_level: str) -> None:
    """Configure console logging for local runtime execution."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )
    logging.getLogger("data_layer").setLevel(level)
