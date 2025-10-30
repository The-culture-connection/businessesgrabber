#!/usr/bin/env python3
"""
Quick test to verify the scraper can find all business links
This doesn't scrape details, just counts the links to verify we can get 534+
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def quick_test():
    print("\n" + "=" * 70)
    print("  QUICK LINK COUNT TEST")
    print("=" * 70)
    print("\nThis will:")
    print("  1. Load the main business directory page")
    print("  2. Scroll to load all dynamic content")
    print("  3. Count total unique business links found")
    print("  4. Report if we can reach 534+ businesses")
    print("\nEstimated time: 3-5 minutes")
    print("=" * 70)
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
        
        print(f"\n🌐 Loading: {main_url}")
        driver.get(main_url)
        time.sleep(3)
        
        print("\n📜 Scrolling to load all content...")
        last_count = 0
        no_change = 0
        scroll = 0
        max_scrolls = 100
        
        while scroll < max_scrolls:
            # Scroll
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Try clicking "Load More" buttons
            try:
                buttons = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Load More') or contains(text(), 'Show More')]")
                for btn in buttons:
                    try:
                        if btn.is_displayed():
                            btn.click()
                            print("   Clicked 'Load More' button")
                            time.sleep(2)
                    except:
                        pass
            except:
                pass
            
            # Count links
            links = driver.find_elements(By.XPATH, "//a[contains(@href, 'black-owned-business/')]")
            unique_links = set()
            for link in links:
                href = link.get_attribute('href')
                if href and not href.endswith('black-owned-businesses/'):
                    if href.count('/') > 4:  # Has a specific business slug
                        unique_links.add(href)
            
            current_count = len(unique_links)
            
            if current_count == last_count:
                no_change += 1
                if no_change >= 5:
                    print(f"   No new content after {scroll} scrolls")
                    break
            else:
                no_change = 0
                last_count = current_count
                if scroll % 5 == 0 or current_count != last_count:
                    print(f"   Scroll {scroll}: Found {current_count} unique business links")
            
            scroll += 1
        
        # Final count
        print("\n" + "=" * 70)
        print("📊 RESULTS")
        print("=" * 70)
        print(f"✅ Total unique business links found: {len(unique_links)}")
        
        if len(unique_links) >= 534:
            print(f"🎉 SUCCESS! Found {len(unique_links)} businesses (target: 534+)")
            print("   The scraper should capture all businesses.")
        elif len(unique_links) >= 400:
            print(f"⚠️  Found {len(unique_links)} businesses (target: 534+)")
            print("   This is close but may need more scrolling/loading time.")
        else:
            print(f"❌ Only found {len(unique_links)} businesses (target: 534+)")
            print("   The page may need different loading strategy.")
        
        print("\n📝 Sample business URLs (first 5):")
        for i, url in enumerate(sorted(unique_links)[:5], 1):
            business_name = url.split('/')[-2].replace('-', ' ').title()
            print(f"   {i}. {business_name}")
        
        print("\n" + "=" * 70)
        
        return len(unique_links)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    try:
        count = quick_test()
        print(f"\n{'✅' if count >= 534 else '⚠️'} Ready to run full scraper: python3 improved_selenium_scraper.py\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
