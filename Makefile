.PHONY: install
install:
	./setup-dev-environment.sh

.PHONY: run
run:
	poetry run python -m e2e_mcp_server

.PHONY: test
test:
	poetry run pytest
