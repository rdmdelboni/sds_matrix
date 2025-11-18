# CI/CD Setup Guide - FDS Reader

This guide explains the Continuous Integration and Continuous Deployment (CI/CD) pipeline implemented for the FDS Reader project.

## 🎯 Overview

The CI/CD pipeline includes:

- **Automated Testing**: Run tests on every push/PR
- **Code Quality Checks**: Linting, formatting, type checking
- **Security Scanning**: Dependency and code vulnerability checks
- **Pre-commit Hooks**: Catch issues before commit
- **Automated Releases**: Build executables on version tags

## 📁 Files Created

### Configuration Files

- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.github/workflows/tests.yml` - Main CI pipeline
- `.github/workflows/release.yml` - Automated release workflow
- `ruff.toml` - Ruff linter/formatter configuration
- `pyproject.toml` - Updated with tool configurations
- `.gitignore` - Ignore patterns for Git

### Documentation

- `CONTRIBUTING.md` - Contribution guidelines
- `CI_CD_GUIDE.md` - This file

### Setup Scripts

- `setup_cicd.sh` - Setup script for Linux/Mac
- `setup_cicd.bat` - Setup script for Windows

## 🚀 Quick Start

### Linux/Mac

```bash
chmod +x setup_cicd.sh
./setup_cicd.sh
```

### Windows

```cmd
setup_cicd.bat
```

### Manual Setup

```bash
# Install dev dependencies
pip install ruff mypy pre-commit safety bandit[toml]

# Install project dependencies
pip install -r requirements.txt

# Setup pre-commit hooks
pre-commit install

# Run all checks
pre-commit run --all-files
```

## 🔧 Tools Overview

### 1. Ruff (Linter & Formatter)

**What it does**: Fast Python linter and code formatter

**Commands**:
```bash
# Format code
ruff format .

# Check formatting
ruff format --check .

# Lint code
ruff check .

# Fix linting issues
ruff check . --fix
```

**Configuration**: `ruff.toml` and `[tool.ruff]` in `pyproject.toml`

### 2. MyPy (Type Checker)

**What it does**: Static type checking for Python

**Commands**:
```bash
# Check types
mypy src

# Check specific file
mypy src/core/heuristics.py
```

**Configuration**: `[tool.mypy]` in `pyproject.toml`

### 3. Pre-commit (Git Hooks)

**What it does**: Run checks automatically before each commit

**Commands**:
```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

**Configuration**: `.pre-commit-config.yaml`

### 4. Bandit (Security Scanner)

**What it does**: Find common security issues in Python code

**Commands**:
```bash
# Scan code
bandit -r src

# Scan with low/medium/high severity
bandit -r src -ll  # Low and above
bandit -r src -lll # Only high severity

# Generate report
bandit -r src -f json -o bandit-report.json
```

**Configuration**: `[tool.bandit]` in `pyproject.toml`

### 5. Safety (Dependency Scanner)

**What it does**: Check dependencies for known security vulnerabilities

**Commands**:
```bash
# Check dependencies
safety check

# Check with JSON output
safety check --json

# Check specific file
safety check -r requirements.txt
```

## 📊 GitHub Actions Workflows

### Tests Workflow (`.github/workflows/tests.yml`)

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs**:

1. **Test** (Matrix: Python 3.10, 3.11, 3.12)
   - Install dependencies
   - Run pytest with coverage
   - Upload coverage to Codecov

2. **Lint**
   - Run Ruff linter
   - Check code formatting
   - Run MyPy type checker

3. **Security**
   - Run Safety (dependency check)
   - Run Bandit (code security scan)
   - Upload security reports

**View Results**: Check the "Actions" tab in GitHub

### Release Workflow (`.github/workflows/release.yml`)

**Triggers**:
- Push tags matching `v*` (e.g., `v2.1.0`)

**Jobs**:
- Build Windows executable with PyInstaller
- Create GitHub release
- Upload executable as release asset

**Usage**:
```bash
git tag v2.2.0
git push origin v2.2.0
```

## 🎨 Pre-commit Hooks Details

The following checks run automatically on commit:

1. **trailing-whitespace**: Remove trailing whitespace
2. **end-of-file-fixer**: Ensure files end with newline
3. **check-yaml**: Validate YAML syntax
4. **check-json**: Validate JSON syntax
5. **check-toml**: Validate TOML syntax
6. **check-merge-conflict**: Detect merge conflict markers
7. **debug-statements**: Detect debug statements
8. **ruff**: Lint and fix code issues
9. **ruff-format**: Format code
10. **mypy**: Type checking (non-blocking for tests/)
11. **pytest-check**: Run tests (can be slow)

