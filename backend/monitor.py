# backend/monitor.py
import time
from difflib import unified_diff
from backend.scraper import scrape_and_save
from backend.alert import alert_user
from backend.export import export_to_csv
from backend.pdf_report import generate_pdf_report

def detect_keywords(content, keywords):
    return [kw for kw in keywords if kw.lower() in content.lower()]

def detect_changes(old, new):
    return '\n'.join(unified_diff(old.splitlines(), new.splitlines(), lineterm=''))

def monitor_job(url, keywords, section=None):
    try:
        content, path = scrape_and_save(url, section)
    except Exception as e:
        print(f"Scraping failed: {e}")
        return

    if os.path.exists("latest_snapshot.html"):
        with open("latest_snapshot.html", 'r', encoding='utf-8') as f:
            prev = f.read()
    else:
        prev = ""

    with open("latest_snapshot.html", 'w', encoding='utf-8') as f:
        f.write(content)

    changes = detect_changes(prev, content)
    found_keywords = detect_keywords(content, keywords)

    if changes or found_keywords:
        alert_user(url, found_keywords, changes)
        export_to_csv(url, changes, found_keywords)
        generate_pdf_report(url, found_keywords, changes, path)

