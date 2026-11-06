"""Analysis endpoints: Poincare section and Lyapunov exponents."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from server.core.deps import ensure_engine_on_path

ensure_engine_on_path()

from packages.sim.plant import model_plant  # noqa: E402

router = APIRouter()


@router.post("/analyze/poincare")
def analyze_poincare(payload: dict[str, Any]) -> dict[str, Any]:
    model = payload.get("model", "JINT")
    controller = payload.get("controller", "pd")
    A_deg = float(payload.get("A_deg", 50.0))
    f = float(payload.get("f", 0.8))
    rho_deg_s = float(payload.get("rho_deg_s", 0.0))
    duration = float(payload.get("duration", 20.0))
    f_sim = float(payload.get("f_sim", 500.0))
    theta = float(payload.get("theta", -3.141592653589793 / 2.0))
    transient = payload.get("transient", None)
    if transient is not None:
        transient = float(transient)

    try:
        plant_factory = model_plant(model, controller=controller)
        plant = plant_factory(A_deg, f, rho_deg_s)
        from packages.dynamics.poincare import analyze_poincare as _ap  # noqa: PLC0415

        analysis = _ap(
            plant.robot,
            __import__("numpy").zeros(32),
            duration,
            1.0 / f_sim,
            theta=theta,
            transient=transient,
        )
        return {
            "model": model.upper(),
            "fixed_point": float(analysis.fixed_point),
            "crossings": int(len(analysis.crossings)),
            "crossing_points": [float(c) for c in analysis.crossings],
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")


@router.post("/analyze/lyapunov")
def analyze_lyapunov(payload: dict[str, Any]) -> dict[str, Any]:
    model = payload.get("model", "JINT")
    controller = payload.get("controller", "pd")
    A_deg = float(payload.get("A_deg", 50.0))
    f = float(payload.get("f", 0.8))
    rho_deg_s = float(payload.get("rho_deg_s", 0.0))
    duration = float(payload.get("duration", 20.0))
    dt = float(payload.get("dt", 0.02))
    transient = payload.get("transient", None)
    if transient is not None:
        transient = float(transient)
    eps = float(payload.get("eps", 1e-6))

    try:
        plant_factory = model_plant(model, controller=controller)
        plant = plant_factory(A_deg, f, rho_deg_s)
        from packages.dynamics.lyapunov import lyapunov_exponents as _le  # noqa: PLC0415

        result = _le(
            plant.robot,
            __import__("numpy").zeros(32),
            duration,
            dt,
            transient=transient,
            eps=eps,
        )
        return {
            "model": model.upper(),
            "dimension": float(result.dimension),
            "classification": result.classification,
            "exponents": [float(e) for e in result.exponents],
            "body_exponents": [float(e) for e in result.body_exponents],
            "full_exponents": [float(e) for e in result.full_exponents],
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")
