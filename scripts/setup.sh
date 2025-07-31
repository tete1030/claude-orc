#!/bin/bash
# Setup script for Claude Multi-Agent Orchestrator

set -e

echo "Setting up Claude Multi-Agent Orchestrator..."

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "Error: Please run this script from the orchestrator directory"
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p config
mkdir -p examples

# Install in development mode
echo "Installing orchestrator in development mode..."
pip install -e .

# Install test dependencies
echo "Installing test dependencies..."
pip install pytest pytest-mock

echo ""
echo "Setup complete!"
echo ""
echo "Quick start:"
echo "1. Create a Python script to configure and start the orchestrator"
echo "2. Or run the example: python examples/basic_two_agent.py"
echo ""
echo "To run tests:"
echo "  python -m pytest tests/"
echo ""