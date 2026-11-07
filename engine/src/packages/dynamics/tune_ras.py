"""RAS periodic tuning: Poincare + Lyapunov with parameter sweeps.

Usage:
    PYTHONPATH=src poetry run python -m packages.dynamics.tune_ras
    PYTHONPATH=src poetry run python -m packages.dynamics.sweep_ras
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np

from .poincare import build_robot, analyze_poincare
from .lyapunov import lyapunov_exponents

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run(A_deg, f, Kp, Kd, Ks, Bs, rho_deg_s=0.0, duration=8.0, dt=1.0 / 100.0, nsub=2, tag="run"):
    overrides = dict(A_deg=A_deg, f=f, Kp=Kp, Kd=Kd, Ks=Ks, Bs=Bs, rho_deg_s=rho_deg_s)
    robot = build_robot("RAS", **overrides)
    y0 = np.zeros(32)

    print(f"=== {tag}: A={A_deg}deg f={f}Hz Kp={Kp} Kd={Kd} Ks={Ks} Bs={Bs} rho={rho_deg_s} ===")

    analysis = analyze_poincare(robot, y0, duration, dt, nsub=nsub)
    print(f"Poincare fixed point: {analysis.fixed_point:.6f}")
    print(f"Num crossings: {len(analysis.crossings)}")
    if len(analysis.radii1) > 0:
        print(f"Radius spread: {float(np.max(analysis.radii2) - np.min(analysis.radii2)):.6f}")
    from .poincare import plot_analysis

    fig, _ = plot_analysis(analysis, show=False)
    fig.savefig(OUTPUT_DIR / f"poincare_{tag}.png", dpi=120)
    print(f"Saved poincare_{tag}.png in {OUTPUT_DIR}\n")


def scan(param_name, values, fixed=None, duration=8.0, dt=1.0 / 100.0, nsub=2):
    fixed = fixed or dict(A_deg=40, f=1.2, Kp=100, Kd=3.0, Ks=100, Bs=10, rho_deg_s=0.0)
    results = []
    for v in values:
        overrides = dict(fixed, **{param_name: v})
        robot = build_robot("RAS", **overrides)
        y0 = np.zeros(32)

        analysis = analyze_poincare(robot, y0, duration, dt, nsub=nsub)
        spread = float(np.max(analysis.radii2) - np.min(analysis.radii2)) if len(analysis.radii1) > 0 else np.nan

        result = lyapunov_exponents(robot, y0, duration, dt, nsub=nsub)
        results.append((v, spread, result.dimension, result.classification, result.exponents.copy(), result.body_exponents.copy()))
        print(f"{param_name}={v:<8g} spread={spread:9.6f} dim={result.dimension:7.3f} {result.classification}")
        print(f"  body exp: Board={result.body_exponents[0]: .4f} Wheels={result.body_exponents[1]: .4f} Rotor={result.body_exponents[2]: .4f}")
    return results


if __name__ == "__main__":
    run(A_deg=20, f=1.2, Kp=30, Kd=1.5, Ks=200, Bs=5, rho_deg_s=0.0, tag="set1_periodic")
    run(A_deg=40, f=1.2, Kp=100, Kd=3.0, Ks=100, Bs=10, rho_deg_s=5.0, tag="set5_drift")
