from __future__ import annotations

import numpy as np
from scipy.linalg import expm, solve_continuous_are
from packages.core.constants import O3_IDX, DO3_IDX, DEG
from .base import BaseController


class FeedbackLinearizationController(BaseController):
    name = "fl"

    def control(self, t, y):
        p = self.p
        O3d, dO3d, ddO3d = self.reference(t)
        O3, dO3, dQ0 = y[O3_IDX], y[DO3_IDX], y[18]
        dQ3 = dQ0 + dO3
        ddO3_des = ddO3d + p.Kd * (dO3d - dO3) + p.Kp * (O3d - O3)
        return p.I3 * ddO3_des + p.BQ[3] * dQ3 + p.BO[3] * dO3


class SlidingModeController(BaseController):
    name = "smc"

    def __init__(self, params=None, lam: float = 10.0, K: float = 5.0, phi: float = 0.05):
        super().__init__(params)
        self.lam = lam
        self.K = K
        self.phi = phi

    def control(self, t, y):
        p = self.p
        O3d, dO3d, ddO3d = self.reference(t)
        O3, dO3, dQ0 = y[O3_IDX], y[DO3_IDX], y[18]
        e, de = O3 - O3d, dO3 - dO3d
        s = de + self.lam * e
        ddO3_des = ddO3d - self.lam * de - self.K * np.tanh(s / self.phi)
        return p.I3 * ddO3_des + p.BQ[3] * (dQ0 + dO3) + p.BO[3] * dO3


class LQRController(BaseController):
    name = "lqr"

    def __init__(self, params=None, Q=(100.0, 10.0), R: float = 0.01):
        super().__init__(params)
        p = self.p
        a = p.BO[3] / p.I3 if p.I3 else 0.0
        A = np.array([[0.0, 1.0], [0.0, -a]])
        B = np.array([[0.0], [1.0 / p.I3]])
        self.K = solve_continuous_are(A, B, np.diag(Q), np.array([[R]]))
        self.K = (np.linalg.inv(np.array([[R]])) @ B.T @ self.K).ravel()
        self._A, self._B = A, B

    def control(self, t, y):
        p = self.p
        O3d, dO3d, ddO3d = self.reference(t)
        x = np.array([y[O3_IDX] - O3d, y[DO3_IDX] - dO3d])
        ff = p.I3 * ddO3d + p.BO[3] * (y[DO3_IDX] - dO3d)
        return float(ff - self.K @ x)


class LQGController(LQRController):
    name = "lqg"

    def __init__(
        self,
        params=None,
        Q=(100.0, 10.0),
        R: float = 0.01,
        Qw=(1e-6, 1e-4),
        Rn: float = 1e-6,
        sensor_noise: float = 0.0,
        seed: int | None = 0,
    ):
        super().__init__(params, Q, R)
        self.Qw, self.Rn = np.diag(Qw), Rn
        self.sensor_noise = sensor_noise
        self.rng = np.random.default_rng(seed)
        self._x = np.zeros(2)
        self._P = np.eye(2)
        self._t_prev = None

    def reset(self):
        self._x = np.zeros(2)
        self._P = np.eye(2)
        self._t_prev = None

    def control(self, t, y):
        p = self.p
        O3d, dO3d, ddO3d = self.reference(t)
        dt = 1e-3 if self._t_prev is None else max(t - self._t_prev, 1e-6)
        self._t_prev = t
        M = expm(np.block([[self._A, self._B], [np.zeros((1, 2)), np.zeros((1, 1))]]) * dt)
        Ad, Bd = M[:2, :2], M[:2, 2]
        self._x = Ad @ self._x
        self._P = Ad @ self._P @ Ad.T + self.Qw * dt
        z = y[O3_IDX] + self.sensor_noise * self.rng.standard_normal()
        C = np.array([[1.0, 0.0]])
        S = C @ self._P @ C.T + self.Rn
        Kf = self._P @ C.T / S
        self._x = self._x + (Kf @ (z - C @ self._x)).ravel()
        self._P = (np.eye(2) - Kf @ C) @ self._P
        x = self._x - np.array([O3d, dO3d])
        ff = p.I3 * ddO3d + p.BO[3] * (self._x[1] - dO3d)
        return float(ff - self.K @ x)


class MRACController(BaseController):
    name = "mrac"

    def __init__(self, params=None, gamma: float = 10.0):
        super().__init__(params)
        p = self.p
        self.gamma = gamma
        self._Om = 0.0
        self._dOm = 0.0
        self._k = np.array([p.I3 * p.Kp, p.I3 * p.Kd, p.I3 * p.Kp])
        self._t_prev = None

    def reset(self):
        self._Om = 0.0
        self._dOm = 0.0
        self._t_prev = None
        p = self.p
        self._k = np.array([p.I3 * p.Kp, p.I3 * p.Kd, p.I3 * p.Kp])

    def control(self, t, y):
        p = self.p
        O3d, _, _ = self.reference(t)
        O3, dO3 = y[O3_IDX], y[DO3_IDX]
        if self._t_prev is None:
            dt = 1e-3
        else:
            dt = max(t - self._t_prev, 1e-6)
        self._t_prev = t
        ddOm = -p.Kd * self._dOm - p.Kp * (self._Om - O3d)
        self._Om += dt * self._dOm
        self._dOm += dt * ddOm
        e = O3 - self._Om
        kx0, kx1, kr = self._k
        self._k += self.gamma * e * dt * np.array([O3, dO3, O3d])
        return float(-(kx0 * O3 + kx1 * dO3) + kr * O3d)


class EnergyShapingController(BaseController):
    name = "energy"

    def __init__(self, params=None, kE: float = 100.0):
        super().__init__(params)
        self.kE = kE

    def control(self, t, y):
        p = self.p
        O3d, _, _ = self.reference(t)
        O3, dO3 = y[O3_IDX], y[DO3_IDX]
        w = 2.0 * np.pi * p.f
        A = p.A_deg * DEG
        E = 0.5 * p.I3 * dO3**2 + 0.5 * p.I3 * w**2 * O3**2
        Ed = 0.5 * p.I3 * w**2 * A**2
        tau_E = -self.kE * (E - Ed) * dO3
        return -p.Kd * dO3 + p.Kp * (O3d - O3) + tau_E


class FlatnessController(BaseController):
    name = "flatness"

    def __init__(self, params=None, kappa: float = 0.1):
        super().__init__(params)
        self.kappa = kappa

    def control(self, t, y):
        p = self.p
        O3d, dO3d, ddO3d = self.reference(t)
        O3, dO3, dQ0 = y[O3_IDX], y[DO3_IDX], y[18]
        ff = p.I3 * ddO3d + p.BQ[3] * (dQ0 + dO3) + p.BO[3] * dO3
        fb = self.kappa * (-p.Kd * dO3 + p.Kp * (O3d - O3))
        return float(ff + fb)
