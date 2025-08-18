# Heston Trading System Makefile

.PHONY: help install test run clean docker

help:
	@echo "Heston Trading System - Available Commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make test        - Run all tests"
	@echo "  make test-ib     - Test IB connection"
	@echo "  make run         - Run system (paper trading)"
	@echo "  make run-dev     - Run in development mode"
	@echo "  make dashboard   - Start dashboard only"
	@echo "  make clean       - Clean cache files"
	@echo "  make docker      - Build Docker image"
	@echo "  make format      - Format code"
	@echo "  make lint        - Run linters"

install:
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

test:
	pytest tests/ -v --cov=src

test-ib:
	python scripts/test_connection.py

run:
	python scripts/start_system.py --env=paper

run-dev:
	python scripts/start_system.py --env=development --mock

dashboard:
	python scripts/start_system.py --no-mock --dashboard

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage

docker:
	docker-compose -f docker/docker-compose.yml build

docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

format:
	black src/ tests/ scripts/
	isort src/ tests/ scripts/

lint:
	pylint src/
	mypy src/

backup:
	tar -czf backup_$(shell date +%Y%m%d_%H%M%S).tar.gz data/ logs/ database/
