from __future__ import annotations

import numpy as np
from packages.core.constants import O3_IDX, DO3_IDX
from .base import BaseController


class PDController(BaseController):
    name = "pd"

    def control(self, t, y):
        O3d, _, _ = self.reference(t)
        return -self.p.Kd * y[DO3_IDX] + self.p.Kp * (O3d - y[O3_IDX])


class PIDController(PDController):
    name = "pid"

    def __init__(self, params=None, Ki: float = 20.0, Imax: float = 10.0):
        super().__init__(params)
        self.Ki = Ki
        self.Imax = Imax
        self._I = 0.0

    def reset(self):
        self._I = 0.0

    def control(self, t, y):
        O3d, _, _ = self.reference(t)
        e = O3d - y[O3_IDX]
        self._I = np.clip(self._I + self.Ki * e, -self.Imax, self.Imax)
        return -self.p.Kd * y[DO3_IDX] + self.p.Kp * e + self._I
