from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np


@dataclass
class Params:
    model: str = "JINT"  # "JINT" or "RAS"
    Mtot: float = 4.0  # Mass in kg
    I0: float = 0.08  # board yaw inertia
    I1: float = 0.002  # front wheel steering inertia
    I2: float = 0.002  # rear wheel steering inertia
    Isup: float = 0.001  # motor-support inertia
    I3: float = 0.05  # rotor inertia
    L1: float = 0.1  # front wheel distance
    L2: float = 0.1  # rear wheel distance
    # gear ratios O1 = g1*O0, O2 = g2*O0
    g1: float = 1.0  # front wheel
    g2: float = -1.0  # rear wheel, counter-rotating
    g0: float = 1.0  # support
    g3: float = 1.0  # rotor
    Bv: tuple = (3.0, 3.0)  # damping coefficients for the wheels
    BQ: tuple = (0.0, 0.0, 0.0, 0.0)  # damping coefficients for the joints
    BO: tuple = (0.0, 0.0, 0.0, 0.0)  # damping coefficients for the motors
    O0_lim: float = np.pi / 4  # limit for O0
    Bs: float = 0.2  # spring damping coefficient
    Ks: float = 5.0  # spring stiffness
    Tlim_max: float = 0.10  # maximum torque limit
    Kp: float = 100.0  # proportional gain
    Kd: float = 3.0  # derivative gain
    A_deg: float = 50.0  # angle in degrees
    f: float = 0.8  # reference frequency in Hz
    rho_deg_s: float = 0.0  # angular velocity in degrees per second


def jint_params(**kw) -> Params:
    """JINT defaults."""
    return replace(Params(model="JINT"), **kw)


def ras_params(**kw) -> Params:
    """RAS defaults."""
    base = Params(
        model="RAS",
        Mtot=3.2,
        I0=0.02,
        I1=0.002,
        I2=0.002,
        Isup=0.004,
        I3=0.015,
        L1=0.15,
        L2=0.15,
        g1=2.0,
        g2=-2.0,
        Bv=(2.0, 2.0),
        # Match the original snakeboard_model.py: wheel joint damping is
        # carried by BQ[0] and the wheel-support damping by BO[0:3].  Earlier
        # engine defaults had these two assigned differently and added
        # 0.02*(dQ1 + dQ2) to the support equation.
        BQ=(0.05, 0.0, 0.0, 0.0),
        BO=(0.04, 0.02, 0.02, 0.06),
        O0_lim=np.pi / 12,
        Bs=7.0,
        Ks=500.0,
        Kp=10.0,
        Kd=0.75,
        A_deg=40.0,
        f=1.2,
        rho_deg_s=0.0,
    )
    return replace(base, **kw)
