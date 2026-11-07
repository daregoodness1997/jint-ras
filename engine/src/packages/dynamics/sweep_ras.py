"""RAS parameter sweep: Poincare + Lyapunov across Ks, Bs, Kd, A_deg.

Usage:
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


def scan(param_name, values, fixed=None, duration=4.0, dt=1.0 / 100.0, nsub=2):
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
    print("=== Sweep Ks (stopper stiffness) ===")
    scan("Ks", [20, 100, 500], fixed=dict(A_deg=40, f=1.2, Kp=100, Kd=3.0, Bs=10, rho_deg_s=0.0))

    print("\n=== Sweep Bs (stopper damping) ===")
    scan("Bs", [1, 10, 50], fixed=dict(A_deg=40, f=1.2, Kp=100, Kd=3.0, Ks=100, rho_deg_s=0.0))

    print("\n=== Sweep Kd (derivative gain) ===")
    scan("Kd", [0.5, 3.0, 10.0], fixed=dict(A_deg=40, f=1.2, Kp=100, Ks=100, Bs=10, rho_deg_s=0.0))

    print("\n=== Sweep A_deg (amplitude) ===")
    scan("A_deg", [10, 40], fixed=dict(f=1.2, Kp=100, Kd=3.0, Ks=100, Bs=10, rho_deg_s=0.0))
