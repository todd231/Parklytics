import pandas as pd
import plotly.graph_objects as go
import sqlite3
import warnings
import dash
import dash_bootstrap_components as dbc
import requests
import sys
from dash import dcc, html
from dash.dependencies import Input, Output
from datetime import datetime, timedelta
from dateutil import parser
from utils.crowd_index_utils import get_crowd_index_summary, get_crowd_level

sys.path.append("I:/Parklytics")

# Ignore warnings
warnings.filterwarnings('ignore', category=UserWarning)

# Database paths
live_db_path = r"E:\app_data\db_live\live.db"
weather_db_path = r"E:\app_data\db_weather\weather.db"
warehouse_db_path = r"E:\app_data\db_data_warehouse\warehouse.db"

# CONFIGURABLE PARAMETERS - Change these numbers to control how many attractions are shown
TOP_RIDES_HOURLY_TRENDS = 10  # Number of rides to show in hourly trends section
COMBINED_ANALYSIS_COUNT = 15  # Number of rides to show in combined day & hour analysis

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
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#1a55FF', '#FF1A8C', '#1AFF55', '#FF551A', '#8C1AFF',
        '#FF8C1A', '#1AFF8C', '#8CFF1A', '#FF1A55', '#551AFF'
    ]
    # If we need more colors than in our list, cycle through them
    return [colors[i % len(colors)] for i in range(num_colors)]

# Function to load park data from SQLite database
def load_park_data(park_name):
    """Load wait time data for a specific park from the database."""
    try:
        conn = sqlite3.connect(live_db_path)
        
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

# Function to load historical data from warehouse database
def load_warehouse_data(park_name):
    """Load historical wait time data for a specific park from the warehouse database."""
    try:
        conn = sqlite3.connect(warehouse_db_path)
        
        # Query to get historical wait time data
        query = """
        SELECT 
            e.name AS Name,
            e.type AS Type,
            qs.wait_minutes AS wait_minutes,
            qs.timestamp AS timestamp,
            qs.status
        FROM queue_status qs
        JOIN entities e ON qs.entity_id = e.id
        WHERE qs.park = ?  -- NOT e.park
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
        df['Wait Minutes'] = df['wait_minutes'].fillna(0)
        
        return df
    
    except Exception as e:
        print(f"Error loading warehouse data for {park_name}: {e}")
        return pd.DataFrame()

# Function to load park schedule and purchase information
def load_park_info(park_name):
    """Load park information including schedule and purchases from database."""
    try:
        conn = sqlite3.connect(live_db_path)

        # Get schedule information
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
        conn = sqlite3.connect(live_db_path)
        
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
                return dt.strftime("%#I:%M %p")
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

# Function to get weather from weather database
def get_weather_report_div():
    """Get weather information from weather database."""
    try:
        conn = sqlite3.connect(weather_db_path)
        
        # Get the most recent weather data
        query = """
        SELECT description, temp, feels_like, timestamp_utc
        FROM weather
        ORDER BY timestamp_utc DESC 
        LIMIT 1
        """
        
        result = conn.execute(query).fetchone()
        conn.close()
        
        if result:
            description, temp, feels_like, timestamp = result
            report = f"Current Weather is: {description.capitalize()} and {int(round(temp))}°F, but it feels like {int(round(feels_like))}°F in Disney World"
        else:
            # Fallback to API if no database data
            API_KEY = "9b2a3de1dbd52c35bd6c2a7630d54391"
            ZIP = "32830,US"
            URL = f"https://api.openweathermap.org/data/2.5/weather?zip={ZIP}&appid={API_KEY}&units=imperial"
            
            response = requests.get(URL)
            data = response.json()
            
            description = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            report = f"Current Weather is: {description.capitalize()} and {int(round(temp))}°F, but it feels like {int(round(feels_like))}°F in Disney World"
    
    except Exception as e:
        print(f"Error getting weather: {e}")
        report = "Weather information currently unavailable"
    
    return html.Div(report, style={
        'fontSize': '30px',
        'fontWeight': 'bold',
        'marginBottom': '15px',
        'textAlign': 'center',
        'color': '#2c3e50'
    })

# Function to get latest snapshot timestamp
def get_latest_snapshot_timestamp(conn):
    query = "SELECT MAX(DATETIME(timestamp)) FROM queue_status"
    result = conn.execute(query).fetchone()
    return pd.to_datetime(result[0]) if result else None

# Modified snapshot function to show ALL attractions over 10 minutes
def get_all_waits_over_threshold(conn, park_name, timestamp, threshold=10):
    """Get all attractions with wait times over the specified threshold."""
    start = (timestamp - timedelta(minutes=2)).isoformat()
    end = (timestamp + timedelta(minutes=2)).isoformat()
    query = """
    SELECT e.name, MAX(qs.wait_minutes) AS wait_minutes
    FROM queue_status qs
    JOIN entities e ON qs.entity_id = e.id
    WHERE e.park = ? AND e.type = 'ATTRACTION'
        AND qs.timestamp BETWEEN ? AND ?
        AND qs.wait_minutes > ?
    GROUP BY e.name
    ORDER BY wait_minutes DESC;
    """
    return pd.read_sql_query(query, conn, params=(park_name, start, end, threshold))

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

# Modified function to get configurable number of rides for hourly trends
def get_top_rides_hourly_data_today(park_df, num_rides=TOP_RIDES_HOURLY_TRENDS):
    """
    Returns a dict {ride_name: hourly_df} for the **top rides TODAY**,
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

    # Top rides by average wait time today
    top_rides = (
        today_df
        .groupby('Name')['Wait Minutes']
        .mean()
        .nlargest(num_rides)
        .index
        .tolist()
    )

    hourly_dict = {}
    all_hours = pd.DataFrame({'Hour': range(7, 25)})

    for ride in top_rides:
        filtered_df = today_df.loc[today_df['Name'] == ride]
        ride_df = pd.DataFrame(filtered_df.copy()).reset_index(drop=True)
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

