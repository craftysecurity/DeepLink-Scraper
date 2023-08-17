## README.md

---

# Deeplink Scraper

Deeplink Scraper is a Python CLI tool designed to extract deeplinks from web pages. Its useful for appsec teams and pentesters that need to find deeplinks and the paramters that can be passed with them without having to look through code for the builders or manually search the web application. Just provide an Android manifest file and it will parse it and build the correct schemes. Then scrape web pages for them using regex, capturing any matching deeplinks and parameters, including multiple scheme/URL types like "myapp:\\item?=1&category?=2" or HTTP/HTTPS "http\s://myapp.onelink.me/item?=1&category?=2/".

## Features

- **Manifest Parsing**: Extracts schemes from an Android manifest file.
- **Scheme Matching**: Identifies and captures deeplinks based on the extracted schemes from web pages.
- **Supports Multiple Schemes**: Handles both standard (HTTP/HTTPS) and custom schemes (e.g., `myapp://`).
- **Threaded Scraping**: Supports multithreaded operation for efficient scraping.
- **Customizable**: Options to provide single or multiple URLs, set delays, and ignore certain patterns.
- **Recusive**: Option to recursively search webpages for deeplinks from a base url.

## Requirements

- Python 3.x
- `requests` 
- `lxml` 
- `beautifulsoup4` 

## Installation

1. **Clone the repository**:
   ```
   git clone https://github.com/craftysecurity/deeplink-scraper.git
   cd deeplink-scraper
   ```

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

## Usage

The Deeplink Extractor can be run from the command line with various options to customize its operation.

### Command-line Options

- `-u`: Single URL to scrape.
- `-U`: File containing a list of URLs to scrape, one per line.
- `-uf`: Single URL to scrape recursively, following links on the page.
- `-m`: Android manifest file to parse for extracting URL schemes (required).
- `-o`: Output file to save extracted deeplinks (required).
- `-t`: Time delay between requests in seconds (default: 3 seconds).
- `-T`: Number of threads to run (default: 4).
- `-i`: Comma-separated list of URL patterns or schemes to ignore.

### Example Usage

**Single URL with manifest file**:
```bash
python3 deeplink-scraper.py -u "https://example.com" -m manifest.xml -o deeplinks.txt
```

**Multiple URLs from a file**:
```bash
python3 deeplink-scraper.py -U urls.txt -m manifest.xml -o deeplinks.txt
```

**Recursive scraping**:
```bash
python3 deeplink-scraper.py -uf "https://example.com" -m manifest.xml -o deeplinks.txt
```

## Output

The extracted deeplinks are saved to the specified output file -o. 

## TODO 

- [ ] **Add iOS/Info.plist Support**
- [ ] **Add cookie/authentication Support**

