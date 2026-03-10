# 🚀 CI/CD Setup Guide

This document describes the comprehensive CI/CD pipeline and development workflow for the Daikin Altherma 4 Modbus integration.

## 📋 Overview

The CI/CD pipeline includes:
- **Automated Testing**: Unit tests, integration tests, and specialized test suites
- **Code Quality**: Linting, formatting, and security checks
- **Coverage Reporting**: Detailed coverage reports with multiple formats
- **Performance Benchmarking**: Test performance tracking
- **Security Scanning**: Vulnerability detection and security analysis
- **Multi-Version Testing**: Testing against multiple Home Assistant versions

## 🔄 GitHub Actions Workflow

### Main Jobs

#### 1. **validate** - Core Testing and Validation
Runs for all HA versions (stable, beta, dev):
- ✅ Code quality checks (Ruff)
- ✅ Unit tests with coverage
- ✅ Integration tests with coverage
- ✅ Slow tests (optional)
- ✅ Coverage reporting (XML, HTML, terminal)
- ✅ Home Assistant configuration validation
- ✅ Performance benchmarking

#### 2. **code-quality** - Advanced Analysis (Pull Requests only)
- 🔒 Security scanning with Bandit
- 🔒 Dependency vulnerability scanning with Safety
- 📊 SonarCloud analysis (optional)

#### 3. **test-summary** - Results Summary
- 📋 Comprehensive test summary
- 📊 Coverage information
- 🔍 Security analysis summary

#### 4. **release** - Release Creation
- 🏷️ Automatic GitHub release creation for tags

## 🧪 Testing Strategy

### Test Categories

#### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- Mock external dependencies
- Focus on individual components

#### Integration Tests (`@pytest.mark.integration`)
- Test component interactions
- Real-world scenarios
- Config flow testing

#### Specialized Tests
- `@pytest.mark.config_flow` - Configuration flow tests
- `@pytest.mark.options_flow` - Options flow tests
- `@pytest.mark.setup_entry` - Setup entry tests
- `@pytest.mark.unload_entry` - Unload entry tests
- `@pytest.mark.slow` - Performance-intensive tests

### Test Execution

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-config-flow
make test-options-flow
make test-setup-entry
make test-unload-entry

# Run tests in parallel
make test-parallel

# Run with coverage
make test-coverage
```

## 📊 Coverage Reporting

### Coverage Formats
- **Terminal**: Immediate feedback during development
- **HTML**: Detailed interactive report (`htmlcov/index.html`)
- **XML**: CI/CD integration and third-party tools
- **JSON**: Programmatic access to coverage data

### Coverage Integration
- **Codecov**: Automatic upload for trend analysis
- **GitHub Artifacts**: Downloadable coverage reports
- **Coverage Thresholds**: Configurable minimum coverage requirements

### Coverage Commands

```bash
# Generate coverage report
make coverage

# View HTML report
open htmlcov/index.html

# Coverage with threshold
pytest --cov-fail-under=80
```

## 🔍 Code Quality Checks

### Ruff (Primary Linter)
- **Linting**: Code quality and style checks
- **Formatting**: Consistent code formatting
- **Import Sorting**: Organized import statements

```bash
# Run all checks
make lint

# Format code
make format

# Check formatting only
make format-check
```

### Security Checks

#### Bandit (Security Linter)
- Scans for common security issues
- Custom configuration for Home Assistant integrations
- Excludes test files from scanning

```bash
# Run security scan
make bandit
```

#### Safety (Dependency Scanner)
- Checks for known vulnerabilities in dependencies
- Automated database updates
- CVE monitoring

```bash
# Check dependencies
make safety
```

## 📈 Performance Benchmarking

### Benchmark Configuration
- **pytest-benchmark**: Performance testing framework
- **JSON Output**: Machine-readable results
- **Trend Tracking**: Performance over time
- **Artifact Storage**: Historical benchmark data

### Benchmark Commands

```bash
# Run benchmarks
make benchmark

# View results
cat benchmark.json
```

## 🔧 Development Workflow

### Local Development Setup

```bash
# Install development dependencies
make install-dev

# Run full CI pipeline locally
make ci-local

# Quick development cycle
make quick-test
make quick-lint
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Git Workflow Integration

1. **Feature Branch**: Create feature branch
2. **Development**: Make changes with pre-commit hooks
3. **Testing**: Run `make ci-local` before push
4. **Pull Request**: Automated CI/CD pipeline runs
5. **Review**: Code quality and test results
6. **Merge**: Automatic release on tag

## 📁 File Structure

```
.github/workflows/
├── ci.yml                 # Main CI/CD pipeline

tests/
├── test_integration_lifecycle.py  # Integration lifecycle tests
├── test_config_flow.py          # Config flow tests
├── test_config_model.py         # Configuration model tests
└── ...

requirements-test.txt    # Test dependencies
pytest.ini             # Pytest configuration
Makefile               # Development commands
.pre-commit-config.yaml # Pre-commit hooks
```

## 🔧 Configuration Files

### pytest.ini
- Test discovery settings
- Coverage configuration
- Marker definitions
- Warning filters

### requirements-test.txt
- Testing framework dependencies
- Code quality tools
- Security scanners
- Performance tools

### Makefile
- Convenient development commands
- Test execution helpers
- Code quality automation
- Maintenance utilities

## 🚀 CI/CD Best Practices

### Performance Optimization
- **Parallel Testing**: Use `pytest-xdist` for faster execution
- **Selective Testing**: Run only relevant tests during development
- **Caching**: Cache dependencies between runs
- **Artifact Management**: Efficient storage of test results

### Quality Gates
- **Coverage Thresholds**: Minimum 80% coverage requirement
- **Security Scanning**: No high-severity vulnerabilities
- **Code Quality**: All linting issues must be resolved
- **Test Success**: All tests must pass

### Monitoring and Alerting
- **Coverage Trends**: Track coverage changes over time
- **Performance Trends**: Monitor benchmark results
- **Security Alerts**: Immediate notification of vulnerabilities
- **Test Failures**: Quick identification of issues

## 🔗 External Integrations

### Codecov
- Coverage trend analysis
- Pull request coverage diff
- Coverage badges
- Historical data

### SonarCloud (Optional)
- Code quality analysis
- Technical debt metrics
- Security hotspot detection
- Maintainability ratings

### GitHub Actions
- Automated workflow execution
- Artifact storage
- Release management
- Status checks

## 🛠️ Troubleshooting

### Common Issues

#### Coverage Not Generated
```bash
# Clean and regenerate
make clean
make coverage
```

#### Pre-commit Hook Failures
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Run manually to debug
pre-commit run --all-files --verbose
```

#### Test Failures in CI
- Check test artifacts in GitHub Actions
- Review coverage reports for missing tests
- Verify security scan results
- Check benchmark performance

### Performance Optimization

#### Slow Test Execution
```bash
# Run tests in parallel
pytest -n auto

# Run only changed tests
pytest --testmon

# Exclude slow tests
pytest -m "not slow"
```

#### Memory Issues
```bash
# Limit parallel workers
pytest -n 2

# Use less memory-intensive coverage
pytest --cov-report=term-missing
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Codecov Documentation](https://docs.codecov.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://safety.readthedocs.io/)
