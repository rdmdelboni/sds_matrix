#!/bin/bash
# Quick start script to verify CI/CD setup

echo "🔍 Verifying CI/CD Setup for FDS Reader..."
echo ""

# Check for required files
echo "📁 Checking configuration files..."

files=(
    ".pre-commit-config.yaml"
    ".github/workflows/tests.yml"
    ".github/workflows/release.yml"
    "ruff.toml"
    "pyproject.toml"
    ".gitignore"
    "CONTRIBUTING.md"
    "CI_CD_GUIDE.md"
)

all_present=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        all_present=false
    fi
done

echo ""

if [ "$all_present" = true ]; then
    echo "✅ All CI/CD files are present!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Run: ./setup_cicd.sh (to install tools and setup hooks)"
    echo "   2. Fix any issues: ruff format . && ruff check . --fix"
    echo "   3. Commit: git add . && git commit -m 'ci: setup CI/CD pipeline'"
    echo "   4. Push: git push origin main"
    echo "   5. Check: https://github.com/rdmdelboni/sds_matrix/actions"
else
    echo "❌ Some files are missing. Please review the setup."
fi

echo ""
echo "📚 Documentation:"
echo "   - CI_CD_GUIDE.md - Complete CI/CD guide"
echo "   - CI_CD_SUMMARY.md - Implementation summary"
echo "   - CONTRIBUTING.md - Contribution guidelines"
