from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from packages.control import BaseController
from packages.core.params import Params


@dataclass
class ChaoticParams(Params):
    """Parameters for low-dimensional chaotic systems."""

    model: str = "CHAOTIC"
    sigma: float = 10.0
    rho: float = 28.0
    beta: float = 8.0 / 3.0
    a: float = 0.2
    b: float = 0.2
    c: float = 5.7


class ChaoticRobot:
    """Base for 3-D chaotic systems (Rossler, Lorenz) exposing the robot interface."""

    def __init__(self, controller: BaseController | None = None, params: Params | None = None):
        self.params = params if params is not None else ChaoticParams()
        self.controller = controller
        self.y = np.zeros(3)
        self.t = 0.0

    @property
    def p(self) -> Params:
        return self.params

    def step(self, t, y, dt, nsub=4):
        """RK4 integrator without snakeboard constraint projection."""
        dt_sub = dt / nsub
        y_new = np.asarray(y, dtype=float).copy()
        for _ in range(nsub):
            k1 = self.deriv(t, y_new)
            k2 = self.deriv(t + dt_sub / 2.0, y_new + dt_sub * k1 / 2.0)
            k3 = self.deriv(t + dt_sub / 2.0, y_new + dt_sub * k2 / 2.0)
            k4 = self.deriv(t + dt_sub, y_new + dt_sub * k3)
            y_new = y_new + dt_sub * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
            t = t + dt_sub
        return y_new

    def deriv(self, t, y):
        raise NotImplementedError

    def control(self, t, y):
        if self.controller is not None:
            return self.controller(t, y)
        return 0.0

    def simulate_rows(self, duration: float, f_sim: float, dt: float | None = None, nsub: int = 4):
        dt = 1.0 / f_sim if dt is None else dt
        t = self.t
        y = self.y.copy()
        rows = []
        while t < duration - 1e-12:
            y = self.step(t, y, dt, nsub)
            t += dt
            rows.append([t, y[0], y[1], y[2], 0.0, 0.0, 0.0, 0.0])
        self.y, self.t = y, t
        return np.asarray(rows, dtype=float)

    def __copy__(self):
        cls = self.__class__
        new = cls.__new__(cls)
        new.params = copy.deepcopy(self.params)
        new.controller = copy.deepcopy(self.controller)
        new.y = self.y.copy()
        new.t = self.t
        return new


class LorenzRobot(ChaoticRobot):
    """Lorenz attractor: dx=sigma(y-x), dy=x(rho-z)-y, dz=xy-beta*z."""

    def __init__(self, controller=None, params=None):
        super().__init__(controller, params if params is not None else ChaoticParams(model="LORENZ"))

    def deriv(self, t, y):
        p = self.params
        x, yv, z = y
        dx = p.sigma * (yv - x)
        dy = x * (p.rho - z) - yv
        dz = x * yv - p.beta * z
        return np.array([dx, dy, dz], dtype=float)


class RosslerRobot(ChaoticRobot):
    """Rossler attractor: dx=-y-z, dy=x+a*y, dz=b+z*(x-c)."""

    def __init__(self, controller=None, params=None):
        super().__init__(controller, params if params is not None else ChaoticParams(model="ROSSLER"))

    def deriv(self, t, y):
        p = self.params
        x, yv, z = y
        dx = -yv - z
        dy = x + p.a * yv
        dz = p.b + z * (x - p.c)
        return np.array([dx, dy, dz], dtype=float)


# Backward-compatible aliases
Lorenz = LorenzRobot
Rossler = RosslerRobot
