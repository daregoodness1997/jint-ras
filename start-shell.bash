eval $(poetry env activate)                               

cd suite/backend && poetry run uvicorn server.main:app --host 127.0.0.1 --port 8000
cd suite/web && npm run dev  

poetry run start --model JINT --lyapunov --lyapunov-duration 20 --lyapunov-dt 0.02 --no-plot
poetry run start --model RAS --lyapunov --lyapunov-duration 20 --lyapunov-dt 0.02 --no-plot