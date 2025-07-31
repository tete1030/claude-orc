#!/bin/bash
# Run all tests for the orchestrator

set -e

echo "Running Claude Multi-Agent Orchestrator tests..."
echo ""

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "Error: Please run this script from the orchestrator directory"
    exit 1
fi

# Run unit tests
echo "=== Running Unit Tests ==="
python -m pytest tests/unit/ -v

echo ""
echo "=== Running Integration Tests ==="
python -m pytest tests/integration/ -v

echo ""
echo "=== Running All Tests with Coverage ==="
python -m pytest tests/ -v --cov=orchestrator --cov-report=term-missing

echo ""
echo "All tests completed!"