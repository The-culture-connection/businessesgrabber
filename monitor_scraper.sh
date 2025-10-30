#!/bin/bash
# Monitor the scraper progress

echo "========================================================================"
echo "                    SCRAPER PROGRESS MONITOR"
echo "========================================================================"
echo ""

# Check if scraper is running
if ps -p $(cat /tmp/scraper_pid 2>/dev/null) > /dev/null 2>&1; then
    echo "✓ Scraper is RUNNING (PID: $(cat /tmp/scraper_pid))"
else
    if pgrep -f "final_scraper.py" > /dev/null; then
        echo "✓ Scraper is RUNNING"
    else
        echo "✗ Scraper is NOT running"
    fi
fi

echo ""
echo "--- Latest Log Output (last 20 lines) ---"
tail -20 /workspace/scraper_full_output.log 2>/dev/null || echo "No log file yet"

echo ""
echo "--- Excel Files Created ---"
ls -lh /workspace/black_owned_businesses_complete_*.xlsx 2>/dev/null || echo "No Excel files yet"

echo ""
echo "--- Quick Stats from Latest Excel ---"
if ls /workspace/black_owned_businesses_complete_*.xlsx 1> /dev/null 2>&1; then
    latest_excel=$(ls -t /workspace/black_owned_businesses_complete_*.xlsx | head -1)
    echo "Latest file: $latest_excel"
    python3 << EOF
import pandas as pd
try:
    df = pd.read_excel("$latest_excel", sheet_name="All Businesses")
    print(f"Total businesses in Excel: {len(df)}")
    print(f"With email: {df['Email'].notna().sum()}")
    print(f"With phone: {df['Phone'].notna().sum()}")
    print(f"With address: {df['Address'].notna().sum()}")
except Exception as e:
    print(f"Could not read Excel: {e}")
EOF
else
    echo "No Excel file found yet"
fi

echo ""
echo "========================================================================"
