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

def create_schedule_tables():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                date DATE NOT NULL,
                start_time DATETIME,
                end_time DATETIME,
                type TEXT,
                description TEXT,  -- Added description column
                park TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id TEXT PRIMARY KEY,
                park_entity_id TEXT NOT NULL,
                name TEXT NOT NULL,
                purchase_type TEXT,
                price_amount REAL,
                price_currency TEXT,
                price_formatted TEXT,
                available BOOLEAN
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_schedule_entity_date ON schedule(entity_id, date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_purchases_park_entity ON purchases(park_entity_id)')

    print("🎉 Schedule tables created/verified with schema and indexes.")

def fetch_and_insert_schedule(park_name, park_id):
    url = f"https://api.themeparks.wiki/v1/entity/{park_id}/schedule"
    print(f"Fetching schedule data for {park_name}...")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        schedules = data.get('schedule') or []
        if not schedules:
            print(f"No schedule data found for {park_name}.")
            return

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            schedule_entries = 0
            purchase_entries = 0

            for entry in schedules:
                entity_id = park_id
                date = entry.get('date')
                start_time = entry.get('openingTime')
                end_time = entry.get('closingTime')
                event_type = entry.get('type')
                description = entry.get('description', '')

                if not date:
                    continue

                if 'Extended Evening' in description:
                    print(f"🟡 Found Extended Evening event: {entry}")

                try:
                    start_time_iso = datetime.datetime.fromisoformat(start_time).isoformat() if start_time else None
                    end_time_iso = datetime.datetime.fromisoformat(end_time).isoformat() if end_time else None
                except Exception as e:
                    print(f"⚠️ Time parse error: {e}")
                    start_time_iso = start_time
                    end_time_iso = end_time

                try:
                    c.execute('''
                        INSERT INTO schedule (entity_id, date, start_time, end_time, type, description, park)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (entity_id, date, start_time_iso, end_time_iso, event_type, description, park_name))
                    schedule_entries += 1
                except Exception as e:
                    print(f"❌ Failed to insert schedule entry: {entry} — Error: {e}")

                purchases = entry.get('purchases', [])
                for purchase in purchases:
                    purchase_id = purchase.get('id')
                    name = purchase.get('name')
                    purchase_type = purchase.get('type')
                    price = purchase.get('price') or {}
                    price_amount = price.get('amount')
                    price_currency = price.get('currency')
                    price_formatted = price.get('formatted')
                    available = purchase.get('available')

                    if purchase_id and name:
                        c.execute('''
                            INSERT OR REPLACE INTO purchases
                            (id, park_entity_id, name, purchase_type, price_amount, price_currency, price_formatted, available)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (purchase_id, park_id, name, purchase_type, price_amount, price_currency, price_formatted, available))
                        purchase_entries += 1

            conn.commit()
            print(f"Inserted {schedule_entries} schedule entries and {purchase_entries} purchase entries for {park_name}.\n")

    except requests.RequestException as e:
        print(f"Error fetching schedule for {park_name}: {e}")
    except json.JSONDecodeError:
        print(f"Invalid JSON response while fetching schedule for {park_name}")
    except Exception as e:
        print(f"Unexpected error while processing schedule for {park_name}: {e}")

# ✅ FUNCTION FOR DASH TO CALL
def fetch_disney_schedule_data():
    print("📅 Fetching Disney schedule data...")
    create_schedule_tables()
    for park_name, park_id in PARKS.items():
        fetch_and_insert_schedule(park_name, park_id)
    print("✅ Disney schedule data fetch complete.")

# 🔁 OPTIONAL SCHEDULE LOOP IF RUN DIRECTLY
if __name__ == "__main__":
    fetch_disney_schedule_data()
    
    # # Run schedule fetch once daily at 4 AM (schedules don't change frequently)
    # schedule.every().day.at("04:00").do(fetch_disney_schedule_data)

    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)  # Check every minute