"""Parameter sweep endpoint (starts background job)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from server.jobs.runner import job_manager, run_sweep_job

router = APIRouter()


@router.post("/sweep")
def start_sweep(payload: dict[str, Any]) -> dict[str, Any]:
    model = payload.get("model", "JINT")
    controller = payload.get("controller", "pd")
    axes = payload.get("axes")
    if not axes or not isinstance(axes, dict):
        raise HTTPException(status_code=400, detail="axes must be a non-empty dict of param -> [values]")
    fixed = payload.get("fixed") or {}
    duration = float(payload.get("duration", 6.0))
    f_sim = float(payload.get("f_sim", 500.0))
    steady_fraction = float(payload.get("steady_fraction", 0.5))
    poincare = bool(payload.get("poincare", False))
    lyapunov = bool(payload.get("lyapunov", False))
    poincare_duration = float(payload.get("poincare_duration", 20.0))
    lyapunov_duration = float(payload.get("lyapunov_duration", 20.0))
    lyapunov_dt = float(payload.get("lyapunov_dt", 0.02))

    run_id = job_manager.create_run(kind="sweep")
    job_manager._broadcast(run_id, {"run_id": run_id, "kind": "sweep", "status": "queued", "progress": 0.0})

    import threading

    threading.Thread(
        target=run_sweep_job,
        args=(run_id, model, axes),
        kwargs={
            "controller": controller,
            "fixed": fixed,
            "duration": duration,
            "f_sim": f_sim,
            "steady_fraction": steady_fraction,
            "poincare": poincare,
            "lyapunov": lyapunov,
            "poincare_duration": poincare_duration,
            "lyapunov_duration": lyapunov_duration,
            "lyapunov_dt": lyapunov_dt,
        },
        daemon=True,
    ).start()

    return {"run_id": run_id, "status": "queued"}


@router.get("/sweep/{run_id}")
def get_sweep(run_id: str) -> dict[str, Any]:
    run = job_manager.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    payload = {
        "run_id": run.run_id,
        "kind": run.kind,
        "status": run.status,
        "progress": run.progress,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
        "message": run.message,
        "error": run.error,
        "result": run.result,
    }
    return payload
