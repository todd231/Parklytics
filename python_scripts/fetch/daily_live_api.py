import requests
import sqlite3
import datetime
import json
import schedule
import time

DB_PATH = r'E:\app_data\db_live\live.db'

PARKS = {
    "Magic Kingdom": "75ea578a-adc8-4116-a54d-dccb60765ef9",
    "Epcot": "47f90d2c-e191-4239-a466-5892ef59a88b",
    "Hollywood Studios": "288747d1-8b4f-4a64-867e-ea7c9b27bad8",
    "Animal Kingdom": "1c84a229-8862-4648-9c71-378ddd2c7693"
}

def create_tables():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

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

        print("🎉 Tables created/verified.")

def fetch_and_insert_data(park_name, park_id):
    url = f"https://api.themeparks.wiki/v1/entity/{park_id}/live"
    print(f"Fetching live data for {park_name}...")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        entities = data.get('liveData') or data.get('children') or []

        if not entities:
            print(f"No usable live data found for {park_name}.")
            return

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            timestamp = datetime.datetime.utcnow().isoformat()

            for entity in entities:
                entity_id = entity.get('id')
                name = entity.get('name')
                if not entity_id or not name:
                    continue

                entity_type = entity.get('entityType') or entity.get('type') or 'ATTRACTION'
                land = None  # Future feature
                status = entity.get('status') or ''
                is_open = status.upper() in ['OPEN', 'OPERATING', 'AVAILABLE']
                last_updated = entity.get('lastUpdated') or timestamp

                c.execute('''
                    INSERT OR REPLACE INTO entities (id, name, type, park, land, is_open, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (entity_id, name, entity_type, park_name, land, is_open, last_updated))

                queue = entity.get('queue', {})
                standby = queue.get('STANDBY') or {}
                wait_minutes = standby.get('waitTime')
                if isinstance(wait_minutes, dict):
                    wait_minutes = wait_minutes.get('postedWaitMinutes')

                posted_time = entity.get('lastUpdated')

                return_time = queue.get('RETURN_TIME') or {}
                return_time_start = return_time.get('returnStart')
                return_time_end = return_time.get('returnEnd')

                paid_ll = queue.get('PAID_RETURN_TIME') or {}
                paid_ll_cost = None
                if 'price' in paid_ll and 'amount' in paid_ll['price']:
                    paid_ll_cost = float(paid_ll['price']['amount']) / 100

                ll = queue.get('LIGHTNING_LANE') or {}
                lightning_lane_available = ll.get('state') == 'AVAILABLE'
                lightning_lane_cost = None
                if 'cost' in ll:
                    try:
                        lightning_lane_cost = float(ll['cost'])
                    except Exception:
                        lightning_lane_cost = None

                # Showtimes
                start_time = None
                end_time = None
                showtimes = entity.get("showtimes", [])
                if showtimes and isinstance(showtimes, list):
                    first_show = showtimes[0]
                    start_time = first_show.get("startTime")
                    end_time = first_show.get("endTime")

                c.execute('''
                    INSERT INTO queue_status 
                    (entity_id, timestamp, status, wait_minutes, posted_time, lightning_lane_available, lightning_lane_cost, paid_ll_cost, return_time_start, return_time_end, park, startTime, endTime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (entity_id, timestamp, status, wait_minutes, posted_time, lightning_lane_available, lightning_lane_cost, paid_ll_cost, return_time_start, return_time_end, park_name, start_time, end_time))

                # Forecast
                for forecast in entity.get('forecast', []):
                    forecast_time = forecast.get('time')
                    wait_time = forecast.get('waitTime')
                    percentage = forecast.get('percentage')
                    c.execute('''
                        INSERT INTO forecast (entity_id, timestamp, forecast_time, wait_time, percentage, park)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (entity_id, timestamp, forecast_time, wait_time, percentage, park_name))

                # Operating Hours
                for op_hour in entity.get('operatingHours', []):
                    op_type = op_hour.get('type')
                    start = op_hour.get('startTime')
                    end = op_hour.get('endTime')
                    c.execute('''
                        INSERT INTO operating_hours (entity_id, timestamp, type, start_time, end_time, park)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (entity_id, timestamp, op_type, start, end, park_name))

            conn.commit()
            print(f"✅ Inserted data for {park_name}.")

    except requests.RequestException as e:
        print(f"❌ Error fetching live data for {park_name}: {e}")
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON response for {park_name}")
    except Exception as e:
        print(f"❌ Unexpected error processing live data for {park_name}: {e}")

def fetch_disney_data():
    print("📡 Starting live Disney data fetch...")
    create_tables()
    for park_name, park_id in PARKS.items():
        fetch_and_insert_data(park_name, park_id)
    print("🏁 Live data fetch complete.")

if __name__ == "__main__":
    fetch_disney_data()
    schedule.every(15).minutes.do(fetch_disney_data)
    while True:
        schedule.run_pending()
        time.sleep(60)
