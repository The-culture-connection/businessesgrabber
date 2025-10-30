#!/usr/bin/env python3
"""
Test script to verify Selenium setup
"""

print("=" * 70)
print("  SELENIUM SETUP TEST")
print("=" * 70)
print()

# Test 1: Import required modules
print("1️⃣  Testing imports...")
try:
    import selenium
    print(f"   ✅ Selenium {selenium.__version__} installed")
except ImportError as e:
    print(f"   ❌ Selenium not installed: {e}")
    print("   Install with: pip install selenium")
    exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    print("   ✅ webdriver-manager installed")
except ImportError:
    print("   ⚠️  webdriver-manager not installed (optional)")
    print("   Install with: pip install webdriver-manager")

try:
    import pandas
    print(f"   ✅ pandas installed")
except ImportError as e:
    print(f"   ❌ pandas not installed: {e}")
    exit(1)

print()

# Test 2: Check for Chrome
print("2️⃣  Checking for Chrome/Chromium...")
import subprocess
import shutil

chrome_found = False
chrome_binary = None

for cmd in ['google-chrome', 'chromium', 'chromium-browser', 'chrome']:
    binary_path = shutil.which(cmd)
    if binary_path:
        chrome_found = True
        chrome_binary = binary_path
        try:
            version_output = subprocess.check_output([cmd, '--version'], stderr=subprocess.STDOUT, text=True)
            print(f"   ✅ Found: {version_output.strip()}")
            print(f"   Location: {binary_path}")
            break
        except:
            print(f"   ✅ Found at: {binary_path}")
            break

if not chrome_found:
    print("   ❌ Chrome/Chromium not found")
    print("   Install with: sudo apt-get install chromium-browser chromium-chromedriver")
    print()
    print("=" * 70)
    print("SETUP INCOMPLETE - Install Chrome/Chromium to continue")
    print("=" * 70)
    exit(1)

print()

# Test 3: Try to initialize WebDriver
print("3️⃣  Testing WebDriver initialization...")
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Try with webdriver-manager first
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("   Attempting with webdriver-manager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("   ✅ WebDriver initialized successfully with webdriver-manager!")
    except Exception as e:
        print(f"   ⚠️  webdriver-manager failed: {e}")
        print("   Attempting with system ChromeDriver...")
        driver = webdriver.Chrome(options=options)
        print("   ✅ WebDriver initialized successfully with system ChromeDriver!")
    
    # Test basic functionality
    print("   Testing basic navigation...")
    driver.get("https://www.example.com")
    title = driver.title
    print(f"   ✅ Successfully loaded page: {title}")
    
    driver.quit()
    print()
    
except Exception as e:
    print(f"   ❌ WebDriver initialization failed: {e}")
    print()
    print("=" * 70)
    print("POSSIBLE SOLUTIONS:")
    print("=" * 70)
    print("1. Install ChromeDriver:")
    print("   sudo apt-get install chromium-chromedriver")
    print()
    print("2. Or use webdriver-manager:")
    print("   pip install webdriver-manager")
    print()
    exit(1)

# Success!
print("=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print()
print("🚀 You're ready to run the scraper:")
print("   python3 improved_selenium_scraper.py")
print()
print("📊 To monitor progress in real-time:")
print("   python3 monitor_excel.py")
print()
