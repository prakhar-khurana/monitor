# gui/streamlit_app.pyx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
from backend.monitor import monitor_job
import schedule
import time
import threading

st.title("🕸️ Dark Web Monitoring Tool")

url = st.text_input("Enter .onion URL")
keywords = st.text_input("Keywords (comma-separated)").split(",")
section = st.text_input("Optional HTML section (id/class)")
interval = st.slider("Monitoring Interval (minutes)", 1, 120, 60)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

if st.button("Start Monitoring"):
    schedule.every(interval).minutes.do(monitor_job, url=url, keywords=keywords, section=section)
    threading.Thread(target=run_schedule).start()
    st.success(f"Monitoring started for {url} every {interval} minutes.")
