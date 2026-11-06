"""Parameter sweeps over snakeboard models, gaits, and controllers."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, fields
from itertools import product
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from packages.control import make_controller
from packages.core.params import jint_params, ras_params
from packages.models.jint import JRobot
from packages.models.ras import RRobot
from packages.sim.metrics import characterize_rows


@dataclass
class SweepCase:
    values: dict[str, Any]
    overrides: dict[str, Any]
    rows: np.ndarray
    metrics: dict[str, Any]
    error: str | None = None


@dataclass
class SweepResult:
    model: str
    controller: str
    axis_names: tuple[str, ...]
    axes: dict[str, list[Any]]
    cases: list[SweepCase]
    duration: float
    f_sim: float
    fixed: dict[str, Any] = field(default_factory=dict)

    def metrics_frame(self) -> pd.DataFrame:
        records = []
        for case in self.cases:
            record = {name: case.values.get(name) for name in self.axis_names}
            record.update(
                {
                    key: value
                    for key, value in case.overrides.items()
                    if key not in self.axis_names
                }
            )
            record.update(case.metrics)
            record["error"] = case.error or ""
            records.append(record)
        return pd.DataFrame.from_records(records)

    def table(self) -> str:
        return self.metrics_frame().to_string(index=False)

    def save_csv(self, path) -> None:
        from pathlib import Path

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_frame().to_csv(path, index=False)


def _controller_name(controller: Any) -> str:
    if isinstance(controller, str):
        return controller
    return getattr(controller, "name", type(controller).__name__)


def _parameter_fields() -> set[str]:
    return {item.name for item in fields(jint_params())}


def _validate_names(names: Sequence[str]) -> None:
    valid = _parameter_fields()
    unknown = [name for name in names if name not in valid]
    if unknown:
        raise ValueError(
            f"unknown parameter(s) {unknown}; expected one of {sorted(valid)}"
        )


def _make_params(model: str, overrides: Mapping[str, Any]):
    model_name = str(overrides.get("model", model)).upper()
    if model_name == "JINT":
        return jint_params(**overrides)
    if model_name == "RAS":
        return ras_params(**overrides)
    raise ValueError(f"unknown model {model_name!r}; expected 'JINT' or 'RAS'")


def _make_robot(params, controller: Any, controller_kwargs: Mapping[str, Any] | None):
    if isinstance(controller, str):
        controller_instance = make_controller(
            controller, params, **(controller_kwargs or {})
        )
    else:
        controller_instance = copy.deepcopy(controller)
    robot_cls = RRobot if params.model.upper() == "RAS" else JRobot
    return robot_cls(controller=controller_instance, params=params)


def _run_analyses(
    robot_factory: Callable[[], Any],
    metrics: dict[str, Any],
    f_sim: float,
    poincare: bool,
    poincare_duration: float,
    poincare_theta: float,
    poincare_transient: float | None,
    lyapunov: bool,
    lyapunov_duration: float,
    lyapunov_dt: float,
    lyapunov_transient: float | None,
    lyapunov_eps: float,
) -> None:
    if poincare:
        try:
            from packages.dynamics.poincare import analyze_poincare

            transient = (
                0.5 * poincare_duration
                if poincare_transient is None
                else poincare_transient
            )
            analysis = analyze_poincare(
                robot_factory(),
                np.zeros(32),
                poincare_duration,
                1.0 / f_sim,
                theta=poincare_theta,
                transient=transient,
            )
            metrics["poincare_fixed_point"] = float(analysis.fixed_point)
            metrics["poincare_crossings"] = int(len(analysis.crossings))
        except Exception as exc:
            metrics["poincare_fixed_point"] = np.nan
            metrics["poincare_crossings"] = np.nan
            metrics["poincare_error"] = str(exc)

    if lyapunov:
        try:
            from packages.dynamics.lyapunov import lyapunov_exponents

            transient = (
                0.5 * lyapunov_duration
                if lyapunov_transient is None
                else lyapunov_transient
            )
            probe = robot_factory()
            y0_l = np.zeros(probe.y.size)
            result = lyapunov_exponents(
                probe,
                y0_l,
                lyapunov_duration,
                lyapunov_dt,
                transient=transient,
                eps=lyapunov_eps,
            )
            metrics["lyapunov_dimension"] = float(result.dimension)
            metrics["lyapunov_classification"] = result.classification
        except Exception as exc:
            metrics["lyapunov_dimension"] = np.nan
            metrics["lyapunov_classification"] = "unavailable"
            metrics["lyapunov_error"] = str(exc)


def run_parameter_sweep(
    model: str = "JINT",
    axes: Mapping[str, Sequence[Any]] | None = None,
    *,
    controller: Any = "pd",
    controller_kwargs: Mapping[str, Any] | None = None,
    fixed: Mapping[str, Any] | None = None,
    duration: float = 6.0,
    f_sim: float = 500.0,
    steady_fraction: float = 0.5,
    keep_rows: bool = True,
    progress: Callable[[int, int, "SweepCase"], None] | None = None,
    poincare: bool = False,
    poincare_duration: float = 20.0,
    poincare_theta: float = -np.pi / 2.0,
    poincare_transient: float | None = None,
    lyapunov: bool = False,
    lyapunov_duration: float = 20.0,
    lyapunov_dt: float = 0.02,
    lyapunov_transient: float | None = None,
    lyapunov_eps: float = 1e-6,
) -> SweepResult:
    """Run a cartesian sweep and characterize every rollout."""
    if not axes:
        raise ValueError("axes must contain at least one parameter")
    if duration <= 0.0:
        raise ValueError("duration must be positive")
    if f_sim <= 0.0:
        raise ValueError("f_sim must be positive")

    axis_names = tuple(axes)
    _validate_names(axis_names)
    fixed = dict(fixed or {})
    _validate_names(tuple(fixed))

    axis_values = {name: list(values) for name, values in axes.items()}
    combinations = list(product(*(axis_values[name] for name in axis_names)))
    if not combinations:
        raise ValueError("axes must produce at least one parameter combination")

    fallback_params = _make_params(model, fixed)
    cases: list[SweepCase] = []
    for index, combination in enumerate(combinations, start=1):
        values = dict(zip(axis_names, combination))
        overrides = {**fixed, **values}
        params = fallback_params
        try:
            params = _make_params(model, overrides)
            robot = _make_robot(params, controller, controller_kwargs)
            rows = robot.simulate_rows(duration, f_sim)
            metrics = characterize_rows(rows, params, steady_fraction)
            case = SweepCase(
                values=values,
                overrides=overrides,
                rows=rows if keep_rows else np.empty((0, 8)),
                metrics=metrics,
            )
            if poincare or lyapunov:
                _run_analyses(
                    lambda p=params: _make_robot(p, controller, controller_kwargs),
                    metrics,
                    f_sim,
                    poincare,
                    poincare_duration,
                    poincare_theta,
                    poincare_transient,
                    lyapunov,
                    lyapunov_duration,
                    lyapunov_dt,
                    lyapunov_transient,
                    lyapunov_eps,
                )
        except Exception as exc:
            case = SweepCase(
                values=values,
                overrides=overrides,
                rows=np.empty((0, 8)),
                metrics=characterize_rows(np.empty((0, 8)), params),
                error=str(exc),
            )
        cases.append(case)
        if progress is not None:
            progress(index, len(combinations), case)

    return SweepResult(
        model=model.upper(),
        controller=_controller_name(controller),
        axis_names=axis_names,
        axes=axis_values,
        cases=cases,
        duration=duration,
        f_sim=f_sim,
        fixed=fixed,
    )
