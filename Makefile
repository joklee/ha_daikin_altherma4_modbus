# Makefile for Daikin Altherma 4 Modbus Integration
# Provides convenient commands for development, testing, and code quality

.PHONY: help install install-dev test test-unit test-integration test-all test-coverage test-ha lint format security clean docs benchmark hassfest test-platform-modules test-e2e test-slow test-parallel test-fast

# Default target
help:
	@echo "🧪 Daikin Altherma 4 Modbus - Development Commands"
	@echo ""
	@echo "📦 Installation:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development and test dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test          Run all tests with coverage"
	@echo "  test-fast      Run fast tests without coverage"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-platform-modules Run platform module contract tests"
	@echo "  test-e2e       Run Docker E2E test for HA boot"
	@echo "  test-coverage  Generate detailed coverage report"
	@echo "  test-slow      Run slow tests (if any)"
	@echo "  test-parallel  Run tests in parallel"
	@echo "  test-ha        Run real Home Assistant integration tests"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint          Run linting with Ruff"
	@echo "  format        Format code with Ruff"
	@echo "  format-check  Check code formatting"
	@echo "  security      Run security checks"
	@echo "  safety        Check dependency vulnerabilities"
	@echo "  bandit        Run security linter"
	@echo ""
	@echo "📊 Reporting:"
	@echo "  coverage      Generate HTML coverage report"
	@echo "  benchmark     Run performance benchmarks"
	@echo "  docs          Generate documentation"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean         Clean test artifacts and cache"
	@echo "  reset         Reset all test environments"
	@echo ""
	@echo "🏠 CI:"
	@echo "  hassfest      Run hassfest integration validation"

# Installation
install:
	@echo "📦 Installing production dependencies..."
	pip install -e .

install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements-test.txt
	pip install -e .

# Testing
test:
	@echo "🧪 Running all tests with coverage..."
	pytest -m "unit or integration or slow" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=html --cov-report=term-missing

test-fast:
	@echo "⚡ Running fast tests without coverage..."
	pytest -x --tb=short -m "not slow"

test-unit:
	@echo "🧪 Running unit tests..."
	pytest -m "unit or not integration" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-integration:
	@echo "🧪 Running integration tests..."
	pytest -m "integration" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-platform-modules:
	@echo "🧪 Running platform module contract tests..."
	pytest tests/integration/test_platform_modules.py -v

test-e2e:
	@echo "🚀 Running Docker E2E test for HA boot..."
	HA_DOCKER_DEMO_TESTS=1 pytest tests/integration/test_ha_docker_demo_mode.py -v

test-coverage:
	@echo "📊 Generating detailed coverage report..."
	pytest --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=html --cov-report=xml --cov-report=term-missing --cov-fail-under=25
	@echo "📈 Coverage report generated in htmlcov/"

test-ha:
	@echo "🏠 Running real Home Assistant integration tests..."
	pytest tests/ha/ -v

test-slow:
	@echo "🐌 Running slow tests..."
	pytest -m "slow" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-parallel:
	@echo "⚡ Running tests in parallel..."
	pytest -n auto --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-all: test-unit test-integration test-platform-modules
	@echo "✅ All test suites completed!"

# Code Quality
lint:
	@echo "🔍 Running linting with Ruff..."
	ruff check .
	ruff check --select I .

format:
	@echo "✏️ Formatting code with Ruff..."
	ruff format .

format-check:
	@echo "🔍 Checking code formatting..."
	ruff format --check .

security:
	@echo "🔒 Running security checks..."
	pip-audit -r requirements-dev.txt --progress-spinner off \
	  --ignore-vuln PYSEC-2026-3552 \
	  --ignore-vuln PYSEC-2026-3553 \
	  --ignore-vuln PYSEC-2026-3554
	@echo "   Note: PYSEC-2026-3552/3553/3554 (cryptography<50) are accepted"
	@echo "   until Home Assistant lifts its exact pin 'cryptography==48.0.1'."

safety:
	@echo "⚠️  Checking dependency vulnerabilities..."
	safety check --json

bandit:
	@echo "🔒 Running security linter..."
	bandit -r custom_components/ -f txt --severity-level medium

# Reporting
coverage:
	@echo "📊 Generating HTML coverage report..."
	pytest --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=html --cov-report=xml
	@echo "📈 Coverage report available at htmlcov/index.html"

benchmark:
	@echo "📈 Running performance benchmarks..."
	pytest --benchmark-only --benchmark-json=benchmark.json
	@echo "📊 Benchmark results saved to benchmark.json"

docs:
	@echo "📚 Generating documentation..."
	@echo "Documentation generation not yet implemented"

# Maintenance
clean:
	@echo "🧹 Cleaning test artifacts and cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml test-results.xml benchmark.json 2>/dev/null || true
	rm -rf .pytest_cache/ 2>/dev/null || true
	rm -rf .ruff_cache/ 2>/dev/null || true

reset: clean
	@echo "🔄 Resetting all test environments..."
	pip uninstall -y ha-daikin-altherma4-modbus 2>/dev/null || true
	pip cache purge

# Hassfest validation
HASSFEST_DIR ?= /tmp/ha-core-sparse

hassfest:
	@echo "🏠 Running hassfest validation..."
	@if [ ! -d "$(HASSFEST_DIR)/script/hassfest" ]; then \
		echo "📦 Cloning HA core hassfest scripts..."; \
		git clone --depth 1 --filter=blob:none --sparse https://github.com/home-assistant/core.git $(HASSFEST_DIR) 2>/dev/null; \
		cd $(HASSFEST_DIR) && git sparse-checkout set script/hassfest script/translations 2>/dev/null; \
	fi
	@PYTHONPATH=$(HASSFEST_DIR) python -m script.hassfest.__main__ --integration-path custom_components/ha_daikin_altherma4_modbus
	@echo "✅ hassfest validation passed!"

# CI/CD Helpers
ci-test:
	@echo "🚀 Running CI test suite..."
	$(MAKE) lint
	$(MAKE) format-check
	$(MAKE) security
	$(MAKE) test-coverage
	$(MAKE) benchmark

ci-local:
	@echo "🏠 Running full CI pipeline locally..."
	$(MAKE) install-dev
	$(MAKE) ci-test
	@echo "✅ Local CI pipeline completed successfully!"

# Development helpers
dev-setup: install-dev
	@echo "🛠️  Development environment setup complete!"
	@echo "Run 'make test' to verify everything is working."

watch-test:
	@echo "👀 Watching for changes and running tests..."
	@echo "Install watchdog for file watching: pip install watchdog"
	@echo "Then run: ptw --runner 'python -m pytest' tests/"

# Quick commands for common tasks
quick-test:
	@echo "⚡ Quick test run..."
	pytest tests/ -x --tb=short

quick-lint:
	@echo "⚡ Quick lint check..."
	ruff check . --select E,F,W

# Integration with our specific test files
test-lifecycle:
	@echo "🧪 Testing integration lifecycle..."
	pytest tests/test_integration_lifecycle.py -v

test-config:
	@echo "🧪 Testing configuration flows..."
	pytest tests/test_config_model.py tests/test_config_flow.py -v

test-platform-setup:
	@echo "🧪 Testing platform setup validation..."
	pytest tests/test_platform_setup.py -v

test-connection-pool:
	@echo "🧪 Testing connection pool performance..."
	pytest tests/test_connection_pool.py -v

test-all-new:
	@echo "🧪 Running all new tests..."
	pytest tests/test_integration_lifecycle.py tests/test_config_model.py tests/test_config_flow.py tests/test_platform_setup.py tests/test_connection_pool.py -v
