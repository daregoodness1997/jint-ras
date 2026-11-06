from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

import numpy as np
from scipy.interpolate import splev, splrep
from scipy.optimize import brentq, fsolve

from packages.core.constants import DO3_IDX, O3_IDX

if TYPE_CHECKING:
    from packages.models.base import SnakeboardRobot

SectionState = Callable[[np.ndarray], np.ndarray]


def z_rotation(theta: float) -> np.ndarray:
    """Return the rotation matrix about the z-axis."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array(
        [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )


def rotor_phase_state(y: np.ndarray) -> np.ndarray:
    """Map a full snakeboard state to the 3-D rotor phase coordinates."""
    return np.array([y[O3_IDX], y[DO3_IDX], 0.0], dtype=float)


def chaotic_phase_state(y: np.ndarray) -> np.ndarray:
    """Map a low-dimensional chaotic state to phase coordinates (x, y, 0)."""
    y = np.asarray(y, dtype=float)
    return np.array([y[0], y[1], 0.0], dtype=float)


def section_template(theta: float = -np.pi / 2.0) -> tuple[np.ndarray, np.ndarray]:
    """Return the section template and normal vectors."""
    e_x = np.array([1.0, 0.0, 0.0])
    template = z_rotation(theta) @ e_x
    normal = z_rotation(np.pi / 2.0) @ template
    return template, normal


def section_value(
    y: np.ndarray,
    theta: float = -np.pi / 2.0,
    state_fn: SectionState = rotor_phase_state,
) -> float:
    """Evaluate the Poincare hyperplane equation for a full state."""
    _, normal = section_template(theta)
    return float(np.dot(state_fn(y), normal))


def flow(
    robot: SnakeboardRobot,
    y0: np.ndarray,
    t0: float,
    duration: float,
    nsub: int = 4,
) -> np.ndarray:
    """Propagate a full snakeboard state for ``duration`` seconds."""
    if duration == 0.0:
        return np.asarray(y0, dtype=float).copy()
    return robot.step(t0, np.asarray(y0, dtype=float), duration, nsub=nsub)


def simulate(
    robot: SnakeboardRobot,
    y0: np.ndarray,
    tf: float,
    dt: float,
    t0: float = 0.0,
    nsub: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the snakeboard and return the time and full-state arrays."""
    y = np.asarray(y0, dtype=float).copy()
    t = float(t0)
    nsteps = max(0, int(np.floor((float(tf) - t) / float(dt) + 1e-12)))
    times = [t]
    states = [y.copy()]
    print(f"Integrating {nsteps} steps ({tf:g} s at dt={dt:g}, nsub={nsub})")
    for i in range(nsteps):
        y = flow(robot, y, t, dt, nsub=nsub)
        t += dt
        times.append(t)
        states.append(y.copy())
        if (i + 1) % 10000 == 0:
            print(f"  step {i + 1}/{nsteps} (t={t:.3f} s)")
    return np.asarray(times, dtype=float), np.asarray(states, dtype=float)


def find_crossings(
    robot: SnakeboardRobot,
    times: np.ndarray,
    states: np.ndarray,
    theta: float = -np.pi / 2.0,
    state_fn: SectionState = rotor_phase_state,
    direction: str = "increasing",
    transient: float = 0.0,
    nsub: int = 4,
) -> np.ndarray:
    """Refine all transversal section crossings in an integrated trajectory."""
    times = np.asarray(times, dtype=float)
    states = np.asarray(states, dtype=float)
    values = np.asarray([section_value(s, theta, state_fn) for s in states])
    crossings = []
    for i in range(len(values) - 1):
        if times[i] < transient:
            continue
        a, b = values[i], values[i + 1]
        if direction == "increasing":
            hit = a < 0.0 <= b
        elif direction == "decreasing":
            hit = a > 0.0 >= b
        elif direction == "both":
            hit = a * b < 0.0
        else:
            raise ValueError("direction must be 'increasing', 'decreasing', or 'both'")
        if not hit:
            continue
        step = times[i + 1] - times[i]

        def residual(tau: float) -> float:
            return section_value(
                flow(robot, states[i], times[i], tau, nsub=nsub),
                theta,
                state_fn,
            )

        try:
            tau = brentq(residual, 0.0, step, xtol=1e-13, rtol=1e-13)
        except ValueError:
            tau = step * (-a) / (b - a)
        crossings.append(flow(robot, states[i], times[i], tau, nsub=nsub))
    return np.asarray(crossings, dtype=float)


