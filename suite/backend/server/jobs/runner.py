"""Background sweep / simulation job runner with WebSocket progress broadcasting."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import numpy as np

from server.core.deps import ensure_engine_on_path
from server.core.config import SWEEPS_DIR

ensure_engine_on_path()

from packages.sim.sweep import run_parameter_sweep  # noqa: E402
from packages.sim.plant import model_plant  # noqa: E402
from packages.sim.metrics import characterize_rows  # noqa: E402


@dataclass
class RunState:
    run_id: str
    kind: str
    status: str = "queued"  # queued | running | completed | failed
    progress: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    message: str = ""


class JobManager:
    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._lock = threading.Lock()
        # run_id -> set of websocket callbacks (callable accepting str)
        self._subscribers: dict[str, set[Callable[[str], None]]] = {}
        self._sub_lock = threading.Lock()

    def create_run(self, kind: str) -> str:
        run_id = str(uuid.uuid4())
        with self._lock:
            self._runs[run_id] = RunState(run_id=run_id, kind=kind)
        return run_id

    def get(self, run_id: str) -> Optional[RunState]:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self) -> list[RunState]:
        with self._lock:
            return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    def _update(self, run_id: str, **fields) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            for key, value in fields.items():
                setattr(run, key, value)
            payload = self._payload(run)
        self._broadcast(run_id, payload)

    def _payload(self, run: RunState) -> dict:
        return {
            "run_id": run.run_id,
            "kind": run.kind,
            "status": run.status,
            "progress": run.progress,
            "created_at": run.created_at,
            "finished_at": run.finished_at,
            "message": run.message,
            "error": run.error,
            "has_result": run.result is not None,
        }

    def subscribe(self, run_id: str, callback: Callable[[str], None]) -> None:
        with self._sub_lock:
            self._subscribers.setdefault(run_id, set()).add(callback)

    def unsubscribe(self, run_id: str, callback: Callable[[str], None]) -> None:
        with self._sub_lock:
            subs = self._subscribers.get(run_id)
            if subs:
                subs.discard(callback)

    def _broadcast(self, run_id: str, payload: dict) -> None:
        message = json.dumps(payload, default=_json_default)
        with self._sub_lock:
            subs = list(self._subscribers.get(run_id, set()))
        dead = []
        for cb in subs:
            try:
                cb(message)
            except Exception:
                dead.append(cb)
        for cb in dead:
            self.unsubscribe(run_id, cb)

    def complete(self, run_id: str, result: dict) -> None:
        finished = datetime.now(timezone.utc).isoformat()
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run.status = "completed"
            run.progress = 1.0
            run.finished_at = finished
            run.result = result
            run.message = "completed"
        self._broadcast(run_id, self._payload(run))

    def fail(self, run_id: str, error: str) -> None:
        finished = datetime.now(timezone.utc).isoformat()
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run.status = "failed"
            run.finished_at = finished
            run.error = error
            run.message = "failed"
        self._broadcast(run_id, self._payload(run))


def _json_default(obj: Any) -> Any:
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"not serializable: {type(obj)!r}")


job_manager = JobManager()


def run_sweep_job(
    run_id: str,
    model: str,
    axes: dict[str, list[Any]],
    *,
    controller: str = "pd",
    controller_kwargs: Optional[dict] = None,
    fixed: Optional[dict] = None,
    duration: float = 6.0,
    f_sim: float = 500.0,
    steady_fraction: float = 0.5,
    poincare: bool = False,
    lyapunov: bool = False,
    poincare_duration: float = 20.0,
    lyapunov_duration: float = 20.0,
    lyapunov_dt: float = 0.02,
) -> None:
    """Execute a parameter sweep in the background, streaming progress."""

    def progress(index: int, total: int, case) -> None:
        job_manager._update(
            run_id,
            status="running",
            progress=index / total,
            message=f"case {index}/{total}: {case.values}",
        )

    try:
        job_manager._update(
            run_id,
            status="running",
            progress=0.0,
            message=f"starting {model} sweep ({len(axes)} axes)",
        )

        result = run_parameter_sweep(
            model=model,
            axes=axes,
            controller=controller,
            controller_kwargs=controller_kwargs or {},
            fixed=fixed or {},
            duration=duration,
            f_sim=f_sim,
            steady_fraction=steady_fraction,
            keep_rows=False,
            progress=progress,
            poincare=poincare,
            poincare_duration=poincare_duration,
            lyapunov=lyapunov,
            lyapunov_duration=lyapunov_duration,
            lyapunov_dt=lyapunov_dt,
        )

        frame = result.metrics_frame()
        csv_path = SWEEPS_DIR / f"{run_id}.csv"
        frame.to_csv(csv_path, index=False)

        payload = {
            "model": result.model,
            "controller": result.controller,
            "axis_names": list(result.axis_names),
            "axes": {k: list(v) for k, v in result.axes.items()},
            "duration": result.duration,
            "f_sim": result.f_sim,
            "fixed": result.fixed,
            "n_cases": len(result.cases),
            "csv_path": str(csv_path),
            "cases": [
                {
                    "values": case.values,
                    "overrides": case.overrides,
                    "metrics": _sanitize(case.metrics),
                    "error": case.error,
                }
                for case in result.cases
            ],
        }
        job_manager.complete(run_id, payload)
    except Exception as exc:  # noqa: BLE001
        job_manager.fail(run_id, f"{type(exc).__name__}: {exc}")


def _sanitize(metrics: dict) -> dict:
    out: dict = {}
    for key, value in metrics.items():
        if isinstance(value, np.generic):
            out[key] = value.item()
        elif isinstance(value, np.ndarray):
            out[key] = value.tolist()
        elif value is None:
            out[key] = None
        else:
            out[key] = value
    return out


def run_sim_job(
    run_id: str,
    model: str,
    controller: str = "pd",
    *,
    A_deg: float = 50.0,
    f: float = 0.8,
    rho_deg_s: float = 0.0,
    duration: float = 6.0,
    f_sim: float = 500.0,
    steady_fraction: float = 0.5,
    overrides: Optional[dict] = None,
) -> None:
    """Execute a single simulation in the background."""

    try:
        job_manager._update(
            run_id,
            status="running",
            progress=0.0,
            message=f"starting {model} simulation ({controller})",
        )

        plant_factory = model_plant(model, controller=controller, **(overrides or {}))
        plant = plant_factory(A_deg, f, rho_deg_s)
        rows = plant.simulate(duration, f_sim)
        params = plant.p
        metrics = characterize_rows(rows, params, steady_fraction=steady_fraction)

        n_rows = int(rows.shape[0]) if rows.ndim == 2 else 0
        payload = {
            "model": model.upper(),
            "controller": controller,
            "A_deg": A_deg,
            "f": f,
            "rho_deg_s": rho_deg_s,
            "duration": duration,
            "f_sim": f_sim,
            "n_rows": n_rows,
            "metrics": _sanitize(metrics),
        }
        job_manager.complete(run_id, payload)
    except Exception as exc:  # noqa: BLE001
        job_manager.fail(run_id, f"{type(exc).__name__}: {exc}")
