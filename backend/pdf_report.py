# backend/pdf_report.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import time

def generate_pdf_report(url, keywords, changes, archive_path):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    report_path = f"reports/monitoring_report_{timestamp}.pdf"
    c = canvas.Canvas(report_path, pagesize=A4)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, 800, "Dark Web Monitoring Report")
    
    c.setFont("Helvetica", 10)
    c.drawString(40, 780, f"Timestamp: {time.ctime()}")
    c.drawString(40, 765, f"Monitored URL: {url}")
    c.drawString(40, 750, f"Archived HTML File: {archive_path}")

    c.drawString(40, 730, "Matched Keywords:")
    y = 715
    for kw in keywords:
        c.drawString(60, y, f"• {kw}")
        y -= 15

    c.drawString(40, y - 10, "Detected Changes:")
    y -= 30

    changes_lines = changes.splitlines()
    for line in changes_lines:
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 800
        c.drawString(50, y, line[:100])  # wrap long lines manually if needed
        y -= 15

    c.save()
    print(f"PDF Report saved to: {"/Users/prakharkhurana/Desktop/acg/dark-web"}")
