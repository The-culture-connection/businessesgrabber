#!/usr/bin/env python3
"""
Test script to verify the improved scraper on a few sample businesses
"""

from improved_scraper import ImprovedBusinessScraper
import json

def main():
    print("Testing improved scraper on sample businesses...\n")

    scraper = ImprovedBusinessScraper()

    # Test URLs
    test_urls = [
        "https://thevoiceofblackcincinnati.com/black-owned-business/1-smokin-ash-hole/",
        "https://thevoiceofblackcincinnati.com/black-owned-business/a-mirage-beauty-salon/",
        "https://thevoiceofblackcincinnati.com/black-owned-business/a-better-you-counseling/"
    ]

    results = []

    for url in test_urls:
        print(f"Testing: {url}")
        print("-" * 70)

        business_info = scraper.extract_business_info(url)
        results.append(business_info)

        # Print results
        for key, value in business_info.items():
            if value:
                print(f"  {key:15s}: {value}")
        print("\n")

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for i, result in enumerate(results, 1):
        print(f"\nBusiness {i}: {result.get('Name', 'Unknown')}")
        print(f"  Has Email:   {'✓' if result.get('Email') else '✗'}")
        print(f"  Has Phone:   {'✓' if result.get('Phone') else '✗'}")
        print(f"  Has Address: {'✓' if result.get('Address') else '✗'}")
        print(f"  Has Website: {'✓' if result.get('Website') else '✗'}")

if __name__ == "__main__":
    main()
