"""Single simulation endpoint (runs as a background job, non-blocking)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from server.jobs.runner import job_manager, run_sim_job

router = APIRouter()


@router.post("/run-simulate")
def start_simulate(payload: dict[str, Any]) -> dict[str, Any]:
    model = payload.get("model", "JINT")
    controller = payload.get("controller", "pd")
    A_deg = float(payload.get("A_deg", 50.0))
    f = float(payload.get("f", 0.8))
    rho_deg_s = float(payload.get("rho_deg_s", 0.0))
    duration = float(payload.get("duration", 6.0))
    f_sim = float(payload.get("f_sim", 500.0))
    steady_fraction = float(payload.get("steady_fraction", 0.5))
    overrides = {k: v for k, v in payload.items() if k not in {
        "model", "controller", "A_deg", "f", "rho_deg_s", "duration", "f_sim", "steady_fraction",
    }}

    run_id = job_manager.create_run(kind="simulate")
    job_manager._broadcast(
        run_id,
        {"run_id": run_id, "kind": "simulate", "status": "queued", "progress": 0.0},
    )

    import threading

    threading.Thread(
        target=run_sim_job,
        args=(run_id, model, controller),
        kwargs={
            "A_deg": A_deg,
            "f": f,
            "rho_deg_s": rho_deg_s,
            "duration": duration,
            "f_sim": f_sim,
            "steady_fraction": steady_fraction,
            "overrides": overrides,
        },
        daemon=True,
    ).start()

    return {"run_id": run_id, "status": "queued"}


@router.get("/run-simulate/{run_id}")
def get_simulate(run_id: str) -> dict[str, Any]:
    run = job_manager.get(run_id)
    if run is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    return {
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
