import requests
from bs4 import BeautifulSoup
import os
import hashlib
import time
import re
import socket

ARCHIVE_DIR = "archive"
MAX_ATTEMPTS = 5
DEFAULT_WAIT = 5

def get_session(is_onion):
    session = requests.session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    session.headers.update(headers)
    if is_onion:
        session.proxies.update({
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        })
    return session, ("Tor" if is_onion else "Clearnet")

def is_queue_page(html_content):
    return bool(re.search(r'queue|waiting|please wait|javascript refresh|cloudflare', str(html_content).lower()))

def sanitize_filename(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def save_content(content, url):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{sanitize_filename(url)}_{timestamp}.html"
    filepath = os.path.join(ARCHIVE_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath

def scrape_and_save(url, section=None):
    is_onion = '.onion' in url
    session, session_type = get_session(is_onion)
    attempt = 0
    wait_time = DEFAULT_WAIT
    timeout = 60 if not is_onion else 90

    print(f"[{session_type}] Scraping: {url}")

    while attempt < MAX_ATTEMPTS:
        try:
            res = session.get(url, timeout=timeout)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'lxml')

            if is_onion and is_queue_page(soup):
                print(f"[Queue] Waiting for {url} {wait_time}s...")
                time.sleep(wait_time)
                wait_time *= 2
                attempt += 1
                continue

            content = soup.find(id=section) if section else soup
            if not content:
                raise Exception("Unable to extract content.")

            html = str(content)
            path = save_content(html, url)
            print(f"[Success] Saved: {path}")
            return html, path

        except (requests.exceptions.RequestException, socket.gaierror) as e:
            print(f"[Error] Attempt {attempt+1} failed for {url}: {e}")
            attempt += 1
            time.sleep(wait_time)
            wait_time *= 2

    print(f"[Failure] Gave up after {MAX_ATTEMPTS} attempts.")
    return None, None
