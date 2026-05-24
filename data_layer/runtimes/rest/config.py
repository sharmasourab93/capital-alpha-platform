"""REST runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_REST_HOST = "0.0.0.0"
DEFAULT_REST_PORT = 8001
DEFAULT_REST_RELOAD = False
DEFAULT_REST_LOG_LEVEL = "debug"


@dataclass(frozen=True, slots=True)
class RestRuntimeSettings:
    """Settings used by the local REST runner."""

    host: str = DEFAULT_REST_HOST
    port: int = DEFAULT_REST_PORT
    reload: bool = DEFAULT_REST_RELOAD
    log_level: str = DEFAULT_REST_LOG_LEVEL

    @classmethod
    def from_env(cls) -> "RestRuntimeSettings":
        """Load settings from environment variables."""
        return cls(
            host=os.getenv("REST_HOST", DEFAULT_REST_HOST),
            port=int(os.getenv("REST_PORT", str(DEFAULT_REST_PORT))),
            reload=os.getenv("REST_RELOAD", "false").lower() == "true",
            log_level=os.getenv(
                "REST_LOG_LEVEL", DEFAULT_REST_LOG_LEVEL
            ).lower(),
        )
