#!/usr/bin/env python3
"""
AJAX-aware scraper that handles "Load More" button clicking
to get ALL 594+ businesses from the directory
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re
import logging
from typing import Dict, List, Optional
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AjaxBusinessScraper:
    def __init__(self):
        self.businesses = []
        self.processed_urls = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })

    def setup_driver(self):
        """Set up Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in background
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        try:
            logger.info("Setting up Chrome WebDriver (this may download ChromeDriver on first run)...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {e}")
            return None

    def load_all_businesses_with_selenium(self, url: str) -> List[str]:
        """Use Selenium to click 'Load More' and collect all business links"""
        driver = self.setup_driver()
        if not driver:
            return []

        try:
            logger.info(f"Loading page: {url}")
            driver.get(url)
            time.sleep(3)  # Wait for initial load

            business_links = set()
            load_more_clicks = 0
            max_clicks = 300  # Safety limit (increased to handle all ~594 businesses)

            while load_more_clicks < max_clicks:
                # Extract current business links
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                links = soup.find_all('a', href=re.compile(r'/black-owned-business/'))

                for link in links:
                    href = link.get('href')
                    if href and '/black-owned-business/' in href and href.count('/') >= 4:
                        if href.startswith('http'):
                            business_links.add(href)
                        else:
                            business_links.add(f"https://thevoiceofblackcincinnati.com{href}")

                logger.info(f"Found {len(business_links)} unique businesses so far...")

                # Try to find and click "Load More" button
                try:
                    # Try multiple selectors for the Load More button
                    load_more = None
                    selectors = [
                        (By.LINK_TEXT, "Load more posts"),
                        (By.ID, "cff-load-more"),
                        (By.CLASS_NAME, "cff-load-more"),
                    ]

                    for selector_type, selector_value in selectors:
                        try:
                            load_more = driver.find_element(selector_type, selector_value)
                            if load_more:
                                break
                        except:
                            continue

                    if not load_more:
                        logger.info("No 'Load More' button found")
                        break

                    # Check if button is visible and enabled
                    button_style = load_more.get_attribute("style") or ""
                    button_class = load_more.get_attribute("class") or ""

                    # Check if button is hidden or disabled
                    if "display: none" in button_style or "display:none" in button_style:
                        logger.info("Load More button is hidden - all posts loaded")
                        break

                    if "disabled" in button_class:
                        logger.info("Load More button is disabled - all posts loaded")
                        break

                    # Check if button text changed to indicate end
                    button_text = load_more.text.strip()
                    if "no more" in button_text.lower():
                        logger.info(f"Button text indicates end: '{button_text}'")
                        break

                    # Scroll to button
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more)
                    time.sleep(1)

                    # Use JavaScript click to bypass any overlays
                    driver.execute_script("arguments[0].click();", load_more)
                    load_more_clicks += 1
                    logger.info(f"Clicked 'Load More' button {load_more_clicks} times")

                    # Wait for new content to load
                    time.sleep(3)

                except TimeoutException:
                    logger.info("No more 'Load More' button found - all businesses loaded!")
                    break
                except Exception as e:
                    logger.info(f"Could not click 'Load More': {e}")
                    break

            logger.info(f"Total unique business links collected: {len(business_links)}")
            return list(business_links)

        finally:
            driver.quit()

    def extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract JSON-LD structured data from page"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if data.get('@type') == 'LocalBusiness':
                            return data
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'LocalBusiness':
                                return item
        except Exception as e:
            logger.debug(f"Error extracting JSON-LD: {e}")
        return None

    def extract_email(self, soup: BeautifulSoup) -> str:
        """Extract email address"""
        try:
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

            page_text = soup.get_text()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_text)
            if emails:
                for email in emails:
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
            # Try to extract from JSON-LD first
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
                    business_info['Category'] = ', '.join(categories)

            # Extract description
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

        except Exception as e:
            logger.error(f"Error extracting business info: {e}")

        return business_info

    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape ALL businesses using Selenium"""
        logger.info("Starting AJAX-aware business scraping...")

        # Use Selenium to load all businesses
        business_links = self.load_all_businesses_with_selenium(main_url)

        if not business_links:
            logger.warning("No business links found")
            return []

        # Scrape each business
        for i, business_url in enumerate(business_links, 1):
            logger.info(f"Scraping business {i}/{len(business_links)}: {business_url}")

            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)

            time.sleep(1)  # Be respectful

        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses")
        return self.businesses

    def export_to_excel(self, filename: str = "all_businesses_complete.xlsx"):
        """Export scraped data to Excel"""
        if not self.businesses:
            logger.warning("No businesses to export")
            return

        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        df = df.drop_duplicates(subset=['Name'], keep='first')

        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='All Businesses', index=False)

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
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 60)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            logger.info(f"Data exported to {filename}")
            print(f"Successfully exported {len(df)} businesses to {filename}")

        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")


def main():
    """Main function"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"

    print("=" * 60)
    print("AJAX-AWARE BUSINESS DIRECTORY SCRAPER")
    print("=" * 60)
    print(f"\nTarget: {main_url}")
    print("\nThis scraper will:")
    print("  1. Click 'Load More' repeatedly to load all businesses")
    print("  2. Extract ~594 businesses from the directory")
    print("  3. Scrape detailed info for each business")
    print("\nThis will take a while - please be patient...")
    print("\nNOTE: Requires ChromeDriver to be installed\n")

    scraper = AjaxBusinessScraper()
    businesses = scraper.scrape_all_businesses(main_url)

    if businesses:
        scraper.export_to_excel()

        # Print summary
        print("\n" + "=" * 60)
        print("SCRAPING SUMMARY")
        print("=" * 60)
        print(f"Total businesses: {len(businesses)}")

        with_email = sum(1 for b in businesses if b.get('Email'))
        with_phone = sum(1 for b in businesses if b.get('Phone'))
        with_address = sum(1 for b in businesses if b.get('Address'))
        with_website = sum(1 for b in businesses if b.get('Website'))

        print(f"With email: {with_email}")
        print(f"With phone: {with_phone}")
        print(f"With address: {with_address}")
        print(f"With website: {with_website}")
    else:
        print("\nNo businesses were scraped")


if __name__ == "__main__":
    main()
