"""Report API routes."""

from fastapi import APIRouter, Depends, HTTPException

from tube_agent.config import get_settings
from tube_agent.api.deps import get_storage
from tube_agent.models.schemas import ReportResponse, ReportListResponse
from tube_agent.services.gemini import GeminiClient
from tube_agent.services.report import generate_channel_report
from tube_agent.storage.postgres import PostgresStorage

router = APIRouter(tags=["reports"])


@router.get(
    "/channels/{handle}/reports",
    response_model=ReportListResponse,
)
def list_reports(
    handle: str,
    storage: PostgresStorage = Depends(get_storage),
):
    """List all analysis reports for a channel."""
    handle = handle.lstrip("@")
    channel = storage.get_channel(handle)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel @{handle} not found")

    reports = storage.list_reports(channel["id"])
    return ReportListResponse(
        reports=[ReportResponse(**r) for r in reports],
        total=len(reports),
    )


@router.get(
    "/channels/{handle}/reports/{report_type}",
    response_model=ReportResponse,
)
def get_report(
    handle: str,
    report_type: str,
    storage: PostgresStorage = Depends(get_storage),
):
    """Get the latest report of a given type for a channel."""
    handle = handle.lstrip("@")
    channel = storage.get_channel(handle)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel @{handle} not found")

    report = storage.get_report(channel["id"], report_type)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_type}' not found")
    return ReportResponse(**report)


@router.post(
    "/channels/{handle}/reports/channel_overview",
    response_model=ReportResponse,
)
def generate_channel_overview(
    handle: str,
    storage: PostgresStorage = Depends(get_storage),
):
    """Generate or regenerate the channel overview report from saved summaries."""
    handle = handle.lstrip("@")
    channel = storage.get_channel(handle)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel @{handle} not found")

    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is not configured")

    generate_channel_report(channel["id"], handle, storage, GeminiClient(settings.gemini_api_key))
    report = storage.get_report(channel["id"], "channel_overview")
    if not report:
        raise HTTPException(status_code=500, detail="Report generation failed")
    return ReportResponse(**report)
