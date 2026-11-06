from __future__ import annotations

import numpy as np
from packages.core.params import Params
from packages.core.constants import DEG, O3_IDX, DO3_IDX


def _rotor_reference(p: Params, t: float):
    """O3d, dO3d, ddO3d of the biased sinusoid."""
    w = 2.0 * np.pi * p.f
    drift = p.rho_deg_s
    if p.model == "RAS":
        drift = float(np.sign(p.A_deg)) * p.rho_deg_s
    O3d = (drift * t + p.A_deg * np.sin(w * t)) * DEG
    dO3d = (drift + p.A_deg * w * np.cos(w * t)) * DEG
    ddO3d = (-p.A_deg * w * w * np.sin(w * t)) * DEG
    return O3d, dO3d, ddO3d


class BaseController:
    name = "base"

    def __init__(self, params: Params | None = None):
        from packages.core.params import Params

        self.p = params if params is not None else Params()
        self.tau = 0.0
        self.O3d = 0.0

    def reset(self):
        pass

    def reference(self, t: float):
        ref = _rotor_reference(self.p, t)
        self.O3d = ref[0]
        return ref

    def __call__(self, t: float, y: np.ndarray) -> float:
        self.tau = float(self.control(t, y))
        return self.tau

    def control(self, t: float, y: np.ndarray) -> float:
        raise NotImplementedError
