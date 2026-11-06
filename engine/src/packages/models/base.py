from __future__ import annotations

import numpy as np

from packages.control import BaseController, PDController
from packages.core.params import Params, jint_params
from packages.dynamics.constraints import project_velocity, compute_dJc
from packages.dynamics.jacobian import snakeboard_jacobian_fns


class SnakeboardRobot:
    """Common machinery for JINT and RAS snakeboards."""

    def __init__(
        self,
        controller: BaseController | None = None,
        params: Params | None = None,
        params_factory=jint_params,
    ):
        self.params = params if params is not None else params_factory()
        self.controller = controller if controller is not None else PDController(self.params)
        self.y = np.zeros(32)
        self.t = 0.0
        self.tau = 0.0
        self.O3d = 0.0
        self.omega = 0.0

    @property
    def p(self) -> Params:
        return self.params

    def compute_jacobian(self, y):
        P = y[0:16].reshape(4, 4)
        Q, O = P[:, 2], P[:, 3]
        Jc_fn, Jv_fn = snakeboard_jacobian_fns(
            float(self.params.L1), float(self.params.L2)
        )
        return Jc_fn(Q[1], O[1], Q[2], O[2]), Jv_fn(Q[1], O[1], Q[2], O[2])

    def compute_dJc(self, y):
        return compute_dJc(y, float(self.params.L1), float(self.params.L2))

    def project_velocity(self, y):
        return project_velocity(y, float(self.params.L1), float(self.params.L2))

    def control(self, t, y):
        self.tau = self.controller(t, y)
        self.O3d = getattr(self.controller, "O3d", self.O3d)
        return self.tau

    def stopper(self, y):
        raise NotImplementedError

    def deriv(self, t, y):
        raise NotImplementedError

    def step(self, t, y, dt, nsub=4):
        dt_sub = dt / nsub
        y_new = y.copy()
        for _ in range(nsub):
            k1 = self.deriv(t, y_new)
            k2 = self.deriv(t + dt_sub / 2, y_new + dt_sub * k1 / 2)
            k3 = self.deriv(t + dt_sub / 2, y_new + dt_sub * k2 / 2)
            k4 = self.deriv(t + dt_sub, y_new + dt_sub * k3)
            y_new = y_new + dt_sub * (k1 + 2 * k2 + 2 * k3 + k4) / 6
            t = t + dt_sub
            y_new = self.project_velocity(y_new)
        return y_new

    def simulate(self, t0, y0, tf, dt, nsub=4):
        t = t0
        y = y0.copy()
        print("Starting simulation...")
        print("t [s] | O3 [rad] | dO3 [rad/s]")
        while t < tf:
            y = self.step(t, y, dt, nsub)
            print(f"{t:6.2f} | {y[15]:8.4f} | {y[31]:12.6f}")
            t += dt
        return y

    def simulate_rows(self, duration: float, f_sim: float, dt: float | None = None, nsub: int = 4):
        dt = 1.0 / f_sim if dt is None else dt
        t = self.t
        y = self.y.copy()
        rows = []
        while t < duration - 1e-12:
            y = self.step(t, y, dt, nsub)
            t += dt
            rows.append([t, y[0], y[1], y[2], y[3], y[15], self.O3d, self.tau])
        self.y, self.t = y, t
        return np.asarray(rows, dtype=float)

    def poincare_points(self, y0, tf, dt, nsub=4):
        y = y0.copy()
        t = 0.0
        poincare_points = []
        O3_prev = y[15]
        steps = int(tf / dt)
        for _ in range(steps):
            y = self.step(t, y, dt, nsub)
            t += dt
            O3 = y[15]
            if O3_prev * O3 < 0.0:
                poincare_points.append(y[31])
            elif abs(O3) < 1e-5 and abs(O3_prev) > 1e-6:
                poincare_points.append(y[31])
            O3_prev = O3
        return np.asarray(poincare_points, dtype=float)

    def plot_poincare(self, y0, tf, dt, nsub=4):
        from packages.viz.plots import plot_poincare

        poincare_points = self.poincare_points(y0, tf, dt, nsub)
        plot_poincare(poincare_points, title=f"Poincare section ({self.params.model})")

    def plot_trajectory(self, y0, tf, dt, nsub=4):
        from packages.viz.plots import plot_time_series

        y = y0.copy()
        t = 0.0
        times = []
        trajectory = []
        while t < tf:
            y = self.step(t, y, dt, nsub)
            t += dt
            times.append(t)
            trajectory.append(y[15])
        plot_time_series(
            np.asarray(times),
            np.asarray(trajectory),
            title="Rotor angle trajectory",
            ylabel=r"$O_3$",
        )

    def plot_phase_diagram(self, y0, tf, dt, nsub=4):
        from packages.viz.plots import plot_phase

        y = y0.copy()
        t = 0.0
        phase_points = []
        while t < tf:
            y = self.step(t, y, dt, nsub)
            t += dt
            phase_points.append((t, y[15], y[31]))
        phase_points = np.array(phase_points)
        rows = np.zeros((len(phase_points), 32))
        rows[:, 0] = phase_points[:, 0]
        rows[:, 5] = phase_points[:, 1]
        rows[:, 31] = phase_points[:, 2]
        plot_phase(rows, title=f"Phase diagram ({self.params.model})")
