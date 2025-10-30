#!/bin/bash
# Run the complete scraper and monitor

echo "=================================="
echo "  STARTING COMPLETE SCRAPER"
echo "=================================="
echo ""
echo "This will take 20-40 minutes to complete"
echo "The scraper will:"
echo "  1. Find all business links (~461+)"
echo "  2. Visit each business page"
echo "  3. Extract all details (name, address, phone, email, website)"
echo "  4. Export to Excel"
echo ""
echo "Press Ctrl+C at any time to save partial results"
echo ""
echo "=================================="
echo ""

# Run the scraper
python3 /workspace/improved_selenium_scraper.py

echo ""
echo "=================================="
echo "  SCRAPING COMPLETE"
echo "=================================="
echo ""

# Check if file was created
if [ -f "black_owned_businesses_complete.xlsx" ]; then
    echo "✅ Excel file created successfully!"
    echo ""
    ls -lh black_owned_businesses_complete.xlsx
    echo ""
    echo "Open the file to view all scraped businesses"
else
    echo "⚠️  No Excel file found"
fi
