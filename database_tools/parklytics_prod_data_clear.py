# This script will only run once, giving Parklytics stable data starting from 7/1/2025 moving forward. All data will be archived into the June Wareshouse database in the test data folder. 


import sqlite3
import os

# --- CONFIG ---
TEST_MODE = True  # ← Flip to False to go live
SOURCE_LIVE = "E:/app_data/live.db"
SOURCE_WAREHOUSE = "E:/app_data/warehouse.db"
DEST_PATH = "E:/app_data/test_data/warehouse_june_testdata.db"

def clone_schema(source_db, target_db):
    with sqlite3.connect(source_db) as src_conn:
        schema_query = "SELECT sql FROM sqlite_master WHERE type='table'"
        schema = [row[0] for row in src_conn.execute(schema_query) if row[0]]
        if TEST_MODE:
            print(f"[TEST] Would create {len(schema)} tables from {source_db}")
        else:
            with sqlite3.connect(target_db) as tgt_conn:
                for stmt in schema:
                    tgt_conn.execute(stmt)

def copy_data(source_db, target_db):
    with sqlite3.connect(source_db) as src_conn:
        cursor = src_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (table_name,) in cursor:
            rows = src_conn.execute(f"SELECT * FROM {table_name}").fetchall()
            if TEST_MODE:
                print(f"[TEST] Would copy {len(rows)} rows from table '{table_name}' in {source_db}")
            else:
                if rows:
                    with sqlite3.connect(target_db) as tgt_conn:
                        placeholders = ','.join(['?'] * len(rows[0]))
                        tgt_conn.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
                        tgt_conn.commit()

def verify_copy(source_db, target_db):
    with sqlite3.connect(source_db) as src_conn, sqlite3.connect(target_db) as tgt_conn:
        cursor = src_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (table_name,) in cursor:
            src_count = src_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            tgt_count = tgt_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"✅ {table_name}: {src_count} → {tgt_count}")
            if src_count != tgt_count:
                raise Exception(f"❌ Row mismatch in table {table_name}!")

def purge_data(database):
    with sqlite3.connect(database) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (table_name,) in cursor:
            if TEST_MODE:
                print(f"[TEST] Would delete all rows from {table_name} in {database}")
            else:
                conn.execute(f"DELETE FROM {table_name}")
        if not TEST_MODE:
            conn.commit()

# --- RUN ---
if TEST_MODE:
    print("🔍 Running in TEST MODE. No files will be modified.\n")

if os.path.exists(DEST_PATH):
    if TEST_MODE:
        print(f"[TEST] Would remove existing backup at {DEST_PATH}")
    else:
        os.remove(DEST_PATH)

print("Creating backup database...")
clone_schema(SOURCE_LIVE, DEST_PATH)
clone_schema(SOURCE_WAREHOUSE, DEST_PATH)

print("Copying data from live.db...")
copy_data(SOURCE_LIVE, DEST_PATH)

print("Copying data from warehouse.db...")
copy_data(SOURCE_WAREHOUSE, DEST_PATH)

if not TEST_MODE:
    print("Verifying data integrity...")
    verify_copy(SOURCE_LIVE, DEST_PATH)
    verify_copy(SOURCE_WAREHOUSE, DEST_PATH)

    print("All verifications passed. Proceeding to purge original databases...")
    purge_data(SOURCE_LIVE)
    purge_data(SOURCE_WAREHOUSE)
    print("✔️ Backup complete and data purged successfully.")
else:
    print("\n✅ Test run complete. No changes made. Set TEST_MODE = False to execute for real.")
