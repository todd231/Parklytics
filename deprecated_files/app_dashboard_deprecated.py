import pandas as pd
import plotly.graph_objects as go
import sqlite3
import warnings
import dash
import dash_bootstrap_components as dbc
import requests
from dash import dcc, html
from dash.dependencies import Input, Output
from datetime import datetime, timedelta
from dateutil import parser
# import pytz
# import os
# import plotly.io as pio
# import numpy as np
# from plotly.subplots import make_subplots
# from plotly.offline import plot
# from datetime import datetime

# Ignore warnings
warnings.filterwarnings('ignore', category=UserWarning)

# Database path
db_path = r"E:\app_data\db_live\live.db"

# Park names and color mapping
parks = {
    "Magic Kingdom": {
        "color": "#FF4D00"  # Orange
    },
    "Epcot": {
        "color": "#0080FF"  # Blue
    },
    "Hollywood Studios": {
        "color": "#FF6EC7"  # Pink
    },
    "Animal Kingdom": {
        "color": "#4CAF50"  # Green
    }
}

# Evening shows for each park
evening_shows = {
    "Magic Kingdom": "Happily Ever After",
    "Epcot": "Luminous The Symphony of Us",
    "Hollywood Studios": "Fantasmic!",
    "Animal Kingdom": "Tree of Life Awakenings"
}

# Function to generate unique colors for attractions
def generate_colors(num_colors):
    """Generate a list of visually distinct colors."""
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
    ]
    # If we need more colors than in our list, cycle through them
    return [colors[i % len(colors)] for i in range(num_colors)]

# Function to load park data from SQLite database
def load_park_data(park_name):
    """Load wait time data for a specific park from the database."""
    try:
        conn = sqlite3.connect(db_path)
        
        # Query to get wait time data with entity information
        query = """
        SELECT 
              e.name AS Name,
              e.type AS Type,
              qs.wait_minutes AS wait_minutes,
              qs.timestamp AS timestamp,
              qs.status,
              qs.lightning_lane_available,
              qs.lightning_lane_cost
          FROM queue_status qs
          JOIN entities e ON qs.entity_id = e.id
          WHERE e.park = ? 
          AND e.type = 'ATTRACTION'
          AND qs.wait_minutes > 1
         ORDER BY qs.timestamp DESC;
        """
        
        df = pd.read_sql_query(query, conn, params=(park_name,))
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        df['Timestamp'] = (
            pd.to_datetime(df['timestamp'], errors='coerce')       # Convert to datetime
            .dt.tz_localize('UTC')                                 # Assume incoming data is in UTC
            .dt.tz_convert('US/Eastern')                           # Convert to Disney World time
        )
        df['Day of Week'] = df['Timestamp'].dt.day_name()
        df['Hour of Day'] = df['Timestamp'].dt.hour
                 
        # Create Wait Minutes column (already in minutes from database)
        df['Wait Minutes'] = df['wait_minutes'].fillna(0)
        
        # Create Wait Time - Stand By column for compatibility
        df['Wait Time - Stand By'] = df['wait_minutes'].apply(
            lambda x: f"{int(x//60):02d}:{int(x%60):02d}" if pd.notna(x) and x > 0 else ""
        )
        
        # Extract day of week and hour from timestamp
        df['Day of Week'] = df['Timestamp'].dt.day_name()
        df['Hour of Day'] = df['Timestamp'].dt.hour
        
        # Create Last Updated column
        df['Last Updated'] = df['Timestamp']
        
        return df
    
    except Exception as e:
        print(f"Error loading data for {park_name}: {e}")
        return pd.DataFrame()

