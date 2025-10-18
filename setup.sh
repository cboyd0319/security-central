#!/bin/bash
# Quick setup script for security-central

set -e

echo "================================"
echo "  security-central Setup"
echo "================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install Python 3.12+"
    exit 1
fi
echo "✅ Python $(python3 --version)"

if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI not found. Install from https://cli.github.com"
    exit 1
fi
echo "✅ GitHub CLI $(gh --version | head -1)"

if ! command -v git &> /dev/null; then
    echo "❌ Git not found"
    exit 1
fi
echo "✅ Git $(git --version)"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if authenticated with GitHub
echo ""
echo "Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo "⚠️  Not authenticated with GitHub"
    echo "   Run: gh auth login"
    exit 1
fi
echo "✅ GitHub authenticated"

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p repos
mkdir -p docs/reports/daily
mkdir -p docs/reports/weekly
mkdir -p docs/reports/housekeeping
echo "✅ Directories created"

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x scripts/*.py
chmod +x scripts/housekeeping/*.py
chmod +x setup.sh
echo "✅ Scripts are executable"

# Verify configuration
echo ""
echo "Checking configuration..."
if [ ! -f "config/repos.yml" ]; then
    echo "❌ config/repos.yml not found"
    exit 1
fi
echo "✅ Configuration files present"

# Summary
echo ""
echo "================================"
echo "  Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your repositories:"
echo "   Edit config/repos.yml"
echo ""
echo "2. Set GitHub secrets:"
echo "   gh secret set REPO_ACCESS_TOKEN"
echo "   gh secret set SLACK_SECURITY_WEBHOOK (optional)"
echo ""
echo "3. Test the scanner:"
echo "   python3 scripts/clone_repos.py"
echo "   python3 scripts/scan_all_repos.py"
echo ""
echo "4. Push to GitHub to enable workflows:"
echo "   git add ."
echo "   git commit -m 'chore: initial setup'"
echo "   git push origin main"
echo ""
echo "5. Before vacation, run:"
echo "   python3 scripts/pre_vacation_hardening.py"
echo ""
echo "Full docs: docs/SETUP.md"
