#!/usr/bin/env python3
"""
Complete Business Scraper with Real-time Monitoring
Scrapes ALL businesses from Voice of Black Cincinnati directory
- Uses Selenium to handle dynamic content loading
- Saves progress incrementally
- Monitors Excel output in real-time
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ComprehensiveBusinessScraper:
    def __init__(self, base_url: str = "https://thevoiceofblackcincinnati.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        self.businesses = []
        self.processed_urls = set()
        self.excel_filename = f"black_owned_businesses_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    def setup_driver(self):
        """Set up Selenium Chrome WebDriver with optimized settings"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            logger.info("Setting up Chrome WebDriver...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {e}")
            return None

    def load_all_business_links(self, main_url: str) -> List[str]:
        """Use Selenium to load all businesses by clicking 'Load More' button"""
        driver = self.setup_driver()
        if not driver:
            logger.error("Failed to setup WebDriver")
            return []

        try:
            logger.info(f"Loading main page: {main_url}")
            driver.get(main_url)
            time.sleep(5)  # Initial page load

            business_links = set()
            previous_count = 0
            no_change_count = 0
            max_attempts = 100  # Maximum number of "Load More" clicks

            for attempt in range(max_attempts):
                # Scroll to bottom to ensure all content is loaded
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                # Extract current business links
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find all links to individual business pages
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    # Look for business detail pages
                    if '/black-owned-business/' in href and href.count('/') >= 4:
                        # Filter out the main directory page
                        if href != main_url and '/black-owned-businesses/' not in href:
                            if href.startswith('http'):
                                business_links.add(href)
                            else:
                                full_url = f"{self.base_url}{href}"
                                business_links.add(full_url)

                current_count = len(business_links)
                logger.info(f"Attempt {attempt + 1}: Found {current_count} unique businesses")

                # Check if we're still finding new businesses
                if current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= 3:
                        logger.info("No new businesses found after 3 attempts - assuming all loaded")
                        break
                else:
                    no_change_count = 0

                previous_count = current_count

                # Try to find and click "Load More" button
                load_more_found = False
                try:
                    # Try different selectors for Load More button
                    possible_selectors = [
                        "//a[contains(text(), 'Load more')]",
                        "//a[contains(text(), 'Load More')]",
                        "//button[contains(text(), 'Load more')]",
                        "//button[contains(text(), 'Load More')]",
                        "//*[@id='cff-load-more']",
                        "//*[contains(@class, 'load-more')]",
                    ]

                    for selector in possible_selectors:
                        try:
                            load_more = driver.find_element(By.XPATH, selector)
                            
                            # Check if button is visible and clickable
                            if load_more.is_displayed() and load_more.is_enabled():
                                # Scroll to button
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more)
                                time.sleep(1)
                                
                                # Click using JavaScript to avoid overlay issues
                                driver.execute_script("arguments[0].click();", load_more)
                                logger.info(f"✓ Clicked 'Load More' button")
                                load_more_found = True
                                time.sleep(3)  # Wait for content to load
                                break
                        except (NoSuchElementException, Exception):
                            continue

                    if not load_more_found:
                        logger.info("No more 'Load More' button found")
                        break

                except Exception as e:
                    logger.debug(f"Error clicking Load More: {e}")
                    break

            logger.info(f"✓ Total unique business links collected: {len(business_links)}")
            return sorted(list(business_links))

        except Exception as e:
            logger.error(f"Error in load_all_business_links: {e}")
            return []
        finally:
            driver.quit()

    def extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract JSON-LD structured data from page"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'LocalBusiness':
                        return data
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'LocalBusiness':
                                return item
        except Exception as e:
            logger.debug(f"Error extracting JSON-LD: {e}")
        return None

    def extract_email(self, soup: BeautifulSoup) -> str:
        """Extract email address from page"""
        try:
            # Check mailto links
            email_links = soup.find_all('a', href=re.compile(r'mailto:|email-protection'))
            for link in email_links:
                text = link.get_text(strip=True)
                if '@' in text:
                    return text
                href = link.get('href', '')
                if 'mailto:' in href:
                    email = href.replace('mailto:', '').split('?')[0]
                    return email
                if 'email-protection' in href:
                    return 'Email available (Cloudflare protected)'

            # Search for email patterns in text
            page_text = soup.get_text()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_text)
            if emails:
                for email in emails:
                    # Filter out common false positives
                    if not any(x in email.lower() for x in ['example.com', 'sentry.io', 'mozilla.org', 'schema.org']):
                        return email
        except Exception as e:
            logger.debug(f"Error extracting email: {e}")
        return ''

    def extract_business_info(self, business_url: str) -> Dict[str, str]:
        """Extract detailed business information from individual business page"""
        if business_url in self.processed_urls:
            return {}

        self.processed_urls.add(business_url)

        try:
            logger.info(f"Fetching: {business_url}")
            response = self.session.get(business_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {business_url}: {e}")
            return {}

        business_info = {
            'Name': '',
            'Category': '',
            'Description': '',
            'Website': '',
            'Email': '',
            'Phone': '',
            'Address': '',
            'City': '',
            'State': '',
            'Zip': '',
            'Source_URL': business_url
        }

        try:
            # Extract from JSON-LD first (most reliable)
            json_ld = self.extract_json_ld(soup)
            if json_ld:
                business_info['Name'] = json_ld.get('name', '')
                business_info['Phone'] = json_ld.get('telephone', '')
                business_info['Website'] = json_ld.get('url', '')

                address_data = json_ld.get('address', {})
                if isinstance(address_data, dict):
                    business_info['Address'] = address_data.get('streetAddress', '')
                    business_info['City'] = address_data.get('addressLocality', '')
                    business_info['State'] = address_data.get('addressRegion', '')
                    business_info['Zip'] = address_data.get('postalCode', '')

            # Extract business name if not found
            if not business_info['Name']:
                name_elem = soup.find('h1', class_='entry-title')
                if not name_elem:
                    name_elem = soup.find('h1')
                if name_elem:
                    business_info['Name'] = name_elem.get_text(strip=True)

            # Extract category
            category_links = soup.find_all('a', href=re.compile(r'/black-owned-business-type/'))
            if category_links:
                categories = []
                for cat_link in category_links:
                    cat_text = cat_link.get_text(strip=True)
                    if cat_text and len(cat_text) > 3:
                        categories.append(cat_text)
                if categories:
                    business_info['Category'] = ', '.join(set(categories))

            # Extract description from entry-content
            content_div = soup.find('div', class_='entry-content')
            if content_div:
                paragraphs = content_div.find_all('p')
                if paragraphs:
                    description_parts = []
                    for p in paragraphs[:3]:
                        text = p.get_text(strip=True)
                        if len(text) > 20:
                            description_parts.append(text)
                    if description_parts:
                        business_info['Description'] = ' '.join(description_parts)[:500]

            # Extract email
            business_info['Email'] = self.extract_email(soup)

            # Extract phone if not found
            if not business_info['Phone']:
                tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
                if tel_links:
                    business_info['Phone'] = tel_links[0].get_text(strip=True)

            # Extract address from h3 tags if not found
            if not business_info['Address']:
                h3_tags = soup.find_all('h3')
                for h3 in h3_tags:
                    text = h3.get_text(strip=True)
                    if re.search(r'\d+\s+[A-Za-z]', text):
                        lines = []
                        for elem in h3.children:
                            if isinstance(elem, str):
                                line = elem.strip()
                                if line:
                                    lines.append(line)

                        if lines:
                            business_info['Address'] = lines[0]
                            if len(lines) >= 2:
                                location = lines[1]
                                parts = location.split()
                                if len(parts) >= 3:
                                    business_info['City'] = parts[0].replace(',', '')
                                    business_info['State'] = parts[1]
                                    business_info['Zip'] = parts[2] if len(parts) > 2 else ''
                        break

            # Extract website if not found
            if not business_info['Website']:
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if href.startswith('http'):
                        excluded = ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube',
                                  'thevoiceofblackcincinnati.com', 'mailchi.mp', 'list-manage',
                                  'subscribe', 'opentable.com/restref']
                        if not any(x in href.lower() for x in excluded):
                            business_info['Website'] = href
                            break

            logger.info(f"✓ Extracted: {business_info['Name'][:40]} - "
                       f"Email: {bool(business_info['Email'])}, "
                       f"Phone: {bool(business_info['Phone'])}, "
                       f"Address: {bool(business_info['Address'])}")

        except Exception as e:
            logger.error(f"Error extracting business info: {e}")

        return business_info

    def save_progress(self):
        """Save current progress to Excel file"""
        if not self.businesses:
            return

        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        df = df.drop_duplicates(subset=['Name'], keep='first')

        try:
            with pd.ExcelWriter(self.excel_filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='All Businesses', index=False)

                # Create sheet with complete contact info
                complete = df[(df['Email'] != '') | (df['Phone'] != '') | (df['Address'] != '')]
                if not complete.empty:
                    complete.to_excel(writer, sheet_name='With Contact Info', index=False)

                # Auto-adjust column widths
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value:
                                    max_length = max(max_length, len(str(cell.value)))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 60)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            logger.info(f"💾 Saved progress: {len(df)} businesses to {self.excel_filename}")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")

    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses"""
        print("\n" + "=" * 70)
        print("BLACK-OWNED CINCINNATI BUSINESSES - COMPLETE SCRAPER")
        print("=" * 70)
        print(f"Target URL: {main_url}")
        print(f"Output File: {self.excel_filename}")
        print("=" * 70 + "\n")

        # Step 1: Load all business links using Selenium
        print("STEP 1: Loading all business links (this may take a few minutes)...")
        business_links = self.load_all_business_links(main_url)

        if not business_links:
            logger.error("❌ No business links found!")
            return []

        print(f"✓ Found {len(business_links)} business links\n")

        # Step 2: Scrape each business
        print(f"STEP 2: Scraping details for {len(business_links)} businesses...")
        print("This will take a while. Progress is saved every 10 businesses.\n")

        for i, business_url in enumerate(business_links, 1):
            print(f"[{i}/{len(business_links)}] Scraping: {business_url.split('/')[-2][:50]}...")

            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)

            # Save progress every 10 businesses
            if i % 10 == 0:
                self.save_progress()
                print(f"  → Saved progress: {len(self.businesses)} businesses collected\n")

            # Be respectful to the server
            time.sleep(1.5)

        # Final save
        self.save_progress()

        # Print summary
        print("\n" + "=" * 70)
        print("SCRAPING COMPLETE!")
        print("=" * 70)
        print(f"Total businesses collected: {len(self.businesses)}")
        print(f"Excel file: {self.excel_filename}")
        print("\nStatistics:")
        print(f"  • With email: {sum(1 for b in self.businesses if b.get('Email'))}")
        print(f"  • With phone: {sum(1 for b in self.businesses if b.get('Phone'))}")
        print(f"  • With address: {sum(1 for b in self.businesses if b.get('Address'))}")
        print(f"  • With website: {sum(1 for b in self.businesses if b.get('Website'))}")
        complete_contact = sum(1 for b in self.businesses 
                              if b.get('Email') and b.get('Phone') and b.get('Address'))
        print(f"  • With all contact info: {complete_contact}")
        print("=" * 70 + "\n")

        return self.businesses


def main():
    """Main function"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"

    scraper = ComprehensiveBusinessScraper()
    businesses = scraper.scrape_all_businesses(main_url)

    if businesses:
        print(f"✓ Successfully scraped {len(businesses)} businesses!")
        print(f"✓ Data saved to: {scraper.excel_filename}")
    else:
        print("❌ No businesses were scraped. Check the logs for errors.")


if __name__ == "__main__":
    main()