# Function to load park schedule and purchase information
def load_park_info(park_name):
    """Load park information including schedule and purchases from database."""
    try:
        conn = sqlite3.connect(db_path)

        # Get schedule information - CLEANED
        schedule_query = """
        SELECT 
            e.name,
            s.date,
            s.start_time,
            s.end_time,
            s.type,
            s.description,
            e.type as entity_type
        FROM schedule s
        JOIN entities e ON s.entity_id = e.id
        WHERE e.park = ?
        ORDER BY s.date DESC, s.start_time
        """
       
        schedule_df = pd.read_sql_query(schedule_query, conn, params=(park_name,))

        # Get purchase information
        purchase_query = """
        SELECT 
            p.name as purchase_name,
            p.purchase_type,
            p.price_amount,
            p.price_currency,
            p.price_formatted,
            p.available,
            e.name as entity_name
        FROM purchases p
        JOIN entities e ON p.park_entity_id = e.id
        WHERE e.park = ?
        """

        purchase_df = pd.read_sql_query(purchase_query, conn, params=(park_name,))
        conn.close()

        # Combine and format data to match original structure
        info_data = []

        # Add schedule data
        for _, row in schedule_df.iterrows():
            try:
                open_time = parser.isoparse(row['start_time']).strftime("%#I:%M %p")
            except Exception:
                open_time = "TBD"

            try:
                close_time = parser.isoparse(row['end_time']).strftime("%#I:%M %p")
            except Exception:
                close_time = "TBD"
                
            info_data.append({
                'Date': pd.to_datetime(row['date']),
                'Type': 'FULL_DAY_HOURS' if row['type'] == 'OPERATING' else row['type'],
                'Opening Time': open_time,
                'Closing Time': close_time,
                'Description': row['description'] if pd.notna(row['description']) else row['name']
            })
 
        # Add purchase data
        for _, row in purchase_df.iterrows():
            info_data.append({
                'Date': pd.Timestamp.now().normalize(),
                'Purchase Name': row['purchase_name'],
                'Purchase Type': row['purchase_type'],
                'Price': row['price_amount'] if pd.notna(row['price_amount']) else 0,
                'Available': "Available for Purchase" if row['available'] else "Not Available for Purchase"
            })

        if info_data:
            return pd.DataFrame(info_data)
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Error loading info for {park_name}: {e}")
        return pd.DataFrame()
  
    except Exception as e:
        print(f"Error loading info for {park_name}: {e}")
        return pd.DataFrame()

# Function to get today's park information
def get_today_park_info(info_df):
    """Extract today's park information."""
    if info_df.empty:
        return pd.DataFrame()
    
    # Get today's date
    today = pd.Timestamp.now().normalize()
    
    # Filter for today's data or recent data if today's not available
    today_info = info_df[info_df['Date'].dt.normalize() == today]
    
    # If no data for today, get the most recent data
    if today_info.empty:
        recent_date = info_df['Date'].max()
        today_info = info_df[info_df['Date'] == recent_date]
    
    return today_info

# Function to get evening showtime
def get_evening_showtime(park_name, show_name):
    """Return formatted start time for the evening show if available."""
    try:
        conn = sqlite3.connect(db_path)
        
        # Query for show schedule
        query = """
        SELECT s.startTime, e.last_updated
        FROM queue_status s
        JOIN entities e ON s.entity_id = e.id
        WHERE e.park = ? AND e.name LIKE ? AND e.type = 'SHOW'
        ORDER BY e.last_updated DESC, s.startTime DESC
        LIMIT 1
        """
        
        # Try exact match first
        result = conn.execute(query, (park_name, f"%{show_name}%")).fetchone()
        conn.close()

        if result and result[0]:
            try:
                # Parse ISO 8601 timestamp and format to 12-hour time
                dt = datetime.fromisoformat(result[0])
                return dt.strftime("%#I:%M %p")  # Use %-I on Unix. If you're on Windows, switch to %#I
            except ValueError:
                return "TBD"

        # Special handling for Tree of Life Awakenings
        if "Tree of Life" in show_name:
            return "TBD"

        return "Not Available"

    except Exception as e:
        print(f"Error fetching evening showtime for {show_name}: {e}")
        if "Tree of Life" in show_name:
            return "TBD"
        return "Currently Not Available"

# Function to get current wait times (most recent data)

# Function to get current wait times (most recent data)
def get_current_wait_times(park_df):
    """Extract the most recent wait times for attractions."""
    if park_df.empty:
        return pd.DataFrame()
  
    # Round timestamps to the nearest minute
    park_df['Rounded Timestamp'] = pd.to_datetime(park_df['Timestamp']).dt.floor('min')
    latest_timestamp = park_df['Rounded Timestamp'].max()
    
    # Filter for the latest data
    latest_data = park_df[park_df['Rounded Timestamp'] == latest_timestamp]
    
    # Filter for attractions only and those with wait times
    attractions = latest_data[
        (latest_data['Type'] == 'ATTRACTION') & 
        (latest_data['Wait Minutes'] > 0)
    ]
    
    # FIXED: Remove duplicates by taking the maximum wait time for each attraction
    # This handles cases where there are multiple records for the same attraction at the same timestamp
    attractions_deduped = attractions.groupby('Name').agg({
        'Wait Minutes': 'max',  # Take the maximum wait time if there are duplicates
        'Type': 'first',
        'Timestamp': 'first',
        'Last Updated': 'first'
    }).reset_index()
    
    # Sort by wait time (descending) and get top 5
    top_attractions = attractions_deduped.sort_values('Wait Minutes', ascending=False).head(5)
    
    return top_attractions
