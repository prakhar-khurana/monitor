import pandas as pd
import time

def export_to_csv(url, changes, keywords):
    df = pd.DataFrame([{
        "timestamp": time.ctime(),
        "url": url,
        "keywords_found": ", ".join(keywords),
        "change_summary": changes[:200]
    }])
    df.to_csv("reports/log.csv", mode='a', index=False)
