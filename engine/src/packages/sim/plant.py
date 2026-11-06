"""Plant adapter for gait optimization."""

from __future__ import annotations

import numpy as np

from packages.control import PDController, make_controller
from packages.core.params import Params, jint_params, ras_params
from packages.models.jint import JRobot
from packages.models.ras import RRobot


class Plant:
    def __init__(self, robot):
        self.robot = robot

    @property
    def p(self) -> Params:
        return self.robot.params

    def simulate(self, duration: float, f_sim: float) -> np.ndarray:
        return self.robot.simulate_rows(duration, f_sim)


def _make_controller(controller, controller_cls, params):
    if isinstance(controller, str):
        return make_controller(controller, params)
    if controller is not None:
        return controller
    return (controller_cls or PDController)(params)


def create_plant(model: str = "JINT", controller_cls=None, controller=None, **overrides):
    model = model.upper()
    if model == "JINT":
        def plant(A_deg: float, f: float, rho_deg_s: float) -> Plant:
            params = jint_params(A_deg=A_deg, f=f, rho_deg_s=rho_deg_s, **overrides)
            ctrl = _make_controller(controller, controller_cls, params)
            robot = JRobot(controller=ctrl, params=params)
            return Plant(robot)
        return plant

    if model == "RAS":
        def plant(A_deg: float, f: float, rho_deg_s: float) -> Plant:
            params = ras_params(A_deg=A_deg, f=f, rho_deg_s=rho_deg_s, **overrides)
            ctrl = _make_controller(controller, controller_cls, params)
            robot = RRobot(controller=ctrl, params=params)
            return Plant(robot)
        return plant

    raise ValueError(f"unknown model {model!r}; expected 'JINT' or 'RAS'")


model_plant = create_plant
