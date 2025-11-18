# Virtual Environment Setup (Arch Linux / PEP 668 Systems)

## Why Virtual Environment?

On Arch Linux and other modern distributions that follow PEP 668, system Python packages are "externally managed" to prevent conflicts with system packages. This means you **must** use a virtual environment for Python development.

## Quick Setup

The `setup_cicd.sh` script automatically creates and configures a virtual environment. Just run:

```bash
./setup_cicd.sh
```

This will:
1. Create `venv/` directory (if it doesn't exist)
2. Install all dependencies in the virtual environment
3. Setup pre-commit hooks
4. Run initial checks

## Daily Workflow

### Activate Virtual Environment

**Every time** you work on the project, activate the venv first:

```bash
source venv/bin/activate
```

Your prompt will change to show `(venv)` prefix.

### Deactivate When Done

```bash
deactivate
```

## Commands (with venv active)

```bash
# Activate venv (do this first!)
source venv/bin/activate

# Format code
ruff format .

# Fix linting
ruff check . --fix

# Run tests
pytest

# Type check
mypy src

# Pre-commit checks
pre-commit run --all-files

# Deactivate when done
deactivate
```

## Git Ignore

The `venv/` directory is already in `.gitignore` - it won't be committed.

## CI/CD Still Works

GitHub Actions creates its own virtual environment automatically, so the CI/CD pipeline works regardless of your local setup.

## Alternative: System Packages

If you prefer system packages (not recommended for development):

```bash
# Install with pacman (Arch Linux)
sudo pacman -S python-pytest python-pytest-cov python-pytest-mock
sudo pacman -S python-ruff python-mypy
sudo pacman -S python-pre-commit

# But you'll still need venv for some packages
```

## Troubleshooting

### "pip not found"
- Activate venv: `source venv/bin/activate`
- Recreate venv: `rm -rf venv && ./setup_cicd.sh`

### "pre-commit not found"
- Activate venv first: `source venv/bin/activate`
- Reinstall: `pip install pre-commit && pre-commit install`

### "Module not found" when running tests
- Activate venv: `source venv/bin/activate`
- Reinstall deps: `pip install -r requirements.txt`

## VS Code Integration

Add to `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.terminal.activateEnvironment": true
}
```

VS Code will automatically use and activate the venv.

---

**Remember**: Always `source venv/bin/activate` before working! 🐍
