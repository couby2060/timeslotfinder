#!/bin/bash
# Quick installation script for timeslotfinder

echo "🚀 Installing Timeslotfinder..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "📥 Installing dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Activate venv:  source venv/bin/activate"
echo "  2. Test mock mode: python timeslotfinder.py find johannes julia --mock"
echo "  3. See full guide:  cat TEST_MOCK_MODE.md"
echo ""

