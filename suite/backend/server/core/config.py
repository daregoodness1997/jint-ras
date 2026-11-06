"""Runtime configuration for the research suite backend."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # suite/backend/server/core/config.py -> alpha-project
ENGINE_SRC = ROOT / "engine" / "src"
OUTPUTS = Path(os.environ.get("SNAKEBOARD_OUTPUT_DIR", ROOT / "outputs"))
PLOTS_DIR = OUTPUTS / "plots"
SWEEPS_DIR = OUTPUTS / "sweeps"
SIMULATIONS_DIR = OUTPUTS / "simulations"

API_PREFIX = "/api"
HOST = os.environ.get("RESEARCH_SUITE_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESEARCH_SUITE_PORT", "8000"))

# Ensure plot outputs exist.
for directory in (OUTPUTS, PLOTS_DIR, SWEEPS_DIR, SIMULATIONS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

__all__ = ["ROOT", "ENGINE_SRC", "OUTPUTS", "PLOTS_DIR", "SWEEPS_DIR", "SIMULATIONS_DIR", "API_PREFIX", "HOST", "PORT"]