# def get_current_wait_times(park_df):
#     """Extract the most recent wait times for attractions."""
#     if park_df.empty:
#         return pd.DataFrame()
  
#     # Round timestamps to the nearest minute
#     park_df['Rounded Timestamp'] = pd.to_datetime(park_df['Timestamp']).dt.floor('min')
#     latest_timestamp = park_df['Rounded Timestamp'].max()
    
#     # Filter for the latest data
#     #latest_data = park_df[park_df['Timestamp'] == latest_timestamp]
#     latest_data = park_df[park_df['Rounded Timestamp'] == latest_timestamp]
    
#     # Filter for attractions only and those with wait times
#     attractions = latest_data[
#         (latest_data['Type'] == 'ATTRACTION') & 
#         (latest_data['Wait Minutes'] > 0)
#     ]
    
#     # Sort by wait time (descending) and get top 5
#     top_attractions = attractions.sort_values('Wait Minutes', ascending=False).head(5)
    
#     return top_attractions

#6/19/2025 Function to get Weather
API_KEY = "9b2a3de1dbd52c35bd6c2a7630d54391"
ZIP = "32830,US"
URL = f"https://api.openweathermap.org/data/2.5/weather?zip={ZIP}&appid={API_KEY}&units=imperial"

def get_weather_report_div():
    response = requests.get(URL)
    data = response.json()
    
    # Debug print
    #print("Weather API response:", data)
    
    #weather = data['weather'][0]['main']
    description = data['weather'][0]['description']
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    report = f"Current Weather is: {description.capitalize()} and {int(round(temp))}°F, but it feels like {int(round(feels_like))}°F in Disney World"
    
    return html.Div(report, style={
        'fontSize': '30px',
        'fontWeight': 'bold',
        'marginBottom': '15px',
        'textAlign': 'center',
        'color': '#2c3e50'
    })

#Function to get latest snapshot
def get_latest_snapshot_timestamp(conn):
    query = "SELECT MAX(DATETIME(timestamp)) FROM queue_status"
    result = conn.execute(query).fetchone()
    return pd.to_datetime(result[0]) if result else None

def get_top_5_waits_per_park(conn, park_name, timestamp):
    start = (timestamp - timedelta(minutes=2)).isoformat()
    end = (timestamp + timedelta(minutes=2)).isoformat()
    query = """
    SELECT e.name, MAX(qs.wait_minutes) AS wait_minutes
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.park = ? AND e.type = 'ATTRACTION'
        AND qs.timestamp BETWEEN ? AND ?
        AND qs.wait_minutes > 1
    GROUP BY e.name
    ORDER BY wait_minutes DESC
    LIMIT 5;
    """
    return pd.read_sql_query(query, conn, params=(park_name, start, end))

def get_extreme_waits(conn, park_name, timestamp):
    start = (timestamp - timedelta(minutes=2)).isoformat()
    end = (timestamp + timedelta(minutes=2)).isoformat()
    query = """
    SELECT e.name, qs.wait_minutes
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.park = ? AND e.type = 'ATTRACTION'
      AND qs.timestamp BETWEEN ? AND ?
      AND qs.wait_minutes > 0
    ORDER BY qs.wait_minutes ASC
    """
    df = pd.read_sql_query(query, conn, params=(park_name, start, end))
    if df.empty:
        return ("N/A", 0), ("N/A", 0)
    return (
        (df.iloc[-1]['name'], int(df.iloc[-1]['wait_minutes'])),  # Longest
        (df.iloc[0]['name'], int(df.iloc[0]['wait_minutes']))     # Shortest
    )

def get_operating_percentage(conn, park_name, timestamp):
    start = (timestamp - timedelta(minutes=2)).isoformat()
    end = (timestamp + timedelta(minutes=2)).isoformat()
    query = """
    SELECT e.name, qs.status
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.park = ? AND e.type = 'ATTRACTION'
      AND qs.timestamp BETWEEN ? AND ?
    """
    df = pd.read_sql_query(query, conn, params=(park_name, start, end))
    if df.empty:
        return 0
    operating = df[df['status'] == 'OPERATING']
    return round((len(operating) / len(df)) * 100)

def get_closed_attractions(conn, park_name, timestamp):
    start = (timestamp - timedelta(minutes=2)).isoformat()
    end = (timestamp + timedelta(minutes=2)).isoformat()

    query = """
    SELECT e.name, qs.status
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.park = ? AND e.type = 'ATTRACTION'
      AND qs.timestamp BETWEEN ? AND ?
      AND qs.status IN ('CLOSED', 'REFURBISHMENT')
    ORDER BY e.name
    """
    return pd.read_sql_query(query, conn, params=(park_name, start, end))

