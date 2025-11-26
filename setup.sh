#!/bin/bash
# SoftLight Setup Script
# Automates the installation process

set -e  # Exit on error

echo "🚀 SoftLight Setup Script"
echo "========================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  venv directory already exists, skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ Pip upgraded"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
echo "(This may take a few minutes...)"
pip install -r requirements.txt --quiet
echo "✅ Python dependencies installed"
echo ""

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium
echo "✅ Playwright browsers installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY=your_key_here"
    echo "   - Optionally: ANTHROPIC_API_KEY, app credentials"
else
    echo "✅ .env file already exists"
fi
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p dataset
mkdir -p logs
echo "✅ Directories created"
echo ""

# Test installation
echo "Testing installation..."
if python src/main.py --list-apps > /dev/null 2>&1; then
    echo "✅ Installation test passed"
else
    echo "⚠️  Warning: Test command failed, but installation completed"
    echo "   Make sure to add your API key to .env"
fi
echo ""

# Summary
echo "========================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   nano .env"
echo ""
echo "2. Activate the virtual environment (in new terminals):"
echo "   source venv/bin/activate"
echo ""
echo "3. Try a test command:"
echo "   python src/main.py --list-apps"
echo ""
echo "4. Run your first workflow:"
echo "   python src/main.py --app linear --task \"View projects page\" --max-steps 3"
echo ""
echo "📚 See SETUP_GUIDE.md for detailed instructions"
echo "========================"

