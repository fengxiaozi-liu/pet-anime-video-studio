#!/bin/bash
# Test runner script for pet-anime-video backend
set -e

echo "🧪 Running Pet Anime Video Backend Tests"
echo "========================================="
echo ""

cd "$(dirname "$0")"

# Check if venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip -q
    pip install pytest pytest-cov pydantic fastapi uvicorn httpx -q
else
    echo "📦 Using existing virtual environment..."
    source .venv/bin/activate
fi

# Run tests with coverage
echo ""
echo "▶️  Running tests..."
pytest tests/ \
    -v \
    --tb=short \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:../front/htmlcov \
    $@

echo ""
echo "✅ Tests complete!"
echo "📊 Coverage report: ../front/htmlcov/index.html"
