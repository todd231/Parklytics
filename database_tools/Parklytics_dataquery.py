import sqlite3
import pandas as pd

# Path to your warehouse.db file
conn = sqlite3.connect(r"E:\app_data\db_data_warehouse\warehouse.db")

query = """
SELECT
-- Extract date part
date_time.date_part || ' ' ||

-- Convert hour to 12-hour format
CASE 
WHEN cast(strftime('%H', date_time.timestamp_et) as integer) = 0 THEN '12'
WHEN cast(strftime('%H', date_time.timestamp_et) as integer) > 12 THEN 
cast(strftime('%H', date_time.timestamp_et) as integer) - 12
ELSE strftime('%H', date_time.timestamp_et)
END
||

-- Add minutes
':' || strftime('%M', date_time.timestamp_et) ||

-- Add AM/PM
CASE
WHEN cast(strftime('%H', date_time.timestamp_et) as integer) < 12 THEN ' AM'
ELSE ' PM'
END AS timestamp_et_12hr,

date_time.wait_minutes

FROM (
SELECT 
datetime(
replace(substr(qs.timestamp, 1, 19), 'T', ' '),
'-4 hours'
) AS timestamp_et,
qs.wait_minutes,
date(datetime(
replace(substr(qs.timestamp, 1, 19), 'T', ' '),
'-4 hours'
)) AS date_part
FROM queue_status qs
JOIN entities e ON qs.entity_id = e.id
WHERE e.name = 'Slinky Dog Dash'
ORDER BY qs.timestamp DESC
LIMIT 100
) AS date_time

"""

df = pd.read_sql_query(query, conn)
conn.close()

print(df)
