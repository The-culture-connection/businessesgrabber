#!/usr/bin/env python3
"""
Enhanced web scraper for The Voice of Black Cincinnati business directory
Specifically designed for the website structure observed
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

class EnhancedBusinessScraper:
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
    
    def extract_business_cards(self, main_url: str) -> List[Dict[str, str]]:
        """Extract business information from the main directory page cards"""
        soup = self.get_page(main_url)
        if not soup:
            return []
        
        businesses = []
        
        # Look for business cards - they seem to be in a structured format
        # Based on the website structure, businesses appear to be in cards or sections
        
        # Try different selectors for business cards
        card_selectors = [
            'div[class*="business"]',
            'div[class*="card"]',
            'article',
            '.entry',
            '.post'
        ]
        
        business_cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                business_cards.extend(cards)
                break
        
        # If no specific cards found, look for any divs that might contain business info
        if not business_cards:
            # Look for divs that contain business names and descriptions
            all_divs = soup.find_all('div')
            for div in all_divs:
                text = div.get_text(strip=True)
                if len(text) > 50 and any(keyword in text.lower() for keyword in ['specializing', 'black-owned', 'restaurant', 'service', 'business']):
                    business_cards.append(div)
        
        logger.info(f"Found {len(business_cards)} potential business cards")
        
        for i, card in enumerate(business_cards):
            try:
                business_info = self.extract_business_from_card(card)
                if business_info and business_info.get('Name'):
                    businesses.append(business_info)
                    logger.info(f"Extracted business {i+1}: {business_info.get('Name', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error processing card {i}: {e}")
                continue
        
        return businesses
    
    def extract_business_from_card(self, card) -> Dict[str, str]:
        """Extract business information from a single card element"""
        business_info = {
            'Name': '',
            'Category': '',
            'Description': '',
            'Website': '',
            'Phone': '',
            'Address': '',
            'Source': 'Main Page'
        }
        
        try:
            # Extract business name - look for headings or bold text
            name_selectors = ['h1', 'h2', 'h3', 'h4', 'strong', 'b', '.title', '.name']
            for selector in name_selectors:
                name_elem = card.select_one(selector)
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    if name_text and len(name_text) > 2 and len(name_text) < 100:
                        business_info['Name'] = name_text
                        break
            
            # If no name found in headings, look for the first significant text
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
            
            # If no description found, use the card text
            if not business_info['Description']:
                full_text = card.get_text(strip=True)
                if len(full_text) > 50:
                    business_info['Description'] = full_text[:500] + '...' if len(full_text) > 500 else full_text
            
            # Look for contact information in the card
            card_text = card.get_text()
            
            # Extract website
            website_patterns = [
                r'https?://[^\s<>"]+',
                r'www\.[^\s<>"]+',
            ]
            for pattern in website_patterns:
                matches = re.findall(pattern, card_text)
                for match in matches:
                    if not any(social in match.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter']):
                        business_info['Website'] = match
                        break
                if business_info['Website']:
                    break
            
            # Extract phone
            phone_patterns = [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            ]
            for pattern in phone_patterns:
                matches = re.findall(pattern, card_text)
                if matches:
                    business_info['Phone'] = matches[0]
                    break
            
            # Extract address
            address_patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)',
                r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
            ]
            for pattern in address_patterns:
                matches = re.findall(pattern, card_text)
                if matches:
                    business_info['Address'] = matches[0]
                    break
            
        except Exception as e:
            logger.error(f"Error extracting business info from card: {e}")
        
        return business_info
    
    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses"""
        logger.info("Starting enhanced business scraping...")
        
        # Extract businesses from main page
        businesses = self.extract_business_cards(main_url)
        
        if not businesses:
            logger.warning("No businesses found on main page")
            return []
        
        self.businesses = businesses
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
        
        # Remove duplicates based on name
        df = df.drop_duplicates(subset=['Name'], keep='first')
        
        # Export to Excel
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Black Owned Businesses', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Black Owned Businesses']
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
    
    def export_to_csv(self, filename: str = "black_owned_businesses.csv"):
        """Export scraped data to CSV file as backup"""
        if not self.businesses:
            return
        
        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        df.to_csv(filename, index=False)
        logger.info(f"Data also exported to {filename}")

def main():
    """Main function to run the scraper"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    scraper = EnhancedBusinessScraper()
    
    print("🚀 Starting enhanced business directory scraper...")
    print(f"Target URL: {main_url}")
    print("This will extract business information from the main directory page...")
    
    # Scrape all businesses
    businesses = scraper.scrape_all_businesses(main_url)
    
    if businesses:
        # Export to Excel
        scraper.export_to_excel()
        scraper.export_to_csv()
        
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
        
        # Show categories found
        categories = set(b.get('Category', '') for b in businesses if b.get('Category'))
        if categories:
            print(f"\n🏷️ Categories found: {', '.join(sorted(categories))}")
    else:
        print("❌ No businesses were scraped. Please check the website structure or try again.")

if __name__ == "__main__":
    main()
