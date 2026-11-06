"""Metadata endpoints: models, controllers, parameter fields."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from server.core.deps import ensure_engine_on_path

ensure_engine_on_path()

from packages.control import available_controllers  # noqa: E402
from packages.core.params import jint_params, ras_params  # noqa: E402
from packages.core.constants import RAD  # noqa: E402

router = APIRouter()

_MODELS = {
    "JINT": {"label": "JINT", "description": "Joint-interrupt mechanism snakeboard"},
    "RAS": {"label": "RAS", "description": "Release-actuated snakeboard"},
}


@router.get("/models")
def list_models() -> dict[str, Any]:
    return {"models": _MODELS}


@router.get("/controllers")
def list_controllers() -> dict[str, Any]:
    return {"controllers": available_controllers()}


def _param_fields(model: str) -> list[dict[str, Any]]:
    params = jint_params() if model.upper() == "JINT" else ras_params()
    import dataclasses

    fields_out = []
    for f in dataclasses.fields(params):
        fields_out.append(
            {
                "name": f.name,
                "type": f.type.__name__ if hasattr(f.type, "__name__") else str(f.type),
                "default": _jsonable(getattr(params, f.name)),
            }
        )
    return fields_out


def _jsonable(value: Any) -> Any:
    import numpy as np

    if isinstance(value, np.generic):
        return value.item()
    return value


@router.get("/params/{model}")
def list_params(model: str) -> dict[str, Any]:
    if model.upper() not in _MODELS:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"unknown model {model!r}")
    return {"model": model.upper(), "params": _param_fields(model)}
