import os
import schedule
import time
import datetime
import psutil
import sqlite3
import pytz
import logging

DB_PATH = r'E:\app_data\db_live\live.db'
PROCESS_NAMES = ['daily_live_api.py', 'daily_scheudle_api.py', 'parklytics_ETL_updated.py', 'weather_api_fetch.py']
DATA_MAX_AGE_MINUTES = 15

# --- Setup logging ---
log_dir = r"I:\watchdog_logs"
os.makedirs(log_dir, exist_ok=True)  # make sure folder exists

log_file = os.path.join(log_dir, "watchdog.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # Also log to console
    ]
)

def is_script_running(script_name):
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and script_name in ' '.join(cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def is_data_fresh():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM queue_status")
        result = cursor.fetchone()
        conn.close()

        if not result or not result[0]:
            return False

        latest_ts = datetime.datetime.fromisoformat(result[0])
        age_minutes = (datetime.datetime.now(datetime.timezone.utc) - latest_ts).total_seconds() / 60
        return age_minutes <= DATA_MAX_AGE_MINUTES
    except Exception as e:
        print(f"[ERROR] Could not check DB freshness: {e}")
        return False
    
def get_latest_timestamp_et():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM queue_status")
        result = cursor.fetchone()
        conn.close()

        if not result or not result[0]:
            return None

        latest_utc = datetime.datetime.fromisoformat(result[0]).replace(tzinfo=datetime.timezone.utc)
        central = pytz.timezone('US/Central')
        latest_et = latest_utc.astimezone(central)

        return latest_et.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception as e:
        print(f"[ERROR] Could not fetch latest timestamp: {e}")
        return None

def check_watchdog():
    logging.info("Running check")

    for script in PROCESS_NAMES:
        if is_script_running(script):
            logging.info(f"{script} is currently running.")
        else:
            logging.error(f"{script} is NOT running!")

    latest_ts_et = get_latest_timestamp_et()
    if is_data_fresh():
        logging.info(f"Data in 'queue_status' is fresh (latest entry at {latest_ts_et}).")
    else:
        logging.error(f"Data in 'queue_status' is STALE (latest entry at {latest_ts_et}).")

if __name__ == "__main__":
    logging.info("Starting watchdog scheduler — checks every 15 minutes.")
    check_watchdog()  # Run once at start

    schedule.every(15).minutes.do(check_watchdog)

    while True:
        schedule.run_pending()
        time.sleep(1)
