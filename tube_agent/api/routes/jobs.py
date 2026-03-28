"""Job tracking API routes."""

from fastapi import APIRouter, Depends, HTTPException

from tube_agent.api.deps import get_storage
from tube_agent.models.schemas import JobResponse
from tube_agent.storage.postgres import PostgresStorage

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    storage: PostgresStorage = Depends(get_storage),
):
    """Get job status and progress."""
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobResponse(**job)
