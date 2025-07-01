import sqlite3
from datetime import datetime

LIVE_DB = r"E:\app_data\db_live\live.db"
WAREHOUSE_DB = r"E:\app_data\db_data_warehouse\warehouse.db"
JUNE_TEST_DB = r"E:\app_data\test_data\warehouse_june_testdata.db"
LOG_FILE = r"C:\Users\Todd\Desktop\migration_log.txt"

TEST_MODE = False

TABLES = {
    "queue_status": "timestamp",
    "forecast": "timestamp",
    "schedule": "date"
}

CUTOFF = "2025-07-01"  # Updated year to 2025

def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} {msg}\n")
    print(f"{timestamp} {msg}")

def copy_rows(src_conn, dest_conn, table, date_col):
    dest_cursor = dest_conn.cursor()
    # 1. Clear matching old rows in destination to avoid duplicates
    if date_col == "date":
        dest_cursor.execute(f"DELETE FROM {table} WHERE {date_col} < ?", (CUTOFF,))
    else:
        dest_cursor.execute(f"DELETE FROM {table} WHERE datetime({date_col}) < datetime(?)", (CUTOFF,))
    dest_conn.commit()

    # 2. Fetch rows from source DB
    cursor = src_conn.cursor()
    if date_col == "date":
        cursor.execute(f"SELECT * FROM {table} WHERE {date_col} < ?", (CUTOFF,))
    else:
        cursor.execute(f"SELECT * FROM {table} WHERE datetime({date_col}) < datetime(?)", (CUTOFF,))
    rows = cursor.fetchall()

    if not rows:
        log(f"No data to copy from {table}.")
        return

    # 3. Insert rows into destination
    placeholders = ",".join(["?"] * len(rows[0]))
    dest_cursor.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
    dest_conn.commit()
    log(f"Copied {len(rows)} rows from {table} into test warehouse.")


def simulate_or_delete_rows(conn, table, date_col):
    cursor = conn.cursor()
    if date_col == "date":
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {date_col} < ?", (CUTOFF,))
    else:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE datetime({date_col}) < datetime(?)", (CUTOFF,))
    count = cursor.fetchone()[0]

    if TEST_MODE:
        log(f"[TEST MODE] Would delete {count} old rows from {table}.")
    else:
        if date_col == "date":
            cursor.execute(f"DELETE FROM {table} WHERE {date_col} < ?", (CUTOFF,))
        else:
            cursor.execute(f"DELETE FROM {table} WHERE datetime({date_col}) < datetime(?)", (CUTOFF,))
        deleted = cursor.rowcount
        conn.commit()
        log(f"Deleted {deleted} old rows from {table}.")

def process_db(db_path, label):
    log(f"\n--- Processing {label.upper()} ---")
    with sqlite3.connect(db_path) as src_conn, sqlite3.connect(JUNE_TEST_DB) as test_conn:
        for table, date_col in TABLES.items():
            try:
                copy_rows(src_conn, test_conn, table, date_col)
                simulate_or_delete_rows(src_conn, table, date_col)
            except Exception as e:
                log(f"ERROR processing {table}: {e}")

if __name__ == "__main__":
    log(f"\n=== BEGIN MIGRATION (TEST MODE: {TEST_MODE}) ===")
    process_db(LIVE_DB, "live.db")
    process_db(WAREHOUSE_DB, "warehouse.db")
    log("=== MIGRATION COMPLETE ===\n")
