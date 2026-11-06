from __future__ import annotations

from .pd import PDController, PIDController
from .advanced import (
    FeedbackLinearizationController,
    SlidingModeController,
    LQRController,
    LQGController,
    MRACController,
    EnergyShapingController,
    FlatnessController,
)

_CONTROLLERS = {
    "pd": PDController,
    "pid": PIDController,
    "fl": FeedbackLinearizationController,
    "feedback_linearization": FeedbackLinearizationController,
    "smc": SlidingModeController,
    "sliding_mode": SlidingModeController,
    "lqr": LQRController,
    "lqg": LQGController,
    "mrac": MRACController,
    "energy": EnergyShapingController,
    "energy_shaping": EnergyShapingController,
    "flatness": FlatnessController,
}


def available_controllers():
    return sorted(set(_CONTROLLERS.keys()))


def make_controller(name: str = "pd", params=None, **kw):
    name = name.lower()
    if name not in _CONTROLLERS:
        raise ValueError(
            f"Unknown controller {name!r}. Available: {available_controllers()}"
        )
    return _CONTROLLERS[name](params, **kw)
