#!/usr/bin/env python3
"""
Improved business scraper with automatic ChromeDriver management
Uses webdriver-manager to automatically download and manage ChromeDriver
"""

import time
import re
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImprovedBusinessScraper:
    def __init__(self):
        """Initialize the scraper with automatic driver management"""
        logger.info("Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Try to use system ChromeDriver first (more reliable)
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ Using system ChromeDriver")
        except Exception as e:
            logger.warning(f"System ChromeDriver failed: {e}")
            logger.info("Trying webdriver-manager...")
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("✅ Using webdriver-manager ChromeDriver")
            except Exception as e2:
                logger.error(f"Both methods failed: {e2}")
                raise
        
        self.driver.implicitly_wait(10)
        self.businesses = []
        self.processed_urls = set()
        
        logger.info("✅ WebDriver initialized successfully")
    
    def __del__(self):
        """Clean up the driver"""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass
    
    def scroll_to_load_all(self):
        """Scroll the page to trigger lazy loading of all content"""
        logger.info("📜 Scrolling to load all businesses...")
        
        # Initial wait for page to load
        time.sleep(3)
        
        last_count = 0
        no_change_count = 0
        scroll_count = 0
        max_scrolls = 150  # Increased to ensure we get everything
        
        while scroll_count < max_scrolls:
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            # Also try scrolling to specific positions to trigger lazy loading
            if scroll_count % 3 == 0:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(0.5)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            # Try clicking "Load More" buttons aggressively
            try:
                load_more_selectors = [
                    "//*[contains(text(), 'Load More')]",
                    "//*[contains(text(), 'Show More')]",
                    "//*[contains(text(), 'View More')]",
                    "//button[contains(@class, 'load-more')]",
                    "//a[contains(@class, 'load-more')]",
                    "//button[contains(text(), 'More')]",
                ]
                for selector in load_more_selectors:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        try:
                            if button.is_displayed():
                                self.driver.execute_script("arguments[0].click();", button)
                                logger.info("Clicked 'Load More' button")
                                time.sleep(2)
                        except:
                            pass
            except:
                pass
            
            # Count current unique business links
            try:
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'black-owned-business/')]")
                unique_links = set()
                for link in links:
                    href = link.get_attribute('href')
                    if href and not href.endswith('black-owned-businesses/'):
                        if href.count('/') > 4:
                            unique_links.add(href)
                
                current_count = len(unique_links)
                
                if current_count == last_count:
                    no_change_count += 1
                    if no_change_count >= 8:  # Increased threshold
                        logger.info(f"No new content after {scroll_count} scrolls, found {current_count} links")
                        break
                else:
                    no_change_count = 0
                    last_count = current_count
                
                # Log progress
                if scroll_count % 5 == 0 or current_count > last_count:
                    logger.info(f"Scroll {scroll_count}: Found {current_count} unique business links")
            except:
                pass
            
            scroll_count += 1
        
        logger.info(f"✅ Finished scrolling after {scroll_count} scrolls")
    
    def find_all_business_links(self, main_url: str) -> List[str]:
        """Find all business links on the page"""
        logger.info(f"🌐 Loading main page: {main_url}")
        self.driver.get(main_url)
        
        # Scroll to load all content
        self.scroll_to_load_all()
        
        # Extract all unique business links
        business_links = set()
        
        try:
            # Method 1: Find all links containing 'black-owned-business/'
            all_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'black-owned-business/')]")
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        # Filter out the main directory page itself
                        if 'black-owned-business/' in href and not href.endswith('black-owned-businesses/'):
                            # Ensure it's a specific business page (contains more than just the base path)
                            if href.count('/') > 4:  # Has a specific business slug
                                business_links.add(href)
                except:
                    continue
            
            logger.info(f"✅ Found {len(business_links)} unique business links")
            
        except Exception as e:
            logger.error(f"Error finding business links: {e}")
        
        return sorted(list(business_links))
    
    def extract_business_info(self, business_url: str) -> Dict[str, str]:
        """Extract detailed information from a business page"""
        if business_url in self.processed_urls:
            return {}
        
        self.processed_urls.add(business_url)
        
        try:
            self.driver.get(business_url)
            time.sleep(1.5)
            
            business_info = {
                'Name': '',
                'Category': '',
                'Description': '',
                'Website': '',
                'Phone': '',
                'Email': '',
                'Address': '',
                'Source_URL': business_url
            }
            
            # Get page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Extract business name
            try:
                name_elem = self.driver.find_element(By.TAG_NAME, "h1")
                name = name_elem.text.strip()
                if name and len(name) > 2:
                    business_info['Name'] = name
            except:
                # Fallback to title
                try:
                    title = self.driver.title
                    if title and '|' in title:
                        name = title.split('|')[0].strip()
                        if name:
                            business_info['Name'] = name
                except:
                    pass
            
            # Extract category
            category_patterns = [
                'Restaurants, Eateries and Caterers',
                'Professional Services',
                'Beauty and Barber',
                'Health and Fitness',
                'Construction and Home Improvement',
                'Photography & Videography',
                'Online Retail',
                'Retail',
                'Night Clubs and Entertainment',
                'Supplies and Services',
                'Event Planners and Venues',
                'Daycare/Preschool',
                'Education',
                'Automotive',
                'Real Estate',
                'Financial Services',
                'Legal Services',
                'Medical Services',
                'Technology',
                'Arts and Entertainment',
                'Other'
            ]
            
            for pattern in category_patterns:
                if pattern in page_text:
                    business_info['Category'] = pattern
                    break
            
            # Extract description - look for paragraphs
            try:
                paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
                for p in paragraphs:
                    text = p.text.strip()
                    # Look for meaningful description (not navigation text)
                    if len(text) > 50 and not any(skip in text.lower() for skip in 
                        ['post navigation', 'copyright', 'all rights reserved', 'subscribe']):
                        business_info['Description'] = text[:500] + '...' if len(text) > 500 else text
                        break
            except:
                pass
            
            # Extract website - look for external links
            try:
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                excluded_domains = [
                    'thevoiceofblackcincinnati.com', 'voiceofblackcincinnati.com',
                    'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
                    'youtube.com', 'mailchi.mp', 'list-manage.com', 'google.com',
                    'yelp.com'
                ]
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        if href and href.startswith('http'):
                            # Check if it's not an excluded domain
                            if not any(domain in href.lower() for domain in excluded_domains):
                                # Additional check: make sure it looks like a business website
                                if '.' in href and len(href) > 10:
                                    business_info['Website'] = href
                                    break
                    except:
                        continue
            except:
                pass
            
            # Extract phone number
            phone_patterns = [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    phone = re.sub(r'[^\d]', '', matches[0])
                    if len(phone) == 10:
                        business_info['Phone'] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                        break
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, page_text)
            # Filter out generic emails
            generic_emails = ['info@thevoiceofblackcincinnati', 'support@', 'noreply@']
            for email in email_matches:
                if not any(generic in email.lower() for generic in generic_emails):
                    business_info['Email'] = email
                    break
            
            # Extract address
            address_patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)(?:,?\s*[A-Za-z\s]+,?\s*(?:OH|Ohio)?\s*\d{5})?',
                r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*(?:OH|Ohio)\s*\d{5}',
            ]
            
            for pattern in address_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    address = matches[0].strip()
                    address = re.sub(r'\s+', ' ', address)
                    # Clean up false positives
                    skip_words = ['post navigation', 'previous business', 'next business', 'share this', 'tech view']
                    if not any(word in address.lower() for word in skip_words):
                        if len(address) > 10:  # Sanity check
                            business_info['Address'] = address
                            break
            
            # Log what we found
            has_contact = bool(business_info['Phone'] or business_info['Email'] or business_info['Website'])
            logger.info(f"✓ {business_info.get('Name', 'Unknown')[:40]:40s} | Contact: {'Yes' if has_contact else 'No '}")
            
            return business_info
            
        except Exception as e:
            logger.error(f"Error extracting info from {business_url}: {e}")
            return {}
    
    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main scraping method"""
        print("\n" + "=" * 70)
        print("🚀 STARTING COMPLETE BUSINESS SCRAPING")
        print("=" * 70)
        
        # Find all business links
        business_links = self.find_all_business_links(main_url)
        
        if not business_links:
            logger.error("❌ No business links found!")
            return []
        
        total = len(business_links)
        print(f"\n📊 Found {total} businesses to scrape")
        print("=" * 70)
        
        # Scrape each business
        for i, business_url in enumerate(business_links, 1):
            progress = f"[{i}/{total}] ({i*100//total}%)"
            print(f"\r{progress} Scraping businesses...", end='', flush=True)
            
            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)
            
            time.sleep(0.8)  # Be respectful to the server
        
        print(f"\n\n✅ Scraping completed! Found {len(self.businesses)} businesses")
        return self.businesses
    
    def export_to_excel(self, filename: str = "black_owned_businesses_complete.xlsx"):
        """Export data to Excel with multiple sheets"""
        if not self.businesses:
            print("❌ No businesses to export")
            return False
        
        try:
            df = pd.DataFrame(self.businesses)
            df = df.fillna('')
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['Source_URL'], keep='first')
            df = df.drop_duplicates(subset=['Name'], keep='first')
            
            # Reorder columns
            columns = ['Name', 'Category', 'Description', 'Address', 'Phone', 'Email', 'Website', 'Source_URL']
            df = df[columns]
            
            # Create Excel file
            print(f"\n📝 Creating Excel file: {filename}")
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main sheet
                df.to_excel(writer, sheet_name='All Businesses', index=False)
                
                # Sheet with contact info
                has_contact = df[(df['Phone'] != '') | (df['Email'] != '') | (df['Website'] != '')]
                if not has_contact.empty:
                    has_contact.to_excel(writer, sheet_name='With Contact Info', index=False)
                
                # Sheets by category
                if df['Category'].notna().any():
                    for category in df['Category'].unique():
                        if category and category != '':
                            cat_df = df[df['Category'] == category]
                            sheet_name = category[:30]
                            cat_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                cell_length = len(str(cell.value))
                                if cell_length > max_length:
                                    max_length = cell_length
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 60)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Print summary
            print("\n" + "=" * 70)
            print("📊 EXPORT SUMMARY")
            print("=" * 70)
            print(f"✅ Exported {len(df)} businesses to: {filename}")
            print(f"\n📈 Data Statistics:")
            print(f"   Total businesses: {len(df)}")
            print(f"   With phone: {len(df[df['Phone'] != ''])}")
            print(f"   With email: {len(df[df['Email'] != ''])}")
            print(f"   With website: {len(df[df['Website'] != ''])}")
            print(f"   With address: {len(df[df['Address'] != ''])}")
            print(f"   Complete contact (phone/email/website): {len(has_contact)}")
            
            if df['Category'].notna().any():
                print(f"\n🏷️  Categories ({len(df['Category'].unique())} total):")
                for category in sorted(df['Category'].unique()):
                    if category:
                        count = len(df[df['Category'] == category])
                        print(f"   - {category}: {count}")
            
            print("=" * 70)
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            print(f"❌ Error exporting: {e}")
            return False

def main():
    """Main function"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    print("\n" + "=" * 70)
    print("        BLACK-OWNED BUSINESSES COMPLETE SCRAPER")
    print("=" * 70)
    print(f"\n🎯 Target: {main_url}")
    print("\n📋 What this scraper does:")
    print("  ✓ Loads ALL businesses (including dynamically loaded content)")
    print("  ✓ Extracts: Name, Category, Description, Address, Phone, Email, Website")
    print("  ✓ Exports to Excel with multiple organized sheets")
    print("  ✓ Shows real-time progress")
    print("\n⏱️  Estimated time: 20-40 minutes")
    print("=" * 70)
    
    scraper = None
    try:
        scraper = ImprovedBusinessScraper()
        businesses = scraper.scrape_all_businesses(main_url)
        
        if businesses:
            scraper.export_to_excel()
            print("\n✅ SUCCESS! Check the Excel file for all scraped data.")
        else:
            print("\n❌ No businesses found. Please check your internet connection.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        if scraper and scraper.businesses:
            print("💾 Saving partial results...")
            scraper.export_to_excel("black_owned_businesses_partial.xlsx")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        if scraper and scraper.businesses:
            print("💾 Attempting to save partial results...")
            scraper.export_to_excel("black_owned_businesses_partial.xlsx")
    
    finally:
        if scraper:
            try:
                scraper.driver.quit()
            except:
                pass

if __name__ == "__main__":
    main()
