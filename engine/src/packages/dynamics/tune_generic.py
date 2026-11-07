"""Generic periodic-tuning runner for JINT, RAS, LORENZ, ROSSLER.

Runs Poincare section + return map and Lyapunov analysis, saving figures.
Usage:
    PYTHONPATH=src poetry run python -m packages.dynamics.tune_generic --model RAS --A-deg 20 --f 1.2 --Kp 30 --Kd 1.5 --Ks 200 --Bs 5 --rho-deg-s 0
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np

from .poincare import build_robot, analyze_poincare, plot_analysis
from .lyapunov import lyapunov_exponents, plot_lyapunov

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run(model, duration, dt, nsub, transient, tag, overrides):
    robot = build_robot(model, **overrides)
    y0 = np.zeros(32) if model.upper() in ("JINT", "RAS") else np.array([1.0, 1.0, 1.0])

    print(f"=== {tag}: model={model} {overrides} transient={transient} ===")

    try:
        analysis = analyze_poincare(robot, y0, duration, dt, transient=transient, nsub=nsub)
        print(f"Poincare fixed point: {analysis.fixed_point:.6f}")
        print(f"Num crossings: {len(analysis.crossings)}")
        if len(analysis.radii1) > 0:
            print(f"Radius spread: {float(np.max(analysis.radii2) - np.min(analysis.radii2)):.6f}")
        fig, _ = plot_analysis(analysis, show=False)
        fig.savefig(OUTPUT_DIR / f"poincare_{tag}.png", dpi=120)
    except ValueError as exc:
        print(f"Poincare analysis skipped: {exc}")
        analysis = None

    result = lyapunov_exponents(robot, y0, duration, dt, transient=transient, nsub=nsub, plotting=True)
    print(f"Lyapunov dimension: {result.dimension:.4f}")
    print(f"Classification: {result.classification}")
    print(f"Full exponents: {np.round(result.exponents, 4)}")
    if hasattr(result, "body_exponents") and result.body_exponents is not None:
        print(f"Body exponents: {dict(zip(result.bodies, np.round(result.body_exponents, 4)))}")
    fig2, _ = plot_lyapunov(result, show=False)
    fig2.savefig(OUTPUT_DIR / f"lyapunov_{tag}.png", dpi=120)
    print(f"Saved poincare_{tag}.png and lyapunov_{tag}.png in {OUTPUT_DIR}\n")
    return analysis, result


def main():
    parser = argparse.ArgumentParser(description="Generic periodic tuning: Poincare + Lyapunov")
    parser.add_argument("--model", choices=("JINT", "RAS", "LORENZ", "ROSSLER"), default="RAS")
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--dt", type=float, default=1.0 / 100.0)
    parser.add_argument("--nsub", type=int, default=2)
    parser.add_argument("--transient", type=float, default=0.0)
    parser.add_argument("--tag", type=str, default="run")
    parser.add_argument("--A-deg", type=float, default=None)
    parser.add_argument("--f", type=float, default=None)
    parser.add_argument("--rho-deg-s", type=float, default=None)
    parser.add_argument("--Kp", type=float, default=None)
    parser.add_argument("--Kd", type=float, default=None)
    parser.add_argument("--Ks", type=float, default=None)
    parser.add_argument("--Bs", type=float, default=None)
    parser.add_argument("--sigma", type=float, default=None)
    parser.add_argument("--rho", type=float, default=None)
    parser.add_argument("--beta", type=float, default=None)
    parser.add_argument("--a", type=float, default=None)
    parser.add_argument("--b", type=float, default=None)
    parser.add_argument("--c", type=float, default=None)
    args = parser.parse_args()

    overrides = {}
    for key, attr in [
        ("A_deg", "A_deg"), ("f", "f"), ("rho_deg_s", "rho_deg_s"),
        ("Kp", "Kp"), ("Kd", "Kd"), ("Ks", "Ks"), ("Bs", "Bs"),
        ("sigma", "sigma"), ("rho", "rho"), ("beta", "beta"),
        ("a", "a"), ("b", "b"), ("c", "c"),
    ]:
        val = getattr(args, attr)
        if val is not None:
            overrides[key] = val

    run(args.model, args.duration, args.dt, args.nsub, args.transient, args.tag, overrides)


if __name__ == "__main__":
    main()
