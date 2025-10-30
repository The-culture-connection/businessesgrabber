#!/usr/bin/env python3
"""
Web scraper for The Voice of Black Cincinnati business directory
Extracts business information and exports to Excel
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

class BusinessScraper:
    def __init__(self, base_url: str = "https://thevoiceofblackcincinnati.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.businesses = []
        
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_business_links(self, main_url: str) -> List[str]:
        """Extract all business detail page links from the main directory"""
        soup = self.get_page(main_url)
        if not soup:
            return []
        
        business_links = []
        
        # Look for business links - they typically contain business names or IDs
        # The website seems to have business cards with "Read More..." links
        read_more_links = soup.find_all('a', string=re.compile(r'Read More', re.IGNORECASE))
        
        for link in read_more_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                business_links.append(full_url)
        
        # Also look for any other business-related links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and ('black-owned-businesses' in href or 'business' in href.lower()):
                full_url = urljoin(self.base_url, href)
                if full_url not in business_links and full_url != main_url:
                    business_links.append(full_url)
        
        logger.info(f"Found {len(business_links)} business links")
        return business_links
    
    def extract_business_info(self, business_url: str) -> Dict[str, str]:
        """Extract detailed business information from individual business page"""
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
            # Extract business name (usually in h1 or h2)
            name_selectors = ['h1', 'h2', '.business-name', '.title']
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem and name_elem.get_text(strip=True):
                    business_info['Name'] = name_elem.get_text(strip=True)
                    break
            
            # Extract category
            category_selectors = ['.category', '.business-category', '[class*="category"]']
            for selector in category_selectors:
                category_elem = soup.select_one(selector)
                if category_elem and category_elem.get_text(strip=True):
                    business_info['Category'] = category_elem.get_text(strip=True)
                    break
            
            # Extract description
            desc_selectors = ['.description', '.business-description', 'p', '.content']
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem and len(desc_elem.get_text(strip=True)) > 20:
                    business_info['Description'] = desc_elem.get_text(strip=True)
                    break
            
            # Extract contact information
            page_text = soup.get_text()
            
            # Look for website URLs
            website_patterns = [
                r'https?://[^\s<>"]+',
                r'www\.[^\s<>"]+',
            ]
            for pattern in website_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    if any(domain in match.lower() for domain in ['facebook', 'instagram', 'linkedin', 'twitter']):
                        continue
                    if '.' in match and len(match) > 10:
                        business_info['Website'] = match
                        break
                if business_info['Website']:
                    break
            
            # Look for phone numbers
            phone_patterns = [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            ]
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    business_info['Phone'] = matches[0]
                    break
            
            # Look for addresses (this is more complex and may need refinement)
            address_patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)',
                r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
            ]
            for pattern in address_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    business_info['Address'] = matches[0]
                    break
            
            # Try to find structured contact information
            contact_sections = soup.find_all(['div', 'section'], class_=re.compile(r'contact|info|details', re.I))
            for section in contact_sections:
                section_text = section.get_text()
                
                # Extract website from contact section
                if not business_info['Website']:
                    links = section.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if href.startswith('http') and not any(social in href.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter']):
                            business_info['Website'] = href
                            break
                
                # Extract phone from contact section
                if not business_info['Phone']:
                    phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', section_text)
                    if phone_matches:
                        business_info['Phone'] = phone_matches[0]
                
                # Extract address from contact section
                if not business_info['Address']:
                    address_matches = re.findall(r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr)', section_text)
                    if address_matches:
                        business_info['Address'] = address_matches[0]
            
        except Exception as e:
            logger.error(f"Error extracting business info from {business_url}: {e}")
        
        return business_info
    
    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses"""
        logger.info("Starting business scraping...")
        
        # Get all business links
        business_links = self.extract_business_links(main_url)
        
        if not business_links:
            logger.warning("No business links found")
            return []
        
        # Scrape each business
        for i, business_url in enumerate(business_links, 1):
            logger.info(f"Scraping business {i}/{len(business_links)}: {business_url}")
            
            business_info = self.extract_business_info(business_url)
            if business_info:
                self.businesses.append(business_info)
            
            # Be respectful - add delay between requests
            time.sleep(2)
        
        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses")
        return self.businesses
    
    def export_to_excel(self, filename: str = "black_owned_businesses.xlsx"):
        """Export scraped data to Excel file"""
        if not self.businesses:
            logger.warning("No businesses to export")
            return
        
        df = pd.DataFrame(self.businesses)
        
        # Clean up the data
        df = df.fillna('')
        
        # Export to Excel
        try:
            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"Data exported to {filename}")
            print(f"✅ Successfully exported {len(self.businesses)} businesses to {filename}")
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            print(f"❌ Error exporting to Excel: {e}")

def main():
    """Main function to run the scraper"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    scraper = BusinessScraper()
    
    print("🚀 Starting business directory scraper...")
    print(f"Target URL: {main_url}")
    print("This may take several minutes depending on the number of businesses...")
    
    # Scrape all businesses
    businesses = scraper.scrape_all_businesses(main_url)
    
    if businesses:
        # Export to Excel
        scraper.export_to_excel()
        
        # Print summary
        print(f"\n📊 Scraping Summary:")
        print(f"Total businesses found: {len(businesses)}")
        
        # Show sample of data
        if businesses:
            print(f"\n📋 Sample business data:")
            sample = businesses[0]
            for key, value in sample.items():
                if value:
                    print(f"  {key}: {value[:100]}{'...' if len(str(value)) > 100 else ''}")
    else:
        print("❌ No businesses were scraped. Please check the website structure or try again.")

if __name__ == "__main__":
    main()
