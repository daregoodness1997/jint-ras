"""Dependency helpers: make engine packages importable on demand."""

from __future__ import annotations

import sys
from pathlib import Path

from server.core.config import ENGINE_SRC


def ensure_engine_on_path() -> None:
    """Add the engine `src` tree to sys.path so `packages.*` imports resolve."""
    engine_src = str(ENGINE_SRC.resolve())
    if engine_src not in sys.path:
        sys.path.insert(0, engine_src)
