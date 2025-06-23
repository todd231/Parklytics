import sqlite3
import pandas as pd
from pytz import timezone
from datetime import datetime

def get_hourly_status_changes(db_path, ride_name):
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT 
        qs.timestamp,
        qs.status
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.name = ?
      AND qs.status IN ('OPERATING', 'CLOSED')
    ORDER BY qs.timestamp;
    """

    df = pd.read_sql_query(query, conn, params=(ride_name,))
    conn.close()

    if df.empty:
        print(f"No data found for ride: {ride_name}")
        return

    # Convert UTC timestamps to datetime and localize to UTC
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')

    # Convert to Eastern Time
    eastern = timezone('US/Eastern')
    df['timestamp_et'] = df['timestamp'].dt.tz_convert(eastern)

    # Extract the hour (as datetime rounded to hour)
    df['hour_et'] = df['timestamp_et'].dt.floor('H')

    # Drop duplicates: keep only first status per hour (assuming status changes within hour are irrelevant)
    hourly_status = df.groupby('hour_et').first().reset_index()[['hour_et', 'status']]

    # Print or return
    for _, row in hourly_status.iterrows():
        print(f"{row['hour_et']}: {row['status']}")

    return hourly_status

# Example usage
if __name__ == "__main__":
    db_path = r"E:\app_data\db_live\live.db"
    ride_name = "Slinky Dog Dash"
    get_hourly_status_changes(db_path, ride_name)
