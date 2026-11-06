"""Static plots for parameter sweeps."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize

from packages.sim.sweep import SweepResult

DEFAULT_SWEEP_METRICS = (
    "distance",
    "speed",
    "turn",
    "energy",
    "sat_frac",
    "tracking_rmse",
)


def _slug(text: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text))
    return "_".join(part for part in cleaned.split("_") if part) or "plot"


def _output_dir(directory) -> Path:
    if directory is not None:
        base = Path(directory)
    else:
        root = os.environ.get(
            "SNAKEBOARD_OUTPUT_DIR", Path(__file__).resolve().parents[4] / "outputs"
        )
        base = Path(root) / "sweeps"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _save(fig, output_dir: Path, stem: str) -> Path:
    path = output_dir / f"{stem}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"Saved plot: {path}")
    return path


def _metric_values(result: SweepResult, metric: str) -> np.ndarray:
    values = [case.metrics.get(metric, np.nan) for case in result.cases]
    return np.asarray(values, dtype=float)


def plot_sweep(
    result: SweepResult,
    metrics=DEFAULT_SWEEP_METRICS,
    *,
    output_dir=None,
    save: bool = True,
    show: bool = False,
    prefix: str = "sweep",
):
    """Plot sweep metrics as lines for 1-D sweeps or heatmaps for 2-D sweeps."""
    metrics = [metric for metric in metrics if metric in result.cases[0].metrics]
    if not metrics:
        raise ValueError("no plottable metrics found in sweep result")

    ncols = 2
    nrows = int(np.ceil(len(metrics) / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(7 * ncols, 4.2 * nrows), squeeze=False
    )
    axes = axes.ravel()

    if len(result.axis_names) == 1:
        axis_name = result.axis_names[0]
        x = result.axes[axis_name]
        for ax, metric in zip(axes, metrics):
            ax.plot(x, _metric_values(result, metric), marker="o", linewidth=1.4)
            ax.set_xlabel(axis_name)
            ax.set_ylabel(metric)
            ax.set_title(metric)
            ax.grid(True, alpha=0.3)
    elif len(result.axis_names) == 2:
        x_name, y_name = result.axis_names
        x_values = result.axes[x_name]
        y_values = result.axes[y_name]
        for ax, metric in zip(axes, metrics):
            grid = np.full((len(y_values), len(x_values)), np.nan)
            for case in result.cases:
                ix = x_values.index(case.values[x_name])
                iy = y_values.index(case.values[y_name])
                grid[iy, ix] = case.metrics.get(metric, np.nan)
            image = ax.imshow(grid, aspect="auto", origin="lower")
            ax.set_xticks(range(len(x_values)), labels=[str(v) for v in x_values])
            ax.set_yticks(range(len(y_values)), labels=[str(v) for v in y_values])
            ax.set_xlabel(x_name)
            ax.set_ylabel(y_name)
            ax.set_title(metric)
            fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    else:
        plt.close(fig)
        raise ValueError("plot_sweep supports one or two sweep axes")

    for ax in axes[len(metrics) :]:
        ax.set_visible(False)
    fig.suptitle(
        f"{result.model} | {result.controller.upper()} | "
        + " vs ".join(result.axis_names)
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))

    path = None
    if save:
        path = _save(fig, _output_dir(output_dir), prefix)
    if show:
        plt.show()
    return fig, axes, path


def _color_values(result: SweepResult) -> tuple[np.ndarray, str]:
    axis_name = result.axis_names[0]
    values = [case.values[axis_name] for case in result.cases]
    try:
        numeric = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        numeric = np.arange(len(values), dtype=float)
    return numeric, axis_name


def plot_sweep_trajectories(
    result: SweepResult,
    *,
    output_dir=None,
    save: bool = True,
    show: bool = False,
    prefix: str = "sweep_trajectories",
    max_cases: int = 80,
):
    """Overlay the planar trajectories of all sweep cases."""
    cases = [case for case in result.cases if case.rows.size][:max_cases]
    if not cases:
        raise ValueError("sweep result does not contain rollout rows")

    fig, ax = plt.subplots(figsize=(9, 7))
    color_values, color_name = _color_values(result)
    finite = color_values[np.isfinite(color_values)]
    if finite.size and finite.max() > finite.min():
        color = (color_values - finite.min()) / (finite.max() - finite.min())
    else:
        color = np.linspace(0.0, 1.0, len(color_values))
    cmap = plt.get_cmap("viridis")
    for value, case in zip(color, cases):
        ax.plot(
            case.rows[:, 1],
            case.rows[:, 2],
            color=cmap(value),
            linewidth=1.3,
        )
    ax.set_xlabel("X0 [m]")
    ax.set_ylabel("Y0 [m]")
    ax.set_title(
        f"{result.model} | {result.controller.upper()} | trajectories by {color_name}"
    )
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")
    scalar = plt.cm.ScalarMappable(
        cmap=cmap,
        norm=Normalize(
            vmin=float(finite.min()) if finite.size else 0.0,
            vmax=float(finite.max()) if finite.size else 1.0,
        ),
    )
    fig.colorbar(scalar, ax=ax, label=color_name)
    fig.tight_layout()

    path = None
    if save:
        path = _save(fig, _output_dir(output_dir), prefix)
    if show:
        plt.show()
    return fig, ax, path
