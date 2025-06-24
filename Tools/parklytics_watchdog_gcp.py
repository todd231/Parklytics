import os
import datetime
import subprocess
import sqlite3
import logging
import smtplib
import pytz
import psutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === CONFIG ===
DB_PATH = '/home/tplatt428/Desktop/Database Files/live.db'
WATCHDOG_LOG_DIR = '/home/tplatt428/Desktop/ParklyticsMonitoring/watchdog/'
LOG_FILE = os.path.join(WATCHDOG_LOG_DIR, "watchdog.log")

SCHEDULE_LOG = '/home/tplatt428/logs/schedule.log'
ETL_LOG = '/home/tplatt428/logs/etl.log'
CRON_MAX_AGE_MINUTES = 30
DATA_MAX_AGE_MINUTES = 0.01

SERVICES = ['parklytics-live.service', 'parklytics-weather.service']

# === Email config ===
EMAIL_ENABLED = True
EMAIL_FROM = "tplatt428@gmail.com"
EMAIL_TO = "todd231@outlook.com"
EMAIL_PASSWORD = "wula mxiq mbtd oixk"
EMAIL_SUBJECT = "🚨 Parklytics Watchdog Alert"

# === Setup logging ===
os.makedirs(WATCHDOG_LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
def send_email(subject, body):
    if not EMAIL_ENABLED:
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info("Alert email sent.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

def check_service_status(service_name):
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name], capture_output=True, text=True)
        return result.stdout.strip() == "active"
    except Exception as e:
        logging.error(f"Error checking service {service_name}: {e}")
        return False

def get_disk_usage():
    try:
        st = os.statvfs('/')
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        used = total - free
        percent = (used / total) * 100

        msg = f"Disk usage: {used // (1024**3)} GB used of {total // (1024**3)} GB ({percent:.2f}%)"
        logging.info(msg)
        return msg
    except Exception as e:
        logging.error(f"Error getting disk usage: {e}")
        return "Disk usage: Error"

def get_memory_usage():
    try:
        mem = psutil.virtual_memory()
        total = mem.total // (1024**2)
        used = (mem.total - mem.available) // (1024**2)
        percent = mem.percent

        msg = f"Memory usage: {used} MB used of {total} MB ({percent}%)"
        logging.info(msg)
        return msg
    except Exception as e:
        logging.error(f"Error getting memory usage: {e}")
        return "Memory usage: Error"


def get_latest_db_timestamp_central():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM queue_status")
        result = cursor.fetchone()
        conn.close()

        if not result or not result[0]:
            logging.warning("DB query ran, but result was empty or NULL.")
            return "No timestamp found"

        latest_utc = datetime.datetime.fromisoformat(result[0]).replace(tzinfo=datetime.timezone.utc)
        central = pytz.timezone('US/Central')
        latest_ct = latest_utc.astimezone(central)
        formatted = latest_ct.strftime('%m/%d/%Y %I:%M %p %Z')
        logging.info(f"Latest queue_status timestamp (Central): {formatted}")
        return formatted
    except Exception as e:
        logging.error(f"Error fetching latest DB timestamp: {e}")
        return "Error fetching timestamp"


def is_data_fresh():
    latest_ts = get_latest_db_timestamp_central()
    if not latest_ts:
        logging.error("No timestamp found in DB — treating as stale.")
        return False

    age = (datetime.datetime.utcnow() - latest_ts).total_seconds() / 60
    logging.info(f"DB timestamp age: {age:.2f} minutes")
    return age <= DATA_MAX_AGE_MINUTES

def check_log_freshness(log_path, max_age_min):
    try:
        mtime = os.path.getmtime(log_path)
        age = (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(mtime)).total_seconds() / 60
        return age <= max_age_min
    except Exception as e:
        logging.error(f"Error checking {log_path}: {e}")
        return False

def watchdog_check():
    alert_messages = []
    logging.info("Running watchdog check...")

    # --- Systemd Services ---
    for svc in SERVICES:
        if check_service_status(svc):
            msg = f"{svc} is ✅ running."
            logging.info(msg)
        else:
            msg = f"{svc} is ❌ NOT running!"
            logging.error(msg)
        alert_messages.append(msg)
        alert_messages.append("") 


    # --- Database Freshness ---
    # --- Latest DB Timestamp (Central) ---
    latest_db_time = get_latest_db_timestamp_central()
    timestamp_msg = f"Latest queue_status timestamp: {latest_db_time}"
    logging.info(timestamp_msg)
    alert_messages.append(timestamp_msg)
    alert_messages.append("")  # ← adds line break before disk info

    disk_msg = get_disk_usage()
    mem_msg = get_memory_usage()

    alert_messages.append(disk_msg)
    alert_messages.append("")  # ← adds line break before disk info
    alert_messages.append(mem_msg)
    alert_messages.append("")  # ← adds line break before cron info

    # --- Cron Job Logs ---
    if check_log_freshness(SCHEDULE_LOG, CRON_MAX_AGE_MINUTES):
        logging.info("Schedule job ran recently.")
    else:
        msg = f"Schedule job may not have run! Check {SCHEDULE_LOG}"
        logging.error(msg)
        alert_messages.append(msg)
        alert_messages.append("")  # ← adds line break before disk info

    if check_log_freshness(ETL_LOG, CRON_MAX_AGE_MINUTES):
        logging.info("ETL job ran recently.")
    else:
        msg = f"ETL job may not have run! Check {ETL_LOG}"
        logging.error(msg)
        alert_messages.append(msg)

    # --- Email if anything is broken ---
    if alert_messages:
        send_email(EMAIL_SUBJECT, "\n".join(alert_messages))

if __name__ == "__main__":
    watchdog_check()