#!/usr/bin/env python3
"""
Debug version of the business scraper to help identify issues
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_main_page():
    """Debug the main page to see what we can extract"""
    url = "https://thevoiceofblackcincinnati.com/black-owned-businesses/"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    print(f"🔍 Debugging main page: {url}")
    
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Successfully fetched main page")
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for "Read More" links
        read_more_links = soup.find_all('a', string=re.compile(r'Read More', re.IGNORECASE))
        print(f"📋 Found {len(read_more_links)} 'Read More' links")
        
        for i, link in enumerate(read_more_links[:5]):  # Show first 5
            href = link.get('href')
            full_url = urljoin(url, href)
            print(f"  {i+1}. {full_url}")
        
        # Look for any business-related links
        all_links = soup.find_all('a', href=True)
        business_links = []
        for link in all_links:
            href = link.get('href')
            if href and ('black-owned-businesses' in href or 'business' in href.lower()):
                full_url = urljoin(url, href)
                if full_url != url:
                    business_links.append(full_url)
        
        print(f"📋 Found {len(business_links)} total business-related links")
        
        # Show first few business links
        for i, link in enumerate(business_links[:5]):
            print(f"  {i+1}. {link}")
        
        return read_more_links, business_links
        
    except Exception as e:
        print(f"❌ Error fetching main page: {e}")
        return [], []

def debug_business_page(url):
    """Debug a specific business page to see what contact info we can extract"""
    print(f"\n🔍 Debugging business page: {url}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Successfully fetched business page")
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for website links
        links = soup.find_all('a', href=True)
        websites = []
        for link in links:
            href = link['href']
            if href.startswith('http') and not any(social in href.lower() for social in ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube']):
                if not any(domain in href.lower() for domain in ['thevoiceofblackcincinnati.com', 'voiceofblackcincinnati.com']):
                    websites.append(href)
        
        print(f"🌐 Found {len(websites)} potential website links:")
        for website in websites[:3]:  # Show first 3
            print(f"  - {website}")
        
        # Look for phone numbers
        page_text = soup.get_text()
        phone_patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, page_text)
            phones.extend(matches)
        
        print(f"📞 Found {len(phones)} potential phone numbers:")
        for phone in phones[:3]:  # Show first 3
            print(f"  - {phone}")
        
        # Look for addresses
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Circle|Ct|Court|Place|Pl)',
            r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
        ]
        
        addresses = []
        for pattern in address_patterns:
            matches = re.findall(pattern, page_text)
            addresses.extend(matches)
        
        print(f"📍 Found {len(addresses)} potential addresses:")
        for address in addresses[:3]:  # Show first 3
            print(f"  - {address}")
        
        # Look for structured contact sections
        contact_sections = soup.find_all(['div', 'section'], class_=re.compile(r'contact|info|details|location', re.I))
        print(f"📋 Found {len(contact_sections)} potential contact sections")
        
        for i, section in enumerate(contact_sections[:2]):  # Show first 2
            print(f"  Section {i+1}: {section.get_text()[:100]}...")
        
        return {
            'websites': websites,
            'phones': phones,
            'addresses': addresses,
            'contact_sections': len(contact_sections)
        }
        
    except Exception as e:
        print(f"❌ Error fetching business page: {e}")
        return {}

def main():
    """Main debug function"""
    print("🐛 Business Scraper Debug Tool")
    print("=" * 50)
    
    # Debug main page
    read_more_links, business_links = debug_main_page()
    
    if business_links:
        print(f"\n🔍 Testing first business page...")
        debug_business_page(business_links[0])
    
    if read_more_links:
        print(f"\n🔍 Testing first 'Read More' link...")
        href = read_more_links[0].get('href')
        if href:
            full_url = urljoin("https://thevoiceofblackcincinnati.com/black-owned-businesses/", href)
            debug_business_page(full_url)

if __name__ == "__main__":
    main()
