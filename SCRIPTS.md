# Development Scripts

This document describes the available development scripts for the Daikin Altherma 4 Modbus integration.

## Makefile Targets

### Testing

| Target | Description |
|--------|-------------|
| `make test` | Run all tests with coverage |
| `make test-fast` | Run fast tests without coverage (excludes slow tests) |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-platform-modules` | Run platform module contract tests (new) |
| `make test-e2e` | Run Docker E2E test for HA boot (new) |
| `make test-coverage` | Generate detailed coverage report |
| `make test-slow` | Run slow tests (if any) |
| `make test-parallel` | Run tests in parallel with xdist |
| `make test-all` | Run all test suites (unit + integration + platform-modules) |

### Code Quality

| Target | Description |
|--------|-------------|
| `make lint` | Run linting with Ruff |
| `make format` | Format code with Ruff |
| `make format-check` | Check code formatting |
| `make security` | Run security checks with pip-audit |
| `make safety` | Check dependency vulnerabilities with safety |
| `make bandit` | Run security linter with bandit |

### Reporting

| Target | Description |
|--------|-------------|
| `make coverage` | Generate HTML coverage report |
| `make benchmark` | Run performance benchmarks |
| `make docs` | Generate documentation |

### Maintenance

| Target | Description |
|--------|-------------|
| `make clean` | Clean test artifacts and cache |
| `make reset` | Reset all test environments |

### Installation

| Target | Description |
|--------|-------------|
| `make install` | Install production dependencies |
| `make install-dev` | Install development and test dependencies |

## Quick Start

```bash
# Install development dependencies
make install-dev

# Run all tests
make test

# Run fast tests without coverage
make test-fast

# Run platform module contract tests (new)
make test-platform-modules

# Run Docker E2E test for HA boot (new)
make test-e2e

# Check code formatting
make format-check

# Run linting
make lint
```

## New Test Categories (2026-08)

### Platform Module Contract Tests (`make test-platform-modules`)

These tests verify that Home Assistant can resolve the entity platform modules:

- `sensor`
- `binary_sensor`
- `number`
- `select`
- `climate`
- `switch`

Each platform must expose an `async_setup_entry` coroutine function.

### Docker E2E Test (`make test-e2e`)

This test runs a full Home Assistant boot with the integration to verify:
- Config flow handler registration via `domain=DOMAIN`
- Platform module resolution
- No "Flow handler not found" errors
- Entity platform setup

Requires Docker and a Home Assistant Docker image.

## Running Specific Test Files

```bash
# Run a single test file
pytest tests/integration/test_platform_modules.py -v

# Run a single test
pytest tests/integration/test_platform_modules.py::test_platform_module_exposes_async_setup_entry -v

# Run tests by marker
pytest -m integration
pytest -m slow
pytest -m unit
```
