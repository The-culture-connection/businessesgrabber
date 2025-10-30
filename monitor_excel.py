#!/usr/bin/env python3
"""
Monitor the Excel file as it's being created and updated
Shows real-time statistics about the scraping progress
"""

import os
import time
import pandas as pd
from datetime import datetime
import sys

def format_size(bytes):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0

def monitor_excel_file(filename="black_owned_businesses_complete.xlsx", check_interval=5):
    """Monitor an Excel file and display statistics"""
    print("=" * 70)
    print("📊 EXCEL FILE MONITOR")
    print("=" * 70)
    print(f"Monitoring file: {filename}")
    print(f"Check interval: {check_interval} seconds")
    print("Press Ctrl+C to stop monitoring")
    print("=" * 70)
    print()
    
    last_modified = None
    last_size = 0
    
    try:
        while True:
            if os.path.exists(filename):
                # Get file stats
                stats = os.stat(filename)
                current_size = stats.st_size
                current_modified = stats.st_mtime
                
                # Check if file has been modified
                if current_modified != last_modified:
                    modification_time = datetime.fromtimestamp(current_modified).strftime('%Y-%m-%d %H:%M:%S')
                    
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 File updated!")
                    print(f"   Last modified: {modification_time}")
                    print(f"   File size: {format_size(current_size)}")
                    
                    if current_size > last_size:
                        size_increase = current_size - last_size
                        print(f"   Size increased by: {format_size(size_increase)}")
                    
                    # Try to read the Excel file
                    try:
                        df = pd.read_excel(filename, sheet_name='All Businesses', engine='openpyxl')
                        print(f"\n   📈 Data Statistics:")
                        print(f"      Total businesses: {len(df)}")
                        print(f"      With phone: {len(df[df['Phone'].notna() & (df['Phone'] != '')])}")
                        print(f"      With email: {len(df[df['Email'].notna() & (df['Email'] != '')])}")
                        print(f"      With website: {len(df[df['Website'].notna() & (df['Website'] != '')])}")
                        print(f"      With address: {len(df[df['Address'].notna() & (df['Address'] != '')])}")
                        
                        # Show category breakdown
                        if 'Category' in df.columns:
                            categories = df['Category'].value_counts()
                            if len(categories) > 0:
                                print(f"\n   🏷️  Top Categories:")
                                for cat, count in categories.head(5).items():
                                    if cat and cat != '':
                                        print(f"      - {cat}: {count}")
                        
                        # Show latest businesses added
                        if len(df) > 0:
                            print(f"\n   📝 Latest businesses:")
                            for idx in range(min(3, len(df))):
                                name = df.iloc[-(idx+1)]['Name']
                                category = df.iloc[-(idx+1)].get('Category', 'N/A')
                                print(f"      {len(df)-idx}. {name} ({category})")
                    
                    except Exception as e:
                        print(f"   ⚠️  Could not read Excel data: {e}")
                    
                    last_modified = current_modified
                    last_size = current_size
                    print()
                    print("-" * 70)
                
                else:
                    # File exists but hasn't changed
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ No changes... (Size: {format_size(current_size)})", end='\r')
            
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Waiting for file to be created...", end='\r')
            
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped by user")
        if os.path.exists(filename):
            try:
                df = pd.read_excel(filename, sheet_name='All Businesses', engine='openpyxl')
                print(f"\n📊 Final Statistics:")
                print(f"   Total businesses: {len(df)}")
                print(f"   File size: {format_size(os.path.getsize(filename))}")
            except:
                pass

def main():
    """Main function"""
    filename = "black_owned_businesses_complete.xlsx"
    
    # Check for command line argument
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    monitor_excel_file(filename)

if __name__ == "__main__":
    main()
