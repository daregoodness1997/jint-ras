from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


class GaitOptimizer:
    def __init__(self, objective):
        self.objective = objective

    def optimize(self, x0, bounds=None, options=None, callback=None):
        options = options or {}
        if bounds is not None:
            return minimize(
                self.objective,
                x0,
                method="Nelder-Mead",
                bounds=bounds,
                options=options,
                callback=callback,
            )
        return minimize(self.objective, x0, method="Nelder-Mead", options=options, callback=callback)
