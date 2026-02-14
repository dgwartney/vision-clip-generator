.PHONY: clean test test-cov install-dev check-dev

# Install dev dependencies
install-dev:
	@echo "Installing dev dependencies..."
	@uv sync --extra dev

# Check if dev dependencies are installed
check-dev:
	@uv run python -c "import pytest" 2>/dev/null || (echo "Dev dependencies not found. Installing..." && $(MAKE) install-dev)

clean:
	$(RM) *.wav
	$(RM) -r .temp
	$(RM) -r htmlcov
	$(RM) .coverage
	$(RM) -r .pytest_cache
	$(RM) *.log

test: check-dev
	uv run --extra dev pytest -v

test-cov: check-dev
	uv run --extra dev pytest --cov=. --cov-report=html --cov-report=term-missing
