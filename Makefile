.PHONY: install install-dev install-locked run test cov lint typecheck lock

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# Install the exact pinned set (reproducible). Generate the locks with `make lock`.
install-locked:
	pip install -r requirements.lock -r requirements-dev.lock

# Regenerate lockfiles from the >= source files (needs pip-tools + network).
lock:
	pip-compile --quiet --output-file=requirements.lock requirements.txt
	pip-compile --quiet --output-file=requirements-dev.lock requirements-dev.txt

test:
	PYTHONPATH=src pytest -q

# Same tests with coverage + the fail-under floor from pyproject ([tool.coverage.report]).
cov:
	PYTHONPATH=src pytest -q --cov=research --cov-report=term-missing

lint:
	ruff check src tests

# Static type checking — validates the hints the code already carries (config in pyproject).
typecheck:
	mypy src

# src/ is on PYTHONPATH so `research` resolves as a top-level package.
# (app.py is scaffolded in a later Phase 1 slice.)
run:
	PYTHONPATH=src python -m research.app
