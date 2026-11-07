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

# Bifurcation CLI
poetry run python -m packages.dynamics.bifurcate --model RAS --param A_deg --start 10 --stop 60 --step 5
poetry run python -m packages.dynamics.bifurcate --model ROSSLER --param c --start 2 --stop 8 --step 0.1
poetry run python -m packages.dynamics.bifurcate --model LORENZ --param rho --start 20 --stop 100
poetry run python -m packages.dynamics.bifurcate --model ROSSLER --param c --start 2 --stop 7 --step 0.1 --a 0.2 --b 0.2 --t-transient 10 --t-compute 30 --dt 0.01 --tag rossler_c_ref

# Bifurcation diagrams (local maxima of x₀ vs parameter)
poetry run python -m packages.dynamics.bifurcate --model ROSSLER --param c --start 2 --stop 7 --step 0.1 --a 0.2 --b 0.2 --t-transient 10 --t-compute 30 --dt 0.01 --tag rossler_c

poetry run python -m packages.dynamics.bifurcate --model LORENZ --param rho --start 20 --stop 100 --step 1 --sigma 10 --beta 2.6667 --t-transient 10 --t-compute 30 --dt 0.01 --tag lorenz_rho

# Generic tuning (Poincare + Lyapunov + plots)
poetry run python -m packages.dynamics.tune_generic --model RAS --A-deg 20 --f 1.2 --Kp 30 --Kd 1.5 --Ks 200 --Bs 5 --rho-deg-s 0 --tag ras_periodic --transient 10

# RAS-specific
poetry run python -m packages.dynamics.tune_ras
poetry run python -m packages.dynamics.sweep_ras