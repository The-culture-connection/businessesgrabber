#!/usr/bin/env python3
"""
Final Business Scraper - No Selenium Required!
Uses pagination and REST API to get ALL businesses
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
from urllib.parse import urljoin

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


class BusinessScraper:
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

    def find_all_business_links(self, main_url: str, max_pages: int = 100) -> List[str]:
        """Find all business links by going through paginated pages"""
        all_links = set()
        current_page = 1

        while current_page <= max_pages:
            # Construct pagination URL
            if current_page == 1:
                page_url = main_url
            else:
                page_url = f"{main_url}page/{current_page}/"

            logger.info(f"Scanning page {current_page}: {page_url}")
            
            try:
                response = self.session.get(page_url, timeout=15)
                
                # If we get 404, we've reached the end
                if response.status_code == 404:
                    logger.info(f"Page {current_page} returned 404 - reached end of pagination")
                    break
                    
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
            except requests.RequestException as e:
                logger.error(f"Error fetching page {current_page}: {e}")
                break

            # Extract business links from current page
            page_links = []
            
            # Method 1: Look for links with '/black-owned-business/' in the URL (singular, not plural)
            all_page_links = soup.find_all('a', href=True)
            for link in all_page_links:
                href = link.get('href', '')
                # Look for individual business pages (not the main directory)
                if '/black-owned-business/' in href and href.count('/') >= 4:
                    # Exclude the main directory page
                    if '/black-owned-businesses/' not in href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in all_links:
                            page_links.append(full_url)
                            all_links.add(full_url)

            if not page_links:
                logger.info(f"No new business links found on page {current_page} - stopping")
                break

            logger.info(f"  ✓ Found {len(page_links)} new businesses on page {current_page} (Total: {len(all_links)})")
            
            current_page += 1
            time.sleep(1)  # Be respectful

        logger.info(f"✓ Total unique business links collected: {len(all_links)}")
        return sorted(list(all_links))

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
                        # Skip "Read More" and navigation text
                        if len(text) > 20 and 'Read More' not in text and 'Post navigation' not in text:
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

        except Exception as e:
            logger.error(f"Error extracting business info: {e}")

        return business_info

    def save_progress(self, force=False):
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

            if force:
                logger.info(f"📊 Final save: {len(df)} businesses to {self.excel_filename}")
            else:
                logger.info(f"💾 Progress saved: {len(df)} businesses")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")

    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses"""
        print("\n" + "=" * 80)
        print(" " * 15 + "BLACK-OWNED CINCINNATI BUSINESSES - SCRAPER")
        print("=" * 80)
        print(f"Target URL: {main_url}")
        print(f"Output File: {self.excel_filename}")
        print("=" * 80 + "\n")

        # Step 1: Find all business links
        print("STEP 1: Finding all business links via pagination...")
        print("-" * 80)
        business_links = self.find_all_business_links(main_url)

        if not business_links:
            logger.error("❌ No business links found!")
            return []

        print(f"\n✓ Found {len(business_links)} business links\n")

        # Step 2: Scrape each business
        print("STEP 2: Scraping details for each business...")
        print("-" * 80)
        print("Progress is saved every 10 businesses.\n")

        for i, business_url in enumerate(business_links, 1):
            business_name = business_url.split('/')[-2].replace('-', ' ').title()[:50]
            print(f"[{i:3d}/{len(business_links)}] {business_name}... ", end='', flush=True)

            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)
                print(f"✓ {business_info['Name'][:40]}")
            else:
                print("✗ Failed")

            # Save progress every 10 businesses
            if i % 10 == 0:
                self.save_progress()

            # Be respectful to the server
            time.sleep(1.5)

        # Final save
        self.save_progress(force=True)

        # Print summary
        print("\n" + "=" * 80)
        print(" " * 30 + "SCRAPING COMPLETE!")
        print("=" * 80)
        print(f"Total businesses collected: {len(self.businesses)}")
        print(f"Excel file: {self.excel_filename}")
        print("\nContact Information Statistics:")
        print(f"  • With email:          {sum(1 for b in self.businesses if b.get('Email')):4d}")
        print(f"  • With phone:          {sum(1 for b in self.businesses if b.get('Phone')):4d}")
        print(f"  • With address:        {sum(1 for b in self.businesses if b.get('Address')):4d}")
        print(f"  • With website:        {sum(1 for b in self.businesses if b.get('Website')):4d}")
        complete_contact = sum(1 for b in self.businesses 
                              if b.get('Email') and b.get('Phone') and b.get('Address'))
        print(f"  • With all 3 contacts: {complete_contact:4d}")
        print("=" * 80 + "\n")

        return self.businesses


def main():
    """Main function"""
    # Use the archive page (singular), not the directory page (plural with 's')
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-business/"

    scraper = BusinessScraper()
    businesses = scraper.scrape_all_businesses(main_url)

    if businesses:
        print(f"✓ SUCCESS! Scraped {len(businesses)} businesses")
        print(f"✓ Data saved to: {scraper.excel_filename}")
    else:
        print("❌ No businesses were scraped. Check scraper.log for errors.")


if __name__ == "__main__":
    main()
