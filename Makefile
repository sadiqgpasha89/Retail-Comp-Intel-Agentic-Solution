.PHONY: help install install-gcp install-ann dev run test test-unit test-integration test-edge test-domain \
        test-perf test-coverage lint format seed-graph eval diagrams docker-build docker-up docker-down \
        docker-logs clean

PYTHON := .venv/bin/python
UVICORN := .venv/bin/uvicorn
PYTEST  := .venv/bin/pytest
PIP     := .venv/bin/pip

help: ## Show available make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Installation ────────────────────────────────────────────────────────────

install: ## Install all Python dependencies (open_stack mode)
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install-gcp: ## Install with GCP cloud extras
	$(PIP) install -e ".[dev,gcp]"

install-ann: ## Install with HNSW/hnswlib ANN extra
	$(PIP) install -e ".[ann]"

# ─── Development ─────────────────────────────────────────────────────────────

dev: ## Run development server with hot-reload
	PYTHONPATH=src $(UVICORN) retail_intel.api.main:app \
		--host 0.0.0.0 --port 8000 --reload \
		--log-level debug

run: ## Run production server
	PYTHONPATH=src $(UVICORN) retail_intel.api.main:app \
		--host 0.0.0.0 --port 8000 --workers 2

# ─── Testing ─────────────────────────────────────────────────────────────────

test: ## Run full test suite
	$(PYTEST) tests/ -v --tb=short

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -v -m unit --tb=short

test-integration: ## Run integration tests only
	$(PYTEST) tests/integration/ -v -m integration --tb=short

test-edge: ## Run edge-case matrix tests
	$(PYTEST) tests/edge_case/ -v -m edge_case --tb=short

test-domain: ## Run the dependency-light domain-layer tests (pricing, matching, observations, policy)
	$(PYTEST) tests/unit/domain/ -v --tb=short

test-coverage: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=retail_intel --cov-report=term-missing \
		--cov-report=html:htmlcov --tb=short

test-perf: ## Run performance benchmark tests
	$(PYTEST) tests/ -v -m performance --tb=short

# ─── Code Quality ────────────────────────────────────────────────────────────

lint: ## Lint with ruff (if installed)
	$(PYTHON) -m ruff check src/ tests/ || echo "Install ruff: pip install ruff"

format: ## Format code with black (if installed)
	$(PYTHON) -m black src/ tests/ || echo "Install black: pip install black"

# ─── Operational Scripts ─────────────────────────────────────────────────────

seed-graph: ## Seed and validate the Retail Knowledge Graph
	PYTHONPATH=src $(PYTHON) scripts/seed_knowledge_graph.py

eval: ## Run Golden Benchmark evaluation suite
	PYTHONPATH=src $(PYTHON) scripts/run_golden_eval.py

# ─── Diagrams ────────────────────────────────────────────────────────────────

diagrams: ## Re-render diagrams/src/*.mmd to diagrams/rendered/*.svg (needs Node + @mermaid-js/mermaid-cli)
	bash diagrams/render.sh

# ─── Docker ──────────────────────────────────────────────────────────────────

docker-build: ## Build the Docker image
	docker build -f docker/Dockerfile -t retail-intel-api:latest .

docker-up: ## Start full stack (API + Redis) via Docker Compose
	docker compose -f docker/docker-compose.yml up -d

docker-down: ## Stop and remove Docker Compose stack
	docker compose -f docker/docker-compose.yml down

docker-logs: ## Tail API container logs
	docker compose -f docker/docker-compose.yml logs -f retail-intel-api

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove caches, pyc files, and test artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage dist build
