# Contributing to FDS Reader

Thank you for your interest in contributing to FDS Reader! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Tesseract OCR (for PDF processing)
- Poppler utils (for PDF conversion)

### Setup Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/sds_matrix.git
   cd sds_matrix
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Install dev dependencies
   ```

4. **Setup pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Run tests to verify setup**
   ```bash
   pytest
   ```

## 🔧 Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications

### 2. Make Your Changes

- Write clean, readable code
- Follow PEP 8 style guidelines (enforced by ruff)
- Add type hints where applicable
- Update documentation as needed

### 3. Write Tests

- Add unit tests for new features
- Ensure all tests pass: `pytest`
- Aim for >90% code coverage
- Run coverage report: `pytest --cov=src --cov-report=html`

### 4. Code Quality Checks

Before committing, ensure your code passes all checks:

```bash
# Format code
ruff format .

# Lint code
ruff check . --fix

# Type check
mypy src

# Run tests
pytest

# Security check
bandit -r src
```

Or let pre-commit handle it automatically:
```bash
pre-commit run --all-files
```

### 5. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: add new field extraction for product name"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Test additions or changes
- `chore:` - Maintenance tasks

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Detailed description of what and why
- Reference any related issues
- Screenshots for UI changes

## 📝 Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints for function parameters and returns
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to all public functions and classes

Example:
```python
def extract_numero_onu(
    text: str,
    sections: dict[int, str] | None = None
) -> dict[str, object] | None:
    """Extract ONU number from FDS text.
    
    Args:
        text: The full text content to search
        sections: Optional dictionary of section numbers to text
        
    Returns:
        Dictionary with 'value', 'confidence', and 'context' keys,
        or None if no ONU number found.
    """
    # Implementation
```

### Testing Guidelines

- Write tests for all new features
- Use descriptive test names: `test_extract_onu_from_formatted_text`
- Group related tests in classes
- Use fixtures for common setup
- Mock external dependencies (APIs, file system)

Example:
```python
def test_extract_numero_onu_with_un_prefix():
    """Test extraction of ONU number with 'UN' prefix."""
    text = "UN Number: UN1234"
    result = extract_numero_onu(text)
    assert result["value"] == "1234"
    assert result["confidence"] > 0.8
```

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_heuristics.py

# Specific test
pytest tests/test_heuristics.py::test_extract_numero_onu

# With coverage
pytest --cov=src --cov-report=html

# Fast tests only (skip slow tests)
pytest -m "not slow"
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_heuristics.py       # Unit tests for heuristics
├── test_validator.py        # Unit tests for validators
├── test_document_processor.py  # Integration tests
└── test_edge_cases.py       # Edge cases and error handling
```

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstrings
- Include type hints in function signatures
- Add inline comments for complex logic

### User Documentation

When adding features, update:
- `README.md` - High-level overview
- `USAGE.md` - Detailed usage instructions
- `IMPROVEMENTS.md` - Changelog and improvements

## 🐛 Reporting Bugs

Create an issue with:

**Title**: Short, descriptive summary

**Description**:
- What happened?
- What did you expect to happen?
- Steps to reproduce
- Environment (OS, Python version, etc.)
- Error messages and stack traces
- Screenshots if applicable

## 💡 Suggesting Features

Create an issue with:

**Title**: Feature: [Description]

**Description**:
- Problem it solves
- Proposed solution
- Alternative solutions considered
- Additional context

## 🔍 Code Review Process

1. All code changes require a Pull Request
2. At least one approval required
3. All CI checks must pass:
   - Tests pass
   - Code coverage maintained
   - Linting passes
   - Type checking passes
4. No merge conflicts
5. Documentation updated

## 📦 Release Process

1. Update version in `pyproject.toml`
2. Update `RELEASE_NOTES.md`
3. Create git tag: `git tag v2.1.0`
4. Push tag: `git push origin v2.1.0`
5. GitHub Actions will create release automatically

## 🤝 Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Celebrate contributions of all sizes

## 📞 Getting Help

- Check existing issues and documentation
- Ask questions in GitHub Discussions
- Reach out to maintainers

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to FDS Reader! 🎉
