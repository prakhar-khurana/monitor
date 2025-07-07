import time
import os
from difflib import unified_diff
from bs4 import BeautifulSoup
import hashlib
from backend.scraper import scrape_and_save
from backend.alert import alert_user
from backend.export import export_to_csv
from backend.pdf_report import generate_pdf_report
import json

# Define a directory to store data files like the snapshot
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'store')
LOG_FILE = os.path.join(DATA_DIR, "monitoring_log.json")

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_log(log_data):
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=4)

def detect_keywords(content, keywords):
    found_keywords = []
    if not keywords:
        return found_keywords
    # Use visible text instead of raw HTML
    soup = BeautifulSoup(content, 'lxml')
    text_lower = soup.get_text(separator=' ', strip=True).lower()
    for kw in keywords:
        if kw and kw.strip():
            if kw.strip().lower() in text_lower:
                found_keywords.append(kw.strip())
    return list(set(found_keywords))

def detect_changes(old, new):
    diff = unified_diff(
        str(old).splitlines(keepends=True),
        str(new).splitlines(keepends=True),
        fromfile='old_snapshot',
        tofile='new_snapshot',
    )
    changes = ''.join(diff)
    print(f"Change detection result for diff: {'Changes found' if changes else 'No changes'} - Diff: {changes[:100]}...")
    return changes

def enumerate_backlinks(soup, base_url):
    backlinks = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.endswith('.onion'):
            backlinks.add(href)
        elif href.startswith(('http://', 'https://')):
            backlinks.add(href)
        elif href.startswith('/'):
            backlinks.add(f"{base_url.rstrip('/')}{href}")
        elif not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            backlinks.add(f"{base_url.rstrip('/')}/{href.lstrip('/')}")
    return list(backlinks)[:10]

def monitor_job(url, keywords, section=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    log_data = load_log()

    try:
        content, path = scrape_and_save(url, section)
        print(f"[Success] Saved: {path}")
        print(f"Successfully scraped {url} (Title: {page_title})")
        soup = BeautifulSoup(content, 'lxml')
        page_title = soup.title.string if soup.title else url
        print(f"Successfully scraped {url} (Title: {page_title})")
        
        found_keywords = detect_keywords(content, keywords)

        snapshot_file = os.path.join(DATA_DIR, f"{hashlib.md5(url.encode()).hexdigest()}_snapshot.html")
        prev_content = ""
        if os.path.exists(snapshot_file):
            with open(snapshot_file, 'r', encoding='utf- 8') as f:
                prev_content = f.read()
            print(f"Previous snapshot found for {url}: {snapshot_file}")
        else:
            print(f"No previous snapshot for {url}. First run.")

        with open(snapshot_file, 'w', encoding='utf-8') as f:
            f.write(str(content))

        changes = detect_changes(prev_content, content)
        print(f"Changes detected for {url}: {'Yes' if changes else 'No'} - Length: {len(changes)}")
        if keywords:
            print(f"Keywords found for {url}: {found_keywords}")

        backlinks = enumerate_backlinks(soup, url)
        print(f"Backlinks found for {url}: {backlinks}")

        if url not in log_data:
            log_data[url] = {"changes_count": 0, "keywords_count": 0, "last_keywords": []}
        if changes:
            log_data[url]["changes_count"] += 1
        if keywords:
            log_data[url]["keywords_count"] += len(found_keywords)
            log_data[url]["last_keywords"] = found_keywords
        save_log(log_data)

        additional_results = []
        if keywords:
            for link in backlinks:
                if link.endswith('.onion'):
                    try:
                        link_content, link_path = scrape_and_save(link, section)
                        link_keywords = detect_keywords(link_content, keywords)
                        if link_keywords:
                            additional_results.append({"url": link, "found_keywords": link_keywords})
                            print(f"Keywords found in additional link {link}: {link_keywords}")
                    except Exception as e:
                        print(f"Failed to scrape additional link {link}: {e}")

        if changes or (keywords and (found_keywords or additional_results)):
            print(f"Alerting and generating reports for {url}...")
            alert_message = (
                f"URL: {url}\n"
                f"Title: {page_title}\n"
                f"Changes:\n{changes}\n"
                f"Keywords: {found_keywords}\n"
                f"Additional Links: {additional_results}\n"
                f"Backlinks: {backlinks}\n"
                f"Insights: {url} has changed {log_data[url]['changes_count']} times, "
                f"found {log_data[url]['keywords_count']} keywords total"
            )
            alert_user(url, found_keywords, alert_message)
            export_to_csv(url, changes, found_keywords, additional_results)
            generate_pdf_report(url, found_keywords, changes, path, additional_results)
            return {
                "changes": changes,
                "found_keywords": found_keywords,
                "additional_results": additional_results,
                "page_title": page_title,
                "backlinks": backlinks,
                "error": None
            }
    except Exception as e:
        print(f"Scraping failed for {url}: {e}")
        return {
            "error": f"Scraping failed: {e}",
            "changes": "",
            "found_keywords": [],
            "additional_results": [],
            "page_title": url,
            "backlinks": []
        }