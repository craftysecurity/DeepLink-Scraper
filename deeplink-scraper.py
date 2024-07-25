import os
import time
import argparse
import threading
import requests
from lxml import etree
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, parse_qs
import urllib3
import plistlib
import zipfile
import tempfile
import subprocess

def print_ascii_art():
    purple = "\033[95m"
    reset = "\033[0m"
    art = f"""{purple}
    ____                 _     _       _       ____                               
   |  _ \  ___  ___ _ __| |   (_)_ __ | | __  / ___|  ___ _ __ __ _ _ __   ___ _ __ 
   | | | |/ _ \/ _ \ '_ \ |   | | '_ \| |/ / \___ \ / __| '__/ _` | '_ \ / _ \ '__|
   | |_| |  __/  __/ |_) | |___| | | |   <   ___) | (__| | | (_| | |_) |  __/ |   
   |____/ \___|\___| .__/|_____|_|_| |_|_|\_\ |____/ \___|_|  \__,_| .__/ \___|_|   
                   |_|                                             |_|              
                                                                          ___
                                                                         /
                                                                     O===[=====>
                                                                        /
                                                                    ___/
    {reset}"""
    print(art)

def parse_manifest(manifest_file):
    namespaces = {'android': 'http://schemas.android.com/apk/res/android'}
    with open(manifest_file, 'r') as file:
        tree = etree.parse(file)
    root = tree.getroot()
    package_name = root.get("package")
    schemes = []

    for activity in root.findall(".//intent-filter", namespaces):
        for data in activity.findall(".//data", namespaces):
            scheme = data.get("{http://schemas.android.com/apk/res/android}scheme")
            host = data.get("{http://schemas.android.com/apk/res/android}host")
            pathPrefix = data.get("{http://schemas.android.com/apk/res/android}pathPrefix")
            
            if scheme and host:
                if pathPrefix:
                    schemes.append(f"{scheme}://{host}{pathPrefix}")
                else:
                    schemes.append(f"{scheme}://{host}")
            elif scheme:
                schemes.append(f"{scheme}://")

    return package_name, schemes

def parse_info_plist(plist_file):
    with open(plist_file, 'rb') as file:
        plist = plistlib.load(file)
    
    bundle_id = plist.get('CFBundleIdentifier', '')
    schemes = []

    url_types = plist.get('CFBundleURLTypes', [])
    for url_type in url_types:
        schemes.extend(url_type.get('CFBundleURLSchemes', []))

    return bundle_id, schemes

