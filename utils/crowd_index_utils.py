import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import logging
from typing import Dict, Optional, Tuple
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration with dynamic normalization factors
PARK_CONFIG = {
    "Magic Kingdom": {"max_attractions": 25, "weight_factor": 1.2},  # Higher weight for premier park
    "Epcot": {"max_attractions": 12, "weight_factor": 1.0},
    "Hollywood Studios": {"max_attractions": 10, "weight_factor": 1.1},
    "Animal Kingdom": {"max_attractions": 6, "weight_factor": 1.0}
}

# Dynamic normalization factors based on config
NORMALIZATION_FACTORS = {
    park: 60 * config["max_attractions"] * config["weight_factor"]
    for park, config in PARK_CONFIG.items()
}

PARKS = list(NORMALIZATION_FACTORS.keys())
DB_PATH = r'E:\app_data\db_live\live.db'

# Time window for crowd calculation (minutes)
TIME_WINDOW_MINUTES = 5  # Increased for more stable results

# Crowd level thresholds (configurable)
CROWD_THRESHOLDS = [
    (25, "🟢 Light"),
    (50, "🟡 Moderate"), 
    (75, "🟠 Busy"),
    (100, "🔴 Packed")
]

@contextmanager
def get_db_connection(db_path: str):
    """Context manager for database connections with proper error handling."""
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def validate_timestamp(timestamp: str) -> bool:
    """Validate timestamp format."""
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00') if timestamp.endswith('Z') else timestamp)
        return True
    except (ValueError, TypeError):
        return False

def get_latest_timestamp(conn: sqlite3.Connection) -> Optional[str]:
    """Get the latest timestamp from queue_status with validation."""
    try:
        query = """
        SELECT MAX(timestamp) as latest_timestamp
        FROM queue_status 
        WHERE timestamp IS NOT NULL
        """
        result = conn.execute(query).fetchone()
        
        if result and result[0]:
            timestamp = result[0]
            if validate_timestamp(timestamp):
                return timestamp
            else:
                logger.warning(f"Invalid timestamp format found: {timestamp}")
        
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching latest timestamp: {e}")
        return None

def get_park_attraction_stats(conn: sqlite3.Connection, park_name: str) -> Tuple[int, int]:
    """Get current operating and total attractions for a park."""
    try:
        # Get total attractions
        total_query = """
        SELECT COUNT(*) as total
        FROM entities 
        WHERE park = ? AND type = 'ATTRACTION'
        """
        total_result = conn.execute(total_query, (park_name,)).fetchone()
        total_attractions = total_result[0] if total_result else 0
        
        # Get currently operating attractions (from recent data)
        operating_query = """
        SELECT COUNT(DISTINCT e.id) as operating
        FROM entities e
        JOIN queue_status qs ON e.id = qs.entity_id
        WHERE e.park = ? 
          AND e.type = 'ATTRACTION'
          AND qs.status = 'OPERATING'
          AND qs.timestamp >= datetime('now', '-1 hour')
        """
        operating_result = conn.execute(operating_query, (park_name,)).fetchone()
        operating_attractions = operating_result[0] if operating_result else 0
        
        return operating_attractions, total_attractions
        
    except sqlite3.Error as e:
        logger.error(f"Error getting park stats for {park_name}: {e}")
        return 0, 0

