#!/usr/bin/env python3
"""
Comprehensive scraper to get ALL businesses from the directory
This version will try to find all businesses including those that might be on multiple pages
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse
import logging
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveBusinessScraper:
    def __init__(self, base_url: str = "https://thevoiceofblackcincinnati.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
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
    
    def find_all_business_links(self, main_url: str) -> List[str]:
        """Find all possible business links from the main directory"""
        soup = self.get_page(main_url)
        if not soup:
            return []
        
        business_links = []
        
        # Look for "Read More" links
        read_more_links = soup.find_all('a', string=re.compile(r'Read More', re.IGNORECASE))
        for link in read_more_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                business_links.append(full_url)
        
        # Look for any links that contain business names or IDs
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and 'black-owned-business' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in business_links:
                    business_links.append(full_url)
        
        # Look for pagination or "Load More" buttons
        pagination_links = soup.find_all('a', href=True)
        for link in pagination_links:
            href = link.get('href')
            if href and ('page' in href.lower() or 'next' in href.lower() or 'more' in href.lower()):
                full_url = urljoin(self.base_url, href)
                if full_url not in business_links:
                    logger.info(f"Found potential pagination link: {full_url}")
                    # Recursively search paginated pages
                    paginated_links = self.find_all_business_links(full_url)
                    business_links.extend(paginated_links)
        
        # Look for category filters that might reveal more businesses
        category_links = soup.find_all('a', href=True)
        for link in category_links:
            href = link.get('href')
            if href and ('category' in href.lower() or 'filter' in href.lower()):
                full_url = urljoin(self.base_url, href)
                if full_url not in business_links:
                    logger.info(f"Found potential category link: {full_url}")
                    # Recursively search category pages
                    category_links = self.find_all_business_links(full_url)
                    business_links.extend(category_links)
        
        return list(set(business_links))  # Remove duplicates
    
    def extract_business_info(self, business_url: str) -> Dict[str, str]:
        """Extract business information from individual business page"""
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
            'Phone': '',
            'Address': '',
            'Source_URL': business_url
        }
        
        try:
            # Extract business name
            name_selectors = ['h1', 'h2', '.business-name', '.title', '.entry-title']
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    if name_text and len(name_text) > 2 and len(name_text) < 100:
                        business_info['Name'] = name_text
                        break
            
            # Extract category
            category_text = soup.get_text()
            category_patterns = [
                r'Restaurants, Eateries and Caterers',
                r'Professional Services',
                r'Beauty and Barber',
                r'Health and Fitness',
                r'Construction and Home Improvement',
                r'Photography & Videography',
                r'Online Retail',
                r'Retail',
                r'Night Clubs and Entertainment',
                r'Supplies and Services',
                r'Event Planners and Venues',
                r'Daycare/Preschool',
                r'Education',
                r'Other'
            ]
            
            for pattern in category_patterns:
                if re.search(pattern, category_text, re.IGNORECASE):
                    business_info['Category'] = pattern
                    break
            
            # Extract description
            desc_selectors = ['.entry-content', '.content', 'p', '.description']
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if len(desc_text) > 20:
                        business_info['Description'] = desc_text[:500] + '...' if len(desc_text) > 500 else desc_text
                        break
            
            # Extract contact information
            page_text = soup.get_text()
            
            # Look for website URLs
            excluded_domains = [
                'thevoiceofblackcincinnati.com', 'voiceofblackcincinnati.com',
                'mailchi.mp', 'list-manage.com', 'thevoiceofyourcustomer.com'
            ]
            
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('http'):
                    if not any(social in href.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube']):
                        if not any(domain in href.lower() for domain in excluded_domains):
                            business_info['Website'] = href
                            break
            
            # Look for phone numbers
            phone_patterns = [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            ]
            
            all_phones = []
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                all_phones.extend(matches)
            
            if all_phones:
                phone = re.sub(r'[^\d]', '', all_phones[0])
                if len(phone) == 10:
                    business_info['Phone'] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                else:
                    business_info['Phone'] = all_phones[0]
            
            # Look for addresses
            address_patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)',
                r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
            ]
            
            all_addresses = []
            for pattern in address_patterns:
                matches = re.findall(pattern, page_text)
                all_addresses.extend(matches)
            
            if all_addresses:
                address = all_addresses[0].strip()
                address = re.sub(r'\s+', ' ', address)
                address = re.sub(r'(Post navigation|Previous Business|Park Place).*', '', address)
                business_info['Address'] = address.strip()
            
            logger.info(f"Extracted info for {business_info.get('Name', 'Unknown')}: Website={bool(business_info['Website'])}, Phone={bool(business_info['Phone'])}, Address={bool(business_info['Address'])}")
            
        except Exception as e:
            logger.error(f"Error extracting business info from {business_url}: {e}")
        
        return business_info
    
    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses"""
        logger.info("Starting comprehensive business scraping...")
        
        # Find all business links
        business_links = self.find_all_business_links(main_url)
        logger.info(f"Found {len(business_links)} total business links")
        
        if not business_links:
            logger.warning("No business links found")
            return []
        
        # Scrape each business
        for i, business_url in enumerate(business_links, 1):
            logger.info(f"Scraping business {i}/{len(business_links)}: {business_url}")
            
            business_info = self.extract_business_info(business_url)
            if business_info and business_info.get('Name'):
                self.businesses.append(business_info)
            
            # Be respectful - add delay between requests
            time.sleep(2)
        
        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses")
        return self.businesses
    
    def export_to_excel(self, filename: str = "all_black_owned_businesses.xlsx"):
        """Export scraped data to Excel file"""
        if not self.businesses:
            logger.warning("No businesses to export")
            return
        
        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        df = df.drop_duplicates(subset=['Name'], keep='first')
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='All Black Owned Businesses', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['All Black Owned Businesses']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"Data exported to {filename}")
            print(f"✅ Successfully exported {len(self.businesses)} businesses to {filename}")
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            print(f"❌ Error exporting to Excel: {e}")

def main():
    """Main function to run the comprehensive scraper"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    scraper = ComprehensiveBusinessScraper()
    
    print("🚀 Starting comprehensive business directory scraper...")
    print(f"Target URL: {main_url}")
    print("This will search for ALL businesses including those on multiple pages...")
    print("This may take several minutes...")
    
    # Scrape all businesses
    businesses = scraper.scrape_all_businesses(main_url)
    
    if businesses:
        # Export to Excel
        scraper.export_to_excel()
        
        # Print summary
        print(f"\n📊 Scraping Summary:")
        print(f"Total businesses found: {len(businesses)}")
        
        # Count businesses with contact info
        with_website = sum(1 for b in businesses if b.get('Website'))
        with_phone = sum(1 for b in businesses if b.get('Phone'))
        with_address = sum(1 for b in businesses if b.get('Address'))
        
        print(f"Businesses with website: {with_website}")
        print(f"Businesses with phone: {with_phone}")
        print(f"Businesses with address: {with_address}")
        
        # Show categories found
        categories = set(b.get('Category', '') for b in businesses if b.get('Category'))
        if categories:
            print(f"\n🏷️ Categories found: {', '.join(sorted(categories))}")
    else:
        print("❌ No businesses were scraped. Please check the website structure or try again.")

if __name__ == "__main__":
    main()
