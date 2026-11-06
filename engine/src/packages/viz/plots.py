"""Animated 3D plotting functions for snakeboard simulation."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation

ANIM_FPS = 20
ANIM_FRAMES = 60
ANIM_ELEV = 24
OUTPUT_DIR = Path(os.environ.get("SNAKEBOARD_OUTPUT_DIR", Path(__file__).resolve().parents[3] / "outputs"))


def _slug(text):
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text))
    return "_".join(part for part in cleaned.split("_") if part) or "plot"


def save_animation(fig, ani, title, fps=ANIM_FPS):
    """Save an animation into the outputs folder and return the path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = _slug(title)
    attempts = []
    if animation.FFMpegWriter.isAvailable():
        attempts.append((OUTPUT_DIR / f"{stem}.mp4", animation.FFMpegWriter(fps=fps)))
    if animation.PillowWriter.isAvailable():
        attempts.append((OUTPUT_DIR / f"{stem}.gif", animation.PillowWriter(fps=fps)))
    for path, writer in attempts:
        try:
            ani.save(path, writer=writer)
            print(f"Saved plot: {path}")
            return path
        except Exception as exc:  # pragma: no cover - depends on local encoders
            print(f"Could not save {path.name}: {exc}")
    png_path = OUTPUT_DIR / f"{stem}.png"
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    print(f"Saved final frame: {png_path}")
    return png_path


def _rate(t, values):
    """Numerically differentiate a signal with respect to time."""
    values = np.asarray(values, dtype=float)
    if values.size < 2:
        return np.zeros_like(values)
    return np.gradient(values, np.asarray(t, dtype=float))


def _phase_rate(rows):
    """Return dO3, using the full state column when available."""
    if rows.shape[1] > 31:
        return rows[:, 31]
    return _rate(rows[:, 0], rows[:, 5])


def _pad_limits(values, pad=0.08):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return -1.0, 1.0
    lo, hi = float(values.min()), float(values.max())
    span = hi - lo
    if span < 1e-12:
        span = max(abs(lo), 1.0)
        return lo - 0.5 * span, hi + 0.5 * span
    return lo - pad * span, hi + pad * span


def _set_limits(ax, traces, equal_xy=False):
    xs = np.concatenate([np.asarray(t["x"], dtype=float) for t in traces])
    ys = np.concatenate([np.asarray(t["y"], dtype=float) for t in traces])
    zs = np.concatenate([np.asarray(t["z"], dtype=float) for t in traces])

    xlim = _pad_limits(xs)
    ylim = _pad_limits(ys)
    if equal_xy:
        cx = 0.5 * (xlim[0] + xlim[1])
        cy = 0.5 * (ylim[0] + ylim[1])
        radius = 0.5 * max(xlim[1] - xlim[0], ylim[1] - ylim[0])
        xlim = (cx - radius, cx + radius)
        ylim = (cy - radius, cy + radius)

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_zlim(*_pad_limits(zs))


def _add_traces(ax, traces, equal_xy=False):
    lines = []
    for spec in traces:
        (line,) = ax.plot(
            [],
            [],
            [],
            color=spec.get("color"),
            linestyle=spec.get("linestyle", "-"),
            linewidth=spec.get("linewidth", 2.0),
            marker=spec.get("marker"),
            markersize=spec.get("markersize", 6.0),
            label=spec.get("label"),
        )
        lines.append((line, spec))
    _set_limits(ax, traces, equal_xy=equal_xy)
    if any(spec.get("label") for _, spec in lines):
        ax.legend(loc="upper right")
    return lines


def _reveal(lines, progress):
    for line, spec in lines:
        x = np.asarray(spec["x"], dtype=float)
        y = np.asarray(spec["y"], dtype=float)
        z = np.asarray(spec["z"], dtype=float)
        n = len(x)
        k = max(1, min(n, int(round(progress * n))))
        line.set_data(x[:k], y[:k])
        line.set_3d_properties(z[:k])


def _animate(
    fig,
    axes,
    update_traces,
    title=None,
    save=True,
    autorotate=True,
    frames=ANIM_FRAMES,
    fps=ANIM_FPS,
    elev=ANIM_ELEV,
):
    """Animate traces while spinning the camera around the 3D axes."""
    axes = list(axes) if isinstance(axes, (list, tuple)) else [axes]
    for ax in axes:
        ax.view_init(elev=elev, azim=0)

    def _update(frame):
        update_traces((frame + 1) / frames)
        if autorotate:
            azim = (frame * 360.0 / frames) % 360.0
            for ax in axes:
                ax.view_init(elev=elev, azim=azim)

    ani = animation.FuncAnimation(fig, _update, frames=frames, interval=1000.0 / fps, blit=False)
    fig._snakeboard_animation = ani
    if save and title is not None:
        fig._snakeboard_plot_path = save_animation(fig, ani, title, fps=fps)
    return ani


