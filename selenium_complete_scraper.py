#!/usr/bin/env python3
"""
Complete business scraper using Selenium to handle dynamic content
This version will capture ALL 534+ businesses from the directory
"""

import time
import re
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SeleniumBusinessScraper:
    def __init__(self):
        """Initialize the scraper with Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.businesses = []
        self.processed_urls = set()
        
    def __del__(self):
        """Clean up the driver"""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def scroll_to_load_all(self):
        """Scroll the page to trigger lazy loading of all content"""
        logger.info("Scrolling to load all content...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_attempts = 50
        
        while scroll_attempts < max_attempts:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # Try a few more times to be sure
                scroll_attempts += 1
                if scroll_attempts >= 3:
                    break
            else:
                scroll_attempts = 0  # Reset if we found more content
            
            last_height = new_height
            
            # Count current businesses
            try:
                business_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'black-owned-business/')]")
                unique_links = set([link.get_attribute('href') for link in business_links if link.get_attribute('href')])
                logger.info(f"Found {len(unique_links)} unique business links so far...")
            except:
                pass
        
        logger.info("Finished scrolling")
    
    def find_all_business_links(self, main_url: str) -> List[str]:
        """Find all business links on the page"""
        logger.info(f"Loading main page: {main_url}")
        self.driver.get(main_url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Scroll to load all content
        self.scroll_to_load_all()
        
        # Find all business links
        business_links = set()
        
        try:
            # Find all links that point to individual business pages
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if href and 'black-owned-business/' in href and href not in business_links:
                        # Make sure it's not the main directory page
                        if href != main_url and not href.endswith('black-owned-businesses/'):
                            business_links.add(href)
                except:
                    continue
            
            logger.info(f"Found {len(business_links)} unique business links")
            
        except Exception as e:
            logger.error(f"Error finding business links: {e}")
        
        return list(business_links)
    
    def extract_business_info(self, business_url: str) -> Dict[str, str]:
        """Extract detailed information from a business page"""
        if business_url in self.processed_urls:
            return {}
        
        self.processed_urls.add(business_url)
        
        logger.info(f"Extracting info from: {business_url}")
        
        try:
            self.driver.get(business_url)
            time.sleep(2)  # Wait for page to load
            
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
            
            # Get page source for text extraction
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Extract business name from title or h1
            try:
                name_elem = self.driver.find_element(By.TAG_NAME, "h1")
                business_info['Name'] = name_elem.text.strip()
            except:
                try:
                    business_info['Name'] = self.driver.title.split('|')[0].strip()
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
                'Other'
            ]
            
            for pattern in category_patterns:
                if pattern in page_text:
                    business_info['Category'] = pattern
                    break
            
            # Extract description
            try:
                desc_elements = self.driver.find_elements(By.TAG_NAME, "p")
                for elem in desc_elements:
                    text = elem.text.strip()
                    if len(text) > 50:
                        business_info['Description'] = text[:500] + '...' if len(text) > 500 else text
                        break
            except:
                pass
            
            # Extract website (exclude social media and the voice site itself)
            try:
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                excluded_domains = [
                    'thevoiceofblackcincinnati.com', 'voiceofblackcincinnati.com',
                    'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
                    'youtube.com', 'mailchi.mp', 'list-manage.com'
                ]
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        if href and href.startswith('http'):
                            if not any(domain in href.lower() for domain in excluded_domains):
                                business_info['Website'] = href
                                break
                    except:
                        continue
            except:
                pass
            
            # Extract phone number
            phone_patterns = [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
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
            if email_matches:
                business_info['Email'] = email_matches[0]
            
            # Extract address
            address_patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)(?:,?\s*[A-Za-z\s]+,?\s*(?:OH|Ohio)?\s*\d{5})?',
                r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
            ]
            
            for pattern in address_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    address = matches[0].strip()
                    address = re.sub(r'\s+', ' ', address)
                    # Clean up common false positives
                    if not any(word in address.lower() for word in ['post navigation', 'previous business', 'next business']):
                        business_info['Address'] = address
                        break
            
            logger.info(f"✓ Extracted: {business_info['Name']}")
            return business_info
            
        except Exception as e:
            logger.error(f"Error extracting info from {business_url}: {e}")
            return {}
    
    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses"""
        logger.info("🚀 Starting complete business scraping with Selenium...")
        
        # Find all business links
        business_links = self.find_all_business_links(main_url)
        
        if not business_links:
            logger.warning("No business links found!")
            return []
        
        logger.info(f"Found {len(business_links)} businesses to scrape")
        print(f"\n📊 Found {len(business_links)} businesses. Starting detailed scraping...")
        
        # Scrape each business
        for i, business_url in enumerate(business_links, 1):
            print(f"Progress: {i}/{len(business_links)} ({i*100//len(business_links)}%)", end='\r')
            
            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)
            
            # Small delay to be respectful
            time.sleep(1)
        
        print(f"\n✅ Scraping completed! Found {len(self.businesses)} businesses")
        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses")
        return self.businesses
    
    def export_to_excel(self, filename: str = "black_owned_businesses_complete.xlsx"):
        """Export scraped data to Excel with monitoring"""
        if not self.businesses:
            logger.warning("No businesses to export")
            print("❌ No businesses to export")
            return False
        
        try:
            df = pd.DataFrame(self.businesses)
            df = df.fillna('')
            
            # Remove duplicates based on URL and Name
            df = df.drop_duplicates(subset=['Source_URL'], keep='first')
            df = df.drop_duplicates(subset=['Name'], keep='first')
            
            # Reorder columns
            columns = ['Name', 'Category', 'Description', 'Address', 'Phone', 'Email', 'Website', 'Source_URL']
            df = df[columns]
            
            # Create Excel file with multiple sheets
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main sheet with all businesses
                df.to_excel(writer, sheet_name='All Businesses', index=False)
                
                # Sheet with complete contact info
                complete_info = df[(df['Phone'] != '') | (df['Email'] != '') | (df['Website'] != '')]
                if not complete_info.empty:
                    complete_info.to_excel(writer, sheet_name='With Contact Info', index=False)
                
                # Sheet by category
                if df['Category'].notna().any():
                    for category in df['Category'].unique():
                        if category and category != '':
                            category_df = df[df['Category'] == category]
                            sheet_name = category[:30]  # Excel sheet name limit
                            category_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 60)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Print summary
            print(f"\n✅ Successfully exported {len(df)} businesses to {filename}")
            print(f"\n📊 Summary:")
            print(f"   Total businesses: {len(df)}")
            print(f"   With phone: {len(df[df['Phone'] != ''])}")
            print(f"   With email: {len(df[df['Email'] != ''])}")
            print(f"   With website: {len(df[df['Website'] != ''])}")
            print(f"   With address: {len(df[df['Address'] != ''])}")
            
            if df['Category'].notna().any():
                print(f"\n🏷️  Categories found:")
                for category in sorted(df['Category'].unique()):
                    if category:
                        count = len(df[df['Category'] == category])
                        print(f"   - {category}: {count} businesses")
            
            logger.info(f"Data exported to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            print(f"❌ Error exporting to Excel: {e}")
            return False

def main():
    """Main function"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    print("=" * 70)
    print("🚀 BLACK-OWNED BUSINESSES SCRAPER")
    print("=" * 70)
    print(f"Target: {main_url}")
    print("This scraper will:")
    print("  ✓ Load ALL businesses (534+) including dynamically loaded content")
    print("  ✓ Extract name, description, address, phone, email, website")
    print("  ✓ Export to Excel with multiple sheets and formatting")
    print("  ✓ Monitor progress in real-time")
    print("\nThis will take 15-30 minutes depending on your connection...")
    print("=" * 70)
    print()
    
    scraper = None
    try:
        scraper = SeleniumBusinessScraper()
        businesses = scraper.scrape_all_businesses(main_url)
        
        if businesses:
            scraper.export_to_excel()
        else:
            print("❌ No businesses were found. Please check the website or your connection.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
        if scraper and scraper.businesses:
            print("Saving partial results...")
            scraper.export_to_excel("black_owned_businesses_partial.xlsx")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        if scraper and scraper.businesses:
            print("Attempting to save partial results...")
            scraper.export_to_excel("black_owned_businesses_partial.xlsx")
    
    finally:
        if scraper:
            scraper.driver.quit()

if __name__ == "__main__":
    main()