# Modified functions for combined analysis using warehouse data
def get_wait_times_by_day_warehouse(park_df, num_attractions=COMBINED_ANALYSIS_COUNT):
    """Get average wait times by day of week for top attractions from warehouse data."""
    if park_df.empty:
        return pd.DataFrame()
    
    # Filter for attractions only with valid wait times
    attractions = park_df[
        (park_df['Type'] == 'ATTRACTION') & 
        (park_df['Wait Minutes'] > 0)
    ]
    
    # Get top attractions by average wait time
    top_attractions = attractions.groupby('Name')['Wait Minutes'].mean().nlargest(num_attractions).index
    filtered_attractions = attractions[attractions['Name'].isin(top_attractions)]
    
    # Calculate average wait times by day of week for top attractions
    day_avg = filtered_attractions.groupby(['Name', 'Day of Week'])['Wait Minutes'].mean().reset_index()
    
    # Ensure proper day order
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_avg['Day of Week'] = pd.Categorical(day_avg['Day of Week'], categories=day_order, ordered=True)
    day_avg = day_avg.sort_values(['Name', 'Day of Week'])
    
    return day_avg

def get_wait_times_by_hour_warehouse(park_df, num_attractions=COMBINED_ANALYSIS_COUNT):
    """Get average wait times by hour of day for top attractions from warehouse data."""
    if park_df.empty:
        return pd.DataFrame()
    
    # Filter for attractions only with valid wait times
    attractions = park_df[
        (park_df['Type'] == 'ATTRACTION') & 
        (park_df['Wait Minutes'] > 0)
    ]
    
    # Get top attractions by average wait time
    top_attractions = attractions.groupby('Name')['Wait Minutes'].mean().nlargest(num_attractions).index
    filtered_attractions = attractions[attractions['Name'].isin(top_attractions)]
    
    # Calculate average wait times by hour for top attractions
    hour_avg = filtered_attractions.groupby(['Name', 'Hour of Day'])['Wait Minutes'].mean().reset_index()
    hour_avg = hour_avg.sort_values(['Name', 'Hour of Day'])
    
    return hour_avg

def get_wait_times_by_day_and_hour_warehouse(park_df, num_attractions=COMBINED_ANALYSIS_COUNT):
    """Get data for combined day of week and hour of day dashboard using warehouse data."""
    day_data = get_wait_times_by_day_warehouse(park_df, num_attractions)
    hour_data = get_wait_times_by_hour_warehouse(park_df, num_attractions)
    
    return {
        'day': day_data,
        'hour': hour_data
    }

