"""Behavior metrics for snakeboard rollouts."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar

from packages.core.constants import RAD

METRIC_NAMES = (
    "distance",
    "x_displacement",
    "y_displacement",
    "path_length",
    "straightness",
    "speed",
    "mean_speed",
    "turn",
    "final_yaw",
    "energy",
    "sat_frac",
    "mean_abs_tau",
    "max_abs_tau",
    "tracking_rmse",
    "tracking_max_error",
    "measured_amplitude_deg",
    "measured_frequency_hz",
    "measured_drift_deg_s",
    "reference_amplitude_deg",
    "reference_drift_deg_s",
    "amplitude_ratio",
    "finite",
    "behavior",
)


def _empty_metrics() -> dict[str, Any]:
    metrics = {name: np.nan for name in METRIC_NAMES}
    metrics["finite"] = False
    metrics["behavior"] = "no data"
    return metrics


def _steady_window(rows: np.ndarray, fraction: float) -> np.ndarray:
    rows = np.asarray(rows, dtype=float)
    if rows.ndim != 2 or rows.shape[0] < 2:
        return rows
    if not 0.0 <= fraction < 1.0:
        raise ValueError("steady_fraction must be in [0, 1)")
    start = min(rows.shape[0] - 1, int(np.floor(fraction * rows.shape[0])))
    return rows[start:]


def _fit_drift_sinusoid(
    t: np.ndarray,
    values: np.ndarray,
    frequency: float,
) -> tuple[float, float, float]:
    t = np.asarray(t, dtype=float)
    values = np.asarray(values, dtype=float)
    if frequency <= 0.0 or t.size < 3:
        return np.nan, np.nan, np.nan
    centered = t - t[0]
    omega = 2.0 * np.pi * frequency
    design = np.column_stack(
        [
            centered,
            np.sin(omega * centered),
            np.cos(omega * centered),
            np.ones_like(centered),
        ]
    )
    try:
        coeff, *_ = np.linalg.lstsq(design, values, rcond=None)
    except np.linalg.LinAlgError:
        return np.nan, np.nan, np.nan
    drift, sin_coeff, cos_coeff, _ = coeff
    amplitude = float(np.hypot(sin_coeff, cos_coeff))
    residual = values - design @ coeff
    sse = float(np.sum(residual**2))
    return float(drift), amplitude, sse


def _estimate_frequency(t: np.ndarray, values: np.ndarray, guess: float) -> float:
    if guess <= 0.0 or len(t) < 3:
        return float("nan")
    lo = max(1e-3, 0.5 * guess)
    hi = max(lo + 1e-6, 1.5 * guess)

    def objective(frequency: float) -> float:
        _, _, sse = _fit_drift_sinusoid(t, values, frequency)
        return sse if np.isfinite(sse) else np.inf

    result = minimize_scalar(objective, bounds=(lo, hi), method="bounded")
    return float(result.x) if result.success else float(guess)


def _classify_behavior(
    distance: float,
    path_length: float,
    turn: float,
    finite: bool,
) -> str:
    if not finite:
        return "unstable"
    if path_length < 1e-4:
        return "stationary"
    if distance < 0.01 and turn < 0.1:
        return "stationary"
    if turn > 0.5 * np.pi and distance < 0.25 * path_length:
        return "turning"
    if distance > 0.01:
        return "translating"
    return "mixed"


def characterize_rows(
    rows: np.ndarray,
    params: Any,
    steady_fraction: float = 0.5,
) -> dict[str, Any]:
    """Compute gait and behavior metrics from simulated rollout rows."""
    rows = np.asarray(rows, dtype=float)
    metrics = _empty_metrics()
    if rows.size == 0:
        return metrics

    metrics["finite"] = bool(np.all(np.isfinite(rows)))
    if rows.ndim != 2 or rows.shape[0] < 3 or rows.shape[1] < 8:
        return metrics

    steady = _steady_window(rows, steady_fraction)
    if steady.shape[0] < 3:
        return metrics

    t = steady[:, 0]
    if not np.all(np.isfinite(t)) or t[-1] <= t[0]:
        return metrics

    x = steady[:, 1]
    y = steady[:, 2]
    yaw = steady[:, 3]
    O0 = steady[:, 4]
    O3 = steady[:, 5]
    O3d = steady[:, 6]
    tau = steady[:, 7]

    dt = np.diff(t)
    elapsed = float(t[-1] - t[0])
    dx = float(x[-1] - x[0])
    dy = float(y[-1] - y[0])
    distance = float(np.hypot(dx, dy))
    path_length = float(np.sum(np.hypot(np.diff(x), np.diff(y))))
    speed = distance / elapsed if elapsed > 0.0 else np.nan
    mean_speed = path_length / elapsed if elapsed > 0.0 else np.nan
    straightness = distance / path_length if path_length > 0.0 else np.nan
    turn = float(abs(yaw[-1] - yaw[0]))

    dO3 = np.gradient(O3, t)
    power = np.abs(tau * dO3)
    energy = float(np.sum(0.5 * (power[1:] + power[:-1]) * dt))

    saturation_limit = 0.999 * float(params.O0_lim)
    sat_frac = float(np.mean(np.abs(O0) >= saturation_limit))
    abs_tau = np.abs(tau)
    tracking_error = O3 - O3d
    tracking_rmse = float(np.sqrt(np.mean(tracking_error**2)))
    tracking_max = float(np.max(np.abs(tracking_error)))

    frequency = _estimate_frequency(t, O3, float(params.f))
    measured_drift, measured_amplitude, _ = _fit_drift_sinusoid(t, O3, frequency)
    reference_drift, reference_amplitude, _ = _fit_drift_sinusoid(
        t, O3d, float(params.f)
    )
    amplitude_ratio = (
        measured_amplitude / reference_amplitude
        if reference_amplitude and np.isfinite(reference_amplitude)
        else np.nan
    )

    metrics.update(
        {
            "distance": distance,
            "x_displacement": dx,
            "y_displacement": dy,
            "path_length": path_length,
            "straightness": straightness,
            "speed": speed,
            "mean_speed": mean_speed,
            "turn": turn,
            "final_yaw": float(yaw[-1]),
            "energy": energy,
            "sat_frac": sat_frac,
            "mean_abs_tau": float(np.mean(abs_tau)),
            "max_abs_tau": float(np.max(abs_tau)),
            "tracking_rmse": tracking_rmse,
            "tracking_max_error": tracking_max,
            "measured_amplitude_deg": float(measured_amplitude * RAD),
            "measured_frequency_hz": float(frequency),
            "measured_drift_deg_s": float(measured_drift * RAD),
            "reference_amplitude_deg": float(reference_amplitude * RAD),
            "reference_drift_deg_s": float(reference_drift * RAD),
            "amplitude_ratio": float(amplitude_ratio),
        }
    )
    metrics["behavior"] = _classify_behavior(
        distance,
        path_length,
        turn,
        bool(metrics["finite"]),
    )
    return metrics