def extract_info_plist_from_ipa(ipa_file):
    with zipfile.ZipFile(ipa_file, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            if file_info.filename.endswith('Info.plist'):
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(zip_ref.read(file_info.filename))
                    temp_file_path = temp_file.name
                return temp_file_path
    return None

def extract_manifest_from_apk(apk_file):
    try:
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use apktool to decode the APK
            subprocess.run(['apktool', 'd', '-f', '-o', temp_dir, apk_file], check=True)
            
            # Path to the extracted AndroidManifest.xml
            manifest_path = os.path.join(temp_dir, 'AndroidManifest.xml')
            
            if os.path.exists(manifest_path):
                return manifest_path
            else:
                print("AndroidManifest.xml not found in the extracted APK.")
                return None
    except subprocess.CalledProcessError:
        print("Error extracting AndroidManifest.xml. Make sure apktool is installed and in your PATH.")
        return None

def fetch_content(url, user_agent):
    try:
        headers = {"User-Agent": user_agent}
        http = urllib3.PoolManager()
        response = http.request('GET', url, headers=headers, redirect=False)
        
        if response.status in (301, 302, 303, 307, 308):
            redirect_url = response.headers['Location']
            parsed_url = urlparse(redirect_url)
            if parsed_url.scheme not in ('http', 'https'):
                return redirect_url  # Return the deeplink directly
            else:
                return fetch_content(redirect_url, user_agent)  # Follow HTTP(S) redirects
        
        return response.data.decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def find_deeplinks(content, schemes):
    found_deeplinks = set()
    if isinstance(content, str) and any(content.startswith(scheme) for scheme in schemes):
        found_deeplinks.add(content)
    else:
        for scheme in schemes:
            pattern = rf'{re.escape(scheme)}[^\s"\'>]+'
            matches = re.findall(pattern, content)
            found_deeplinks.update(matches)
    return found_deeplinks

def scrape_page(url, user_agent, schemes, ignore_list, found_deeplinks, lock):
    content = fetch_content(url, user_agent)
    if content:
        page_deeplinks = find_deeplinks(content, schemes)
        with lock:
            for deeplink in page_deeplinks:
                if not any(ignored in deeplink for ignored in ignore_list):
                    found_deeplinks.add(deeplink)
                    print(f"Found deeplink: {deeplink}\n")

def main():
    print_ascii_art()
    
    parser = argparse.ArgumentParser(description="Deeplink Extractor for Android and iOS Applications")
    parser.add_argument("-u", type=str, help="Single URL to scrape")
    parser.add_argument("-U", type=str, help="File with list of URLs to scrape")
    parser.add_argument("-uf", type=str, help="Single URL to scrape recursively")
    parser.add_argument("-m", type=str, required=True, help="Android manifest file, APK file, iOS Info.plist file, or iOS .ipa file")
    parser.add_argument("-o", type=str, required=True, help="Output file to save results")
    parser.add_argument("-t", type=int, default=3, help="Time delay between requests (seconds)")
    parser.add_argument("-T", type=int, default=4, help="Number of threads to run")
    parser.add_argument("-i", type=str, help="Comma-separated list of URL patterns or schemes to ignore")
    
    args = parser.parse_args()
    
    if args.m.endswith('.xml'):
        package_name, schemes = parse_manifest(args.m)
        user_agent = "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.99 Mobile Safari/537.36"
    elif args.m.endswith('.apk'):
        manifest_path = extract_manifest_from_apk(args.m)
        if manifest_path:
            package_name, schemes = parse_manifest(manifest_path)
            os.unlink(manifest_path)  # Delete the temporary file
            user_agent = "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.99 Mobile Safari/537.36"
        else:
            print("Could not extract AndroidManifest.xml from the provided .apk file.")
            return
    elif args.m.endswith('.plist'):
        package_name, schemes = parse_info_plist(args.m)
        user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    elif args.m.endswith('.ipa'):
        plist_path = extract_info_plist_from_ipa(args.m)
        if plist_path:
            package_name, schemes = parse_info_plist(plist_path)
            os.unlink(plist_path)  # Delete the temporary file
            user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        else:
            print("Could not extract Info.plist from the provided .ipa file.")
            return
    else:
        print("Unsupported file format. Please use .xml or .apk for Android, .plist or .ipa for iOS.")
        return

    if not schemes:
        print("No exposed activities/intents with schemes found in the manifest/plist.")
        return

    schemes_file = f"{package_name}_schemes.txt"
    with open(schemes_file, 'w') as f:
        for scheme in schemes:
            f.write(f"{scheme}\n")
    
    found_deeplinks = set()
    lock = threading.Lock()
    
    ignore_list = args.i.split(",") if args.i else []

    def scrape_wrapper(url):
        print(f"Scraping URL: {url}\n")
        scrape_page(url, user_agent, schemes, ignore_list, found_deeplinks, lock)
        time.sleep(args.t)
    
    if args.u:
        scrape_wrapper(args.u)
    
    if args.U:
        with open(args.U, 'r') as file:
            urls = [line.strip() for line in file.readlines()]
        for url in urls:
            scrape_wrapper(url)
    
    if args.uf:
        urls_to_scrape = [args.uf]
        scraped_urls = set()
        while urls_to_scrape:
            url = urls_to_scrape.pop()
            if url in scraped_urls:
                continue
            scrape_wrapper(url)
            scraped_urls.add(url)
            response = requests.get(url, headers={"User-Agent": user_agent})
            soup = BeautifulSoup(response.content, 'html.parser')
            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                if urlparse(full_url).netloc == urlparse(url).netloc:
                    urls_to_scrape.append(full_url)
    
    with open(args.o, 'w') as output_file:
        for deeplink in found_deeplinks:
            output_file.write(f"{deeplink}\n")
    
    print("Deeplink scrape complete.")

if __name__ == "__main__":
    main()
