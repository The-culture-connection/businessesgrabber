#!/usr/bin/env python3
"""
Sitemap-based scraper that gets ALL businesses from the sitemap.xml
This is the most reliable method to get all 400+ businesses.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import logging
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SitemapBusinessScraper:
    def __init__(self, base_url: str = "https://thevoiceofblackcinnati.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
        self.businesses = []
        self.processed_urls = set()

    def get_business_urls_from_sitemap(self, sitemap_url: str) -> List[str]:
        """Extract all business URLs from the sitemap"""
        logger.info(f"Fetching sitemap: {sitemap_url}")

        try:
            response = self.session.get(sitemap_url, timeout=15)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            # Extract all URLs (handle XML namespaces)
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []

            for url_elem in root.findall('.//ns:url', namespaces):
                loc = url_elem.find('ns:loc', namespaces)
                if loc is not None and loc.text:
                    # Only get business URLs
                    if '/black-owned-business/' in loc.text:
                        urls.append(loc.text)

            logger.info(f"Found {len(urls)} business URLs in sitemap")
            return urls

        except Exception as e:
            logger.error(f"Error fetching sitemap: {e}")
            return []

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

    def scrape_all_businesses(self, sitemap_url: str) -> List[Dict[str, str]]:
        """Main method to scrape ALL businesses from sitemap"""
        logger.info("Starting sitemap-based business scraping...")

        # Get all business URLs from sitemap
        business_urls = self.get_business_urls_from_sitemap(sitemap_url)

        if not business_urls:
            logger.warning("No business URLs found in sitemap")
            return []

        logger.info(f"Starting to scrape {len(business_urls)} businesses...")

        # Scrape each business
        for i, business_url in enumerate(business_urls, 1):
            logger.info(f"Scraping business {i}/{len(business_urls)}")

            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)

            # Be respectful - add delay between requests
            time.sleep(1)

            # Progress update every 50 businesses
            if i % 50 == 0:
                logger.info(f"Progress: {i}/{len(business_urls)} businesses scraped ({len(self.businesses)} with data)")

        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses with data")
        return self.businesses

    def export_to_excel(self, filename: str = "all_businesses_from_sitemap.xlsx"):
        """Export scraped data to Excel"""
        if not self.businesses:
            logger.warning("No businesses to export")
            return

        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
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
            print(f"Successfully exported {len(df)} businesses to {filename}")

        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")


def main():
    """Main function"""
    sitemap_url = "https://thevoiceofblackcincinnati.com/businesses-sitemap.xml"

    print("=" * 70)
    print("SITEMAP-BASED BUSINESS DIRECTORY SCRAPER")
    print("=" * 70)
    print(f"\nSitemap: {sitemap_url}")
    print("\nThis scraper will:")
    print("  1. Extract ALL business URLs from the sitemap (400+)")
    print("  2. Scrape detailed info for each business")
    print("  3. Export to Excel with complete contact information")
    print("\nThis will take a while (estimated 10-15 minutes)...")
    print("=" * 70)
    print()

    scraper = SitemapBusinessScraper()
    businesses = scraper.scrape_all_businesses(sitemap_url)

    if businesses:
        scraper.export_to_excel()

        # Print summary
        print("\n" + "=" * 70)
        print("SCRAPING SUMMARY")
        print("=" * 70)
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
