"""Single simulation endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from server.core.deps import ensure_engine_on_path

ensure_engine_on_path()

from packages.sim.plant import model_plant  # noqa: E402
from packages.sim.metrics import characterize_rows  # noqa: E402

router = APIRouter()


@router.post("/simulate")
def simulate(payload: dict[str, Any]) -> dict[str, Any]:
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

    try:
        plant_factory = model_plant(model, controller=controller, **overrides)
        plant = plant_factory(A_deg, f, rho_deg_s)
        rows = plant.simulate(duration, f_sim)
        params = plant.p
        metrics = characterize_rows(rows, params, steady_fraction=steady_fraction)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")

    metrics = _sanitize(metrics)
    return {
        "model": model.upper(),
        "controller": controller,
        "A_deg": A_deg,
        "f": f,
        "rho_deg_s": rho_deg_s,
        "duration": duration,
        "f_sim": f_sim,
        "n_rows": int(rows.shape[0]) if rows.ndim == 2 else 0,
        "metrics": metrics,
        "rows_preview": _rows_preview(rows),
    }


def _sanitize(metrics: dict) -> dict:
    import numpy as np

    out: dict = {}
    for key, value in metrics.items():
        if isinstance(value, np.generic):
            out[key] = value.item()
        elif isinstance(value, np.ndarray):
            out[key] = value.tolist()
        else:
            out[key] = value
    return out


def _rows_preview(rows, limit: int = 50) -> list[list[float]]:
    import numpy as np

    rows = np.asarray(rows, dtype=float)
    if rows.ndim != 2 or rows.size == 0:
        return []
    step = max(1, rows.shape[0] // limit)
    return [row.tolist() for row in rows[::step][:limit]]
