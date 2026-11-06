# Research Suite Backend

Fullstack research suite for comprehensive snakeboard gait testing.

## Backend

FastAPI application exposing the existing `engine` simulation/sweep/analysis
packages as a REST API with WebSocket progress streaming.

### Run

```bash
cd suite/backend
poetry install
poetry run python -m server.main
```

or

```bash
cd suite/backend
poetry run uvicorn server.main:app --host 127.0.0.1 --port 8000
```

### API

- `GET /api/health` — health check
- `GET /api/models` — available snakeboard models (JINT, RAS)
- `GET /api/controllers` — available controllers
- `GET /api/params/{model}` — parameter fields with defaults
- `POST /api/simulate` — single rollout + metrics
- `POST /api/sweep` — start a background parameter sweep (returns `run_id`)
- `GET /api/sweep/{run_id}` — sweep status / result
- `GET /api/runs` — list all runs
- `POST /api/analyze/poincare` — Poincare section analysis
- `POST /api/analyze/lyapunov` — Lyapunov exponent analysis
- `GET /api/plots` — list generated plots
- `GET /api/plots/{name}` — serve a plot image
- `WS /api/ws/sweep/{run_id}` — stream sweep progress

### Tests

```bash
cd suite/backend
poetry run pytest
```