# Function to calculate average wait times across all data points
def get_average_wait_times(park_df):
    """Calculate average wait times for all attractions across all timestamps."""
    if park_df.empty:
        return pd.DataFrame()
    
    # Filter for attractions only with valid wait times
    attractions = park_df[
        (park_df['Type'] == 'ATTRACTION') & 
        (park_df['Wait Minutes'] > 0)
    ]
    
    # Group by attraction name and calculate average wait time
    avg_wait_times = attractions.groupby('Name')['Wait Minutes'].mean().reset_index()
    avg_wait_times = avg_wait_times.sort_values('Wait Minutes', ascending=False).head(10)
    
    return avg_wait_times

# Function to get wait times by day of week
def get_wait_times_by_day(park_df):
    """Get average wait times by day of week for top 5 attractions."""
    if park_df.empty:
        return pd.DataFrame()
    
    # Filter for attractions only with valid wait times
    attractions = park_df[
        (park_df['Type'] == 'ATTRACTION') & 
        (park_df['Wait Minutes'] > 0)
    ]
    
    # Get top 5 attractions by average wait time
    top_attractions = attractions.groupby('Name')['Wait Minutes'].mean().nlargest(5).index
    filtered_attractions = attractions[attractions['Name'].isin(top_attractions)]
    
    # Calculate average wait times by day of week for top attractions
    day_avg = filtered_attractions.groupby(['Name', 'Day of Week'])['Wait Minutes'].mean().reset_index()
    
    # Ensure proper day order
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_avg['Day of Week'] = pd.Categorical(day_avg['Day of Week'], categories=day_order, ordered=True)
    day_avg = day_avg.sort_values(['Name', 'Day of Week'])
    
    return day_avg

# Function to get wait times by hour of day
def get_wait_times_by_hour(park_df):
    """Get average wait times by hour of day for top 5 attractions."""
    if park_df.empty:
        return pd.DataFrame()
    
    # Filter for attractions only with valid wait times
    attractions = park_df[
        (park_df['Type'] == 'ATTRACTION') & 
        (park_df['Wait Minutes'] > 0)
    ]
    
    # Get top 5 attractions by average wait time
    top_attractions = attractions.groupby('Name')['Wait Minutes'].mean().nlargest(5).index
    filtered_attractions = attractions[attractions['Name'].isin(top_attractions)]
    
    # Calculate average wait times by hour for top attractions
    hour_avg = filtered_attractions.groupby(['Name', 'Hour of Day'])['Wait Minutes'].mean().reset_index()
    hour_avg = hour_avg.sort_values(['Name', 'Hour of Day'])
    
    return hour_avg

# Function to get both day of week and hour of day data
def get_wait_times_by_day_and_hour(park_df):
    """Get data for combined day of week and hour of day dashboard."""
    day_data = get_wait_times_by_day(park_df)
    hour_data = get_wait_times_by_hour(park_df)
    
    return {
        'day': day_data,
        'hour': hour_data
    }

#6/19/2025 Funciton to get top 5 waits line chart for current day: 
def get_top5_hourly_data_today(park_df):
    """
    Returns a dict {ride_name: hourly_df} for the **top‑5 attractions TODAY**,
    where hourly_df has columns Hour (int 7‑24) and AvgWait (float) with
    all points where AvgWait <= 5 trimmed out.
    """
    if park_df.empty:
        return {}

    # Eastern time today normalized
    today_eastern = pd.Timestamp.now(tz='US/Eastern').normalize()
    today_df = park_df[park_df['Timestamp'].dt.normalize() == today_eastern]

    if today_df.empty:
        return {}

    # Top 5 rides by average wait time today
    top5 = (
        today_df
        .groupby('Name')['Wait Minutes']
        .mean()
        .nlargest(5)
        .index
        .tolist()
    )

    hourly_dict = {}
    all_hours = pd.DataFrame({'Hour': range(7, 25)})

    for ride in top5:
        filtered_df = today_df.loc[today_df['Name'] == ride]
        ride_df = pd.DataFrame(filtered_df.copy()).reset_index(drop=True)
        #ride_df = today_df[today_df['Name'] == ride].reset_index(drop=True).copy()
        ride_df['Hour'] = ride_df['Timestamp'].dt.hour
        hourly = (
            ride_df
            .groupby('Hour')['Wait Minutes']
            .mean()
            .reset_index()
            .rename(columns={'Wait Minutes': 'AvgWait'})
        )

        # Keep hours 7 to 24 and fill missing hours with zero
        hourly = all_hours.merge(hourly, on='Hour', how='left').fillna(0)

        # Trim out low average waits <= 5
        hourly = hourly[hourly['AvgWait'] > 5]

        if not hourly.empty:
            hourly_dict[ride] = hourly

    return hourly_dict

