install:
	python3 -m pip install -r backend/requirements.txt
	cd frontend && npm install

run-backend:
	python3 -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8006

run-ui:
	cd frontend && npm run dev -- --host 0.0.0.0

run-papertrade:
	@echo "Please use the UI to start Paper Trading, or api call /start"
	@echo "Starting Backend..."
	make run-backend

backtest:
	python3 run_backtest.py

test:
	python3 -m pytest backend/tests
