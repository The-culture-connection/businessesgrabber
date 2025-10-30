#!/usr/bin/env python3
"""
Final comprehensive scraper that gets ALL businesses
Handles main page + category pages to ensure 534+ businesses
"""

import time
import re
from typing import Dict, List, Set
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalBusinessScraper:
    def __init__(self):
        """Initialize with Chrome WebDriver"""
        logger.info("Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.businesses = []
        self.processed_urls: Set[str] = set()
        self.all_business_urls: Set[str] = set()
        
        logger.info("✅ WebDriver initialized")
    
    def __del__(self):
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass
    
    def scroll_and_load(self, max_scrolls=150):
        """Aggressively scroll to load all content"""
        logger.info("📜 Scrolling to load all content...")
        
        time.sleep(3)
        last_count = 0
        no_change = 0
        
        for scroll in range(max_scrolls):
            # Scroll
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            # Try load more buttons
            try:
                for selector in ["//*[contains(text(), 'Load More')]", "//*[contains(text(), 'Show More')]"]:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    for btn in buttons:
                        try:
                            if btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.info("✓ Clicked load button")
                                time.sleep(2)
                        except:
                            pass
            except:
                pass
            
            # Count links
            links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'black-owned-business/')]")
            unique = set()
            for link in links:
                href = link.get_attribute('href')
                if href and not href.endswith('black-owned-businesses/') and href.count('/') > 4:
                    unique.add(href)
            
            current = len(unique)
            if current == last_count:
                no_change += 1
                if no_change >= 8:
                    break
            else:
                no_change = 0
                last_count = current
                if scroll % 10 == 0:
                    logger.info(f"Scroll {scroll}: {current} links")
        
        logger.info(f"✅ Loaded {last_count} business links")
        return unique
    
    def find_all_business_urls(self, main_url: str) -> Set[str]:
        """Find ALL business URLs from main page and category pages"""
        print("\n" + "=" * 70)
        print("🔍 DISCOVERING ALL BUSINESS URLS")
        print("=" * 70)
        
        all_urls: Set[str] = set()
        
        # Get from main page
        print("\n1️⃣ Loading main directory page...")
        self.driver.get(main_url)
        urls_main = self.scroll_and_load()
        all_urls.update(urls_main)
        print(f"   Found {len(urls_main)} businesses on main page")
        
        # Check for category filters/links
        print("\n2️⃣ Checking for category pages...")
        try:
            category_links = []
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute('href')
                text = link.text.strip()
                # Look for category links
                if href and ('category' in href.lower() or 
                            any(cat in text.lower() for cat in ['restaurant', 'beauty', 'health', 'professional', 'retail'])):
                    if href not in category_links and 'black-owned' in href:
                        category_links.append((href, text))
            
            if category_links:
                print(f"   Found {len(category_links)} potential category pages")
                for i, (url, name) in enumerate(category_links[:10], 1):  # Limit to 10 categories
                    print(f"   Checking category {i}: {name}...")
                    try:
                        self.driver.get(url)
                        urls_cat = self.scroll_and_load(max_scrolls=50)
                        new_urls = urls_cat - all_urls
                        if new_urls:
                            all_urls.update(new_urls)
                            print(f"      +{len(new_urls)} new businesses")
                    except Exception as e:
                        logger.warning(f"Failed to load category {name}: {e}")
            else:
                print("   No category pages found")
        except Exception as e:
            logger.warning(f"Error checking categories: {e}")
        
        print(f"\n✅ Total unique business URLs: {len(all_urls)}")
        return all_urls
    
    def extract_business_data(self, url: str) -> Dict:
        """Extract data from a business page"""
        if url in self.processed_urls:
            return {}
        
        self.processed_urls.add(url)
        
        try:
            self.driver.get(url)
            time.sleep(1.2)
            
            info = {
                'Name': '',
                'Category': '',
                'Description': '',
                'Website': '',
                'Phone': '',
                'Email': '',
                'Address': '',
                'Source_URL': url
            }
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Name
            try:
                h1 = self.driver.find_element(By.TAG_NAME, "h1")
                info['Name'] = h1.text.strip()
            except:
                pass
            
            # Category
            categories = [
                'Restaurants, Eateries and Caterers', 'Professional Services',
                'Beauty and Barber', 'Health and Fitness',
                'Construction and Home Improvement', 'Photography & Videography',
                'Online Retail', 'Retail', 'Night Clubs and Entertainment',
                'Supplies and Services', 'Event Planners and Venues',
                'Daycare/Preschool', 'Education', 'Automotive', 'Real Estate',
                'Financial Services', 'Legal Services', 'Medical Services',
                'Technology', 'Arts and Entertainment', 'Other'
            ]
            for cat in categories:
                if cat in page_text:
                    info['Category'] = cat
                    break
            
            # Description
            try:
                paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
                for p in paragraphs:
                    text = p.text.strip()
                    if len(text) > 50 and not any(skip in text.lower() for skip in 
                        ['post navigation', 'copyright', 'subscribe']):
                        info['Description'] = text[:500] + '...' if len(text) > 500 else text
                        break
            except:
                pass
            
            # Website
            try:
                excluded = ['thevoiceofblackcincinnati', 'facebook', 'instagram', 
                           'twitter', 'linkedin', 'youtube', 'google', 'yelp']
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if href and href.startswith('http'):
                        if not any(ex in href.lower() for ex in excluded):
                            info['Website'] = href
                            break
            except:
                pass
            
            # Phone
            phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', page_text)
            if phone_matches:
                phone = re.sub(r'[^\d]', '', phone_matches[0])
                if len(phone) == 10:
                    info['Phone'] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
            
            # Email
            email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', page_text)
            for email in email_matches:
                if 'thevoiceofblackcincinnati' not in email.lower():
                    info['Email'] = email
                    break
            
            # Address
            addr_patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)',
            ]
            for pattern in addr_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    addr = matches[0].strip()
                    addr = re.sub(r'\s+', ' ', addr)
                    if len(addr) > 10 and not any(skip in addr.lower() for skip in 
                        ['post navigation', 'previous', 'next', 'share']):
                        info['Address'] = addr
                        break
            
            contact = bool(info['Phone'] or info['Email'] or info['Website'])
            logger.info(f"✓ {info.get('Name', 'Unknown')[:35]:35s} | {'Yes' if contact else 'No '}")
            
            return info
        except Exception as e:
            logger.error(f"Error on {url}: {e}")
            return {}
    
    def scrape_all(self, main_url: str):
        """Main scraping method"""
        start_time = datetime.now()
        
        print("\n" + "=" * 70)
        print("        COMPLETE BUSINESS DIRECTORY SCRAPER")
        print("=" * 70)
        print(f"\n🎯 Target: {main_url}")
        print(f"⏰ Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Find all business URLs
        all_urls = self.find_all_business_urls(main_url)
        
        if not all_urls:
            print("\n❌ No businesses found!")
            return []
        
        # Scrape each business
        print("\n" + "=" * 70)
        print("📊 SCRAPING BUSINESS DETAILS")
        print("=" * 70)
        print(f"\nTotal to scrape: {len(all_urls)}")
        print("This will take approximately {:.0f} minutes\n".format(len(all_urls) * 1.5 / 60))
        
        for i, url in enumerate(sorted(all_urls), 1):
            progress = f"[{i}/{len(all_urls)}] ({i*100//len(all_urls)}%)"
            print(f"\r{progress} Scraping...", end='', flush=True)
            
            data = self.extract_business_data(url)
            if data and data.get('Name'):
                self.businesses.append(data)
            
            time.sleep(0.8)
        
        print(f"\n\n✅ Scraping completed!")
        
        elapsed = datetime.now() - start_time
        print(f"⏱️  Time taken: {elapsed}")
        print(f"📊 Businesses scraped: {len(self.businesses)}")
        
        return self.businesses
    
    def export_excel(self, filename="black_owned_businesses_complete.xlsx"):
        """Export to Excel"""
        if not self.businesses:
            print("❌ No data to export")
            return False
        
        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        df = df.drop_duplicates(subset=['Source_URL'], keep='first')
        df = df.drop_duplicates(subset=['Name'], keep='first')
        
        columns = ['Name', 'Category', 'Description', 'Address', 'Phone', 'Email', 'Website', 'Source_URL']
        df = df[columns]
        
        print(f"\n📝 Creating Excel file: {filename}")
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Businesses', index=False)
            
            has_contact = df[(df['Phone'] != '') | (df['Email'] != '') | (df['Website'] != '')]
            if not has_contact.empty:
                has_contact.to_excel(writer, sheet_name='With Contact Info', index=False)
            
            if df['Category'].notna().any():
                for category in df['Category'].unique():
                    if category:
                        cat_df = df[df['Category'] == category]
                        sheet_name = category[:30]
                        cat_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Auto-adjust columns
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_len = 0
                    col_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_len:
                                max_len = len(str(cell.value))
                        except:
                            pass
                    worksheet.column_dimensions[col_letter].width = min(max_len + 2, 60)
        
        print("\n" + "=" * 70)
        print("📊 FINAL SUMMARY")
        print("=" * 70)
        print(f"✅ Exported {len(df)} businesses to: {filename}\n")
        print(f"📈 Statistics:")
        print(f"   Total: {len(df)}")
        print(f"   With phone: {len(df[df['Phone'] != ''])}")
        print(f"   With email: {len(df[df['Email'] != ''])}")
        print(f"   With website: {len(df[df['Website'] != ''])}")
        print(f"   With address: {len(df[df['Address'] != ''])}")
        print(f"   Complete contact: {len(has_contact)}")
        
        if df['Category'].notna().any():
            print(f"\n🏷️  Categories ({len(df['Category'].unique())}):")
            for cat in sorted(df['Category'].unique()):
                if cat:
                    print(f"   - {cat}: {len(df[df['Category'] == cat])}")
        
        print("=" * 70)
        return True

def main():
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    scraper = None
    try:
        scraper = FinalBusinessScraper()
        businesses = scraper.scrape_all(main_url)
        
        if businesses:
            scraper.export_excel()
            print("\n✅ SUCCESS! Check the Excel file.")
        else:
            print("\n❌ No businesses found.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted!")
        if scraper and scraper.businesses:
            print("💾 Saving partial results...")
            scraper.export_excel("black_owned_businesses_partial.xlsx")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        if scraper and scraper.businesses:
            scraper.export_excel("black_owned_businesses_partial.xlsx")
    
    finally:
        if scraper:
            try:
                scraper.driver.quit()
            except:
                pass

if __name__ == "__main__":
    main()
