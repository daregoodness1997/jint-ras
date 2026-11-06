"""Plot generation and static file listing endpoints."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.core.config import PLOTS_DIR, OUTPUTS

router = APIRouter()


@router.get("/plots")
def list_plots() -> dict[str, Any]:
    files = []
    if PLOTS_DIR.exists():
        for path in sorted(PLOTS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.is_file():
                files.append(
                    {
                        "name": path.name,
                        "path": f"/api/plots/{path.name}",
                        "size": path.stat().st_size,
                        "modified": path.stat().st_mtime,
                    }
                )
    return {"plots": files}


@router.get("/plots/{name}")
def get_plot(name: str) -> FileResponse:
    path = PLOTS_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"plot {name} not found")
    return FileResponse(path)


@router.delete("/plots/{name}")
def delete_plot(name: str) -> dict[str, Any]:
    path = PLOTS_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"plot {name} not found")
    path.unlink()
    return {"deleted": name}
