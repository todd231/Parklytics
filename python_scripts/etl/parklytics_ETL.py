import sqlite3
import os
from datetime import datetime, timedelta

# === CONFIGURATION ===
ETL_DAYS_TO_KEEP_RUNTIME_DATA = 1
BATCH_SIZE = 1000
TEST_MODE = False  # Set to True to test without committing

LIVE_DB = r'E:\app_data\db_live\live.db'
WAREHOUSE_DB = r'E:\app_data\db_data_warehouse\warehouse.db'
LOG_DIR = r'E:\app_data\etl_logging'

# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f'ETL_LiveToWarehouse_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Tables to copy: (table_name, date_column)
TABLES_WITH_DATES = [
    ('entities', None),  # full copy, no date filtering
    ('queue_status', 'timestamp'),
    ('forecast', 'forecast_time'),
    ('schedule', 'date'),
    ('operating_hours', 'timestamp'),
]

def log(message):
    timestamp = datetime.now().isoformat()
    print(f"{timestamp} - {message}")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{timestamp} - {message}\n")

def copy_data(table, date_column, conn_src, conn_dst, target_date):
    if date_column is None:
        log(f"🔄 Copying full table {table} (no date filter)")
        rows = conn_src.execute(f"SELECT * FROM {table}").fetchall()
        total_copied = 0
        if rows:
            placeholders = ','.join(['?'] * len(rows[0]))
            conn_dst.executemany(f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})", rows)
            total_copied = len(rows)
        log(f"   Copied {total_copied} rows (full table)")
        return total_copied
    else:
        log(f"🔄 Copying from {table} for date {target_date}")
        offset = 0
        total_copied = 0
        while True:
            rows = conn_src.execute(
                f"SELECT * FROM {table} WHERE DATE({date_column}) = ? LIMIT {BATCH_SIZE} OFFSET {offset}",
                (target_date,)
            ).fetchall()
            if not rows:
                break
            placeholders = ','.join(['?'] * len(rows[0]))
            conn_dst.executemany(f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})", rows)
            offset += BATCH_SIZE
            total_copied += len(rows)
            log(f"   Copied {len(rows)} rows (Total: {total_copied})")
        return total_copied

def prune_old_data(table, date_column, conn, cutoff_date):
    log(f"🧹 Pruning rows in {table} older than {cutoff_date}")
    cur = conn.execute(
        f"DELETE FROM {table} WHERE DATE({date_column}) < ?", (cutoff_date,)
    )
    deleted = cur.rowcount
    log(f"   Deleted {deleted} old rows")
    return deleted

def run_etl():
    target_date = (datetime.now().date() - timedelta(days=2)).strftime('%Y-%m-%d')
    cutoff_date = (datetime.now().date() - timedelta(days=ETL_DAYS_TO_KEEP_RUNTIME_DATA)).strftime('%Y-%m-%d')

    log(f"=== ETL PROCESS STARTED for target date {target_date} ===")
    log(f"TEST MODE: {'ON' if TEST_MODE else 'OFF'}")
    log(f"Keeping {ETL_DAYS_TO_KEEP_RUNTIME_DATA} days in live.db (Cutoff: {cutoff_date})")

    conn_live = sqlite3.connect(LIVE_DB)
    conn_warehouse = sqlite3.connect(WAREHOUSE_DB)

    try:
        for table, date_column in TABLES_WITH_DATES:
            if table == 'entities':
                copied = copy_data(table, None, conn_live, conn_warehouse, target_date=None)
            else:
                copied = copy_data(table, date_column, conn_live, conn_warehouse, target_date)
            log(f"✅ Copied {copied} rows from {table}")

            if date_column is not None and table != 'entities':
                deleted = prune_old_data(table, date_column, conn_live, cutoff_date)
                log(f"🗑️ Deleted {deleted} old rows from {table} in live.db")

        if TEST_MODE:
            log("🚫 TEST MODE ACTIVE — Rolling back changes")
            conn_warehouse.rollback()
            conn_live.rollback()
        else:
            conn_warehouse.commit()
            conn_live.commit()
            log("✅ Changes committed successfully")

    except Exception as e:
        log(f"❌ ERROR: {e}")
        conn_warehouse.rollback()
        conn_live.rollback()
    finally:
        conn_live.close()
        conn_warehouse.close()
        log("=== ETL PROCESS COMPLETED ===")

if __name__ == "__main__":
    run_etl()
