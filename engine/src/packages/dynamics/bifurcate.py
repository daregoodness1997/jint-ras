"""Bifurcation diagrams for JINT, RAS, LORENZ, ROSSLER.

Follows the reference implementation pattern:
  1. Integrate a transient (t_transient) to settle onto the attractor.
  2. Integrate a compute window (t_compute) starting from the transient end.
  3. Find local maxima of x_0 via dx/dt sign change:
       dx_dt = np.diff(x) / dt
       maxima_idx = np.where((dx_dt[:-1] > 0) & (dx_dt[1:] < 0))[0]
  4. Plot parameter vs local maxima of x_0.

Periodic = one line per period; period-doubling = 2, 4, 8... lines; chaos = dense band.

Usage:
    PYTHONPATH=src poetry run python -m packages.dynamics.bifurcate --model RAS --param A_deg --start 1 --stop 60 --step 0.5 --state-idx 5
    PYTHONPATH=src poetry run python -m packages.dynamics.bifurcate --model ROSSLER --param c --start 2 --stop 8 --step 0.1
    PYTHONPATH=src poetry run python -m packages.dynamics.bifurcate --model LORENZ --param rho --start 20 --stop 100 --step 2
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt

from .poincare import build_robot, simulate

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


STATE_NAMES = {
    0: "x0 position [m]",
    1: "y0 position [m]",
    2: "Q0 front steering [rad]",
    3: "O0 board yaw [rad]",
    4: "state[4] (aux position)",
    5: "state[5] (aux position)",
    15: "O3 rotor angle [rad]",
}


def _state_label(state_idx: int) -> str:
    return STATE_NAMES.get(state_idx, f"state[{state_idx}]")


def bifurcate(
    model, param, start, stop, step, t_transient, t_compute, dt, fixed_overrides, tag, state_idx=0
):
    param_values = np.arange(start, stop + 1e-9, step)
    xs, ys = [], []

    original_overrides = dict(fixed_overrides)
    print(param_values, "parameter values>>>")

    for val in param_values:
        overrides = dict(original_overrides, **{param: float(val)})
        robot = build_robot(model, **overrides)
        y0 = (
            np.zeros(32)
            if model.upper() in ("JINT", "RAS")
            else np.array([1.0, 1.0, 1.0])
        )

        # --- Transient integration: settle onto attractor ------------------
        _, transient_states = simulate(robot, y0, t_transient, dt)
        y_start = transient_states[-1].copy()

        # --- Compute integration: sample attractor -------------------------
        _, states = simulate(robot, y_start, t_compute, dt)

        # Local maxima of the chosen state via dx/dt sign change
        x = states[:, state_idx]
        dx_dt = np.diff(x) / dt
        maxima_idx = np.where((dx_dt[:-1] > 0) & (dx_dt[1:] < 0))[0]

        for idx in maxima_idx:
            xs.append(val)
            ys.append(x[idx])

    xs = np.asarray(xs)
    ys = np.asarray(ys)

    fig, ax = plt.subplots(figsize=(12, 6))
    if len(xs) > 0:
        ax.scatter(xs, ys, s=0.5, alpha=0.5, color="C0")
    ax.set_xlabel(param)
    ax.set_ylabel(f"Local maxima of {_state_label(state_idx)}")
    ax.set_title(f"Bifurcation Diagram - Varying {param} ({model})")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = OUTPUT_DIR / f"bifurcation_{tag}.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out} ({len(xs)} points)")
    return fig, ax


def main():
    parser = argparse.ArgumentParser(description="Bifurcation diagrams")
    parser.add_argument(
        "--model", choices=("JINT", "RAS", "LORENZ", "ROSSLER"), default="RAS"
    )
    parser.add_argument(
        "--param", type=str, required=True, help="Parameter name to sweep"
    )
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--stop", type=float, required=True)
    parser.add_argument("--step", type=float, required=True)
    parser.add_argument(
        "--t-transient", type=float, default=500.0, help="Transient integration time"
    )
    parser.add_argument(
        "--t-compute", type=float, default=500.0, help="Compute integration time"
    )
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--tag", type=str, default="run")
    parser.add_argument(
        "--state-idx",
        type=int,
        default=15,
        help="state column to bifurcate (0=x0, 1=y0, 2=Q0, 3=O0, 15=O3 rotor; default 15)",
    )
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

    fixed_overrides = {}
    for key, attr in [
        ("A_deg", "A_deg"),
        ("f", "f"),
        ("rho_deg_s", "rho_deg_s"),
        ("Kp", "Kp"),
        ("Kd", "Kd"),
        ("Ks", "Ks"),
        ("Bs", "Bs"),
        ("sigma", "sigma"),
        ("rho", "rho"),
        ("beta", "beta"),
        ("a", "a"),
        ("b", "b"),
        ("c", "c"),
    ]:
        val = getattr(args, attr)
        if val is not None:
            fixed_overrides[key] = val

    bifurcate(
        args.model,
        args.param,
        args.start,
        args.stop,
        args.step,
        args.t_transient,
        args.t_compute,
        args.dt,
        fixed_overrides,
        args.tag,
        args.state_idx,
    )


if __name__ == "__main__":
    main()
