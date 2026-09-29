UV ?= uv

.PHONY: bootstrap format format-check lint typecheck test check

bootstrap:
	$(UV) sync --all-extras

format:
	$(UV) run ruff format packages/shared/python packages/contracts/python src tests

format-check:
	$(UV) run ruff format --check packages/shared/python packages/contracts/python src tests

lint:
	$(UV) run ruff check packages/shared/python packages/contracts/python src tests

typecheck:
	$(UV) run mypy

test:
	$(UV) run python -m unittest discover -s tests/phase0 -p "test_*.py" -v
	$(UV) run python -m unittest discover -s tests/phase1 -p "test_*.py" -v

check: format-check lint typecheck test