## 🔍 Code Quality Standards

### Ruff Rules Enabled

- **E**: pycodestyle errors
- **W**: pycodestyle warnings
- **F**: pyflakes (undefined names, unused imports)
- **I**: isort (import sorting)
- **B**: flake8-bugbear (common bugs)
- **C4**: flake8-comprehensions (list/dict comprehensions)
- **UP**: pyupgrade (modern Python syntax)

### Type Hints

- Add type hints to all function parameters and returns
- Use `from __future__ import annotations` for forward references
- Use `TypeVar`, `Generic` for generic types
- Mark optional parameters with `| None` or `Optional[]`

### Test Coverage

- Maintain >90% coverage on critical modules
- All new features must include tests
- Use fixtures for common setup
- Mock external dependencies

## 📈 Monitoring & Badges

### Add Badges to README

```markdown
![Tests](https://github.com/rdmdelboni/sds_matrix/workflows/Tests/badge.svg)
![Coverage](https://codecov.io/gh/rdmdelboni/sds_matrix/branch/main/graph/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
```

### Setup Codecov (Optional)

1. Sign up at https://codecov.io
2. Connect your GitHub repository
3. Get the upload token
4. Add to GitHub Secrets: `CODECOV_TOKEN`
5. Coverage will be uploaded automatically

## 🐛 Troubleshooting

### Pre-commit hooks fail

```bash
# Update hooks
pre-commit autoupdate

# Clear cache
pre-commit clean

# Reinstall
pre-commit uninstall
pre-commit install
```

### Tests fail in CI but pass locally

- Check Python version compatibility
- Ensure all dependencies in `requirements.txt`
- Check for system dependencies (Tesseract, Poppler)
- Review environment variables

### Ruff/MyPy too strict

- Add exceptions in `pyproject.toml`:
  ```toml
  [tool.ruff.lint.per-file-ignores]
  "path/to/file.py" = ["E501", "F401"]
  ```

- Add type ignore comments:
  ```python
  result = some_function()  # type: ignore
  ```

## 🚦 Workflow

### Before Committing

1. Write code and tests
2. Run locally:
   ```bash
   ruff format .
   ruff check . --fix
   pytest
   ```
3. Commit (pre-commit runs automatically)
4. Push to GitHub

### During Code Review

1. Check GitHub Actions status
2. Review coverage report
3. Address any CI failures
4. Merge when all checks pass

### Creating a Release

1. Update version in `pyproject.toml`
2. Update `RELEASE_NOTES.md`
3. Commit changes
4. Create and push tag:
   ```bash
   git tag -a v2.2.0 -m "Release version 2.2.0"
   git push origin v2.2.0
   ```
5. GitHub Actions builds and creates release

## 📚 Best Practices

### Commit Messages

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Code restructuring
- `test:` - Tests
- `chore:` - Maintenance
- `ci:` - CI/CD changes

Example:
```bash
git commit -m "feat: add new field extraction for packaging group"
git commit -m "fix: correct CAS number validation regex"
git commit -m "ci: update GitHub Actions to use Python 3.12"
```

### Pull Requests

1. Create feature branch: `git checkout -b feature/new-field`
2. Make changes and commit
3. Push: `git push origin feature/new-field`
4. Create PR on GitHub
5. Wait for CI checks
6. Address review comments
7. Merge when approved

### Code Review Checklist

- [ ] All CI checks pass
- [ ] Tests added for new features
- [ ] Documentation updated
- [ ] Code coverage maintained
- [ ] No security warnings
- [ ] Type hints added
- [ ] Code formatted and linted

## 🎓 Learning Resources

- **Ruff**: https://docs.astral.sh/ruff/
- **MyPy**: https://mypy.readthedocs.io/
- **Pre-commit**: https://pre-commit.com/
- **GitHub Actions**: https://docs.github.com/actions
- **Pytest**: https://docs.pytest.org/
- **Bandit**: https://bandit.readthedocs.io/

## 🤝 Contributing

See `CONTRIBUTING.md` for detailed contribution guidelines.

## 📞 Support

If you encounter issues with the CI/CD setup:

1. Check this guide
2. Review workflow logs in GitHub Actions
3. Check existing issues
4. Create a new issue with details

---

**Last Updated**: November 17, 2025
