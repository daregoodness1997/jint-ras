"""Research suite FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.core.config import API_PREFIX, HOST, PORT, PLOTS_DIR, OUTPUTS
from server.core.deps import ensure_engine_on_path

ensure_engine_on_path()

from server.api import meta, simulate, sweep, analyze, plots, runs, simulate_async  # noqa: E402

app = FastAPI(title="Research Suite API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router, prefix=API_PREFIX)
app.include_router(simulate.router, prefix=API_PREFIX)
app.include_router(simulate_async.router, prefix=API_PREFIX)
app.include_router(sweep.router, prefix=API_PREFIX)
app.include_router(analyze.router, prefix=API_PREFIX)
app.include_router(plots.router, prefix=API_PREFIX)
app.include_router(runs.router, prefix=API_PREFIX)

# Serve generated plots and outputs as static files.
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS), html=False), name="outputs")
app.mount("/plots", StaticFiles(directory=str(PLOTS_DIR), html=False), name="plots")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "research-suite", "version": "0.1.0", "docs": "/docs"}


@app.get(API_PREFIX + "/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket(API_PREFIX + "/ws/sweep/{run_id}")
async def sweep_ws(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()

    def on_message(message: str) -> None:
        try:
            websocket.send_text(message)
        except Exception:
            pass

    from server.jobs.runner import job_manager

    job_manager.subscribe(run_id, on_message)
    try:
        # Send current state immediately.
        run = job_manager.get(run_id)
        if run is not None:
            import json

            state = {
                "run_id": run.run_id,
                "kind": run.kind,
                "status": run.status,
                "progress": run.progress,
                "created_at": run.created_at,
                "finished_at": run.finished_at,
                "message": run.message,
                "error": run.error,
                "has_result": run.result is not None,
            }
            await websocket.send_text(json.dumps(state))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        job_manager.unsubscribe(run_id, on_message)


def run() -> None:
    import uvicorn

    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    run()
