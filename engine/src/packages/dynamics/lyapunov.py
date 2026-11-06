from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy.linalg import expm

from packages.dynamics.poincare import build_robot, flow, simulate

if TYPE_CHECKING:
    from packages.models.base import SnakeboardRobot

LOG2_E = np.log2(np.e)

BODY_GROUPS: dict[str, tuple[int, ...]] = {
    "Board": (0,),
    "Wheels": (1, 2),
    "Rotor": (3,),
}


def _body_indices(bodies: tuple[int, ...]) -> np.ndarray:
    """Return the position and velocity indices belonging to the given bodies."""
    positions = [4 * body + offset for body in bodies for offset in range(4)]
    velocities = [16 + 4 * body + offset for body in bodies for offset in range(4)]
    return np.asarray(positions + velocities, dtype=int)


def _mode_owners(
    tangent_vectors: np.ndarray,
    groups: dict[str, np.ndarray],
) -> np.ndarray:
    """Assign each tangent mode to the body carrying most of its energy."""
    energies = np.asarray(
        [
            np.sum(tangent_vectors[indices, :] ** 2, axis=0)
            for indices in groups.values()
        ]
    )
    return np.argmax(energies, axis=0)


def numerical_jacobian(
    robot: SnakeboardRobot,
    t: float,
    y: np.ndarray,
    eps: float = 1e-6,
) -> np.ndarray:
    """Finite-difference Jacobian of the snakeboard vector field."""
    y = np.asarray(y, dtype=float)
    base_controller = copy.deepcopy(robot.controller)

    def evaluate(y_eval):
        worker = copy.copy(robot)
        worker.controller = copy.deepcopy(base_controller)
        return worker.deriv(t, y_eval)

    f0 = evaluate(y)
    jacobian = np.empty((y.size, y.size), dtype=float)
    for j in range(y.size):
        yp = y.copy()
        step = eps * max(1.0, abs(y[j]))
        yp[j] += step
        jacobian[:, j] = (evaluate(yp) - f0) / step
    return jacobian


def calculate_lyapunov_dimension(lyapunov_exponents: np.ndarray) -> float:
    """Return the Kaplan-Yorke dimension from a Lyapunov spectrum."""
    sorted_exponents = np.sort(np.asarray(lyapunov_exponents, dtype=float))[::-1]
    k = 0
    sum_exponents = 0.0
    for i, exponent in enumerate(sorted_exponents):
        sum_exponents += exponent
        if sum_exponents < 0.0:
            k = i
            break
        k = i + 1
    if k == 0:
        return 0.0
    if k == len(sorted_exponents):
        return float(k)
    partial_sum = float(np.sum(sorted_exponents[:k]))
    return float(k + partial_sum / abs(sorted_exponents[k]))


def classify_fractal_behavior(
    lyapunov_exponents: np.ndarray,
    dimension: float,
) -> str:
    """Classify the attractor from the rounded Lyapunov spectrum."""
    rounded_exponents = np.round(np.asarray(lyapunov_exponents, dtype=float), decimals=1)
    positive_count = int(np.sum(rounded_exponents > 0.01))
    zero_count = int(np.sum((rounded_exponents >= -0.01) & (rounded_exponents <= 0.01)))
    negative_count = int(np.sum(rounded_exponents < -0.01))
    exponent_sum = float(np.sum(rounded_exponents))
    integer_dimension = float(dimension).is_integer()

    if positive_count > 0 and exponent_sum < 0.0 and not integer_dimension:
        return "Chaotic (Fractal Attractor)"
    if zero_count == 1 and positive_count == 0 and integer_dimension:
        return "Periodic (Limit Cycle)"
    if negative_count == len(rounded_exponents) and integer_dimension:
        return "Stable (Fixed Point)"
    return "Unclassified (Transitional or Complex)"


@dataclass
class LyapunovResult:
    exponents: np.ndarray
    body_exponents: np.ndarray
    exponents_over_time: np.ndarray
    full_exponents_over_time: np.ndarray
    times: np.ndarray
    dimension: float
    classification: str
    bodies: tuple[str, ...]
    full_exponents: np.ndarray