def calculate_crowd_index(conn: sqlite3.Connection, park_name: str, timestamp: str) -> Dict:
    """
    Calculate crowd index with enhanced accuracy and additional metrics.
    Returns dictionary with crowd_index, metrics, and metadata.
    """
    try:
        # Parse timestamp and create time window
        base_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if timestamp.endswith('Z') else timestamp)
        start_time = (base_time - timedelta(minutes=TIME_WINDOW_MINUTES)).isoformat()
        end_time = (base_time + timedelta(minutes=TIME_WINDOW_MINUTES)).isoformat()

        # Enhanced query with better filtering and additional data
        query = """
        SELECT 
            qs.wait_minutes,
            qs.timestamp,
            e.name as attraction_name,
            qs.status
        FROM queue_status qs
        JOIN entities e ON qs.entity_id = e.id
        WHERE e.park = ?
          AND e.type = 'ATTRACTION'
          AND qs.status = 'OPERATING'
          AND qs.timestamp BETWEEN ? AND ?
          AND qs.wait_minutes IS NOT NULL
          AND qs.wait_minutes >= 0
          AND qs.wait_minutes <= 480  -- Filter out unrealistic wait times (8 hours max)
        ORDER BY qs.timestamp DESC
        """

        df = pd.read_sql_query(query, conn, params=(park_name, start_time, end_time))

        # Get park statistics
        operating_count, total_count = get_park_attraction_stats(conn, park_name)

        if df.empty:
            logger.warning(f"No valid data found for {park_name} in time window")
            return {
                'crowd_index': 0,
                'avg_wait': 0,
                'max_wait': 0,
                'attractions_operating': operating_count,
                'attractions_total': total_count,
                'data_points': 0,
                'confidence': 'Low',
                'timestamp': timestamp
            }

        # Remove duplicate entries (keep most recent per attraction)
        df_latest = df.sort_values('timestamp').groupby('attraction_name').last().reset_index()

        # Calculate metrics
        avg_wait = df_latest['wait_minutes'].mean()
        max_wait = df_latest['wait_minutes'].max()
        num_operating = len(df_latest)
        
        # Enhanced scoring algorithm
        # Base score from average wait times
        base_score = avg_wait * num_operating
        
        # Apply park-specific weighting
        park_weight = PARK_CONFIG.get(park_name, {}).get("weight_factor", 1.0)
        weighted_score = base_score * park_weight
        
        # Adjust for park capacity utilization
        expected_operating = PARK_CONFIG.get(park_name, {}).get("max_attractions", 10)
        if operating_count > 0:
            utilization_factor = min(num_operating / expected_operating, 1.0)
        else:
            utilization_factor = num_operating / expected_operating if expected_operating > 0 else 0
        
        # Final score calculation
        normalization_factor = NORMALIZATION_FACTORS.get(park_name, 60 * 10)
        raw_index = (weighted_score / normalization_factor) * 100
        
        # Apply utilization adjustment (higher utilization = more reliable score)
        adjusted_index = raw_index * (0.5 + 0.5 * utilization_factor)
        
        # Cap at 100 and round
        crowd_index = min(round(adjusted_index), 100)
        
        # Determine confidence level
        confidence = 'High' if num_operating >= expected_operating * 0.7 else \
                    'Medium' if num_operating >= expected_operating * 0.4 else 'Low'

        return {
            'crowd_index': crowd_index,
            'avg_wait': round(avg_wait, 1),
            'max_wait': int(max_wait),
            'attractions_operating': num_operating,
            'attractions_total': total_count,
            'data_points': len(df),
            'confidence': confidence,
            'timestamp': timestamp,
            'utilization_rate': round(utilization_factor * 100, 1)
        }

    except Exception as e:
        logger.error(f"Error calculating crowd index for {park_name}: {e}")
        return {
            'crowd_index': 0,
            'avg_wait': 0,
            'max_wait': 0,
            'attractions_operating': 0,
            'attractions_total': 0,
            'data_points': 0,
            'confidence': 'Error',
            'timestamp': timestamp
        }

def get_crowd_level(score: int) -> str:
    """Get crowd level description based on score."""
    for threshold, level in CROWD_THRESHOLDS:
        if score < threshold:
            return level
    return CROWD_THRESHOLDS[-1][1]  # Return highest level if score >= 100

def format_crowd_report(park_results: Dict) -> None:
    """Format and display crowd report with enhanced information."""
    print("\n🌐 Disney World Park Crowd Index Report")
    print(f"📅 Timestamp: {park_results[PARKS[0]]['timestamp']}")
    print(f"⏰ Analysis Window: ±{TIME_WINDOW_MINUTES} minutes")
    print("=" * 80)
    
    for park in PARKS:
        result = park_results[park]
        score = result['crowd_index']
        level = get_crowd_level(score)
        
        print(f"\n🏰 {park}")
        print(f"   Crowd Index: {score:>3}% {level}")
        print(f"   Avg Wait: {result['avg_wait']:>5.1f} min  |  Max Wait: {result['max_wait']:>3} min")
        print(f"   Operating: {result['attractions_operating']:>2}/{result['attractions_total']:<2} attractions  |  Utilization: {result['utilization_rate']:>5.1f}%")
        print(f"   Data Quality: {result['confidence']:<6} ({result['data_points']} data points)")

def get_crowd_index_summary(db_path: str, parks: list) -> Optional[Dict[str, Dict]]:
    """Returns crowd index data per park for Dash."""
    try:
        with get_db_connection(db_path) as conn:
            latest_timestamp = get_latest_timestamp(conn)
            if not latest_timestamp:
                return None
            return {
                park: calculate_crowd_index(conn, park, latest_timestamp)
                for park in parks
            }
    except Exception as e:
        logger.error(f"Failed to calculate crowd index summary: {e}")
        return None

def main():
    """Main execution function with comprehensive error handling."""
    try:
        with get_db_connection(DB_PATH) as conn:
            # Get latest timestamp
            latest_timestamp = get_latest_timestamp(conn)
            
            if not latest_timestamp:
                logger.error("No valid data available in database")
                print("❌ No data available. Please check database connection and data integrity.")
                return
            
            logger.info(f"Processing crowd data for timestamp: {latest_timestamp}")
            
            # Calculate crowd index for all parks
            park_results = {}
            for park in PARKS:
                logger.info(f"Calculating crowd index for {park}")
                park_results[park] = calculate_crowd_index(conn, park, latest_timestamp)
            
            # Display results
            format_crowd_report(park_results)
            
            # Log summary
            avg_confidence = sum(1 for r in park_results.values() if r['confidence'] == 'High')
            logger.info(f"Analysis complete. {avg_confidence}/{len(PARKS)} parks have high confidence scores")
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Application error: {e}")
        return

if __name__ == "__main__":
    main()