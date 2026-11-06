"""Command-line parameter sweep for the snakeboard engine."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from packages.control import available_controllers
from packages.core.params import jint_params, ras_params
from packages.sim.metrics import METRIC_NAMES
from packages.sim.sweep import run_parameter_sweep
from packages.viz.sweep import plot_sweep, plot_sweep_trajectories


def _default_params(model: str):
    return jint_params() if model.upper() == "JINT" else ras_params()


# Gait parameterization axes: (A_deg, f, rho_deg_s). A gait-map sweep varies a
# pair of these while holding the remaining gait parameter fixed.
GAIT_PARAMS = ("A_deg", "f", "rho_deg_s")
MAX_GAIT_AXES = 2


def _coerce(name: str, raw: str, model: str) -> Any:
    defaults = _default_params(model)
    if not hasattr(defaults, name):
        raise ValueError(f"unknown parameter {name!r}")
    default = getattr(defaults, name)
    text = raw.strip()
    if isinstance(default, bool):
        return text.lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        return int(text)
    if isinstance(default, float):
        return float(text)
    if isinstance(default, tuple):
        inner = text.strip("()[]")
        parts = [part.strip() for part in inner.split(",") if part.strip()]
        try:
            return tuple(float(part) for part in parts)
        except ValueError:
            return tuple(parts)
    return text


def _parse_assignments(
    items: Iterable[str],
    model: str,
    *,
    split_values: bool,
) -> list[tuple[str, Any]]:
    parsed = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"expected NAME=VALUE, got {item!r}")
        name, raw = item.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"expected NAME=VALUE, got {item!r}")
        if split_values:
            values = [
                _coerce(name, part, model)
                for part in raw.split(",")
                if part.strip()
            ]
            if not values:
                raise ValueError(f"no values supplied for {name!r}")
            parsed.append((name, values))
        else:
            parsed.append((name, _coerce(name, raw, model)))
    return parsed


def _parse_gait_axes(items: list[str], model: str) -> dict[str, list[Any]]:
    """Parse gait parameter axes (A_deg, f, rho_deg_s) for a gait-map sweep."""
    parsed: dict[str, list[Any]] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"expected NAME=VALUE, got {item!r}")
        name, raw = item.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"expected NAME=VALUE, got {item!r}")
        if name not in GAIT_PARAMS:
            raise ValueError(
                f"unknown gait axis {name!r}; expected one of {GAIT_PARAMS}"
            )
        values = [
            _coerce(name, part, model)
            for part in raw.split(",")
            if part.strip()
        ]
        if not values:
            raise ValueError(f"no values supplied for {name!r}")
        if name in parsed:
            raise ValueError(f"duplicate gait axis {name!r}")
        parsed[name] = values
    if len(parsed) > MAX_GAIT_AXES:
        raise ValueError(
            f"at most {MAX_GAIT_AXES} gait axes allowed; got {len(parsed)}"
        )
    return parsed


def _slug(text: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text))
    return "_".join(part for part in cleaned.split("_") if part) or "sweep"


def _parser(argv=None):
    parser = argparse.ArgumentParser(
        description="Sweep snakeboard parameters and characterize each rollout"
    )
    parser.add_argument("--model", choices=("JINT", "RAS"), default="JINT")
    parser.add_argument(
        "--controller",
        choices=available_controllers(),
        default="pd",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=None,
        metavar="NAME=V1,V2,...",
        help="parameter axis (repeat for a 2-D sweep)",
    )
    parser.add_argument(
        "--gait-axis",
        action="append",
        default=[],
        metavar="NAME=V1,V2,...",
        help=f"gait parameter axis ({', '.join(GAIT_PARAMS)}; repeat for a 2-D gait map)",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="fixed parameter override",
    )
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--f-sim", type=float, default=500.0)
    parser.add_argument("--steady-fraction", type=float, default=0.5)
    parser.add_argument(
        "--metrics",
        default="distance,speed,turn,energy,sat_frac,tracking_rmse",
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-plot", dest="plot", action="store_false")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--poincare", action="store_true")
    parser.add_argument("--poincare-duration", type=float, default=20.0)
    parser.add_argument("--poincare-theta", type=float, default=-np.pi / 2.0)
    parser.add_argument("--poincare-transient", type=float, default=None)
    parser.add_argument("--lyapunov", action="store_true")
    parser.add_argument("--lyapunov-duration", type=float, default=20.0)
    parser.add_argument("--lyapunov-dt", type=float, default=0.02)
    parser.add_argument("--lyapunov-transient", type=float, default=None)
    parser.add_argument("--lyapunov-eps", type=float, default=1e-6)
    return parser


def run(argv=None):
    args = _parser().parse_args(argv)
    try:
        param_items = args.param or []
        axes = dict(
            _parse_assignments(param_items, args.model, split_values=True)
        )
        fixed = dict(
            _parse_assignments(args.set, args.model, split_values=False)
        )
        gait_axes = _parse_gait_axes(args.gait_axis, args.model)
        axes = {**axes, **gait_axes}
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if not axes:
        raise SystemExit(
            "at least one sweep axis is required (--param or --gait-axis)"
        )

    metrics = [name.strip() for name in args.metrics.split(",") if name.strip()]
    unknown_metrics = [name for name in metrics if name not in METRIC_NAMES]
    if unknown_metrics:
        raise SystemExit(
            f"unknown metric(s) {unknown_metrics}; expected one of {METRIC_NAMES}"
        )

    def progress(index: int, total: int, case) -> None:
        values = ", ".join(f"{name}={value}" for name, value in case.values.items())
        suffix = f" error={case.error}" if case.error else ""
        print(f"[{index}/{total}] {values}{suffix}")

    result = run_parameter_sweep(
        args.model,
        axes,
        controller=args.controller,
        fixed=fixed,
        duration=args.duration,
        f_sim=args.f_sim,
        steady_fraction=args.steady_fraction,
        progress=progress,
        poincare=args.poincare,
        poincare_duration=args.poincare_duration,
        poincare_theta=args.poincare_theta,
        poincare_transient=args.poincare_transient,
        lyapunov=args.lyapunov,
        lyapunov_duration=args.lyapunov_duration,
        lyapunov_dt=args.lyapunov_dt,
        lyapunov_transient=args.lyapunov_transient,
        lyapunov_eps=args.lyapunov_eps,
    )

    print()
    print(result.table())

    if args.output_dir is not None:
        output_dir = Path(args.output_dir)
    else:
        stem = _slug(
            f"{result.model}_{result.controller}_"
            + "_".join(result.axis_names)
        )
        output_dir = (
            Path(__file__).resolve().parents[4] / "outputs" / "sweeps" / stem
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    result.save_csv(output_dir / "metrics.csv")
    print(f"Saved metrics: {output_dir / 'metrics.csv'}")

    if args.plot:
        stem = _slug(
            f"{result.model}_{result.controller}_"
            + "_".join(result.axis_names)
        )
        plot_sweep(
            result,
            metrics,
            output_dir=output_dir,
            show=args.show,
            prefix=f"{stem}_metrics",
        )
        if any(case.rows.size for case in result.cases):
            plot_sweep_trajectories(
                result,
                output_dir=output_dir,
                show=args.show,
                prefix=f"{stem}_trajectories",
            )

    return result


def main(argv=None):
    run(argv)


if __name__ == "__main__":
    main()
