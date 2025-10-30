# Business Directory Scraper

A Python web scraper designed to extract business information from The Voice of Black Cincinnati's business directory and export it to Excel format.

## Features

- Extracts business names, categories, descriptions, websites, phone numbers, and addresses
- Two scraping approaches: basic (follows individual links) and enhanced (extracts from main page)
- Exports data to Excel (.xlsx) and CSV formats
- Respectful scraping with delays between requests
- Error handling and logging
- Auto-adjusts Excel column widths

## Installation

1. Install Python 3.7 or higher
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start
```bash
python run_scraper.py
```

### Manual Usage

#### Basic Scraper (follows individual business links)
```bash
python business_scraper.py
```

#### Enhanced Scraper (extracts from main page cards)
```bash
python enhanced_business_scraper.py
```

## Output

The scraper will generate:
- `black_owned_businesses.xlsx` - Excel file with all business data
- `black_owned_businesses.csv` - CSV backup file (enhanced scraper only)

## Data Fields

Each business record includes:
- **Name**: Business name
- **Category**: Business category (e.g., "Restaurants, Eateries and Caterers")
- **Description**: Business description
- **Website**: Business website URL
- **Phone**: Phone number
- **Address**: Business address
- **Source_URL**: URL where the data was scraped from (basic scraper only)
- **Source**: Data source indicator (enhanced scraper only)

## Scraper Versions

### Basic Scraper (`business_scraper.py`)
- Follows individual business detail page links
- More comprehensive data extraction
- Slower but more thorough
- Better for getting complete contact information

### Enhanced Scraper (`enhanced_business_scraper.py`)
- Extracts data directly from main directory page
- Faster execution
- Good for getting basic business information
- May miss some detailed contact information

## Important Notes

### Legal and Ethical Considerations
- **Always respect the website's Terms of Service**
- **Check robots.txt** before scraping
- **Use reasonable delays** between requests (2+ seconds)
- **Don't overload the server** with too many concurrent requests

### Rate Limiting
The scrapers include built-in delays between requests to be respectful to the server:
- Basic scraper: 2-second delay between requests
- Enhanced scraper: Processes main page only (no additional delays needed)

### Error Handling
- Logs all errors and warnings
- Continues scraping even if individual businesses fail
- Provides detailed error messages

## Troubleshooting

### Common Issues

1. **No businesses found**
   - Check if the website structure has changed
   - Verify the target URL is accessible
   - Try the other scraper version

2. **Missing contact information**
   - The enhanced scraper may not capture all contact details
   - Try the basic scraper for more comprehensive data

3. **Connection errors**
   - Check your internet connection
   - The website might be temporarily unavailable
   - Try again later

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Verify all requirements are installed
3. Try both scraper versions
4. Check if the website structure has changed

## Requirements

- Python 3.7+
- requests
- beautifulsoup4
- pandas
- openpyxl
- lxml

## License

This scraper is for educational and research purposes. Always ensure compliance with website terms of service and applicable laws.
