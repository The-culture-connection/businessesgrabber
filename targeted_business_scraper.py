#!/usr/bin/env python3
"""
Targeted web scraper for The Voice of Black Cincinnati business directory
Specifically designed to extract 'Read More' links and scrape detailed contact information
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

class TargetedBusinessScraper:
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
    
    def extract_read_more_links(self, main_url: str) -> List[Dict[str, str]]:
        """Extract 'Read More' links and basic business info from main page"""
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
                
                # Try to extract basic info from the card containing this link
                card = link.find_parent(['div', 'article', 'section'])
                if not card:
                    # Look for parent elements that might contain business info
                    card = link.find_parent()
                
                business_info = self.extract_basic_info_from_card(card, full_url)
                business_links.append(business_info)
        
        # Also look for any other business detail links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and ('black-owned-businesses' in href or 'business' in href.lower()):
                full_url = urljoin(self.base_url, href)
                # Skip if already found
                if not any(b['detail_url'] == full_url for b in business_links):
                    card = link.find_parent(['div', 'article', 'section'])
                    if not card:
                        card = link.find_parent()
                    business_info = self.extract_basic_info_from_card(card, full_url)
                    business_links.append(business_info)
        
        logger.info(f"Total business links found: {len(business_links)}")
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
            
            # Look for website URLs - be more specific and exclude newsletter/social links
            excluded_domains = [
                'thevoiceofblackcincinnati.com', 'voiceofblackcincinnati.com',
                'mailchi.mp', 'list-manage.com', 'thevoiceofyourcustomer.com'
            ]
            
            # First, look for links in the page that might be business websites
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('http'):
                    # Skip social media and excluded domains
                    if not any(social in href.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube']):
                        if not any(domain in href.lower() for domain in excluded_domains):
                            # Look for business-related text near the link
                            link_text = link.get_text(strip=True).lower()
                            parent_text = link.parent.get_text(strip=True).lower() if link.parent else ""
                            
                            # Check if this looks like a business website link
                            if any(keyword in link_text or keyword in parent_text for keyword in ['website', 'visit', 'online', 'order', 'menu', 'services']):
                                contact_info['Website'] = href
                                break
                            # If no specific keywords, still take the first valid link
                            elif not contact_info['Website']:
                                contact_info['Website'] = href
            
            # If no website found in links, try text patterns
            if not contact_info['Website']:
                website_patterns = [
                    r'https?://[^\s<>"]+',
                    r'www\.[^\s<>"]+',
                ]
                for pattern in website_patterns:
                    matches = re.findall(pattern, page_text)
                    for match in matches:
                        if not any(social in match.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube']):
                            if not any(domain in match.lower() for domain in excluded_domains):
                                contact_info['Website'] = match
                                break
                    if contact_info['Website']:
                        break
            
            # Look for phone numbers with more specific patterns
            phone_patterns = [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
                r'Phone:\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'Call:\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            ]
            
            # Get all phone numbers and pick the first valid one
            all_phones = []
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                all_phones.extend(matches)
            
            if all_phones:
                # Clean up the first phone number
                phone = re.sub(r'[^\d]', '', all_phones[0])
                if len(phone) == 10:
                    contact_info['Phone'] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                else:
                    contact_info['Phone'] = all_phones[0]
            
            # Look for addresses with more specific patterns
            address_patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)',
                r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
                r'Address:\s*([^\n\r]+)',
                r'Location:\s*([^\n\r]+)',
            ]
            
            # Get all addresses and pick the first valid one
            all_addresses = []
            for pattern in address_patterns:
                matches = re.findall(pattern, page_text)
                all_addresses.extend(matches)
            
            if all_addresses:
                # Clean up the first address
                address = all_addresses[0].strip()
                # Remove any extra text that might have been captured
                address = re.sub(r'\s+', ' ', address)
                # Remove navigation text and other artifacts
                address = re.sub(r'(Post navigation|Previous Business|Park Place).*', '', address)
                address = address.strip()
                contact_info['Address'] = address
            
            # Try to find structured contact information sections
            contact_sections = soup.find_all(['div', 'section'], class_=re.compile(r'contact|info|details|location', re.I))
            for section in contact_sections:
                section_text = section.get_text()
                
                # Extract website from contact section
                if not contact_info['Website']:
                    section_links = section.find_all('a', href=True)
                    for link in section_links:
                        href = link['href']
                        if href.startswith('http') and not any(social in href.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter']):
                            if not any(domain in href.lower() for domain in excluded_domains):
                                contact_info['Website'] = href
                                break
                
                # Extract phone from contact section
                if not contact_info['Phone']:
                    phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', section_text)
                    if phone_matches:
                        phone = re.sub(r'[^\d]', '', phone_matches[0])
                        if len(phone) == 10:
                            contact_info['Phone'] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                        else:
                            contact_info['Phone'] = phone_matches[0]
                
                # Extract address from contact section
                if not contact_info['Address']:
                    address_matches = re.findall(r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr)', section_text)
                    if address_matches:
                        contact_info['Address'] = address_matches[0]
            
            logger.info(f"Extracted contact info for {detail_url}: Website={bool(contact_info['Website'])}, Phone={bool(contact_info['Phone'])}, Address={bool(contact_info['Address'])}")
            
        except Exception as e:
            logger.error(f"Error extracting contact info from {detail_url}: {e}")
        
        return contact_info
    
    def scrape_all_businesses(self, main_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all businesses with detailed contact info"""
        logger.info("Starting targeted business scraping...")
        
        # First, get all business links from main page
        business_links = self.extract_read_more_links(main_url)
        
        if not business_links:
            logger.warning("No business links found")
            return []
        
        logger.info(f"Found {len(business_links)} businesses to scrape")
        
        # Now scrape detailed info from each business page
        for i, business in enumerate(business_links, 1):
            logger.info(f"Scraping detailed info for business {i}/{len(business_links)}: {business.get('Name', 'Unknown')}")
            
            # Get detailed contact information
            contact_info = self.extract_detailed_contact_info(business['detail_url'])
            
            # Merge the information
            business.update(contact_info)
            self.businesses.append(business)
            
            # Be respectful - add delay between requests
            time.sleep(2)
        
        logger.info(f"Scraping completed. Found {len(self.businesses)} businesses with detailed info")
        return self.businesses
    
    def export_to_excel(self, filename: str = "black_owned_businesses_detailed.xlsx"):
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
    
    def export_to_csv(self, filename: str = "black_owned_businesses_detailed.csv"):
        """Export scraped data to CSV file as backup"""
        if not self.businesses:
            return
        
        df = pd.DataFrame(self.businesses)
        df = df.fillna('')
        df.to_csv(filename, index=False)
        logger.info(f"Data also exported to {filename}")

def main():
    """Main function to run the targeted scraper"""
    main_url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    scraper = TargetedBusinessScraper()
    
    print("🚀 Starting targeted business directory scraper...")
    print(f"Target URL: {main_url}")
    print("This will extract 'Read More' links and scrape detailed contact information...")
    print("This may take several minutes depending on the number of businesses...")
    
    # Scrape all businesses
    businesses = scraper.scrape_all_businesses(main_url)
    
    if businesses:
        # Export to Excel
        scraper.export_to_excel()
        scraper.export_to_csv()
        
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