# Load all park data and park info
park_data = {}
park_warehouse_data = {}
park_info = {}
for park_name in parks.keys():
    park_data[park_name] = load_park_data(park_name)
    park_warehouse_data[park_name] = load_warehouse_data(park_name)
    park_info[park_name] = load_park_info(park_name)

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
    
    # 06/25/2025 - Crowd Index Summary Section
    html.Div([
        html.H2("Current Crowd Index Summary", className="text-center mb-4"),
        html.Div(id="crowd-index-summary", className="mb-5"),
    ]),
    
    # Current Day Snapshot Section (Modified to show ALL attractions over 10 minutes)
    html.Div([
        html.H2("Today's Day Snapshot - Attractions with 10+ Minute Waits", className="text-center mb-4"),
        html.Div(id="snapshot-section", className="mb-5"),
    ]),
    
    # Top Rides Hourly Trends Section (Modified to be configurable)
    html.Div([
        html.H2(f"Top {TOP_RIDES_HOURLY_TRENDS} Rides – Hourly Trends (Today)", className="text-center mb-4"),
        html.Div(id="ride-hourly-trends", className="mb-5"),
    ]),
    
    # Combined Day and Hour Section (Modified to use warehouse data and be configurable)
    html.Div([
        html.H2(f"Combined Day & Hour Analysis - Top {COMBINED_ANALYSIS_COUNT} Attractions (Historical Data)", className="text-center mb-4"),
        html.Div(id="combined-day-hour", className="mb-5"),
    ]),
    
    # Disclaimer Section
    html.Div([
        html.Hr(),
        html.Div([
            html.P([
                html.Strong("Parklytics – Disney World Dashboard"), 
                " is a comprehensive, near real-time tool for monitoring Disney World park operations, including attraction wait times, park schedules, Lightning Lane pricing, and detailed analytics across all four theme parks."
            ], className="mb-3"),
            html.P([
                html.Strong("Disclaimer:"), 
                " This dashboard is for informational purposes only and is not affiliated with or endorsed by The Walt Disney Company. Wait times, pricing, and park data are based on publicly available sources and may not reflect official Disney data. Always consult official Disney resources when planning your visit."
            ], className="text-muted mb-4")
        ], style={
            'backgroundColor': '#f8f9fa',
            'padding': '20px',
            'borderRadius': '5px',
            'border': '1px solid #dee2e6'
        })
    ]),
    
    # Refresh Interval 
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

                card_content.append(html.Div([
                    html.H5("Lightning Lanes", className="section-title"),
                    *ll_lines
                ], style={"marginBottom": "1rem"}))
                                
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

