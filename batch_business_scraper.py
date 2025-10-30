#!/usr/bin/env python3
"""
Batch business scraper that processes businesses in groups of 50
Saves JSON file after each batch for real-time progress monitoring
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs
import logging
from typing import Dict, List, Optional
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchBusinessScraper:
    def __init__(self, base_url: str = "https://thevoiceofblackcincinnati.com", batch_size: int = 50):
        self.base_url = base_url
        self.batch_size = batch_size
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
        self.json_filename = "batch_black_owned_businesses.json"
        
    def save_to_json(self):
        """Save current businesses to JSON file"""
        try:
            with open(self.json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.businesses, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved {len(self.businesses)} businesses to {self.json_filename}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def find_business_links_simple(self, main_url: str) -> List[str]:
        """Find business links using a simpler approach"""
        business_links = []
        pages_to_check = [main_url]
        processed_pages = set()
        
        logger.info("Finding business links...")
        
        # First, get all "Read More" links from main page
        soup = self.get_page(main_url)
        if soup:
            read_more_links = soup.find_all('a', string=re.compile(r'Read More', re.IGNORECASE))
            for link in read_more_links:
                href = link.get('href')
                if href and 'black-owned-business/' in href:
                    full_url = urljoin(main_url, href)
                    business_links.append(full_url)
            
            # Look for pagination
            pagination_links = soup.find_all('a', href=True)
            for link in pagination_links:
                href = link.get('href')
                if href and ('page' in href.lower() or 'paged' in href.lower()):
                    full_url = urljoin(main_url, href)
                    if full_url not in processed_pages:
                        pages_to_check.append(full_url)
        
        # Check a few more pages for pagination
        for page_url in pages_to_check[:5]:  # Limit to first 5 pages
            if page_url in processed_pages:
                continue
            processed_pages.add(page_url)
            
            soup = self.get_page(page_url)
            if soup:
                read_more_links = soup.find_all('a', string=re.compile(r'Read More', re.IGNORECASE))
                for link in read_more_links:
                    href = link.get('href')
                    if href and 'black-owned-business/' in href:
                        full_url = urljoin(page_url, href)
                        if full_url not in business_links:
                            business_links.append(full_url)
            
            time.sleep(1)  # Be respectful
        
        # Remove duplicates
        unique_links = list(set(business_links))
        logger.info(f"Found {len(unique_links)} unique business links")
        return unique_links
    
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
            
        except Exception as e:
            logger.error(f"Error extracting business info from {business_url}: {e}")
        
        return business_info
    
    def scrape_businesses_in_batches(self, main_url: str) -> List[Dict[str, str]]:
        """Scrape businesses in batches of 50"""
        logger.info("Starting batch business scraping...")
        
        # Find all business links
        business_links = self.find_business_links_simple(main_url)
        
        if not business_links:
            logger.warning("No business links found")
            return []
        
        logger.info(f"Found {len(business_links)} total business links to scrape")
        
        # Process in batches
        total_batches = (len(business_links) + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(business_links))
            batch_links = business_links[start_idx:end_idx]
            
            print(f"\n🔄 Processing Batch {batch_num + 1}/{total_batches} ({len(batch_links)} businesses)")
            print(f"   Businesses {start_idx + 1}-{end_idx} of {len(business_links)}")
            
            # Process each business in this batch
            for i, business_url in enumerate(batch_links, 1):
                global_idx = start_idx + i
                print(f"   📋 Scraping business {global_idx}/{len(business_links)}: {business_url}")
                
                business_info = self.extract_business_info(business_url)
                if business_info and business_info.get('Name'):
                    self.businesses.append(business_info)
                    print(f"   ✅ Added: {business_info.get('Name', 'Unknown')}")
                else:
                    print(f"   ⚠️  Skipped: No valid business info found")
                
                # Be respectful - add delay between requests
                time.sleep(2)
            
            # Save after each batch
            self.save_to_json()
            print(f"💾 Batch {batch_num + 1} complete! Total businesses: {len(self.businesses)}")
            
            # Ask user if they want to continue
            if batch_num < total_batches - 1:
                continue_input = input(f"\nContinue to batch {batch_num + 2}? (y/n): ").strip().lower()
                if continue_input != 'y':
                    print("⏹️  Stopping at user request")
                    break
        
        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses")
        return self.businesses
    
    def export_to_excel(self, filename: str = "batch_black_owned_businesses.xlsx"):
        """Export scraped data to Excel file"""
        if not self.businesses:
            logger.warning("No businesses to export")
            return
        
        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        df = df.drop_duplicates(subset=['Name'], keep='first')
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
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
            
            logger.info(f"Data exported to {filename}")
            print(f"✅ Successfully exported {len(self.businesses)} businesses to {filename}")
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            print(f"❌ Error exporting to Excel: {e}")

def main():
    """Main function to run the batch scraper"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    scraper = BatchBusinessScraper(batch_size=50)
    
    print("🚀 Starting BATCH business directory scraper...")
    print(f"Target URL: {main_url}")
    print("This will process businesses in batches of 50...")
    print("JSON file will be updated after each batch!")
    
    # Scrape all businesses in batches
    businesses = scraper.scrape_businesses_in_batches(main_url)
    
    if businesses:
        # Export to Excel
        scraper.export_to_excel()
        
        # Print summary
        print(f"\n📊 Final Scraping Summary:")
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
        print(f"  - {scraper.json_filename} (Updated after each batch)")
        print(f"  - batch_black_owned_businesses.xlsx (Final Excel file)")
    else:
        print("❌ No businesses were scraped. Please check the website structure or try again.")

if __name__ == "__main__":
    main()
