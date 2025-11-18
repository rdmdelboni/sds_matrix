#!/bin/bash
# Setup script for CI/CD tools and pre-commit hooks

set -e

echo "🚀 Setting up CI/CD for FDS Reader..."
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version

# Check for virtual environment or create one
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
    echo "   Virtual environment created at ./venv"
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Check if pip is available
echo "✓ Checking pip availability..."
if command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "❌ pip is not available even in venv"
    exit 1
fi

echo "   Using: $PIP_CMD (in venv)"

# Upgrade pip
echo "✓ Upgrading pip..."
$PIP_CMD install --upgrade pip || echo "⚠️  Could not upgrade pip (continuing anyway)"

# Install dev dependencies
echo "✓ Installing development dependencies..."
$PIP_CMD install ruff mypy pre-commit safety bandit[toml]

# Install project dependencies
echo "✓ Installing project dependencies..."
$PIP_CMD install -r requirements.txt

# Setup pre-commit hooks
echo "✓ Setting up pre-commit hooks..."
pre-commit install

# Run initial checks
echo ""
echo "🔍 Running initial code quality checks..."
echo ""

echo "1️⃣  Running Ruff format check..."
ruff format --check . || echo "⚠️  Some files need formatting. Run: ruff format ."

echo ""
echo "2️⃣  Running Ruff linter..."
ruff check . || echo "⚠️  Some linting issues found. Run: ruff check . --fix"

echo ""
echo "3️⃣  Running MyPy type checker..."
mypy src --ignore-missing-imports --no-strict-optional || echo "⚠️  Some type issues found (non-blocking)"

echo ""
echo "4️⃣  Running tests..."
pytest --tb=short -q

echo ""
echo "5️⃣  Running security checks..."
bandit -r src -ll -q || echo "⚠️  Some security warnings (review if needed)"

echo ""
echo "✅ CI/CD setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Activate venv: source venv/bin/activate"
echo "   2. Review any warnings above"
echo "   3. Fix formatting: ruff format ."
echo "   4. Fix linting: ruff check . --fix"
echo "   5. Commit changes: git add . && git commit -m 'ci: setup CI/CD pipeline'"
echo "   6. Push to GitHub to trigger workflows"
echo ""
echo "💡 Pre-commit hooks will run automatically on each commit"
echo "   To run manually: pre-commit run --all-files"
echo ""
echo "⚠️  Remember to activate the venv before working:"
echo "   source venv/bin/activate"
