import requests
from bs4 import BeautifulSoup
import os
import hashlib
import time

def get_tor_session():
    session = requests.session()
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    return session

def scrape_and_save(url, section=None):
    session = get_tor_session()
    res = session.get(url, timeout=30)
    soup = BeautifulSoup(res.text, 'lxml')

    content = soup.find(id=section) if section else soup
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{hashlib.md5(url.encode()).hexdigest()}_{timestamp}.html"
    filepath = os.path.join("archive", filename)

    os.makedirs("archive", exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(str(content))

    return str(content), filepath
