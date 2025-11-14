.PHONY: clean test test-cov

clean:
	$(RM) *.wav
	$(RM) -r .temp

test:
	uv run pytest -v

test-cov:
	uv run pytest --cov=. --cov-report=html --cov-report=term-missing
