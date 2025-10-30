#!/usr/bin/env python3
"""
Test script to verify contact information extraction
"""

from targeted_business_scraper import TargetedBusinessScraper

def test_single_business():
    """Test contact extraction on a single business"""
    scraper = TargetedBusinessScraper()
    
    # Test with the first business we know has contact info
    test_url = "https://thevoiceofblackcincinnati.com/black-owned-business/1-smokin-ash-hole/"
    
    print(f"🧪 Testing contact extraction for: {test_url}")
    
    contact_info = scraper.extract_detailed_contact_info(test_url)
    
    print(f"\n📊 Results:")
    print(f"Website: {contact_info.get('Website', 'Not found')}")
    print(f"Phone: {contact_info.get('Phone', 'Not found')}")
    print(f"Address: {contact_info.get('Address', 'Not found')}")
    
    # Check if we got any contact info
    has_contact = any(contact_info.values())
    if has_contact:
        print(f"\n✅ Successfully extracted contact information!")
    else:
        print(f"\n❌ No contact information extracted")
    
    return contact_info

if __name__ == "__main__":
    test_single_business()
