#!/usr/bin/env python3
"""
Improved business scraper that extracts data from JSON-LD structured data
and properly handles email, phone, and address extraction
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
from urllib.parse import urljoin
import logging
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImprovedBusinessScraper:
    def __init__(self, base_url: str = "https://thevoiceofblackcincinnati.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        self.businesses = []
        self.processed_urls = set()

    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract JSON-LD structured data from page"""
        try:
            # Find all script tags with type="application/ld+json"
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if script.string:
                    data = json.loads(script.string)
                    # Check if it's LocalBusiness schema
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
        """Extract email address (even if Cloudflare protected)"""
        try:
            # Look for email links
            email_links = soup.find_all('a', href=re.compile(r'mailto:|email-protection'))
            for link in email_links:
                # Check if there's visible text that looks like an email
                text = link.get_text(strip=True)
                if '@' in text:
                    return text
                # Check the href attribute
                href = link.get('href', '')
                if 'mailto:' in href:
                    email = href.replace('mailto:', '').split('?')[0]
                    return email
                # If Cloudflare protected, mark as "Protected"
                if 'email-protection' in href:
                    return 'Email available (Cloudflare protected)'

            # Look for email patterns in page text
            page_text = soup.get_text()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_text)
            if emails:
                # Filter out common false positives
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
        soup = self.get_page(business_url)
        if not soup:
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
            # Try to extract from JSON-LD first (most reliable)
            json_ld = self.extract_json_ld(soup)
            if json_ld:
                logger.info("Found JSON-LD structured data")
                business_info['Name'] = json_ld.get('name', '')
                business_info['Phone'] = json_ld.get('telephone', '')
                business_info['Website'] = json_ld.get('url', '')

                # Extract address from JSON-LD
                address_data = json_ld.get('address', {})
                if isinstance(address_data, dict):
                    business_info['Address'] = address_data.get('streetAddress', '')
                    business_info['City'] = address_data.get('addressLocality', '')
                    business_info['State'] = address_data.get('addressRegion', '')
                    business_info['Zip'] = address_data.get('postalCode', '')

            # Extract business name if not found in JSON-LD
            if not business_info['Name']:
                name_elem = soup.find('h1', class_='entry-title')
                if not name_elem:
                    name_elem = soup.find('h1')
                if name_elem:
                    business_info['Name'] = name_elem.get_text(strip=True)

            # Extract category from the page
            # Look for the specific category links (they have the black-owned-business-type in the URL)
            category_links = soup.find_all('a', href=re.compile(r'/black-owned-business-type/'))
            if category_links:
                categories = []
                for cat_link in category_links:
                    cat_text = cat_link.get_text(strip=True)
                    if cat_text and len(cat_text) > 3:
                        categories.append(cat_text)
                if categories:
                    business_info['Category'] = ', '.join(categories)  # All relevant categories

            # Extract description from the main content
            content_div = soup.find('div', class_='entry-content')
            if content_div:
                # Get all paragraphs
                paragraphs = content_div.find_all('p')
                if paragraphs:
                    description_parts = []
                    for p in paragraphs[:3]:  # First 3 paragraphs
                        text = p.get_text(strip=True)
                        if len(text) > 20:  # Only include substantial paragraphs
                            description_parts.append(text)
                    if description_parts:
                        business_info['Description'] = ' '.join(description_parts)[:500]

            # Extract email
            business_info['Email'] = self.extract_email(soup)

            # Extract phone number from tel: links if not found in JSON-LD
            if not business_info['Phone']:
                tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
                if tel_links:
                    phone = tel_links[0].get_text(strip=True)
                    business_info['Phone'] = phone

            # Extract address from h3 tags if not found in JSON-LD
            if not business_info['Address']:
                # Look for address in h3 tags
                h3_tags = soup.find_all('h3')
                for h3 in h3_tags:
                    text = h3.get_text(strip=True)
                    # Check if it looks like an address (contains number and street)
                    if re.search(r'\d+\s+[A-Za-z]', text):
                        # Split by <br> tags
                        lines = []
                        for elem in h3.children:
                            if isinstance(elem, str):
                                lines.append(elem.strip())
                            elif elem.name == 'br':
                                continue

                        if len(lines) >= 1:
                            business_info['Address'] = lines[0]
                            # Try to parse city, state, zip from second line
                            if len(lines) >= 2:
                                location = lines[1]
                                # Parse "Cincinnati OH 45215"
                                parts = location.split()
                                if len(parts) >= 3:
                                    business_info['City'] = parts[0]
                                    business_info['State'] = parts[1]
                                    business_info['Zip'] = parts[2]
                        break

            # Extract website if not found in JSON-LD
            if not business_info['Website']:
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if href.startswith('http'):
                        # Exclude social media, newsletters, and the directory site itself
                        excluded = ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube',
                                  'thevoiceofblackcincinnati.com', 'mailchi.mp', 'list-manage',
                                  'subscribe', 'opentable.com/restref']
                        if not any(x in href.lower() for x in excluded):
                            business_info['Website'] = href
                            break

            logger.info(f"Extracted: {business_info['Name']} - Email: {bool(business_info['Email'])}, "
                       f"Phone: {bool(business_info['Phone'])}, Address: {bool(business_info['Address'])}")

        except Exception as e:
            logger.error(f"Error extracting business info from {business_url}: {e}")

        return business_info

    def find_all_business_links(self, main_url: str, max_pages: int = 50) -> List[str]:
        """Find all business links from the directory"""
        all_links = []
        current_page = 1

        while current_page <= max_pages:
            # Construct URL with page number
            if current_page == 1:
                page_url = main_url
            else:
                # Try different pagination patterns
                page_url = f"{main_url}page/{current_page}/"

            logger.info(f"Scanning page {current_page}: {page_url}")
            soup = self.get_page(page_url)
            if not soup:
                break

            # Extract business links from current page
            page_links = []

            # Look for "Read More" links
            read_more_links = soup.find_all('a', string=re.compile(r'Read More', re.IGNORECASE))
            for link in read_more_links:
                href = link.get('href')
                if href and 'black-owned-business/' in href:
                    full_url = urljoin(self.base_url, href)
                    page_links.append(full_url)

            # Also look for direct business links
            all_page_links = soup.find_all('a', href=True)
            for link in all_page_links:
                href = link.get('href')
                if href and '/black-owned-business/' in href and href.count('/') >= 4:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in page_links and full_url != main_url:
                        page_links.append(full_url)

            if not page_links:
                logger.info(f"No business links found on page {current_page}, stopping")
                break

            logger.info(f"Found {len(page_links)} business links on page {current_page}")
            all_links.extend(page_links)

            current_page += 1
            time.sleep(1)  # Be respectful

        # Remove duplicates
        unique_links = list(set(all_links))
        logger.info(f"Total unique business links: {len(unique_links)}")
        return unique_links

    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Scrape all businesses from the directory"""
        logger.info("Starting business scraping...")

        # Find all business links
        business_links = self.find_all_business_links(main_url)

        if not business_links:
            logger.warning("No business links found")
            return []

        # Scrape each business
        for i, business_url in enumerate(business_links, 1):
            logger.info(f"Scraping business {i}/{len(business_links)}")

            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)

            # Be respectful - add delay between requests
            time.sleep(2)

        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses")
        return self.businesses

    def export_to_excel(self, filename: str = "improved_businesses.xlsx"):
        """Export scraped data to Excel"""
        if not self.businesses:
            logger.warning("No businesses to export")
            return

        df = pd.DataFrame(self.businesses)
        df = df.fillna('')

        # Remove duplicates
        df = df.drop_duplicates(subset=['Name'], keep='first')

        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # All businesses
                df.to_excel(writer, sheet_name='All Businesses', index=False)

                # Businesses with complete contact info
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
            print(f"✓ Successfully exported {len(df)} businesses to {filename}")

        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            print(f"✗ Error exporting: {e}")


def main():
    """Main function"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"

    print("=" * 60)
    print("IMPROVED BUSINESS DIRECTORY SCRAPER")
    print("=" * 60)
    print(f"\nTarget: {main_url}")
    print("\nThis scraper extracts:")
    print("  • Business name")
    print("  • Category")
    print("  • Description")
    print("  • Website")
    print("  • Email address")
    print("  • Phone number")
    print("  • Full address (street, city, state, zip)")
    print("\nStarting scrape...\n")

    scraper = ImprovedBusinessScraper()
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

        complete = sum(1 for b in businesses if b.get('Email') and b.get('Phone') and b.get('Address'))
        print(f"With all contact info: {complete}")

    else:
        print("\n✗ No businesses were scraped")


if __name__ == "__main__":
    main()
