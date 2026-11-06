from __future__ import annotations

import numpy as np

from packages.control import BaseController, PDController
from packages.core.params import Params, jint_params
from .base import SnakeboardRobot


class JRobot(SnakeboardRobot):
    def __init__(self, controller: BaseController | None = None, params: Params | None = None):
        super().__init__(controller, params if params is not None else jint_params(), jint_params)

    def stopper(self, y):
        p = self.params
        O0, dO0 = y[3], y[19]
        if O0 < -p.O0_lim:
            T = -p.Ks * (O0 + p.O0_lim)
            if dO0 < 0.0:
                T -= p.Bs * dO0
            return T
        if O0 > p.O0_lim:
            T = -p.Ks * (O0 - p.O0_lim)
            if dO0 > 0.0:
                T -= p.Bs * dO0
            return T
        return 0.0

    def limiter(self, y, tau, T_stop):
        p = self.params
        gamma = np.array([p.g0, p.g1, p.g2, p.g3])
        I = np.array([p.I0, p.I1, p.I2, p.I3])
        BQ = np.array(p.BQ)
        BO = np.array(p.BO)
        dQ = y[16:32].reshape(4, 4)[:, 2]
        dO = y[16:32].reshape(4, 4)[:, 3]
        sum_abs_gamma_I = np.sum(np.abs(gamma) * I)
        term1 = (np.sum(np.abs(gamma[0:3]) * I[0:3])) * (tau - BQ[3] * dQ[3] - BO[3] * dO[3])
        term2 = (
            np.abs(gamma[3])
            * I[3]
            * (T_stop - np.sum(BQ[1:3] * dQ[1:3]) - np.sum(BO[0:3] * dO[0:3]))
        )
        T_lim = (term1 - term2) / sum_abs_gamma_I if sum_abs_gamma_I != 0 else 0.0
        Tlim_max = getattr(p, "Tlim_max", 0.10)
        if T_lim > Tlim_max:
            T_lim = Tlim_max
        if T_lim < -Tlim_max:
            T_lim = -Tlim_max
        return T_lim

    def deriv(self, t, y):
        p = self.params
        dydt = np.zeros_like(y)
        dydt[0:16] = y[16:32]

        P = y[0:16].reshape(4, 4)
        Qv = y[16:32].reshape(4, 4)
        Q = P[:, 2]
        dQ = Qv[:, 2]
        dO = Qv[:, 3]

        tau = self.control(t, y)
        self.tau = tau
        T_stop = self.stopper(y)
        T_lim = self.limiter(y, tau, T_stop)

        gamma = np.array([p.g0, p.g1, p.g2, p.g3])
        I = np.array([p.I0, p.I1, p.I2, p.I3])
        BQ = np.array(p.BQ)
        BO = np.array(p.BO)

        M = np.diag([p.Mtot, p.Mtot, p.I0])
        Jc, Jv = self.compute_jacobian(y)
        Bv = np.diag(p.Bv)
        Rdamp = -Jv.T @ (Bv @ (Jv @ y[16:19]))
        g = np.array([0.0, 0.0, -BQ[0] * dQ[0] - tau])
        KKT = np.block([[M, -Jc.T], [-Jc, np.zeros((2, 2))]])
        rhs = np.concatenate([Rdamp + g, self.compute_dJc(y)])
        sol = np.linalg.solve(KKT, rhs)
        v0dd = sol[0:3]
        dydt[16:19] = v0dd

        sum_abs_gI_02 = np.sum(np.abs(gamma[0:3]) * I[0:3])
        if sum_abs_gI_02 == 0:
            ddO0 = 0.0
        else:
            ddO0 = (T_lim + T_stop - np.sum(BQ[1:3] * dQ[1:3]) - np.sum(BO[0:3] * dO[0:3])) / sum_abs_gI_02
        if np.abs(gamma[3] * I[3]) == 0:
            ddO3 = 0.0
        else:
            ddO3 = (tau - T_lim - BQ[3] * dQ[3] - BO[3] * dO[3]) / np.abs(gamma[3] * I[3])
        ddO1 = gamma[1] * ddO0
        ddO2 = gamma[2] * ddO0
        dydt[19 + 0 * 4] = ddO0
        dydt[19 + 1 * 4] = ddO1
        dydt[19 + 2 * 4] = ddO2
        dydt[19 + 3 * 4] = ddO3
        ddQ0 = v0dd[2]
        dydt[16 + 0 * 4 + 2] = ddQ0
        dydt[16 + 1 * 4 + 2] = ddQ0 + ddO1
        dydt[16 + 2 * 4 + 2] = ddQ0 + ddO2
        dydt[16 + 3 * 4 + 2] = ddQ0 + ddO3
        dydt[16 + 0 * 4 + 0] = v0dd[0]
        dydt[16 + 0 * 4 + 1] = v0dd[1]
        dydt[16 + 3 * 4 + 0] = v0dd[0]
        dydt[16 + 3 * 4 + 1] = v0dd[1]
        L1, L2 = p.L1, p.L2
        dydt[16 + 1 * 4 + 0] = v0dd[0] - L1 * np.sin(Q[0]) * v0dd[2] - L1 * np.cos(Q[0]) * (dQ[0]) ** 2
        dydt[16 + 1 * 4 + 1] = v0dd[1] + L1 * np.cos(Q[0]) * v0dd[2] - L1 * np.sin(Q[0]) * (dQ[0]) ** 2
        dydt[16 + 2 * 4 + 0] = v0dd[0] + L2 * np.sin(Q[0]) * v0dd[2] + L2 * np.cos(Q[0]) * (dQ[0]) ** 2
        dydt[16 + 2 * 4 + 1] = v0dd[1] - L2 * np.cos(Q[0]) * v0dd[2] + L2 * np.sin(Q[0]) * (dQ[0]) ** 2

        return dydt


# Backward compatibility
JBoard = JRobot
