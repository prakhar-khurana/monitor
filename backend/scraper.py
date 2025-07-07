import requests
from bs4 import BeautifulSoup
import os
import hashlib
import time
import re

def get_tor_session():
    session = requests.session()
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9150',
        'https': 'socks5h://127.0.0.1:9150'
    }
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    })
    return session, "Tor"

def get_clearnet_session():
    session = requests.session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    })
    return session, "Clearnet"

def is_queue_page(content):
    return bool(re.search(r'(queue|waiting|please wait|javascript refresh)', str(content).lower()))

def scrape_and_save(url, section=None):
    is_onion = url.endswith('.onion')
    session, session_type = get_tor_session() if is_onion else get_clearnet_session()
    max_attempts = 5
    attempt = 0
    wait_time = 5
    timeout = 30 if is_onion else 60

    print(f"Scraping {url} using {session_type} session")
    
    while attempt < max_attempts:
        try:
            res = session.get(url, timeout=timeout)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'lxml')
            
            if is_onion and is_queue_page(soup):
                print(f"Queue page detected for {url}. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                wait_time *= 2
                attempt += 1
                continue
            
            content = soup.find(id=section) if section else soup
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{hashlib.md5(url.encode()).hexdigest()}_{timestamp}.html"
            filepath = os.path.join("archive", filename)

            os.makedirs("archive", exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(content))

            print(f"Successfully scraped {url} using {session_type} session")
            return str(content), filepath
        except Exception as e:
            attempt += 1
            print(f"Scraping attempt {attempt} failed for {url} ({session_type}): {str(e)}")
            if attempt < max_attempts:
                time.sleep(wait_time)
                wait_time *= 2
            else:
                raise Exception(f"Failed to scrape {url} after {max_attempts} attempts using {session_type} session: {str(e)}")