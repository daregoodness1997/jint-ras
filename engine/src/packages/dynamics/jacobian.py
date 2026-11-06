from __future__ import annotations

from functools import lru_cache

import numpy as np
import sympy as sp


class JacobianSolver:
    def __init__(self, variables_str, equations_list):
        self.variables_str = variables_str
        self.equations_list = equations_list
        self.variables = sp.symbols(variables_str)
        self.equations = [sp.sympify(eq) for eq in equations_list]

    def compute_jacobian(self):
        jacobian_matrix = []
        for eq in self.equations:
            row = []
            for var in self.variables:
                row.append(sp.diff(eq, var))
            jacobian_matrix.append(row)
        return sp.Matrix(jacobian_matrix)


@lru_cache(maxsize=8)
def snakeboard_jacobian_fns(L1: float, L2: float):
    """Numeric evaluators (Jc, Jv)."""
    variables_str = "dX0 dY0 dQ0"
    eq_c = [
        f"sin(Q1)*dX0 - cos(Q1)*dY0 - {L1}*cos(O1)*dQ0",
        f"sin(Q2)*dX0 - cos(Q2)*dY0 + {L2}*cos(O2)*dQ0",
    ]
    eq_v = [
        f"cos(Q1)*dX0 + sin(Q1)*dY0 + {L1}*sin(O1)*dQ0",
        f"cos(Q2)*dX0 + sin(Q2)*dY0 - {L2}*sin(O2)*dQ0",
    ]

    Jc_sym = JacobianSolver(variables_str, eq_c).compute_jacobian()
    Jv_sym = JacobianSolver(variables_str, eq_v).compute_jacobian()
    Q1, O1, Q2, O2 = sp.symbols("Q1 O1 Q2 O2")

    def wrap(fn):
        def evaluate(q1, o1, q2, o2):
            return np.asarray(fn(q1, o1, q2, o2), dtype=float)

        return evaluate

    return wrap(sp.lambdify((Q1, O1, Q2, O2), Jc_sym, "numpy")), wrap(
        sp.lambdify((Q1, O1, Q2, O2), Jv_sym, "numpy")
    )


def main():
    variables_str = "x y"
    equations_list = ["x**2 + y", "x*y"]
    solver = JacobianSolver(variables_str, equations_list)
    J = solver.compute_jacobian()
    print(J)


if __name__ == "__main__":
    main()
