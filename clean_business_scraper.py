#!/usr/bin/env python3
"""
Clean business scraper that filters out non-business entries and exports to multiple formats
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse
import logging
from typing import Dict, List, Optional
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CleanBusinessScraper:
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
    
    def is_valid_business(self, business_info: Dict[str, str]) -> bool:
        """Check if this is a valid business entry"""
        name = business_info.get('Name', '').strip()
        url = business_info.get('detail_url', '')
        
        # Must have a name
        if not name or len(name) < 3:
            return False
        
        # Must be a business detail page (not main page or submit page)
        if not url or 'black-owned-business/' not in url:
            return False
        
        # Filter out navigation and system pages
        invalid_names = [
            'Things To Do', 'Submit an Event', 'Black Businesses', 'Submit a Business',
            'Cincy Jobs', 'Submit a Job', 'Scholarships', 'Contact', 'Find businesses'
        ]
        
        if any(invalid in name for invalid in invalid_names):
            return False
        
        # Filter out very short or generic names
        if len(name) < 5:
            return False
        
        return True
    
    def extract_business_links(self, main_url: str) -> List[Dict[str, str]]:
        """Extract business links and basic info from main page"""
        soup = self.get_page(main_url)
        if not soup:
            return []
        
        business_links = []
        
        # Look for "Read More" links specifically
        read_more_links = soup.find_all('a', string=re.compile(r'Read More', re.IGNORECASE))
        logger.info(f"Found {len(read_more_links)} 'Read More' links")
        
        for link in read_more_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                
                # Extract basic info from the card containing this link
                card = link.find_parent(['div', 'article', 'section'])
                if not card:
                    card = link.find_parent()
                
                business_info = self.extract_basic_info_from_card(card, full_url)
                if self.is_valid_business(business_info):
                    business_links.append(business_info)
        
        # Also look for any other business detail links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and 'black-owned-business/' in href:
                full_url = urljoin(self.base_url, href)
                # Skip if already found
                if not any(b['detail_url'] == full_url for b in business_links):
                    card = link.find_parent(['div', 'article', 'section'])
                    if not card:
                        card = link.find_parent()
                    business_info = self.extract_basic_info_from_card(card, full_url)
                    if self.is_valid_business(business_info):
                        business_links.append(business_info)
        
        logger.info(f"Found {len(business_links)} valid business links")
        return business_links
    
    def extract_basic_info_from_card(self, card, detail_url: str) -> Dict[str, str]:
        """Extract basic business info from a card element"""
        business_info = {
            'Name': '',
            'Category': '',
            'Description': '',
            'detail_url': detail_url,
            'Website': '',
            'Phone': '',
            'Address': '',
            'Source': 'Main Page'
        }
        
        if not card:
            return business_info
        
        try:
            # Extract business name
            name_selectors = ['h1', 'h2', 'h3', 'h4', 'strong', 'b', '.title', '.name']
            for selector in name_selectors:
                name_elem = card.select_one(selector)
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    if name_text and len(name_text) > 2 and len(name_text) < 100:
                        business_info['Name'] = name_text
                        break
            
            # If no name found, look for first significant text
            if not business_info['Name']:
                text_parts = card.get_text().split('\n')
                for part in text_parts:
                    part = part.strip()
                    if 5 < len(part) < 50 and not part.startswith(('Specializing', 'Black-owned', 'Located')):
                        business_info['Name'] = part
                        break
            
            # Extract category
            category_text = card.get_text()
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
            desc_selectors = ['p', '.description', '.content', 'div']
            for selector in desc_selectors:
                desc_elem = card.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if len(desc_text) > 20 and 'Specializing' in desc_text:
                        business_info['Description'] = desc_text
                        break
            
            if not business_info['Description']:
                full_text = card.get_text(strip=True)
                if len(full_text) > 50:
                    business_info['Description'] = full_text[:500] + '...' if len(full_text) > 500 else full_text
            
        except Exception as e:
            logger.error(f"Error extracting basic info from card: {e}")
        
        return business_info
    
    def extract_detailed_contact_info(self, detail_url: str) -> Dict[str, str]:
        """Extract detailed contact information from individual business page"""
        soup = self.get_page(detail_url)
        if not soup:
            return {}
        
        contact_info = {
            'Website': '',
            'Phone': '',
            'Address': ''
        }
        
        try:
            page_text = soup.get_text()
            
            # Look for website URLs
            excluded_domains = [
                'thevoiceofblackcincinnati.com', 'voiceofblackcincinnati.com',
                'mailchi.mp', 'list-manage.com', 'thevoiceofyourcustomer.com'
            ]
            
            # First, look for links in the page
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('http'):
                    if not any(social in href.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube']):
                        if not any(domain in href.lower() for domain in excluded_domains):
                            contact_info['Website'] = href
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
                    contact_info['Phone'] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                else:
                    contact_info['Phone'] = all_phones[0]
            
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
                contact_info['Address'] = address.strip()
            
        except Exception as e:
            logger.error(f"Error extracting contact info from {detail_url}: {e}")
        
        return contact_info
    
    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses"""
        logger.info("Starting clean business scraping...")
        
        # Get all business links
        business_links = self.extract_business_links(main_url)
        
        if not business_links:
            logger.warning("No business links found")
            return []
        
        logger.info(f"Found {len(business_links)} businesses to scrape")
        
        # Scrape each business
        for i, business in enumerate(business_links, 1):
            logger.info(f"Scraping business {i}/{len(business_links)}: {business.get('Name', 'Unknown')}")
            
            # Get detailed contact information
            contact_info = self.extract_detailed_contact_info(business['detail_url'])
            
            # Merge the information
            business.update(contact_info)
            self.businesses.append(business)
            
            # Be respectful - add delay between requests
            time.sleep(2)
        
        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses")
        return self.businesses
    
    def export_to_multiple_formats(self):
        """Export to multiple file formats"""
        if not self.businesses:
            logger.warning("No businesses to export")
            return
        
        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        
        # Remove duplicates based on name
        df = df.drop_duplicates(subset=['Name'], keep='first')
        
        # Clean up the data
        df = df[df['Name'].str.len() > 3]  # Remove entries with very short names
        
        try:
            # Export to Excel with multiple sheets
            with pd.ExcelWriter('clean_black_owned_businesses.xlsx', engine='openpyxl') as writer:
                # Main sheet with all data
                df.to_excel(writer, sheet_name='All Businesses', index=False)
                
                # Sheet with only businesses that have complete contact info
                complete_info = df[(df['Website'] != '') & (df['Phone'] != '') & (df['Address'] != '')]
                if not complete_info.empty:
                    complete_info.to_excel(writer, sheet_name='Complete Contact Info', index=False)
                
                # Sheet with businesses by category
                for category in df['Category'].unique():
                    if category and category != '':
                        category_df = df[df['Category'] == category]
                        sheet_name = category[:30]  # Excel sheet names have length limits
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
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info("Data exported to clean_black_owned_businesses.xlsx")
            print(f"✅ Successfully exported {len(df)} businesses to clean_black_owned_businesses.xlsx")
            
            # Export to CSV
            df.to_csv('clean_black_owned_businesses.csv', index=False)
            logger.info("Data also exported to clean_black_owned_businesses.csv")
            
            # Export to JSON
            df.to_json('clean_black_owned_businesses.json', orient='records', indent=2)
            logger.info("Data also exported to clean_black_owned_businesses.json")
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            print(f"❌ Error exporting data: {e}")

def main():
    """Main function to run the clean scraper"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    scraper = CleanBusinessScraper()
    
    print("🚀 Starting clean business directory scraper...")
    print(f"Target URL: {main_url}")
    print("This will filter out non-business entries and export to multiple formats...")
    
    # Scrape all businesses
    businesses = scraper.scrape_all_businesses(main_url)
    
    if businesses:
        # Export to multiple formats
        scraper.export_to_multiple_formats()
        
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
        
        print(f"\n📁 Files created:")
        print(f"  - clean_black_owned_businesses.xlsx (Excel with multiple sheets)")
        print(f"  - clean_black_owned_businesses.csv (CSV format)")
        print(f"  - clean_black_owned_businesses.json (JSON format)")
    else:
        print("❌ No businesses were scraped. Please check the website structure or try again.")

if __name__ == "__main__":
    main()
