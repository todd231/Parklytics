import sqlite3
from datetime import datetime, timedelta
import pandas as pd

# Max number of attractions per park for normalization
NORMALIZATION_FACTORS = {
    "Magic Kingdom": 60 * 25,  # 25 attractions
    "Epcot": 60 * 12,          # 12 attractions
    "Hollywood Studios": 60 * 10,
    "Animal Kingdom": 60 * 6
}

PARKS = list(NORMALIZATION_FACTORS.keys())
DB_PATH = r'E:\app_data\db_live\live.db'

def get_latest_timestamp(conn):
    query = "SELECT MAX(timestamp) FROM queue_status"
    result = conn.execute(query).fetchone()
    return result[0] if result else None

def calculate_crowd_index(conn, park_name, timestamp):
    start = (datetime.fromisoformat(timestamp) - timedelta(minutes=2)).isoformat()
    end = (datetime.fromisoformat(timestamp) + timedelta(minutes=2)).isoformat()

    query = """
    SELECT qs.wait_minutes
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.park = ?
      AND e.type = 'ATTRACTION'
      AND qs.status = 'OPERATING'
      AND qs.timestamp BETWEEN ? AND ?
    """

    df = pd.read_sql_query(query, conn, params=(park_name, start, end))

    if df.empty:
        return 0

    avg_wait = df['wait_minutes'].mean()
    num_operating = len(df)
    score_raw = avg_wait * num_operating
    normalization_factor = NORMALIZATION_FACTORS.get(park_name, 60 * 10)  # default fallback
    crowd_index = min(round((score_raw / normalization_factor) * 100), 100)
    return crowd_index

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    latest = get_latest_timestamp(conn)

    if not latest:
        print("No data available.")
        exit()

    print(f"\n🌐 Park Crowd Index for {latest}:\n")

    for park in PARKS:
        score = calculate_crowd_index(conn, park, latest)

        if score < 25:
            level = "🟢 Light"
        elif score < 50:
            level = "🟡 Moderate"
        elif score < 75:
            level = "🟠 Busy"
        else:
            level = "🔴 Packed"

        print(f"{park:<20} → {score:>3}%   {level}")

    conn.close()
