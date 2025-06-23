import sqlite3
import os

live_db_path = r'E:\app_data\db_live\live.db'
warehouse_db_path = r'E:\app_data\db_data_warehouse\warehouse.db'

def copy_schema(source_db, target_db):
    # Connect to source (live) DB
    src_conn = sqlite3.connect(source_db)
    src_cursor = src_conn.cursor()

    # Extract all schema objects except sqlite_sequence
    src_cursor.execute("""
        SELECT type, name, sql 
        FROM sqlite_master 
        WHERE sql NOT NULL 
          AND name != 'sqlite_sequence' 
          AND type IN ('table', 'index', 'trigger')
        ORDER BY 
            CASE type 
                WHEN 'table' THEN 0 
                WHEN 'index' THEN 1 
                WHEN 'trigger' THEN 2 
            END,
            name;
    """)
    schema_objects = src_cursor.fetchall()
    src_conn.close()

    os.makedirs(os.path.dirname(target_db), exist_ok=True)

    tgt_conn = sqlite3.connect(target_db)
    tgt_cursor = tgt_conn.cursor()

    for obj_type, name, sql in schema_objects:
        print(f"Creating {obj_type} '{name}'...")
        try:
            tgt_cursor.execute(sql)
        except sqlite3.Error as e:
            print(f"Error creating {obj_type} '{name}': {e}")

    tgt_conn.commit()
    tgt_conn.close()
    print(f"\n✅ Schema copied successfully to: {target_db}")

if __name__ == "__main__":
    copy_schema(live_db_path, warehouse_db_path)
