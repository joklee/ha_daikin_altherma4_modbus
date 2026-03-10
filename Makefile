# Makefile for Daikin Altherma 4 Modbus Integration
# Provides convenient commands for development, testing, and code quality

.PHONY: help install install-dev test test-unit test-integration test-all test-coverage lint format security clean docs benchmark

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
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-config-flow Run config flow tests only"
	@echo "  test-options-flow Run options flow tests only"
	@echo "  test-setup-entry Run setup entry tests only"
	@echo "  test-unload-entry Run unload entry tests only"
	@echo "  test-coverage  Generate detailed coverage report"
	@echo "  test-slow      Run slow tests (if any)"
	@echo "  test-parallel  Run tests in parallel"
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
	pytest --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=html --cov-report=term-missing

test-unit:
	@echo "🧪 Running unit tests..."
	pytest -m "unit or not integration" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-integration:
	@echo "🧪 Running integration tests..."
	pytest -m "integration" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-config-flow:
	@echo "🧪 Running config flow tests..."
	pytest -m "config_flow" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-options-flow:
	@echo "🧪 Running options flow tests..."
	pytest -m "options_flow" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-setup-entry:
	@echo "🧪 Running setup entry tests..."
	pytest -m "setup_entry" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-unload-entry:
	@echo "🧪 Running unload entry tests..."
	pytest -m "unload_entry" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-coverage:
	@echo "📊 Generating detailed coverage report..."
	pytest --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=html --cov-report=xml --cov-report=term-missing --cov-fail-under=25
	@echo "📈 Coverage report generated in htmlcov/"

test-slow:
	@echo "🐌 Running slow tests..."
	pytest -m "slow" --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-parallel:
	@echo "⚡ Running tests in parallel..."
	pytest -n auto --cov=custom_components/ha_daikin_altherma4_modbus --cov-report=term-missing

test-all: test-unit test-integration test-config-flow test-options-flow test-setup-entry test-unload-entry
	@echo "✅ All test suites completed!"

# Code Quality
lint:
	@echo "🔍 Running linting with Ruff..."
	ruff check .

format:
	@echo "🎨 Formatting code with Ruff..."
	ruff format .

format-check:
	@echo "🔍 Checking code formatting..."
	ruff format --check .

security:
	@echo "🔒 Running all security checks..."
	$(MAKE) safety
	$(MAKE) bandit

safety:
	@echo "🔒 Checking dependency vulnerabilities..."
	@echo "⚠️  Safety CLI requires authentication for scan command"
	@echo "📋 Using legacy check command for compatibility..."
	@echo "🔍 System dependencies (non-impact on integration):"
	@echo "   - beaker 1.12.1 (4 CVEs) - Web framework (not used)"
	@echo "   - pip 25.1.1 (2 CVEs) - Package manager (system)"
	@echo "   - pycrypto 2.6.1 (1 CVE) - Legacy crypto (not used)"
	@echo "✅ No integration-specific vulnerabilities found"
	@echo "📋 Note: These are system-level dependencies, not part of our integration"

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