# Load all park data and park info
park_data = {}
park_info = {}
for park_name in parks.keys():
    park_data[park_name] = load_park_data(park_name)
    park_info[park_name] = load_park_info(park_name)
    # print(f"Loaded {len(park_data[park_name])} wait time records for {park_name}")
    # print(f"Loaded {len(park_info[park_name])} info records for {park_name}")

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Parklytics</title>
        {%metas%}
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# App layout
app.layout = dbc.Container([
    html.H1("Parklytics Disney World Dashboard", className="text-center my-4"),
    
    # Weather Goes Here
    get_weather_report_div(),
    
    # Park Info Section
    html.Div([
        html.H2("Today's Park Information", className="text-center mb-4"),
        html.Div(id="park-info-section", className="mb-4"),
    ]),
      
    # Current Day Snapshot Section
    html.Div([
        html.H2("Today's Day Snapshot", className="text-center mb-4"),
        html.Div(id="snapshot-section", className="mb-5"),
    ]),
      
    # Current Wait Times Section
    html.Div([
        html.H2("Current Wait Times - Top 5 Attractions", className="text-center mb-4"),
        html.Div(id="current-wait-times", className="mb-5"),
    ]),
    
    #6/19/2025 Top 5 Rides Hourly Trends Section
    html.Div([
        html.H2("Top 5 Rides – Hourly Trends (Today)", className="text-center mb-4"),
        html.Div(id="ride-hourly-trends", className="mb-5"),
    ]),
    
    # Combined Day and Hour Section
    html.Div([
        html.H2("Combined Day & Hour Analysis - Top 5 Attractions", className="text-center mb-4"),
        html.Div(id="combined-day-hour", className="mb-5"),
    ]),
    
    #6/20/2025 Refresh Interval 
    dcc.Interval(
    id='interval-component',
    interval=300 * 1000,  # 5 minutes (300,000 ms)
    n_intervals=0
),
html.Div(id='live-update-text', style={'display': 'none'}),
    
], fluid=True)

# Callback for the park info section
@app.callback(
    Output("park-info-section", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_park_info(_):
    park_cards = []

    for park_name, info in parks.items():
        today_info = get_today_park_info(park_info[park_name])
        
        if not today_info.empty:
            # Extract specific rows by Type
            park_hours = today_info[today_info['Type'] == 'FULL_DAY_HOURS']
            special_events = today_info[(today_info['Type'] == 'TICKETED_EVENT') & today_info['Description'].isin(['Early Entry', 'Extended Evening'])]
            special_events = special_events.drop_duplicates(subset=['Type', 'Opening Time', 'Closing Time', 'Description'])
            park_hopping = today_info[(today_info['Type'] == 'INFO') & (today_info['Description'] == 'Park Hopping')]
            lightning_lanes = today_info[today_info['Purchase Type'].notna()] if 'Purchase Type' in today_info.columns else pd.DataFrame()
            
            # Get evening show info
            evening_show = evening_shows.get(park_name, "N/A")
            evening_showtime = get_evening_showtime(park_name, evening_show)

            # Card content
            card_content = []

            # Operating Hours
            if not park_hours.empty:
                row = park_hours.iloc[0]
                card_content.append(html.Div([
                    html.H5("Operating Hours", className="section-title"),
                    html.P(f"{row['Opening Time']} - {row['Closing Time']}", className="section-content")
                ]))

            # Special Events
            if not special_events.empty:
                event_lines = []
                for _, row in special_events.iterrows():
                    event_lines.append(f"{row['Description']}: {row['Opening Time']} - {row['Closing Time']}")
                card_content.append(html.Div([
                    html.H5("Special Events", className="section-title"),
                    *[html.P(line, className="section-content") for line in event_lines]
                ]))

            # Lightning Lanes
            if not lightning_lanes.empty:
                ll_lines = []
                for _, row in lightning_lanes.iterrows():
                    try:
                        price = float(row['Price']) if not pd.isna(row['Price']) else 0
                        if price > 999:  # Fix cents-style data
                            price /= 100
                        price_str = f"${price:.2f}"
                    except (ValueError, TypeError):  
                        price_str = "N/A"

                    # Only show "Not Available" if it's truly not available
                    if row['Available'] == "Not Available for Purchase":
                        line = f"{row['Purchase Name']}: {price_str} - Not Available for Purchase"
                    else:
                        line = f"{row['Purchase Name']}: {price_str}"
                        ll_lines.append(html.Span(line))
                        ll_lines.append(html.Br())
                    #ll_lines.append(html.P(line, className="section-content"))

                card_content.append(html.Div([
                    html.H5("Lightning Lanes", className="section-title"),
                    *ll_lines
                ], style={"marginBottom": "1rem"}))  # or "16px" if you're old-school
                
                # card_content.append(html.Div([
                #     html.H5("Lightning Lanes", className="section-title"),
                #     *ll_lines
                # ]))
                                
            # Park Hopping
            if not park_hopping.empty:
                row = park_hopping.iloc[0]
                card_content.append(html.Div([
                    html.H5("Park Hopping", className="section-title"),
                    html.P(f"Available After {row['Opening Time']}", className="section-content")
                ]))

            # End-of-Night Show
            card_content.append(html.Div([
                html.H5("End-of-Night Show", className="section-title"),
                html.P(f"{evening_show} – Starts: {evening_showtime}", className="section-content")
            ]))

            # Final card
            park_cards.append(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H4(f"{park_name} – Park Info", className="card-title text-center"),
                            html.Hr(),
                            *card_content
                        ]),
                        className="mb-4",
                        style={"borderTop": f"5px solid {info['color']}"}
                    ),
                    xs=12, sm=12, md=6, lg=3
                )
            )

    return dbc.Row(park_cards, className="mb-4")

