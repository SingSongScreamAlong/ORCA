# ORCA convenience targets. Run `make help` for the list.

.DEFAULT_GOAL := help
.PHONY: help backend-install backend-test backend-lint frontend-install \
        frontend-typecheck frontend-build up down test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

backend-install: ## Install backend (editable, with dev deps)
	cd backend && pip install -e ".[dev]"

backend-test: ## Run backend + structure tests
	cd backend && python -m pytest -q

backend-lint: ## Lint the backend with ruff
	cd backend && ruff check .

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-typecheck: ## Typecheck the frontend
	cd frontend && npm run typecheck

frontend-build: ## Production build of the frontend
	cd frontend && npm run build

up: ## Start local PostgreSQL and Neo4j
	cd infrastructure && docker compose up -d postgres neo4j

down: ## Stop local services
	cd infrastructure && docker compose down

test: backend-test ## Run the test suite
