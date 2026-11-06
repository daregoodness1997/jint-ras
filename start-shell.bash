eval $(poetry env activate)                               

cd suite/backend && poetry run uvicorn server.main:app --host 127.0.0.1 --port 8000
cd suite/web && npm run dev  

poetry run start --model JINT --lyapunov --lyapunov-duration 20 --lyapunov-dt 0.02 --no-plot
poetry run start --model RAS --lyapunov --lyapunov-duration 20 --lyapunov-dt 0.02 --no-plot
 python -m packages.cli.sweep --model RAS --controller flatness  --gait-axis A_deg=40,50,60 --duration 2 --f-sim 200 --lyapunov --poincare

 CLI commands
# Standalone Lyapunov CLI
poetry run python -m packages.dynamics.lyapunov --model LORENZ --duration 10 --dt 0.01 --plot
poetry run python -m packages.dynamics.lyapunov --model ROSSLER --duration 10 --dt 0.01 --plot

# Standalone Poincare CLI
poetry run python -m packages.dynamics.poincare --model LORENZ --duration 20 --dt 0.01 --plot
poetry run python -m packages.dynamics.poincare --model ROSSLER --duration 20 --dt 0.01 --plot

# Base snakeboard CLI
poetry run start --model LORENZ --lyapunov --poincare --no-plot
poetry run start --model ROSSLER --lyapunov --poincare --no-plot