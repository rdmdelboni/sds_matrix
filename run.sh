#!/bin/bash
# Quick run script - automatically activates venv and runs the app

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: ./setup_cicd.sh first"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import duckdb" 2>/dev/null; then
    echo "⚠️  Dependencies not installed in venv"
    echo "   Installing now..."
    pip install -r requirements.txt -q
fi

# Run the application
echo "🚀 Starting FDS Reader..."
python main.py