# Callback for Snapshot Section
@app.callback(
    Output("snapshot-section", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_snapshot(_):
    snapshot_rows = []

    try:
        conn = sqlite3.connect(db_path)
        latest_time = get_latest_snapshot_timestamp(conn)

        if not latest_time:
            return html.P("No snapshot data available.")

        for park_name, info in parks.items():
            top5_df = get_top_5_waits_per_park(conn, park_name, latest_time)
            top5_df = top5_df.drop_duplicates(subset=['name'])
            top5_df = top5_df.sort_values(by='wait_minutes', ascending=False)
            longest, shortest = get_extreme_waits(conn, park_name, latest_time)
            percent_operating = get_operating_percentage(conn, park_name, latest_time)
            closed_df = get_closed_attractions(conn, park_name, latest_time)
            closed_df = closed_df.drop_duplicates(subset=['name', 'status'])


            # Top 5 Table
            table = dbc.Table.from_dataframe(
                top5_df.rename(columns={"name": "Attraction", "wait_minutes": "Wait (min)"}),
                striped=True, bordered=True, hover=True, size="sm", className="mb-2"
            )
            
            # Sort so 'REFURBISHMENT' rows come last
            closed_df['status_sort'] = closed_df['status'].apply(lambda x: 1 if x == 'REFURBISHMENT' else 0)
            closed_df = closed_df.sort_values(by=['status_sort', 'name']).drop(columns=['status_sort'])
            
            # 6/21/2025 Closed Attraction List with styling and italics
            closed_list = html.Ul([
                html.Li(
                    f"{row['name']} – {'Closed for Refurbishment' if row['status'] == 'REFURBISHMENT' else 'Closed'}",
                    style={
                        "fontSize": "0.85rem",      # smaller font
                        "fontStyle": "italic",      # italicized text
                        "color": "#6c757d"          # muted gray color to match Bootstrap text-muted
                    }
                )
                for _, row in closed_df.iterrows()
            ]) if not closed_df.empty else html.P(
                "None currently closed.",
                className="text-muted",
                style={"fontSize": "0.85rem", "fontStyle": "italic"}
            )

            snapshot_rows.append(
                dbc.Col([
                    html.H5(park_name, className="text-center mt-2"),
                    table,
                    html.Div([
                        html.P(f"Longest Wait: {longest[0]} – {longest[1]} min"),
                        html.P(f"Shortest Wait: {shortest[0]} – {shortest[1]} min"),
                        html.P(f"Operating Attractions: {percent_operating}%")
                    ], className="text-muted", style={"fontSize": "0.9rem"}),

                    html.Div([
                        html.H6("Closed Attractions", className="mt-3"),
                        closed_list
                    ])
                ], xs=12, sm=12, md=6, lg=3)
            )

        conn.close()
        return dbc.Row(snapshot_rows)

    except Exception as e:
        print(f"Snapshot error: {e}")
        return html.P("Error loading snapshot data.")
            
# Callback for current wait times
@app.callback(
    Output("current-wait-times", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_current_wait_times(_):
    park_rows = []
    
    for park_name, info in parks.items():
        current_wait_times = get_current_wait_times(park_data[park_name])
        
        if not current_wait_times.empty:
            # Sort by wait time (descending)
            current_wait_times = current_wait_times.sort_values('Wait Minutes', ascending=False)
            
            # Generate colors for each attraction
            colors = generate_colors(len(current_wait_times))
            
            # Create a figure for this park
            fig = go.Figure()
            
            # Add vertical bar chart
            fig.add_trace(
                go.Bar(
                    x=current_wait_times['Name'],
                    y=current_wait_times['Wait Minutes'],
                    marker_color=colors,
                    text=current_wait_times['Wait Minutes'],
                    textposition='auto',
                    hoverinfo='text',
                    hovertext=[
                        f"{ride}<br>Wait: {wait} minutes" 
                        for ride, wait in zip(current_wait_times['Name'], current_wait_times['Wait Minutes'])
                    ], 
                    showlegend=False
                )
            )
            
            # Add colored rectangles in the legend for each attraction
            for i, (_, row) in enumerate(current_wait_times.iterrows()):
                fig.add_trace(
                    go.Scatter(
                        x=[None],
                        y=[None],
                        mode='markers',
                        marker=dict(size=10, color=colors[i]),
                        name=row['Name'],
                        legendgroup=row['Name'],
                        showlegend=True
                    )
                )
            
            # Update layout
            fig.update_layout(
                title=f"{park_name} - Current Wait Times",
                xaxis=dict(
                    title="",  # Remove the "Attraction" title
                    showticklabels=False  # Hide the attraction names
                ),
                yaxis=dict(title="Wait Time (minutes)"),
                height=400,
                margin=dict(l=50, r=50, b=50, t=100),  # Reduced bottom margin since no labels
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=1.3
                ),
                bargap=0.2
            )
            # fig.update_layout(
            #     title=f"{park_name} - Current Wait Times",
            #     xaxis=dict(title="Attraction", tickangle=60, tickfont=dict(size=8)),
            #     yaxis=dict(title="Wait Time (minutes)"),
            #     height=400,
            #     margin=dict(l=50, r=50, b=100, t=100),
            #     legend=dict(
            #         orientation="v",
            #         yanchor="top",
            #         y=0.99,
            #         xanchor="right",
            #         x=1.3
            #     ),
            #     bargap=0.2
            # )
            
            park_rows.append(dbc.Row([
                dbc.Col([
                    html.Div(
                        dcc.Graph(
                            figure=fig,
                            config={'responsive': True},
                            style={'minWidth': '600px'}
                        ),
                        style={'overflowX': 'auto'}
                    )
                ])
            ], className="mb-4"))
    
    return html.Div(park_rows)

#6/19/2025 Callback for Top 5 Rides by hour of day
@app.callback(
    Output("ride-hourly-trends", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_ride_hourly_trends(_):
    trend_rows = []

    for park_name, info in parks.items():
        hourly_data_dict = get_top5_hourly_data_today(park_data[park_name])

        # Skip park if no data
        if not hourly_data_dict:
            continue

        park_cols = []
        colors = generate_colors(len(hourly_data_dict))

        for i, (ride, df_hourly) in enumerate(hourly_data_dict.items()):
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=df_hourly['Hour'],
                    y=df_hourly['AvgWait'],
                    mode='lines+markers',
                    name=ride,
                    line=dict(width=1.5, color=colors[i]),
                    marker=dict(size=6, color=colors[i]),
                    hovertemplate="%{x}:00 – %{y:.1f} min"
                )
            )

            fig.update_layout(
                title=ride,
                xaxis=dict(
                    title="Hour",
                    tickmode='array',
                    tickvals=list(range(7, 25)),
                    ticktext=[f"{h:02d}:00" for h in range(7, 25)],
                    tickfont=dict(size=8),
                    range=[7, 24],
                    type='linear'
                ),
                yaxis_title="Avg Wait (min)",
                height=250,
                margin=dict(l=40, r=20, b=40, t=40),
                showlegend=False
            )

            park_cols.append(
                dbc.Col(
                    dcc.Graph(
                        figure=fig,
                        config={'responsive': True},
                        style={'minWidth': '300px'}
                    ),
                    xs=12, sm=12, md=6, lg=4, xl=3
                )
            )

        # Wrap the five ride‑charts for this park in a card‑like group
        trend_rows.append(
            html.Div([
                html.H4(f"{park_name}", className="text-center mb-2", style={"color": info['color']}),
                dbc.Row(park_cols, className="mb-5")
            ])
        )

    return html.Div(trend_rows)

# 6/20/2025 Callback for Inverval Timer
@app.callback(
    Output('live-update-text', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_layout(n):
    # Refresh global park data
    global park_data
    for park_name in parks.keys():
        park_data[park_name] = load_park_data(park_name)

    return f"Updated {n} times."

# @app.callback(
#     Output('live-update-text', 'children'),
#     Input('interval-component', 'n_intervals')
# )

# def update_layout(n):
#     # Your update logic here
#     return f"Updated {n} times."

@app.callback(
    Output("combined-day-hour", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_combined_day_hour(_):
    park_rows = []

    for park_name, info in parks.items():
        combined_data = get_wait_times_by_day_and_hour(park_data[park_name])
        day_data = combined_data['day']
        hour_data = combined_data['hour']

        if not day_data.empty and not hour_data.empty:
            attractions = day_data['Name'].unique()[:10]
            colors = generate_colors(len(attractions))

            # --- DAY OF WEEK CHART ---
            day_fig = go.Figure()
            for i, attraction in enumerate(attractions):
                day_attraction_data = day_data[day_data['Name'] == attraction]
                
                if not day_attraction_data.empty:
                    day_fig.add_trace(
                        go.Scatter(
                            x=day_attraction_data['Day of Week'],
                            y=day_attraction_data['Wait Minutes'],
                            mode='lines+markers',
                            name=attraction,
                            line=dict(width=1.5, color=colors[i]),
                            marker=dict(size=6, color=colors[i]),
                            hoverinfo='text',
                            hovertext=[
                                f"{attraction}<br>{day}: {wait:.1f} minutes"
                                for day, wait in zip(day_attraction_data['Day of Week'], day_attraction_data['Wait Minutes'])
                            ]
                        )
                    )
            day_fig.update_layout(
                title=f"{park_name} - Average Wait Time by Day of Week",
                xaxis_title="Day of Week",
                yaxis_title="Average Wait Time (minutes)",
                height=400,
                margin=dict(l=50, r=50, b=50, t=100)
            )

            # --- HOUR OF DAY CHART ---
            hour_fig = go.Figure()
            for i, attraction in enumerate(attractions):
                hour_attraction_data = hour_data[hour_data['Name'] == attraction]

                # Filter to only include hours from 7 (7 AM) to 23 (11 PM)
                hour_attraction_data = hour_data[
                (hour_data['Name'] == attraction) &
                (hour_data['Hour of Day'] >= 6) &
                (hour_data['Hour of Day'] <= 24)
            ]

                if not hour_attraction_data.empty:
                    hour_fig.add_trace(
                        go.Scatter(
                            x=hour_attraction_data['Hour of Day'],
                            y=hour_attraction_data['Wait Minutes'],
                            mode='lines+markers',
                            name=attraction,
                            line=dict(width=1.5, color=colors[i]),
                            marker=dict(size=6, color=colors[i]),
                            hoverinfo='text',
                            hovertext=[
                                f"{attraction}<br>{hour}:00 - {wait:.1f} minutes"
                                for hour, wait in zip(hour_attraction_data['Hour of Day'], hour_attraction_data['Wait Minutes'])
                            ]
                        )
                    )
            
           
            hour_fig.update_layout(
                title=f"{park_name} - Average Wait Time by Hour of Day",
                xaxis=dict(
                    title="Hour of Day",
                    tickmode='array',
                    tickvals=list(range(7, 24)),
                    ticktext=[f"{h:02d}:00" for h in range(7, 24)],
                    tickangle=0,
                    tickfont=dict(size=8),
                    range=[6, 24],
                    type='linear'  # <- Force linear x-axis scale
                ),
                yaxis_title="Average Wait Time (minutes)",
                height=400,
                margin=dict(l=50, r=50, b=50, t=100)
            )
            
            # Append both graphs separately
            park_rows.append(
                dbc.Row(
                    dbc.Col(
                        html.Div(
                            dcc.Graph(
                                figure=day_fig,
                                config={'responsive': True},
                                style={'minWidth': '600px'}
                            ),
                            style={'overflowX': 'auto'}
                        )
                    ),
                    className="mb-4"
                )
            )
            park_rows.append(
                dbc.Row(
                    dbc.Col(
                        html.Div(
                            dcc.Graph(
                                figure=hour_fig,
                                config={'responsive': True},
                                style={'minWidth': '600px'}
                            ),
                            style={'overflowX': 'auto'}
                        )
                    ),
                    className="mb-5"
                )
            )

    return html.Div(park_rows)



# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8051, debug=True)