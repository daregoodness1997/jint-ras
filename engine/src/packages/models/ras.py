from __future__ import annotations

import numpy as np

from packages.control import BaseController, PDController
from packages.core.params import Params, ras_params
from .base import SnakeboardRobot


class RRobot(SnakeboardRobot):
    def __init__(self, controller: BaseController | None = None, params: Params | None = None):
        super().__init__(controller, params if params is not None else ras_params(), ras_params)

    def stopper(self, y):
        p = self.params
        O0, dO0 = y[3], y[19]
        if O0 < -p.O0_lim:
            return -p.Bs * dO0 - p.Ks * (O0 + p.O0_lim)
        if O0 > p.O0_lim:
            return -p.Bs * dO0 - p.Ks * (O0 - p.O0_lim)
        return 0.0

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

        gamma = np.array([p.g0, p.g1, p.g2, p.g3])
        I = np.array([p.I0, p.I1, p.I2, p.I3])
        BQ = np.array(p.BQ)
        BO = np.array(p.BO)

        dO1 = gamma[1] * dO[0]
        dO2 = gamma[2] * dO[0]
        dQ3 = dQ[0] + dO[3]
        BQ_wheels = BQ[1] * dQ[1] + BQ[2] * dQ[2]
        BO_012 = BO[0] * dO[0] + BO[1] * dO1 + BO[2] * dO2
        rotor = BQ[3] * dQ3 + BO[3] * dO[3]

        Ieff = p.Isup + abs(gamma[1]) * I[1] + abs(gamma[2]) * I[2]
        ddO0 = (-BQ_wheels - BO_012 + T_stop - tau) / Ieff
        ddO3 = (-rotor + tau) / (I[3] * gamma[3])

        tau_gen = T_stop - BO[0] * dO[0]
        M = np.diag([p.Mtot, p.Mtot, p.I0])
        Jc, Jv = self.compute_jacobian(y)
        Bv = np.diag(p.Bv)
        Rdamp = -Jv.T @ (Bv @ (Jv @ y[16:19]))
        g = np.array([0.0, 0.0, -BQ[0] * dQ[0] - tau_gen])
        KKT = np.block([[M, -Jc.T], [-Jc, np.zeros((2, 2))]])
        # The reference implementation replaces the yaw row of the wheel-damping
        # term with the support/rotor torque balance.  Keep that convention here
        # so the engine and notebooks/snakeboard_model.py agree quantitatively.
        rhs = Rdamp + g
        rhs[2] = g[2]
        rhs = np.concatenate([rhs, self.compute_dJc(y)])
        sol = np.linalg.solve(KKT, rhs)
        v0dd = sol[0:3]
        dydt[16:19] = v0dd

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
        dydt[16 + 3 * 4 + 2] = ddQ0 + ddO0 + ddO3
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


def main():
    robot = RRobot()
    print("RAS params: Kp =", robot.params.Kp, " Kd =", robot.params.Kd,
          " A =", robot.params.A_deg, "deg  f =", robot.params.f, "Hz")

    y = np.zeros(32)
    y[16:19] = [0.3, -0.2, 0.7]
    robot.project_velocity(y)
    Jc, _ = robot.compute_jacobian(y)
    print("Jc @ v0 after projection:", Jc @ y[16:19], "(should be ~0)")

    tau = robot.control(0.0, y)
    print(f"O3d: {robot.O3d:.4f} rad,  tau: {tau:.4f} Nm")

    y[3], y[19] = robot.params.O0_lim * 1.5, 0.2
    print(f"stopper torque at O0 = 1.5*O0_lim: {robot.stopper(y):.4f} Nm")


if __name__ == "__main__":
    main()


# Backward compatibility
SBRobot = RRobot
