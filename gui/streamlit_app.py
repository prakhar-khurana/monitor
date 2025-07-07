import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import time
import requests
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from backend.monitor import monitor_job

# Suppress Streamlit warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'urls.db')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE
        )''')
        conn.commit()

# Initialize database
init_db()

# --- Page and UI Configuration ---
st.set_page_config(layout="wide", page_title="Kautilya")
st.title("KAUTILYA: Web Scanner")

# --- Helper Functions to Display Results ---
def display_change_card(changes_text, url, title):
    with st.container(border=True):
        st.markdown(f"### {title or url}")
        if not changes_text or not changes_text.strip():
            st.info("No changes detected in the page content since the last scan.")
        else:
            st.code(changes_text, language='diff')
            st.session_state.alerts.append(f"Changes detected for {title or url}")
        st.markdown("---")

def display_keywords_card(keywords_found, url):
    with st.container(border=True):
        st.markdown(f"### Keywords for {url}")
        if not keywords_found:
            st.info("No keywords of interest were found on the page.")
        else:
            st.success(f"Found the following keywords: **{', '.join(keywords_found)}**")
        st.markdown("---")

def display_additional_results_card(additional_results, url):
    with st.container(border=True):
        st.markdown(f"### Additional Links for {url}")
        if not additional_results:
            st.info("No additional links with keywords found.")
        else:
            for result in additional_results:
                st.write(f"- **{result['url']}**: {', '.join(result['found_keywords'])}")
        st.markdown("---")

def display_backlinks_card(backlinks, alias, url):
    with st.container(border=True):
        st.markdown(f"### Backlinks/Subdomains for {alias or url}")
        if not backlinks:
            st.info("No backlinks or subdomains found.")
        else:
            for link in backlinks:
                st.write(f"- {link}")
        st.markdown("---")

def display_keyword_hits_card(keyword_hits):
    with st.container(border=True):
        st.markdown("### Keyword Hit Analysis")
        if not keyword_hits:
            st.info("No keyword hits recorded.")
        else:
            for url, hits in keyword_hits.items():
                st.write(f"- **{url}**: {hits} hits")
        st.markdown("---")

def display_status_alert(alias, url, status_code, error=None):
    with st.container(border=True):
        st.markdown(f"### Status Alert for {alias}")
        if status_code == 200:
            st.success(f"URL {url} is reachable (Status: {status_code})")
        else:
            st.error(f"URL {url} returned status {status_code}: {error or 'Unknown error'}")
        st.markdown("---")

# --- Database and URL Functions ---
def check_url_status(url):
    try:
        session = requests.session()
        if url.endswith('.onion'):
            session.proxies = {'http': 'socks5h://127.0.0.1:9150', 'https': 'socks5h://127.0.0.1:9150'}
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0'
        })
        res = session.head(url, timeout=10)
        return res.status_code, None
    except Exception as e:
        return None, str(e)

def is_valid_url(url):
    if not (url.endswith('.onion') or url.startswith(('http://', 'https://'))):
        return False, "Invalid URL. Must be a .onion URL or start with http:// or https://"
    status_code, error = check_url_status(url)
    if status_code != 200:
        return False, f"URL is unreachable (Status: {status_code or 'N/A'}, Error: {error or 'Unknown'})"
    return True, None

def save_url(alias, url):
    valid, error = is_valid_url(url)
    if not valid:
        st.error(error)
        return False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO urls (alias, url) VALUES (?, ?)", (alias, url))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Failed to save URL: {e}")
        return False

def load_urls():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT alias, url FROM urls")
            return c.fetchall()
    except Exception as e:
        st.error(f"Failed to load URLs: {e}")
        return []

def delete_url(url):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM urls WHERE url = ?", (url,))
            conn.commit()
    except Exception as e:
        st.error(f"Failed to delete URL: {e}")

# --- Main Application Logic ---
if 'scheduler' not in st.session_state:
    st.session_state.scheduler = None
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'keyword_hits' not in st.session_state:
    st.session_state.keyword_hits = {}
if 'status_alerts' not in st.session_state:
    st.session_state.status_alerts = {}

# --- Sidebar for Configuration ---
with st.sidebar:
    st.header("Scan Configuration")
    st.warning("Ensure Tor Browser is running (socks5h://127.0.0.1:9150) for .onion URLs.")

    # URL and Alias Input
    st.subheader("Add New URL")
    new_url = st.text_input("Enter URL", placeholder="http://example.onion or https://example.com")
    new_alias = st.text_input("Enter Alias for URL", placeholder="e.g., Forum 1")
    if st.button("Add URL"):
        if new_url and new_alias:
            if save_url(new_alias, new_url):
                st.success(f"Added {new_url} as {new_alias}")
        else:
            st.error("Please provide both URL and alias.")

    # URL Selection
    st.subheader("Select URLs to Monitor")
    saved_urls = load_urls()
    selected_urls = []
    if saved_urls:
        selected_urls = st.multiselect("Choose URLs (max 10)", 
                                      options=[f"{alias} ({url})" for alias, url in saved_urls],
                                      default=[])
        selected_urls = [url for alias, url in saved_urls if f"{alias} ({url})" in selected_urls][:10]

    # Display Selected URLs
    st.subheader("Monitored URLs")
    if selected_urls:
        for alias, url in saved_urls:
            if url in selected_urls:
                with st.container():
                    st.write(f"**{alias}**: {url}")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button(f"Edit {alias}", key=f"edit_{url}"):
                            st.session_state[f"editing_{url}"] = True
                    with col2:
                        if st.button(f"Delete {alias}", key=f"delete_{url}"):
                            delete_url(url)
                            st.rerun()
                    if st.session_state.get(f"editing_{url}", False):
                        new_alias = st.text_input(f"New alias for {url}", value=alias, key=f"alias_{url}")
                        new_url = st.text_input(f"New URL for {alias}", value=url, key=f"url_{url}")
                        if st.button(f"Save Changes for {alias}", key=f"save_{url}"):
                            if save_url(new_alias, new_url):
                                st.session_state[f"editing_{url}"] = False
                                st.rerun()
    else:
        st.info("No URLs selected for monitoring.")

    # Keyword Input
    st.subheader("Keywords to Monitor (Optional)")
    keywords_input = st.text_input("Enter keywords (comma-separated, leave blank for general monitoring)", placeholder="keyword1, keyword2")
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

    # Monitoring Controls
    if st.button("Start Automated Monitoring", type="primary"):
        if not selected_urls:
            st.error("Please select at least one URL.")
        else:
            for url in selected_urls:
                alias = next((a for a, u in saved_urls if u == url), url)
                status_code, error = check_url_status(url)
                st.session_state.status_alerts[url] = (alias, status_code, error)
            if all(st.session_state.status_alerts.get(url, (None, 200, None))[1] == 200 for url in selected_urls):
                if st.session_state.scheduler is None:
                    try:
                        scheduler = BackgroundScheduler()
                        scheduler.add_job(
                            lambda: run_monitoring_cycle(selected_urls, keywords),
                            'interval',
                            seconds=30,
                            max_instances=10
                        )
                        scheduler.start()
                        st.session_state.scheduler = scheduler
                        st.success("Automated monitoring started (every 10 minutes).")
                    except Exception as e:
                        st.error(f"Failed to start scheduler: {e}")
                else:
                    st.warning("Monitoring already running.")
            else:
                st.error("Cannot start monitoring: Some URLs are unreachable.")

    if st.button("Stop Monitoring"):
        if st.session_state.scheduler:
            try:
                st.session_state.scheduler.shutdown()
                st.session_state.scheduler = None
                st.success("Monitoring stopped.")
            except Exception as e:
                st.error(f"Failed to stop scheduler: {e}")
        else:
            st.warning("No monitoring process is running.")

    if st.button("Manual Scan", type="secondary"):
        if not selected_urls:
            st.error("Please select at least one URL.")
        else:
            for url in selected_urls:
                alias = next((a for a, u in saved_urls if u == url), url)
                status_code, error = check_url_status(url)
                st.session_state.status_alerts[url] = (alias, status_code, error)
            if all(st.session_state.status_alerts.get(url, (None, 200, None))[1] == 200 for url in selected_urls):
                with st.spinner("Running manual scan..."):
                    try:
                        run_monitoring_cycle(selected_urls, keywords)
                    except Exception as e:
                        st.error(f"Manual scan failed: {e}")
            else:
                st.error("Cannot run scan: Some URLs are unreachable.")

# --- Monitoring Cycle ---
def run_monitoring_cycle(urls, keywords):
    results = {}
    for url in urls:
        try:
            result = monitor_job(url, keywords)
            results[url] = result
            if keywords and result.get("found_keywords"):
                st.session_state.keyword_hits[url] = st.session_state.keyword_hits.get(url, 0) + len(result["found_keywords"])
            print(f"Monitoring cycle completed for {url}: {result}")
        except Exception as e:
            print(f"Error in monitoring cycle for {url}: {e}")
            results[url] = {"error": str(e), "changes": "", "found_keywords": [], "additional_results": [], "page_title": url, "backlinks": []}
    st.session_state.results = results
    st.session_state.last_scan_time = time.ctime()
    st.rerun()

# --- Landing Page with Individual Cards ---
st.header("Monitoring Dashboard")
if st.session_state.alerts:
    st.warning(f"Alerts: {', '.join(st.session_state.alerts)}")
if st.session_state.last_scan_time:
    st.caption(f"Last scanned on: {st.session_state.last_scan_time}")
else:
    st.caption("No scans have been run yet.")

# Display Status Alerts
if st.session_state.status_alerts:
    for url, (alias, status_code, error) in st.session_state.status_alerts.items():
        display_status_alert(alias, url, status_code, error)

if keywords:
    display_keyword_hits_card(st.session_state.keyword_hits)

if st.session_state.results:
    for url, result in st.session_state.results.items():
        alias = next((a for a, u in saved_urls if u == url), url)
        if result.get("error"):
            with st.container(border=True):
                st.error(f"### Error for {alias}\n{result['error']}")
        else:
            title = result.get("page_title", alias)
            display_change_card(result.get("changes", ""), url, title)
            if keywords:
                display_keywords_card(result.get("found_keywords", []), url)
                display_additional_results_card(result.get("additional_results", []), url)
            display_backlinks_card(result.get("backlinks", []), alias, url)
else:
    st.info("Start monitoring or run a manual scan from the sidebar.")

# Debugging: Display raw results
with st.expander("Debug: Raw Results"):
    st.write(st.session_state.results)