#!/bin/bash
# Setup script to install dependencies and run the scraper

echo "=================================="
echo "  BUSINESS SCRAPER SETUP"
echo "=================================="
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -q requests beautifulsoup4 pandas openpyxl lxml selenium webdriver-manager

# Check if Chrome/Chromium is installed
echo ""
echo "🔍 Checking for Chrome/Chromium..."
if command -v google-chrome &> /dev/null; then
    echo "✅ Google Chrome found"
    CHROME_VERSION=$(google-chrome --version)
    echo "   Version: $CHROME_VERSION"
elif command -v chromium &> /dev/null; then
    echo "✅ Chromium found"
    CHROME_VERSION=$(chromium --version)
    echo "   Version: $CHROME_VERSION"
elif command -v chromium-browser &> /dev/null; then
    echo "✅ Chromium browser found"
    CHROME_VERSION=$(chromium-browser --version)
    echo "   Version: $CHROME_VERSION"
else
    echo "⚠️  Chrome/Chromium not found. Installing..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq chromium-browser chromium-chromedriver
fi

echo ""
echo "=================================="
echo "  READY TO SCRAPE!"
echo "=================================="
echo ""
echo "To run the scraper:"
echo "  python3 selenium_complete_scraper.py"
echo ""
echo "To monitor the Excel file in real-time (in another terminal):"
echo "  python3 monitor_excel.py"
echo ""
