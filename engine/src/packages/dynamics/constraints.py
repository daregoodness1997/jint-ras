from __future__ import annotations

import numpy as np
from .jacobian import snakeboard_jacobian_fns


def compute_dJc(y, L1: float, L2: float):
    """Compute dJc * dot v0."""
    P = y[0:16].reshape(4, 4)
    Qv = y[16:32].reshape(4, 4)
    Q = P[:, 2]
    O = P[:, 3]
    dQ = Qv[:, 2]
    dO = Qv[:, 3]
    dJc = np.array(
        [
            [dQ[1] * np.cos(Q[1]), dQ[1] * np.sin(Q[1]), dO[1] * L1 * np.sin(O[1])],
            [
                dQ[2] * np.cos(Q[2]),
                dQ[2] * np.sin(Q[2]),
                -dO[2] * L2 * np.sin(O[2]),
            ],
        ]
    )
    v0 = y[16:19]
    return dJc @ v0


def project_velocity(y, L1: float, L2: float):
    """Enforce non-holonomic constraints on board velocity."""
    Jc_fn, _ = snakeboard_jacobian_fns(L1, L2)
    Q = y[0:16].reshape(4, 4)[:, 2]
    O = y[0:16].reshape(4, 4)[:, 3]
    Jc = Jc_fn(Q[1], O[1], Q[2], O[2])
    v0 = y[16:19].copy()
    JcJT = Jc @ Jc.T
    z = np.linalg.solve(JcJT, Jc @ v0)
    y[16:19] = v0 - Jc.T @ z
    return y
