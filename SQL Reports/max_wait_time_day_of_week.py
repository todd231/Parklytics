import sqlite3
import pandas as pd

# Connect to your DB
conn = sqlite3.connect(r'C:\Users\Todd\OneDrive\Project Data\db_data_warehouse\warehouse.db')

# Write your query
query = """
WITH MaxWaits AS (
    SELECT 
        e.name AS attraction,
        MAX(qs.wait_minutes) AS max_wait
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.park = 'Hollywood Studios'
      AND e.type = 'ATTRACTION'
      AND qs.timestamp BETWEEN '2025-05-15' AND '2025-06-15'
      AND qs.wait_minutes IS NOT NULL
    GROUP BY e.name
),
MaxWaitDetails AS (
    SELECT 
        e.name AS attraction,
        qs.wait_minutes,
        DATE(qs.timestamp) AS max_wait_date,
        STRFTIME('%w', qs.timestamp) AS day_of_week_numeric,  -- 0=Sunday, 1=Monday...
        CASE STRFTIME('%w', qs.timestamp)
            WHEN '0' THEN 'Sunday'
            WHEN '1' THEN 'Monday'
            WHEN '2' THEN 'Tuesday'
            WHEN '3' THEN 'Wednesday'
            WHEN '4' THEN 'Thursday'
            WHEN '5' THEN 'Friday'
            WHEN '6' THEN 'Saturday'
        END AS day_of_week
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    JOIN MaxWaits mw ON e.name = mw.attraction AND qs.wait_minutes = mw.max_wait
    WHERE e.park = 'Hollywood Studios'
      AND e.type = 'ATTRACTION'
      AND qs.timestamp BETWEEN '2025-05-15' AND '2025-06-15'
)
SELECT 
    attraction,
    MAX(wait_minutes) AS max_wait,
    max_wait_date,
    day_of_week
FROM MaxWaitDetails
GROUP BY attraction
ORDER BY max_wait DESC;
"""

# Run and save to CSV
df = pd.read_sql_query(query, conn)
df.to_csv(r'C:\Users\Todd\OneDrive\Project Data\Reports\Hollywood Studios Max Wait Times DOW.csv', index=False)

conn.close()
print("✅ Export complete.")
