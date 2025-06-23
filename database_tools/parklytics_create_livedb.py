import sqlite3
import os

DB_PATH = r'E:\app_data\db_live\live.db'

def create_live_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Entities table
        c.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                park TEXT NOT NULL,
                land TEXT,
                is_open BOOLEAN,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Queue status table
        c.execute('''
            CREATE TABLE IF NOT EXISTS queue_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                wait_minutes INTEGER,
                posted_time DATETIME,
                lightning_lane_available BOOLEAN,
                lightning_lane_cost REAL,
                paid_ll_cost REAL,
                return_time_start TEXT,
                return_time_end TEXT,
                park TEXT,
                startTime TEXT,
                endTime TEXT,
                FOREIGN KEY(entity_id) REFERENCES entities(id)
            )
        ''')

        # Forecast table
        c.execute('''
            CREATE TABLE IF NOT EXISTS forecast (
                entity_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                forecast_time TEXT,
                wait_time INTEGER,
                percentage INTEGER,
                park TEXT
            )
        ''')

        # Operating hours table
        c.execute('''
            CREATE TABLE IF NOT EXISTS operating_hours (
                entity_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                type TEXT,
                start_time TEXT,
                end_time TEXT,
                park TEXT
            )
        ''')

        # Indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_queue_entity_timestamp ON queue_status(entity_id, timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_entities_park ON entities(park)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_forecast_entity_time ON forecast(entity_id, forecast_time)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_hours_entity_type ON operating_hours(entity_id, type)')

    print("✅ New 'Live' database created with all required tables and indexes.")

if __name__ == '__main__':
    create_live_db()