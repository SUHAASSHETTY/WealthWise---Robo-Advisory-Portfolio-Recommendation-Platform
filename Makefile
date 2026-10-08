.PHONY: dev dev-backend dev-frontend migrate test test-backend test-frontend install

install:
	cd backend && poetry install
	cd frontend && npm install

migrate:
	cd backend && poetry run alembic upgrade head

dev: migrate
	@echo "Starting WealthWise backend (port 8000) and frontend (port 5173)..."
	@(trap 'kill 0' SIGINT; \
		(cd backend && WEALTHWISE_STUB_AUTH_ENABLED=true poetry run uvicorn app.main:app --reload --port 8000) & \
		(cd frontend && npm run dev) & \
		wait)

test: test-backend test-frontend

test-backend:
	poetry run pytest tests/

test-frontend:
	cd frontend && npx playwright test
