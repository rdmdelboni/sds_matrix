@echo off
REM Setup script for CI/CD tools and pre-commit hooks (Windows)

echo 🚀 Setting up CI/CD for FDS Reader...
echo.

REM Check Python version
echo ✓ Checking Python version...
python --version

REM Upgrade pip
echo ✓ Upgrading pip...
python -m pip install --upgrade pip

REM Install dev dependencies
echo ✓ Installing development dependencies...
pip install ruff mypy pre-commit safety bandit[toml]

REM Install project dependencies
echo ✓ Installing project dependencies...
pip install -r requirements.txt

REM Setup pre-commit hooks
echo ✓ Setting up pre-commit hooks...
pre-commit install

REM Run initial checks
echo.
echo 🔍 Running initial code quality checks...
echo.

echo 1️⃣  Running Ruff format check...
ruff format --check . 2>nul || echo ⚠️  Some files need formatting. Run: ruff format .

echo.
echo 2️⃣  Running Ruff linter...
ruff check . 2>nul || echo ⚠️  Some linting issues found. Run: ruff check . --fix

echo.
echo 3️⃣  Running MyPy type checker...
mypy src --ignore-missing-imports --no-strict-optional 2>nul || echo ⚠️  Some type issues found (non-blocking)

echo.
echo 4️⃣  Running tests...
pytest --tb=short -q

echo.
echo 5️⃣  Running security checks...
bandit -r src -ll -q 2>nul || echo ⚠️  Some security warnings (review if needed)

echo.
echo ✅ CI/CD setup complete!
echo.
echo 📋 Next steps:
echo    1. Review any warnings above
echo    2. Fix formatting: ruff format .
echo    3. Fix linting: ruff check . --fix
echo    4. Commit changes: git add . ^&^& git commit -m "ci: setup CI/CD pipeline"
echo    5. Push to GitHub to trigger workflows
echo.
echo 💡 Pre-commit hooks will run automatically on each commit
echo    To run manually: pre-commit run --all-files

pause