# Modified Callback for Snapshot Section (shows ALL attractions over 10 minutes)
@app.callback(
    Output("snapshot-section", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_snapshot(_):
    snapshot_rows = []

    try:
        conn = sqlite3.connect(live_db_path)  # Fixed: was db_path, now live_db_path
        latest_time = get_latest_snapshot_timestamp(conn)

        if not latest_time:
            return html.P("No snapshot data available.")

        for park_name, info in parks.items():
            # Fixed: Use the correct function for all waits over threshold
            all_waits_df = get_all_waits_over_threshold(conn, park_name, latest_time, threshold=10)
            all_waits_df = all_waits_df.drop_duplicates(subset=['name'])
            all_waits_df = all_waits_df.sort_values(by='wait_minutes', ascending=False)
            
            longest, shortest = get_extreme_waits(conn, park_name, latest_time)
            percent_operating = get_operating_percentage(conn, park_name, latest_time)
            closed_df = get_closed_attractions(conn, park_name, latest_time)
            closed_df = closed_df.drop_duplicates(subset=['name', 'status'])

            # All attractions over 10 minutes table
            if not all_waits_df.empty:
                table = dbc.Table.from_dataframe(
                    all_waits_df.rename(columns={"name": "Attraction", "wait_minutes": "Wait (min)"}),
                    striped=True, bordered=True, hover=True, size="sm", className="mb-2"
                )
            else:
                table = html.P("No attractions currently have waits over 10 minutes.", className="text-muted")
            
            # Sort so 'REFURBISHMENT' rows come last
            closed_df['status_sort'] = closed_df['status'].apply(lambda x: 1 if x == 'REFURBISHMENT' else 0)
            closed_df = closed_df.sort_values(by=['status_sort', 'name']).drop(columns=['status_sort'])
            
            # Closed Attraction List with styling and italics
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

# Fixed Callback for Top Rides Hourly Trends (corrected function name)
@app.callback(
    Output("ride-hourly-trends", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_ride_hourly_trends(_):
    trend_rows = []

    for park_name, info in parks.items():
        # Fixed: Use the correct function name
        hourly_data_dict = get_top_rides_hourly_data_today(park_data[park_name])

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
                    hovertemplate="%{x}:00 – %{y:.1f} min"
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

        # Wrap the ride charts for this park in a card-like group
        trend_rows.append(
            html.Div([
                html.H4(f"{park_name}", className="text-center mb-2", style={"color": info['color']}),
                dbc.Row(park_cols, className="mb-5")
            ])
        )

    return html.Div(trend_rows)

# Fixed Combined Day and Hour Analysis Callback (using warehouse data)
@app.callback(
    Output("combined-day-hour", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_combined_day_hour(_):
    park_rows = []

    for park_name, info in parks.items():
        # Use warehouse data for historical analysis
        combined_data = get_wait_times_by_day_and_hour_warehouse(park_warehouse_data[park_name])
        day_data = combined_data['day']
        hour_data = combined_data['hour']

        if not day_data.empty and not hour_data.empty:
            attractions = day_data['Name'].unique()[:COMBINED_ANALYSIS_COUNT]  # Use configurable count
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
                title=f"{park_name} - Average Wait Time by Day of Week (Historical)",
                xaxis_title="Day of Week",
                yaxis_title="Average Wait Time (minutes)",
                height=400,
                margin=dict(l=50, r=50, b=50, t=100)
            )

            # --- HOUR OF DAY CHART ---
            hour_fig = go.Figure()
            for i, attraction in enumerate(attractions):
                # Filter to only include hours from 6 to 24
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
                title=f"{park_name} - Average Wait Time by Hour of Day (Historical)",
                xaxis=dict(
                    title="Hour of Day",
                    tickmode='array',
                    tickvals=list(range(7, 24)),
                    ticktext=[f"{h:02d}:00" for h in range(7, 24)],
                    tickangle=0,
                    tickfont=dict(size=8),
                    range=[6, 24],
                    type='linear'
                ),
                yaxis_title="Average Wait Time (minutes)",
                height=400,
                margin=dict(l=50, r=50, b=50, t=100)
            )
            
            # Add both charts for this park
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

# 06/25/2025 - Bulletproofed Callback for Crowd Index Summary
@app.callback(
    Output("crowd-index-summary", "children"),
    Input("interval-component", "n_intervals")
)
def update_crowd_index_summary(n):
    data = get_crowd_index_summary(live_db_path, list(parks.keys()))
    if not data:
        return html.Div("⚠️ Crowd data unavailable.", className="text-muted text-center")

    rows = []
    for park, result in data.items():
        if not result or 'crowd_index' not in result:
            # Park likely closed or data unavailable
            level = "🟢 Light"
            color = "green"
            crowd_index = 0
            avg_wait = 0.0
            max_wait = 0
            attractions_operating = 0
            attractions_total = 0
            utilization = 0
            confidence = "N/A"
            status_note = html.P("📌 Park has not opened yet. Data will begin updating at park open.", className="text-muted small")
        else:
            crowd_index = result.get('crowd_index', 0)
            level = get_crowd_level(crowd_index)
            color = {
                "🟢 Light": "green",
                "🟡 Moderate": "goldenrod",
                "🟠 Busy": "orange",
                "🔴 Packed": "red"
            }.get(level, "black")
            avg_wait = result.get('avg_wait', 0.0)
            max_wait = result.get('max_wait', 0)
            attractions_operating = result.get('attractions_operating', 0)
            attractions_total = result.get('attractions_total', 0)
            utilization = result.get('utilization_rate', 0)
            confidence = result.get('confidence', "N/A")
            status_note = None

        card_body = [
            html.H4(f"{park}", className="card-title"),
            html.P(f"{crowd_index}% {level}", style={"color": color, "fontSize": "1.5rem", "fontWeight": "bold"}),
            html.P(f"Avg Wait: {avg_wait} min", className="text-muted"),
            html.P(f"Max Wait: {max_wait} min", className="text-muted"),
            html.P(f"{attractions_operating}/{attractions_total} Attractions Operating", className="text-muted"),
            html.P(f"Utilization: {utilization}%", className="text-muted"),
            html.P(f"Confidence: {confidence}", className="text-muted")
        ]

        if status_note:
            card_body.append(status_note)

        rows.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(card_body)
                ),
                xs=12, sm=12, md=6, lg=3
            )
        )

    return dbc.Row(rows)


# Callback for Interval Timer (refresh global park data)
@app.callback(
    Output('live-update-text', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_layout(n):
    # Refresh global park data
    global park_data, park_warehouse_data, park_info
    for park_name in parks.keys():
        park_data[park_name] = load_park_data(park_name)
        park_warehouse_data[park_name] = load_warehouse_data(park_name)
        park_info[park_name] = load_park_info(park_name)

    return f"Updated {n} times."

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8051, debug=True)