"""Reserved fundamental-data REST namespace."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/funda", tags=["fundamentals"])
WORK_IN_PROGRESS_STATUS = "work_in_progress"


@router.get("/{market}")
def fundamentals_namespace(market: str) -> dict[str, str]:
    """Return reserved namespace metadata."""
    return {
        "market": market,
        "status": WORK_IN_PROGRESS_STATUS,
        "message": "Fundamental data endpoints are not implemented yet.",
    }
