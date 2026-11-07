from __future__ import annotations

import argparse
import os
from pathlib import Path
import matplotlib.pyplot as plt

import numpy as np

from packages.control import available_controllers
from packages.core.params import jint_params, ras_params
from packages.dynamics.lyapunov import lyapunov_exponents, plot_lyapunov
from packages.dynamics.poincare import analyze_poincare, build_robot, plot_analysis
from packages.sim import model_plant


def _parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Optimize the snakeboard gait (JINT/RAS)")
    ap.add_argument(
        "--model",
        choices=("JINT", "RAS", "LORENZ", "ROSSLER"),
        default="JINT",
        help="snakeboard model or chaotic system",
    )
    ap.add_argument(
        "--controller",
        choices=available_controllers(),
        default="pd",
        help="feedback controller",
    )
    ap.add_argument("--duration", type=float, default=6.0, help="rollout length [s]")
    ap.add_argument("--f-sim", type=float, default=500.0, help="sim rate [Hz]")
    ap.add_argument(
        "--dt",
        type=float,
        default=None,
        help="override simulation step [s] (defaults to 1/f-sim)",
    )
    ap.add_argument(
        "--plot-samples",
        type=int,
        default=5000,
        help="minimum number of samples used in saved overview plots",
    )
    ap.add_argument(
        "--no-plot", dest="plot", action="store_false", help="skip plotting results"
    )
    ap.add_argument(
        "--poincare",
        action="store_true",
        help="run Poincare section and return-map analysis",
    )
    ap.add_argument(
        "--poincare-duration",
        type=float,
        default=20.0,
        help="Poincare analysis duration [s]",
    )
    ap.add_argument(
        "--poincare-theta",
        type=float,
        default=-np.pi / 2.0,
        help="Poincare section angle [rad]",
    )
    ap.add_argument(
        "--poincare-transient",
        type=float,
        default=None,
        help="discard this many seconds before sectioning",
    )
    ap.add_argument(
        "--poincare-nsub",
        type=int,
        default=4,
        help="substeps per dt for Poincare integration",
    )
    ap.add_argument(
        "--lyapunov",
        action="store_true",
        help="run Lyapunov exponent and fractal classification analysis",
    )
    ap.add_argument(
        "--lyapunov-duration",
        type=float,
        default=20.0,
        help="Lyapunov analysis duration [s]",
    )
    ap.add_argument(
        "--lyapunov-dt",
        type=float,
        default=0.02,
        help="Lyapunov integration step [s]",
    )
    ap.add_argument(
        "--lyapunov-transient",
        type=float,
        default=None,
        help="discard this many seconds before Lyapunov analysis",
    )
    ap.add_argument(
        "--lyapunov-eps",
        type=float,
        default=1e-6,
        help="finite-difference step for the Jacobian",
    )
    ap.add_argument(
        "--A-deg",
        type=float,
        default=None,
        help="gait amplitude [deg] (default: model default)",
    )
    ap.add_argument(
        "--f",
        type=float,
        default=None,
        help="gait frequency [Hz] (default: model default)",
    )
    ap.add_argument(
        "--rho-deg-s",
        type=float,
        default=None,
        help="gait drift [deg/s] (default: model default)",
    )

    return ap.parse_args(argv)


def _default_gait(model):
    params = jint_params() if model == "JINT" else ras_params()
    return params.A_deg, params.f, params.rho_deg_s


def _cache_path(args, gait, dt=None):
    A_deg, f, rho_deg_s = gait
    cache_dir = os.environ.get("SNAKEBOARD_CACHE_DIR")
    root = (
        Path(cache_dir)
        if cache_dir
        else Path(__file__).resolve().parents[4] / "outputs" / "simulations"
    )
    name = (
        f"{args.model}_{args.controller}_A{A_deg:g}_f{f:g}_rho{rho_deg_s:g}"
        f"_dur{args.duration:g}_fsim{args.f_sim:g}"
        + (f"_dt{dt:g}" if dt is not None else "")
        + ".npz"
    )
    return root / name