def _new_3d_axes(fig, nrows=1, ncols=1, index=1):
    return fig.add_subplot(nrows, ncols, index, projection="3d")


def plot_time_series(t, values, title: str = "Time Series", ylabel: str = "", show: bool = True, save: bool = True, autorotate: bool = True):
    """Animated 3D time series (t, value, sample index)."""
    t = np.asarray(t, dtype=float)
    values = np.asarray(values, dtype=float)
    fig = plt.figure(figsize=(9, 7))
    ax = _new_3d_axes(fig)
    traces = [
        {
            "x": t,
            "y": values,
            "z": np.arange(len(values)),
            "label": ylabel or "signal",
        }
    ]
    lines = _add_traces(ax, traces)
    ax.set_xlabel("t [s]")
    ax.set_ylabel(ylabel)
    ax.set_zlabel("Sample index")
    ax.set_title(title)
    _animate(fig, ax, lambda progress: _reveal(lines, progress), title=title, save=save, autorotate=autorotate)
    if show:
        plt.show()
    return fig, ax


def plot_trajectory(rows, title: str = "Snakeboard Trajectory", show: bool = True, save: bool = True, autorotate: bool = True):
    """Animated 3D X-Y-t trajectory."""
    rows = np.asarray(rows, dtype=float)
    fig = plt.figure(figsize=(9, 7))
    ax = _new_3d_axes(fig)
    traces = [
        {
            "x": rows[:, 1],
            "y": rows[:, 2],
            "z": rows[:, 0],
            "label": "trajectory",
            "color": "C0",
        }
    ]
    lines = _add_traces(ax, traces, equal_xy=True)
    ax.set_xlabel("X0 [m]")
    ax.set_ylabel("Y0 [m]")
    ax.set_zlabel("t [s]")
    ax.set_title(title)
    _animate(fig, ax, lambda progress: _reveal(lines, progress), title=title, save=save, autorotate=autorotate)
    if show:
        plt.show()
    return fig, ax


def plot_phase(rows, title: str = "Rotor Phase Diagram", show: bool = True, save: bool = True, autorotate: bool = True):
    """Animated 3D O3-dO3-t phase diagram."""
    rows = np.asarray(rows, dtype=float)
    fig = plt.figure(figsize=(9, 7))
    ax = _new_3d_axes(fig)
    traces = [
        {
            "x": rows[:, 5],
            "y": _phase_rate(rows),
            "z": rows[:, 0],
            "label": "phase",
            "color": "C0",
        }
    ]
    lines = _add_traces(ax, traces)
    ax.set_xlabel(r"$O_3$ [rad]")
    ax.set_ylabel(r"$\dot{O}_3$ [rad/s]")
    ax.set_zlabel("t [s]")
    ax.set_title(title)
    _animate(fig, ax, lambda progress: _reveal(lines, progress), title=title, save=save, autorotate=autorotate)
    if show:
        plt.show()
    return fig, ax


