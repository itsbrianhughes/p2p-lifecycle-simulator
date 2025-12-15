#!/bin/bash

# ============================================================================
# P2P Lifecycle Simulator - Quick Start Script
# ============================================================================
#
# This script:
# 1. Checks for Python 3.10+
# 2. Creates virtual environment if needed
# 3. Installs dependencies
# 4. Runs the application
#
# Usage:
#   ./run.sh
#
# ============================================================================

set -e  # Exit on error

echo ""
echo "============================================================"
echo "P2P LIFECYCLE SIMULATOR - QUICK START"
echo "============================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Run the application
echo ""
echo "============================================================"
echo "STARTING APPLICATION"
echo "============================================================"
echo ""
echo "Frontend: http://localhost:8000/"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python backend/main.py