def poincare_section(
    robot: SnakeboardRobot,
    y0: np.ndarray,
    tf: float,
    dt: float,
    t0: float = 0.0,
    nsub: int = 4,
    theta: float = -np.pi / 2.0,
    state_fn: SectionState = rotor_phase_state,
    direction: str = "increasing",
    transient: float = 0.0,
) -> np.ndarray:
    """Integrate and return the full states on the Poincare section."""
    times, states = simulate(robot, y0, tf, dt, t0=t0, nsub=nsub)
    return find_crossings(
        robot,
        times,
        states,
        theta=theta,
        state_fn=state_fn,
        direction=direction,
        transient=transient,
        nsub=nsub,
    )


def project_section(
    crossings: np.ndarray,
    theta: float = -np.pi / 2.0,
    state_fn: SectionState = rotor_phase_state,
) -> np.ndarray:
    """Project section states onto the section basis."""
    crossings = np.asarray(crossings, dtype=float)
    if crossings.size == 0:
        return np.empty((0, 3), dtype=float)
    template, normal = section_template(theta)
    e_z = np.array([0.0, 0.0, 1.0])
    projection = np.array([template, e_z, normal])
    section_states = np.asarray([state_fn(s) for s in crossings])
    return section_states @ projection.T


def return_map(
    crossings: np.ndarray,
    theta: float = -np.pi / 2.0,
    state_fn: SectionState = rotor_phase_state,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the radii of successive section crossings."""
    section = project_section(crossings, theta=theta, state_fn=state_fn)
    radii = np.linalg.norm(section[:, :2], axis=1)
    return radii[:-1], radii[1:]


def _locate_fixed_point(
    tck: tuple,
    lo: float,
    hi: float,
    guess: float,
) -> float:
    grid = np.linspace(lo, hi, 1024)
    values = splev(grid, tck) - grid
    roots = []
    for i in range(len(grid) - 1):
        a, b = values[i], values[i + 1]
        if a == 0.0:
            roots.append(float(grid[i]))
        elif a * b < 0.0:
            try:
                root = brentq(
                    lambda r: splev(r, tck) - r,
                    grid[i],
                    grid[i + 1],
                    xtol=1e-12,
                    rtol=1e-12,
                )
            except ValueError:
                continue
            roots.append(float(root))
    if roots:
        return min(roots, key=lambda r: abs(r - guess))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fixed = fsolve(lambda r: splev(r, tck) - r, float(guess))
    return float(fixed[0])


def spline_return_map(
    radii1: np.ndarray,
    radii2: np.ndarray,
    guess: float | None = None,
) -> tuple[tuple | None, float]:
    """Fit a spline to the return map and locate its fixed point."""
    radii1 = np.asarray(radii1, dtype=float)
    radii2 = np.asarray(radii2, dtype=float)
    order = np.argsort(radii1)
    radii1 = radii1[order]
    radii2 = radii2[order]
    unique, index = np.unique(radii1, return_index=True)
    radii2 = radii2[index]
    if unique.size == 0:
        raise ValueError("no section crossings were found")
    if unique.size == 1:
        return None, float(unique[0])
    tck = splrep(unique, radii2, k=min(3, unique.size - 1))
    if guess is None:
        guess = float(np.median(unique))
    fixed = _locate_fixed_point(tck, float(unique.min()), float(unique.max()), float(guess))
    return tck, fixed


@dataclass
class PoincareAnalysis:
    times: np.ndarray
    states: np.ndarray
    crossings: np.ndarray
    section: np.ndarray
    radii1: np.ndarray
    radii2: np.ndarray
    spline: tuple | None
    fixed_point: float


def analyze_poincare(
    robot: SnakeboardRobot,
    y0: np.ndarray,
    tf: float,
    dt: float,
    t0: float = 0.0,
    nsub: int = 4,
    theta: float = -np.pi / 2.0,
    state_fn: SectionState | None = None,
    direction: str = "increasing",
    transient: float = 0.0,
    guess: float | None = None,
) -> PoincareAnalysis:
    """Run the full Poincare-section and return-map analysis."""
    if state_fn is None:
        state_fn = (
            chaotic_phase_state if np.asarray(y0).size != 32 else rotor_phase_state
        )
    times, states = simulate(robot, y0, tf, dt, t0=t0, nsub=nsub)
    crossings = find_crossings(
        robot,
        times,
        states,
        theta=theta,
        state_fn=state_fn,
        direction=direction,
        transient=transient,
        nsub=nsub,
    )
    section = project_section(crossings, theta=theta, state_fn=state_fn)
    radii = np.linalg.norm(section[:, :2], axis=1)
    radii1 = radii[:-1]
    radii2 = radii[1:]
    tck, fixed = spline_return_map(radii1, radii2, guess=guess)
    return PoincareAnalysis(
        times=times,
        states=states,
        crossings=crossings,
        section=section,
        radii1=radii1,
        radii2=radii2,
        spline=tck,
        fixed_point=fixed,
    )


def plot_analysis(
    analysis: PoincareAnalysis,
    theta: float = -np.pi / 2.0,
    state_fn: SectionState | None = None,
    show: bool = True,
):
    """Plot the phase portrait and the return map.

    For 3-D chaotic systems (Lorenz/Rossler) the left panel shows a 3-D
    trajectory; for the 32-D snakeboard it shows the rotor phase portrait.
    """
    import matplotlib.pyplot as plt

    is_chaotic = analysis.states.shape[1] != 32
    if state_fn is None:
        state_fn = chaotic_phase_state if is_chaotic else rotor_phase_state

    if is_chaotic:
        fig = plt.figure(figsize=(12, 5))
        ax3d = fig.add_subplot(1, 2, 1, projection="3d")
        states = np.asarray(analysis.states, dtype=float)
        ax3d.plot(
            states[:, 0],
            states[:, 1],
            states[:, 2],
            color="C0",
            linewidth=0.8,
            label="trajectory",
        )
        if len(analysis.crossings) > 0:
            crossings = np.asarray(analysis.crossings, dtype=float)
            ax3d.scatter(
                crossings[:, 0],
                crossings[:, 1],
                crossings[:, 2],
                color="C3",
                s=20,
                label="section",
            )
        ax3d.set_xlabel("x")
        ax3d.set_ylabel("y")
        ax3d.set_zlabel("z")
        ax3d.set_title("3-D phase portrait")
        ax3d.grid(True, alpha=0.3)
        ax3d.legend(fontsize="x-small")

        ax_rm = fig.add_subplot(1, 2, 2)
    else:
        template, _ = section_template(theta)
        phase = np.asarray([state_fn(s)[:2] for s in analysis.states])
        section_phase = np.asarray([state_fn(s)[:2] for s in analysis.crossings])
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        ax = axes[0]
        ax.plot(phase[:, 0], phase[:, 1], color="C0", linewidth=0.8, label="trajectory")
        ax.plot(
            section_phase[:, 0],
            section_phase[:, 1],
            "o",
            color="C3",
            markersize=4,
            label="section",
        )
        direction = template[:2]
        norm = np.linalg.norm(direction)
        if norm > 0.0:
            direction = direction / norm
            span = max(float(np.max(np.abs(phase))), 1.0) * 1.1
            ax.plot(
                [-span * direction[0], span * direction[0]],
                [-span * direction[1], span * direction[1]],
                "k--",
                linewidth=1.0,
                label="section line",
            )
        ax.set_xlabel(r"$O_3$ [rad]")
        ax.set_ylabel(r"$\dot{O}_3$ [rad/s]")
        ax.set_title("Rotor phase portrait")
        ax.grid(True, alpha=0.3)
        ax.legend()

        ax_rm = axes[1]

    ax_rm.plot(
        analysis.radii1,
        analysis.radii2,
        ".",
        color="C3",
        markersize=6,
        label="return map",
    )
    lo = min(float(np.min(analysis.radii1)), float(np.min(analysis.radii2)))
    hi = max(float(np.max(analysis.radii1)), float(np.max(analysis.radii2)))
    if hi <= lo:
        lo -= 0.5
        hi += 0.5
    span = hi - lo
    rn = np.linspace(lo - 0.05 * span, hi + 0.05 * span, 200)
    if analysis.spline is not None:
        ax_rm.plot(rn, splev(rn, analysis.spline), color="C0", label="spline")
    else:
        ax_rm.axhline(analysis.fixed_point, color="C0", label="spline")
    ax_rm.plot(rn, rn, "k--", linewidth=1.0, label=r"$r_{n+1}=r_n$")
    ax_rm.axvline(
        analysis.fixed_point,
        color="C2",
        linestyle=":",
        label=f"fixed = {analysis.fixed_point:.6f}",
    )
    ax_rm.set_xlabel(r"$r_n$")
    ax_rm.set_ylabel(r"$r_{n+1}$")
    ax_rm.set_title("Return map")
    ax_rm.grid(True, alpha=0.3)
    ax_rm.legend()

    fig.tight_layout()
    if show:
        plt.show()
    return fig, ax_rm


def build_robot(model: str = "JINT", controller=None, **overrides):
    """Build a JINT/RAS snakeboard or a chaotic system (Lorenz/Rossler)."""
    model = model.upper()
    if model == "JINT":
        from packages.core.params import jint_params
        from packages.models.jint import JRobot

        params = jint_params(**overrides)
        robot_cls = JRobot
    elif model == "RAS":
        from packages.core.params import ras_params
        from packages.models.ras import RRobot

        params = ras_params(**overrides)
        robot_cls = RRobot
    elif model == "LORENZ":
        from packages.models.chaotic import ChaoticParams, LorenzRobot

        params = ChaoticParams(model="LORENZ", **overrides)
        return LorenzRobot(controller=controller, params=params)
    elif model == "ROSSLER":
        from packages.models.chaotic import ChaoticParams, RosslerRobot

        params = ChaoticParams(model="ROSSLER", **overrides)
        return RosslerRobot(controller=controller, params=params)
    else:
        raise ValueError(
            f"unknown model {model!r}; expected 'JINT', 'RAS', 'LORENZ', or 'ROSSLER'"
        )

    if isinstance(controller, str):
        from packages.control import make_controller

        controller = make_controller(controller, params)
    return robot_cls(controller=controller, params=params)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Poincare section and return map for the snakeboard rotor"
    )
    parser.add_argument("--model", choices=("JINT", "RAS", "LORENZ", "ROSSLER"), default="JINT")
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--dt", type=float, default=1.0 / 500.0)
    parser.add_argument("--theta", type=float, default=-np.pi / 2.0)
    parser.add_argument("--transient", type=float, default=None)
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
    try:
        if args.model.upper() in ("JINT", "RAS"):
            y0_p = np.zeros(32)
        else:
            y0_p = np.array([1.0, 1.0, 1.0])
        analysis = analyze_poincare(
            robot,
            y0_p,
            args.duration,
            args.dt,
            theta=args.theta,
            transient=transient,
            nsub=args.nsub,
        )
    except ValueError as exc:
        print(f"Poincare analysis failed: {exc}")
        return None
    print(f"Fixed point: {analysis.fixed_point:.6f}")
    if args.plot:
        plot_analysis(analysis, theta=args.theta)
    return analysis


if __name__ == "__main__":
    main()
