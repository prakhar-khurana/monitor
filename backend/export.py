import pandas as pd
import time
import os

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')

def export_to_csv(url, changes, keywords, additional_results=None):
    additional_results = additional_results or []
    data = [{
        "timestamp": time.ctime(),
        "url": url,
        "keywords_found": ", ".join(keywords),
        "change_summary": changes[:200],
        "additional_links_keywords": "; ".join([f"{r['url']}: {', '.join(r['found_keywords'])}" for r in additional_results])
    }]
    os.makedirs(REPORTS_DIR, exist_ok=True)
    log_file = os.path.join(REPORTS_DIR, "log.csv")
    df = pd.DataFrame(data)
    df.to_csv(log_file, mode='a', index=False)