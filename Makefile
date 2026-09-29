PYTHON ?= python3

.PHONY: bootstrap format format-check lint typecheck test check

bootstrap:
	$(PYTHON) -m pip install -e ".[dev]"

format:
	$(PYTHON) -m ruff format packages/shared/python tests

format-check:
	$(PYTHON) -m ruff format --check packages/shared/python tests

lint:
	$(PYTHON) -m ruff check packages/shared/python tests

typecheck:
	$(PYTHON) -m mypy packages/shared/python

test:
	$(PYTHON) -m unittest discover -s tests/phase0 -p "test_*.py" -v
	$(PYTHON) -m unittest discover -s tests/phase1 -p "test_*.py" -v

check: format-check lint typecheck test
