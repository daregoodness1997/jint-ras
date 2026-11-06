"""Run listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from server.jobs.runner import job_manager

router = APIRouter()


@router.get("/runs")
def list_runs() -> dict[str, Any]:
    return {"runs": [run.__dict__ for run in job_manager.list_runs()]}