def plot_poincare(poincare_points, title: str = "Poincare Section (O3=0)", show: bool = True, save: bool = True, autorotate: bool = True):
    """Animated 3D Poincare section."""
    points = np.asarray(poincare_points, dtype=float)
    fig = plt.figure(figsize=(9, 7))
    ax = _new_3d_axes(fig)
    if len(points) == 0:
        ax.text2D(
            0.5,
            0.5,
            "No zero crossings found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
    traces = [
        {
            "x": points,
            "y": np.zeros_like(points),
            "z": np.arange(len(points)),
            "label": "crossings",
            "linestyle": "none",
            "marker": "o",
        }
    ]
    lines = _add_traces(ax, traces)
    ax.set_xlabel(r"$\dot{O}_3$ at $O_3=0$ [rad/s]")
    ax.set_ylabel("Poincare plane")
    ax.set_zlabel("Crossing index")
    ax.set_title(title)
    _animate(fig, ax, lambda progress: _reveal(lines, progress), title=title, save=save, autorotate=autorotate)
    if show:
        plt.show()
    return fig, ax


def plot_poincare_comparison(sections, title: str = "Poincare Sections", show: bool = True, save: bool = True, autorotate: bool = True):
    """Animated 3D Poincare sections for multiple gaits.

    ``sections`` is a sequence of ``(label, points)`` pairs.
    """
    ncols = max(1, len(sections))
    fig = plt.figure(figsize=(7 * ncols, 6.5))
    axes = [fig.add_subplot(1, ncols, i + 1, projection="3d") for i in range(ncols)]
    all_lines = []
    for ax, (label, pts) in zip(axes, sections):
        points = np.asarray(pts, dtype=float)
        if len(points) == 0:
            ax.text2D(
                0.5,
                0.5,
                "No zero crossings found",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
        traces = [
            {
                "x": points,
                "y": np.zeros_like(points),
                "z": np.arange(len(points)),
                "label": label,
                "linestyle": "none",
                "marker": "o",
            }
        ]
        all_lines.extend(_add_traces(ax, traces))
        ax.set_xlabel(r"$\dot{O}_3$ at $O_3=0$ [rad/s]")
        ax.set_ylabel("Poincare plane")
        ax.set_zlabel("Crossing index")
        ax.set_title(f"Poincare section ({label})")
    fig.suptitle(title)
    _animate(fig, axes, lambda progress: _reveal(all_lines, progress), title=title, save=save, autorotate=autorotate)
    if show:
        plt.show()
    return fig, axes


def plot_gait_comparison(base_rows, opt_rows, title: str = "Baseline vs Optimized Gait", show: bool = True, save: bool = True, autorotate: bool = True):
    """Animated 3D trajectory and rotor-tracking comparison."""
    base_rows = np.asarray(base_rows, dtype=float)
    opt_rows = np.asarray(opt_rows, dtype=float)

    fig = plt.figure(figsize=(14, 6.5))
    ax0 = fig.add_subplot(1, 2, 1, projection="3d")
    ax1 = fig.add_subplot(1, 2, 2, projection="3d")

    trajectory_traces = [
        {
            "x": base_rows[:, 1],
            "y": base_rows[:, 2],
            "z": base_rows[:, 0],
            "label": "baseline",
            "linestyle": "--",
        },
        {
            "x": opt_rows[:, 1],
            "y": opt_rows[:, 2],
            "z": opt_rows[:, 0],
            "label": "optimized",
        },
    ]
    lines = _add_traces(ax0, trajectory_traces, equal_xy=True)
    ax0.set_xlabel("X0 [m]")
    ax0.set_ylabel("Y0 [m]")
    ax0.set_zlabel("t [s]")
    ax0.set_title("Trajectory")

    rotor_traces = [
        {
            "x": opt_rows[:, 0],
            "y": opt_rows[:, 6],
            "z": _rate(opt_rows[:, 0], opt_rows[:, 6]),
            "label": "ref O3d",
            "linestyle": ":",
            "color": "C1",
        },
        {
            "x": opt_rows[:, 0],
            "y": opt_rows[:, 5],
            "z": _phase_rate(opt_rows),
            "label": "rotor O3",
            "color": "C1",
        },
    ]
    lines += _add_traces(ax1, rotor_traces)
    ax1.set_xlabel("t [s]")
    ax1.set_ylabel("O3 [rad]")
    ax1.set_zlabel(r"$\dot{O}_3$ [rad/s]")
    ax1.set_title("Optimized rotor tracking")

    fig.suptitle(title)
    _animate(fig, [ax0, ax1], lambda progress: _reveal(lines, progress), title=title, save=save, autorotate=autorotate)
    if show:
        plt.show()
    return fig, (ax0, ax1)


def plot_rotor_tracking(rows, title: str = "Rotor Tracking", show: bool = True, save: bool = True, autorotate: bool = True):
    """Animated 3D rotor angle, reference, and rate."""
    rows = np.asarray(rows, dtype=float)
    fig = plt.figure(figsize=(10, 7))
    ax = _new_3d_axes(fig)
    traces = [
        {
            "x": rows[:, 0],
            "y": rows[:, 6],
            "z": _rate(rows[:, 0], rows[:, 6]),
            "label": "O3d (reference)",
            "linestyle": "--",
        },
        {
            "x": rows[:, 0],
            "y": rows[:, 5],
            "z": _phase_rate(rows),
            "label": "O3 (actual)",
        },
    ]
    lines = _add_traces(ax, traces)
    ax.set_xlabel("t [s]")
    ax.set_ylabel("O3 [rad]")
    ax.set_zlabel(r"$\dot{O}_3$ [rad/s]")
    ax.set_title(title)
    _animate(fig, ax, lambda progress: _reveal(lines, progress), title=title, save=save, autorotate=autorotate)
    if show:
        plt.show()
    return fig, ax
