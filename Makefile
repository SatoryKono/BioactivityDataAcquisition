.PHONY: install test lint run-local docker-up quarantine-purge docker-reset seed-local

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	# Rule 4.2: Fail if VCR cassettes are missing (no network in CI)
	pytest tests/ --vcr-record=none

lint:
	ruff check .
	ruff format --check .
	mypy .

run-local:
	# Runs a sample pipeline using local fixture data
	python -m bioetl.main --config configs/pipelines/chembl_activity.yaml --dry-run

docker-up:
	docker-compose up -d postgres redis minio

docker-reset:
	docker-compose down -v

quarantine-purge:
	# Rule 2.6: Quarantine Ops
	@echo "Purging quarantine for $(PIPELINE)..."
	python -m bioetl.ops.quarantine purge --pipeline $(PIPELINE) --older-than 30d

seed-local:
	@echo "Seeding local database with fixtures..."
	# Implementation would go here
