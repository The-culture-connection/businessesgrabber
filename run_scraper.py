#!/usr/bin/env python3
"""
Simple script to run the business scraper
"""

import sys
import os

def install_requirements():
    """Install required packages"""
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False
    return True

def main():
    print("🔧 Business Directory Scraper")
    print("=" * 40)
    
    # Check if requirements are installed
    try:
        import requests
        import bs4
        import pandas
        import openpyxl
        print("✅ All required packages are available")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Installing requirements...")
        if not install_requirements():
            print("Please install requirements manually: pip install -r requirements.txt")
            return
    
    # Ask user which scraper to use
    print("\nChoose scraper version:")
    print("1. Basic scraper (follows individual business links)")
    print("2. Enhanced scraper (extracts from main page cards)")
    print("3. Targeted scraper (extracts 'Read More' links + detailed contact info)")
    print("4. Debug scraper (analyze website structure)")
    
    choice = input("Enter choice (1, 2, 3, or 4): ").strip()
    
    if choice == "1":
        print("\n🚀 Running basic scraper...")
        from business_scraper import main as run_basic_scraper
        run_basic_scraper()
    elif choice == "2":
        print("\n🚀 Running enhanced scraper...")
        from enhanced_business_scraper import main as run_enhanced_scraper
        run_enhanced_scraper()
    elif choice == "3":
        print("\n🚀 Running targeted scraper...")
        from targeted_business_scraper import main as run_targeted_scraper
        run_targeted_scraper()
    elif choice == "4":
        print("\n🐛 Running debug scraper...")
        from debug_scraper import main as run_debug_scraper
        run_debug_scraper()
    else:
        print("❌ Invalid choice. Please run again and choose 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
