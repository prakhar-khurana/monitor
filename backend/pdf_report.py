import os
import time
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
import html
import re

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reports'))

def sanitize_diff(changes):
    if not changes or not changes.strip():
        return "No content changes detected since the last scan."
    
    sanitized = []
    for line in changes.splitlines():
        if line.startswith('@@') or line.startswith('---') or line.startswith('+++'):
            continue
        if re.match(r'^\s*<\w+\b[^>]*>\s*$', line) or re.match(r'^\s*</\w+>\s*$', line):
            continue
        if re.match(r'^\s*(?:function|\{|\}|\.[\w\-]+\s*\{)', line):
            continue
        if line.startswith('+') or line.startswith('-'):
            cleaned_line = re.sub(r'\s+', ' ', line.strip())
            if cleaned_line and len(cleaned_line) > 10:
                sanitized.append(cleaned_line)
    
    if not sanitized:
        return "No meaningful content changes detected."
    
    return '\n'.join(sanitized[:50])

def generate_pdf_report(url, keywords, changes, archive_path, additional_results=None):
    print(f"Generating PDF report for {url}")
    additional_results = additional_results or []
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    report_path = os.path.join(REPORTS_DIR, f"monitoring_report_{timestamp}.pdf")
    
    print(f"Attempting to generate PDF report at: {report_path}")
    
    doc = SimpleDocTemplate(report_path, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    story = []
    styles = getSampleStyleSheet()
    
    if 'Justify' not in styles.byName:
        styles.add(ParagraphStyle(name='Justify', alignment=TA_LEFT))
    if 'Code' not in styles.byName:
        styles.add(ParagraphStyle(name='Code', fontName='Courier', fontSize=8, leading=8.8))
    
    story.append(Paragraph("Web Monitoring Report", styles['h1']))
    story.append(Spacer(1, 24))

    metadata = [
        ['Monitored URL:', Paragraph(f'<a href="{url}">{url}</a>', styles['Normal'])],
        ['Scan Timestamp:', time.ctime()],
        ['Archived Snapshot:', Paragraph(archive_path.replace('\\', '/'), styles['Code'])],
    ]
    
    tbl = Table(metadata, colWidths=[120, 340])
    tbl.setStyle(TableStyle([ 
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(tbl)
    story.append(Spacer(1, 24))

    story.append(Paragraph("Matched Keywords", styles['h2']))
    if keywords:
        for kw in keywords:
            story.append(Paragraph(f"• {kw}", styles['Normal']))
    else:
        story.append(Paragraph("No keywords of interest were found during this scan.", styles['Justify']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Detected Changes (Sanitized)", styles['h2']))
    
    sanitized_changes = sanitize_diff(changes)
    if sanitized_changes.startswith("No"):
        story.append(Paragraph(sanitized_changes, styles['Justify']))
    else:
        formatted_changes = ""
        for line in sanitized_changes.splitlines():
            if line.startswith('+'):
                line = f'<font color="green">{html.escape(line)}</font>'
            elif line.startswith('-'):
                line = f'<font color="red">{html.escape(line)}</font>'
            else:
                line = html.escape(line)
            formatted_changes += line + '<br/>'
        story.append(Paragraph(formatted_changes, styles['Code']))
    
    story.append(Paragraph("Additional Links Scanned", styles['h2']))
    if additional_results:
        for result in additional_results:
            story.append(Paragraph(f"URL: {result['url']}", styles['Normal']))
            story.append(Paragraph(f"Keywords: {', '.join(result['found_keywords'])}", styles['Normal']))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No additional links with keywords found.", styles['Justify']))
    story.append(Spacer(1, 12))
    
    try:
        doc.build(story)
        print(f"PDF Report saved to: {report_path}")
    except Exception as e:
        print(f"Failed to generate PDF report: {e}")