def lyapunov_exponents(
    robot: SnakeboardRobot,
    y0: np.ndarray,
    duration: float,
    dt: float,
    transient: float = 0.0,
    nsub: int = 8,
    eps: float = 1e-6,
    plotting: bool = False,
) -> LyapunovResult:
    """Compute the Lyapunov spectrum with continuous QR reorthonormalization.

    The tangent dynamics use a frozen-Jacobian matrix exponential per step,
    which keeps the stiff RAS modes stable during the variational update.  The
    full 32-state spectrum is propagated and returned in `exponents`, while each
    mode is also attributed to the physical body carrying most of its
    tangent-vector energy (available as `body_exponents`).  The Kaplan-Yorke
    dimension and classification use the full spectrum.
    """
    if duration <= 0.0:
        raise ValueError("duration must be positive")
    if dt <= 0.0:
        raise ValueError("dt must be positive")

    if transient > 0.0:
        transient_times, transient_states = simulate(
            robot, y0, transient, dt, nsub=nsub
        )
        y = transient_states[-1].copy()
        t = float(transient_times[-1])
    else:
        y = np.asarray(y0, dtype=float).copy()
        t = 0.0

    n = y.size
    if n != 32:
        raise ValueError("Lyapunov analysis expects the 32-state snakeboard")

    bodies = tuple(BODY_GROUPS)
    groups = {name: _body_indices(members) for name, members in BODY_GROUPS.items()}

    nsteps = max(1, int(np.floor(duration / dt + 1e-12)))
    tangent_vectors = np.eye(n)
    lyapunov_sums = np.zeros(n)
    lyapunov_over_time = np.zeros((nsteps, len(bodies)))
    full_over_time = np.zeros((nsteps, n))
    times = np.zeros(nsteps)

    for i in range(nsteps):
        jacobian = numerical_jacobian(robot, t, y, eps=eps)
        tangent_vectors = expm(jacobian * dt) @ tangent_vectors
        q, r = np.linalg.qr(tangent_vectors)
        tangent_vectors = q
        diagonal = np.abs(np.diag(r))
        diagonal = np.maximum(diagonal, np.finfo(float).tiny)
        lyapunov_sums += np.log(diagonal)
        elapsed = (i + 1) * dt
        owners = _mode_owners(q, groups)
        for g in range(len(bodies)):
            mask = owners == g
            if np.any(mask):
                lyapunov_over_time[i, g] = (
                    np.max(lyapunov_sums[mask]) / elapsed * LOG2_E
                )
        full_over_time[i, :] = lyapunov_sums / elapsed * LOG2_E
        times[i] = t + dt
        y = flow(robot, y, t, dt, nsub=nsub)
        t += dt

    full_exponents = lyapunov_sums / (nsteps * dt) * LOG2_E
    owners = _mode_owners(tangent_vectors, groups)
    body_exponents = np.zeros(len(bodies))
    for g in range(len(bodies)):
        mask = owners == g
        if np.any(mask):
            body_exponents[g] = np.max(full_exponents[mask])

    dimension = calculate_lyapunov_dimension(full_exponents)
    classification = classify_fractal_behavior(full_exponents, dimension)
    result = LyapunovResult(
        exponents=full_exponents,
        body_exponents=body_exponents,
        exponents_over_time=lyapunov_over_time,
        full_exponents_over_time=full_over_time,
        times=times,
        dimension=dimension,
        classification=classification,
        bodies=bodies,
        full_exponents=full_exponents,
    )
    if plotting:
        plot_lyapunov(result)
    return result


def plot_lyapunov(result: LyapunovResult, show: bool = True):
    """Plot per-body and full Lyapunov exponent spectra over time."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        2, 1, figsize=(10, 9), sharex=True,
        gridspec_kw={"height_ratios": [1, 2]},
    )

    # Per-body (simplified) exponents over time
    ax_body = axes[0]
    for g, body in enumerate(result.bodies):
        ax_body.plot(
            result.times,
            result.exponents_over_time[:, g],
            label=f"{body} ({result.body_exponents[g]:.3f})",
        )
    ax_body.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
    ax_body.set_ylabel("Exponent [bits/time]")
    ax_body.set_title("Lyapunov Exponents by Body (Simplified)")
    ax_body.legend(fontsize="small")
    ax_body.grid(True, alpha=0.3)

    # Full spectrum exponents over time (modes 1-32)
    ax_full = axes[1]
    n_modes = result.full_exponents_over_time.shape[1]
    for mode in range(n_modes):
        ax_full.plot(
            result.times,
            result.full_exponents_over_time[:, mode],
            label=f"{mode + 1}",
            color=plt.cm.tab20(mode % 20),
            alpha=0.7,
            linewidth=1.0,
        )
    ax_full.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
    ax_full.set_xlabel("Time [s]")
    ax_full.set_ylabel("Exponent [bits/time]")
    ax_full.set_title(f"Full Lyapunov Spectrum (modes 1-{n_modes})")
    ax_full.legend(
        title="Mode",
        ncol=8,
        fontsize="x-small",
        title_fontsize="small",
        loc="upper right",
    )
    ax_full.grid(True, alpha=0.3)

    fig.suptitle(
        f"Lyapunov spectrum | D={result.dimension:.3f} | {result.classification}"
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    if show:
        plt.show()
    return fig, axes


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Lyapunov exponents and fractal classification for the snakeboard"
    )
    parser.add_argument("--model", choices=("JINT", "RAS"), default="JINT")
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--dt", type=float, default=0.02)
    parser.add_argument("--transient", type=float, default=None)
    parser.add_argument("--eps", type=float, default=1e-6)
    parser.add_argument("--nsub", type=int, default=4)
    parser.add_argument("--A-deg", type=float, default=None)
    parser.add_argument("--f", type=float, default=None)
    parser.add_argument("--rho-deg-s", type=float, default=None)
    parser.add_argument("--no-plot", dest="plot", action="store_false")
    args = parser.parse_args(argv)

    overrides = {}
    if args.A_deg is not None:
        overrides["A_deg"] = args.A_deg
    if args.f is not None:
        overrides["f"] = args.f
    if args.rho_deg_s is not None:
        overrides["rho_deg_s"] = args.rho_deg_s
    transient = 0.5 * args.duration if args.transient is None else args.transient

    robot = build_robot(args.model, **overrides)
    result = lyapunov_exponents(
        robot,
        np.zeros(32),
        args.duration,
        args.dt,
        transient=transient,
        nsub=args.nsub,
        eps=args.eps,
    )
    print("Lyapunov exponents [bits/time]:")
    print("  Per-body (simplified):")
    for body, exponent in zip(result.bodies, result.body_exponents):
        print(f"    {body:<8s} {exponent: .4f}")
    print("  Full spectrum:")
    for idx, exponent in enumerate(result.exponents):
        print(f"    mode {idx:<3d} {exponent: .4f}")
    print(f"Lyapunov dimension: {result.dimension:.4f}")
    print(f"Classification: {result.classification}")
    if args.plot:
        plot_lyapunov(result)
    return result


if __name__ == "__main__":
    main()