def _load_cached(path):
    with np.load(path) as data:
        return data["rows"]


def _save_cached(path, rows, args, gait):
    A_deg, f, rho_deg_s = gait
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        rows=rows,
        model=args.model,
        controller=args.controller,
        A_deg=A_deg,
        f=f,
        rho_deg_s=rho_deg_s,
        duration=args.duration,
        f_sim=args.f_sim,
    )


def _slug(text):
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text))
    return "_".join(part for part in cleaned.split("_") if part) or "plot"


def _plot_dir():
    root = os.environ.get("SNAKEBOARD_OUTPUT_DIR")
    base = Path(root) if root else Path(__file__).resolve().parents[4] / "outputs"
    return base / "plots"


def _plot_stem(args, gait):
    A_deg, f, rho_deg_s = gait
    return _slug(
        f"{args.model}_{args.controller}_A{A_deg:g}_f{f:g}"
        f"_rho{rho_deg_s:g}_dur{args.duration:g}"
    )


def _figure_title(args, gait):
    A_deg, f, rho_deg_s = gait
    return (
        f"{args.model} | {args.controller.upper()} controller | "
        f"A={A_deg:g} deg, f={f:g} Hz, rho={rho_deg_s:g} deg/s"
    )


def _save_figure(fig, stem):
    plot_dir = _plot_dir()
    plot_dir.mkdir(parents=True, exist_ok=True)
    path = plot_dir / f"{stem}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"Saved plot: {path}")
    return path


def _plot_rows(plant_factory, args, gait, rows):
    target = args.plot_samples
    if target <= 0 or target <= len(rows) or args.duration <= 0.0:
        return rows
    plot_f_sim = target / args.duration
    print(f"Simulating {target} plot samples at {plot_f_sim:g} Hz")
    return plant_factory(*gait).simulate(args.duration, plot_f_sim)


