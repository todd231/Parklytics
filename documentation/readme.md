# Parklytics - Disney World Dashboard

A comprehensive real-time dashboard for monitoring Disney World park operations, wait times, and analytics. This application provides live tracking of attraction wait times, park schedules, Lightning Lane pricing, and detailed analytics across all four Disney World theme parks.

## Features

### Real-Time Park Monitoring

* Live Wait Times: Current wait times for all attractions across Magic Kingdom, Epcot, Hollywood Studios, and Animal Kingdom
* Park Operating Hours: Daily operating schedules including early entry and extended evening hours
* Lightning Lane Pricing: Real-time Individual Lightning Lane (ILL) and Genie+ pricing
* Show Schedules: Evening show times including Happily Ever After, Luminous, Fantasmic!, and Tree of Life Awakenings
* Weather Integration: Current weather conditions for Disney World area

### Analytics & Insights

* Daily Snapshots: Top 5 longest waits, shortest waits, and operating percentages per park
* Hourly Trend Analysis: Wait time patterns throughout the day for top attractions
* Day-of-Week Analysis: Historical wait time averages by day of the week
* Closed Attractions Tracking: Real-time monitoring of attraction closures and refurbishments

### Interactive Dashboard

* Auto-Refresh: Dashboard updates every 5 minutes with fresh data
* Responsive Design: Mobile-friendly interface with Bootstrap styling
* Color-Coded Parks: Each park has distinct color theming for easy identification
* Interactive Charts: Hover effects and detailed tooltips on all visualizations

## Technology Stack

* Backend: Python with SQLite database
* Frontend: Dash (Plotly) with Bootstrap components
* Data Visualization: Plotly graphs and charts
* External APIs: OpenWeatherMap API for weather data
* Database: SQLite with entities, queue\_status, schedule, and purchases tables

## Installation

### Prerequisites

* Python 3.7+
* SQLite database with Disney World data

### Required Dependencies

```bash
pip install pandas plotly dash dash-bootstrap-components requests sqlite3 python-dateutil
```

### Environment Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Update the database path in the code:

   ```python
   db_path = r"path/to/your/live.db"
   ```
4. Configure OpenWeatherMap API:

   ```python
   API_KEY = "your_openweathermap_api_key"
   ZIP = "32830,US"  # Disney World area zip code
   ```

## Database Schema

The application expects a SQLite database with the following tables:

### entities

* id: Primary key
* name: Attraction/entity name
* type: ATTRACTION, SHOW, etc.
* park: Park name (Magic Kingdom, Epcot, Hollywood Studios, Animal Kingdom)

### queue\_status

* entity\_id: Foreign key to entities table
* wait\_minutes: Wait time in minutes
* timestamp: ISO 8601 timestamp
* status: OPERATING, CLOSED, REFURBISHMENT
* lightning\_lane\_available: Boolean
* lightning\_lane\_cost: Cost in cents

### schedule

* entity\_id: Foreign key to entities table
* date: Schedule date
* start\_time: Start time (ISO 8601)
* end\_time: End time (ISO 8601)
* type: OPERATING, TICKETED\_EVENT, INFO
* description: Schedule description

### purchases

* park\_entity\_id: Foreign key to entities table
* name: Purchase name (e.g., "Genie+", "Individual Lightning Lane")
* purchase\_type: Type of purchase
* price\_amount: Price in cents
* price\_currency: Currency code
* available: Boolean availability

## Usage

### Starting the Application

```bash
python app_dashboard.py
```

The dashboard will be available at [http://localhost:8051](http://localhost:8051)

### Dashboard Sections

1. Weather Report: Current conditions at Disney World
2. Today's Park Information: Operating hours, special events, Lightning Lane pricing, and evening shows
3. Today's Snapshot: Real-time summary of top waits, extremes, and closures
4. Current Wait Times: Top 5 attractions with highest wait times per park
5. Hourly Trends: Wait time patterns for top attractions throughout the day
6. Historical Analysis: Day-of-week and hour-of-day wait time patterns

## Configuration

### Park Configuration

```python
parks = {
    "Magic Kingdom": {"color": "#FF4D00"},
    "Epcot": {"color": "#0080FF"},
    "Hollywood Studios": {"color": "#FF6EC7"},
    "Animal Kingdom": {"color": "#4CAF50"}
}
```

### Evening Shows Mapping

```python
evening_shows = {
    "Magic Kingdom": "Happily Ever After",
    "Epcot": "Luminous The Symphony of Us",
    "Hollywood Studios": "Fantasmic!",
    "Animal Kingdom": "Tree of Life Awakenings"
}
```

### Auto-Refresh Settings

* Refresh Interval: 5 minutes (300 seconds)
* Data Reload: Complete park data refresh on each interval

## Data Processing

### Wait Time Processing

* Converts UTC timestamps to Eastern Time (Disney World timezone)
* Filters out wait times ≤ 1 minute to focus on meaningful waits
* Handles duplicate records by taking maximum wait time per attraction
* Rounds timestamps to nearest minute for consistent snapshots

### Analytics Processing

* Top 5 Analysis: Identifies attractions with highest current wait times
* Hourly Trends: Aggregates wait times by hour (7 AM - 11 PM)
* Day-of-Week Analysis: Historical averages across all seven days
* Operating Status: Calculates percentage of attractions currently operating

## Customization

### Adding New Parks

1. Add park to `parks` dictionary with unique color
2. Add evening show to `evening_shows` dictionary
3. Ensure database contains entities for the new park

### Modifying Refresh Rate

```python
dcc.Interval(
    id='interval-component',
    interval=300 * 1000,  # Change this value (in milliseconds)
    n_intervals=0
)
```

### Customizing Charts

* Colors are automatically generated using the `generate_colors()` function
* Chart styling can be modified in individual callback functions
* Responsive design adapts to different screen sizes

## API Integration

### OpenWeatherMap

* Provides current weather conditions for Disney World area
* Displays temperature, "feels like" temperature, and weather description
* Updates with dashboard refresh cycle

### Future API Integrations

* Disney's official APIs (when available)
* Third-party wait time services
* Social media sentiment analysis
* Crowd calendar integrations

## Performance Considerations

* Database Optimization: Indexes recommended on timestamp, entity\_id, and park columns
* Memory Management: Large datasets are processed in chunks
* Caching: Consider implementing Redis for frequently accessed data
* Concurrent Users: Dash can handle multiple concurrent users, but consider load balancing for high traffic

## Troubleshooting

### Common Issues

1. Database Connection Errors

   * Verify database path is correct
   * Ensure database file has proper permissions
   * Check that all required tables exist
2. Missing Data

   * Verify data ingestion pipeline is running
   * Check for timezone conversion issues
   * Ensure entity types match expected values
3. Chart Display Issues

   * Clear browser cache
   * Check console for JavaScript errors
   * Verify Plotly version compatibility

### Debug Mode

Enable debug mode for development:

```python
app.run(host='0.0.0.0', port=8051, debug=True)
```

## Contributing

1. Follow PEP 8 style guidelines
2. Add comments for complex data processing logic
3. Test with sample data before deploying
4. Update documentation for new features

## License

This project is designed for personal use and Disney World trip planning. Ensure compliance with Disney's terms of service and data usage policies.

## Acknowledgments

* Built with Plotly Dash for interactive web applications
* Weather data provided by OpenWeatherMap
* Designed for Disney World enthusiasts and data analysts

> **Note**: This dashboard is for informational purposes only. Wait times and park information may not reflect official Disney data. Always verify information through official Disney channels for trip planning.
