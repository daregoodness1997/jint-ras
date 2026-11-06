"""Dynamics utilities."""

from packages.dynamics.jacobian import snakeboard_jacobian_fns
from packages.dynamics.constraints import project_velocity, compute_dJc
from packages.dynamics.lyapunov import (
    BODY_GROUPS,
    LyapunovResult,
    calculate_lyapunov_dimension,
    classify_fractal_behavior,
    lyapunov_exponents,
    numerical_jacobian,
    plot_lyapunov,
)
from packages.dynamics.poincare import (
    PoincareAnalysis,
    analyze_poincare,
    build_robot,
    find_crossings,
    flow,
    plot_analysis,
    poincare_section,
    project_section,
    return_map,
    rotor_phase_state,
    section_template,
    section_value,
    simulate,
    spline_return_map,
    z_rotation,
)

__all__ = [
    "snakeboard_jacobian_fns",
    "project_velocity",
    "compute_dJc",
    "BODY_GROUPS",
    "LyapunovResult",
    "calculate_lyapunov_dimension",
    "classify_fractal_behavior",
    "lyapunov_exponents",
    "numerical_jacobian",
    "plot_lyapunov",
    "PoincareAnalysis",
    "analyze_poincare",
    "build_robot",
    "find_crossings",
    "flow",
    "plot_analysis",
    "poincare_section",
    "project_section",
    "return_map",
    "rotor_phase_state",
    "section_template",
    "section_value",
    "simulate",
    "spline_return_map",
    "z_rotation",
]