def run(argv=None):
    args = _parse_args(argv)
    plant_factory = model_plant(args.model, controller=args.controller)
    default_A, default_f, default_rho = _default_gait(args.model)
    A_deg = args.A_deg if args.A_deg is not None else default_A
    f = args.f if args.f is not None else default_f
    rho_deg_s = args.rho_deg_s if args.rho_deg_s is not None else default_rho
    gait = (A_deg, f, rho_deg_s)
    cache_path = _cache_path(args, gait, dt=args.dt)

    if cache_path.exists():
        rows = _load_cached(cache_path)
        print(f"Loaded cached simulation ({len(rows)} samples) from {cache_path}")
    else:
        print(
            f"Simulating the {args.model} robot with initial gait parameters: "
            f"A={A_deg:g} deg, f={f:g} Hz, rho={rho_deg_s:g} deg/s"
        )
        plant = plant_factory(A_deg, f, rho_deg_s)
        rows = plant.simulate(args.duration, args.f_sim, dt=args.dt)
        _save_cached(cache_path, rows, args, gait)
        print(
            f"Simulated {len(rows)} samples ({args.duration:g} s at "
            f"{args.f_sim:g} Hz" + (f", dt={args.dt:g}" if args.dt else "") + "); "
            f"saved to {cache_path}"
        )

    poincare_analysis = None
    if args.poincare:
        transient = (
            0.5 * args.poincare_duration
            if args.poincare_transient is None
            else args.poincare_transient
        )
        try:
            robot = build_robot(
                args.model,
                controller=args.controller,
                A_deg=A_deg,
                f=f,
                rho_deg_s=rho_deg_s,
            )
            if args.model.upper() in ("JINT", "RAS"):
                y0_p = np.zeros(32)
            else:
                y0_p = np.array([1.0, 1.0, 1.0])
            poincare_analysis = analyze_poincare(
                robot,
                y0_p,
                args.poincare_duration,
                1.0 / args.f_sim,
                theta=args.poincare_theta,
                transient=transient,
                nsub=args.poincare_nsub,
            )
            print(f"Poincare fixed point: {poincare_analysis.fixed_point:.6f}")
        except ValueError as exc:
            print(f"Poincare analysis failed: {exc}")

    lyapunov_result = None
    if args.lyapunov:
        transient = (
            0.5 * args.lyapunov_duration
            if args.lyapunov_transient is None
            else args.lyapunov_transient
        )
        try:
            robot = build_robot(
                args.model,
                controller=args.controller,
                A_deg=A_deg,
                f=f,
                rho_deg_s=rho_deg_s,
            )
            if args.model.upper() in ("JINT", "RAS"):
                y0_l = np.zeros(32)
            else:
                y0_l = np.array([1.0, 1.0, 1.0])
            lyapunov_result = lyapunov_exponents(
                robot,
                y0_l,
                args.lyapunov_duration,
                args.lyapunov_dt,
                transient=transient,
                eps=args.lyapunov_eps,
            )
            print("Lyapunov exponents [bits/time]:")

            for body, exponent in zip(
                lyapunov_result.bodies, lyapunov_result.body_exponents
            ):
                print(f"  {body:<8s} {exponent: .4f}")
            print(f" Full spectrum: {lyapunov_result.exponents}")
            for idx, exponent in enumerate(lyapunov_result.exponents):
                print(f"    mode {idx:<3d} {exponent: .4f}")

            print(f"Lyapunov dimension: {lyapunov_result.dimension:.4f}")
            print(f"Classification: {lyapunov_result.classification}")
        except (ValueError, np.linalg.LinAlgError) as exc:
            print(f"Lyapunov analysis failed: {exc}")

    if args.plot:
        plot_rows = _plot_rows(plant_factory, args, gait, rows)
        t = plot_rows[:, 0]
        if len(t) > 1:
            dO3 = np.gradient(plot_rows[:, 5], t)
        else:
            dO3 = np.zeros_like(t)

        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        axes[0].plot(plot_rows[:, 1], plot_rows[:, 2], color="C0", linewidth=1.2)
        axes[0].set_xlabel("X0 [m]")
        axes[0].set_ylabel("Y0 [m]")
        axes[0].set_title("Planar Trajectory")
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(t, plot_rows[:, 5], color="C0", linewidth=1.2, label="O3 actual")
        axes[1].plot(
            t,
            plot_rows[:, 6],
            color="C1",
            linestyle="--",
            linewidth=1.0,
            label="O3d reference",
        )
        axes[1].set_xlabel("Time [s]")
        axes[1].set_ylabel("Rotor angle [rad]")
        axes[1].set_title("Rotor Tracking")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        axes[2].plot(plot_rows[:, 5], dO3, color="C2", linewidth=1.0)
        axes[2].set_xlabel("O3 [rad]")
        axes[2].set_ylabel("dO3 [rad/s]")
        axes[2].set_title("Rotor Phase Portrait")
        axes[2].grid(True, alpha=0.3)

        fig.suptitle(_figure_title(args, gait))
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
        stem = _plot_stem(args, gait)
        _save_figure(fig, f"{stem}_overview")

        if poincare_analysis is not None:
            poincare_fig, _ = plot_analysis(
                poincare_analysis,
                theta=args.poincare_theta,
                show=False,
            )
            poincare_fig.suptitle(
                f"{args.model} | {args.controller.upper()} | "
                f"Poincare section at theta={args.poincare_theta:.3f} rad"
            )
            poincare_fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
            _save_figure(poincare_fig, f"{stem}_poincare")

        if lyapunov_result is not None:
            lyapunov_fig, _ = plot_lyapunov(lyapunov_result, show=False)
            lyapunov_fig.suptitle(
                f"{args.model} | {args.controller.upper()} | Lyapunov spectrum | "
                f"D={lyapunov_result.dimension:.3f} | {lyapunov_result.classification}"
            )
            lyapunov_fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
            _save_figure(lyapunov_fig, f"{stem}_lyapunov")

        plt.close("all")

    return rows


def main(argv=None):
    run(argv)


if __name__ == "__main__":
    main()
