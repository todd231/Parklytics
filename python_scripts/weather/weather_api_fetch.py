import requests
from datetime import datetime, timezone
import sqlite3
import os
import pytz  # pip install pytz
import schedule
import time

DB_PATH = r'E:\app_data\db_weather\weather.db'
API_KEY = '9b2a3de1dbd52c35bd6c2a7630d54391'
CITY = 'Kissimmee,US'
eastern = pytz.timezone('US/Eastern')

def create_weather_db(db_path=DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_utc TEXT,
            city TEXT,
            lat REAL,
            lon REAL,
            condition TEXT,
            description TEXT,
            icon TEXT,
            temp REAL,
            feels_like REAL,
            temp_min REAL,
            temp_max REAL,
            pressure INTEGER,
            humidity INTEGER,
            visibility INTEGER,
            wind_speed REAL,
            wind_deg INTEGER,
            clouds_all INTEGER,
            sunrise_utc TEXT,
            sunset_utc TEXT
        )
    ''')
    conn.commit()
    conn.close()

def store_weather_data(data, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO weather (
            timestamp_utc, city, lat, lon, condition, description, icon, temp, feels_like, temp_min, temp_max,
            pressure, humidity, visibility, wind_speed, wind_deg, clouds_all, sunrise_utc, sunset_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.fromtimestamp(data['dt'], tz=timezone.utc).isoformat(),
        data['name'],
        data['coord']['lat'],
        data['coord']['lon'],
        data['weather'][0]['main'],
        data['weather'][0]['description'],
        data['weather'][0]['icon'],
        data['main']['temp'],
        data['main']['feels_like'],
        data['main']['temp_min'],
        data['main']['temp_max'],
        data['main']['pressure'],
        data['main']['humidity'],
        data.get('visibility'),
        data['wind']['speed'],
        data['wind']['deg'],
        data['clouds']['all'],
        datetime.fromtimestamp(data['sys']['sunrise'], tz=timezone.utc).isoformat(),
        datetime.fromtimestamp(data['sys']['sunset'], tz=timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()
    print(f"Stored weather data for {data['name']} at {datetime.now(timezone.utc).isoformat()} UTC")

def fetch_weather(city=CITY, api_key=API_KEY):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&units=imperial&appid={api_key}'
    response = requests.get(url)
    print(f"API request status: {response.status_code}")
    print(f"API response: {response.text}")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching weather data: {response.status_code} - {response.text}")
        return None

def fetch_and_store_weather():
    now_et = datetime.now(eastern)
    current_hour = now_et.hour
    if (7 <= current_hour <= 23) or (current_hour == 0) or (current_hour == 1):
        print(f"Fetching weather data at {now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}...")
        create_weather_db()
        data = fetch_weather()
        if data:
            store_weather_data(data)
    else:
        print(f"Outside fetch window ({now_et.strftime('%H:%M')} ET). Skipping.")

if __name__ == "__main__":
    import schedule
    import time

    fetch_and_store_weather()  # Run immediately on start

    schedule.every(30).minutes.do(fetch_and_store_weather)

    while True:
        schedule.run_pending()
        time.sleep(30)
