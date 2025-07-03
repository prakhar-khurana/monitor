import smtplib
from email.mime.text import MIMEText

def alert_user(url, keywords, changes):
    msg = MIMEText(f"Changes found at {url}\nKeywords: {keywords}\nChanges:\n{changes}")
    msg['Subject'] = 'Dark Web Alert'
    msg['From'] = 'you@example.com'
    msg['To'] = 'receiver@example.com'

    try:
        with smtplib.SMTP('smtp.example.com', 587) as s:
            s.starttls()
            s.login('you@example.com', 'password')
            s.send_message(msg)
        print("Alert sent.")
    except Exception as e:
        print(f"Failed to send alert: {e}")
