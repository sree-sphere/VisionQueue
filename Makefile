.PHONY: help install lint test coverage docker-up docker-down format

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  lint         - Run flake8 and black checks"
	@echo "  test         - Run all tests with coverage"
	@echo "  test-ci      - Run tests with MinIO endpoint set for CI"
	@echo "  coverage     - Show coverage report"
	@echo "  format       - Format code using black"
	@echo "  docker-up    - Start Docker services"
	@echo "  docker-down  - Stop Docker services"
	@echo "  run          - Run the application with uvicorn"

install:
	pip install -r requirements.txt

lint:
	pip install flake8 black
	flake8 .
	black --check .

format:
	black .

test:
	dotenv run -- PROMETHEUS_MULTIPROC_DIR=/tmp/metrics-multiproc pytest --cov=.

coverage:
	coverage report -m
	coverage html
	open htmlcov/index.html

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

run:
	uvicorn main:app --reload