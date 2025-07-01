#7/1/2025 IMPROVED SCRIPT: 

import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple, List
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enhanced configuration with more accurate park-specific data
PARK_CONFIG = {
    "Magic Kingdom": {
        "weight_factor": 1.2,
        "key_attractions": [
            "Space Mountain", "Seven Dwarfs Mine Train", "Splash Mountain", 
            "Big Thunder Mountain Railroad", "Pirates of the Caribbean",
            "Haunted Mansion", "Peter Pan's Flight", "Jungle Cruise"
        ],
        "baseline_wait": 15,  # Expected wait during low crowds
        "peak_multiplier": 4.0,  # How much waits increase at peak
        "capacity_factor": 1.0  # Relative capacity compared to other parks
    },
    "Epcot": {
        "weight_factor": 1.0,
        "key_attractions": [
            "Guardians of the Galaxy", "Remy's Ratatouille Adventure",
            "Test Track", "Soarin'", "Frozen Ever After", "Spaceship Earth"
        ],
        "baseline_wait": 12,
        "peak_multiplier": 3.5,
        "capacity_factor": 1.2
    },
    "Hollywood Studios": {
        "weight_factor": 1.1,
        "key_attractions": [
            "Rise of the Resistance", "Millennium Falcon", "Slinky Dog Dash",
            "Tower of Terror", "Rock 'n' Roller Coaster", "Mickey & Minnie's Runaway Railway"
        ],
        "baseline_wait": 18,
        "peak_multiplier": 5.0,
        "capacity_factor": 0.8
    },
    "Animal Kingdom": {
        "weight_factor": 1.0,
        "key_attractions": [
            "Avatar Flight of Passage", "Na'vi River Journey", "Expedition Everest",
            "Kilimanjaro Safaris", "Dinosaur"
        ],
        "baseline_wait": 10,
        "peak_multiplier": 4.5,
        "capacity_factor": 0.9
    }
}

# Time-based crowd patterns (hour of day adjustments)
HOURLY_ADJUSTMENTS = {
    8: 0.7,   # Early morning - lower crowds
    9: 0.8,   # Building up
    10: 1.0,  # Normal
    11: 1.2,  # Getting busy
    12: 1.4,  # Lunch rush
    13: 1.3,  # Post-lunch
    14: 1.2,  # Afternoon
    15: 1.1,  # Mid-afternoon
    16: 1.0,  # Evening approaches
    17: 0.9,  # Dinner time
    18: 0.8,  # Evening
    19: 0.7,  # Night
    20: 0.6,  # Late night
    21: 0.5   # Very late
}

# Day of week adjustments
DAY_ADJUSTMENTS = {
    0: 1.2,   # Monday - busy (people extending weekends)
    1: 0.8,   # Tuesday - quieter
    2: 0.7,   # Wednesday - quietest
    3: 0.8,   # Thursday - quiet
    4: 1.0,   # Friday - normal
    5: 1.3,   # Saturday - busy
    6: 1.2    # Sunday - busy
}

PARKS = list(PARK_CONFIG.keys())
DB_PATH = r'E:\app_data\db_live\live.db'
TIME_WINDOW_MINUTES = 10  # Wider window for more data points

# More nuanced crowd level thresholds
CROWD_THRESHOLDS = [
    (15, "🟢 Very Light"),
    (30, "🟢 Light"),
    (45, "🟡 Moderate"), 
    (65, "🟠 Busy"),
    (85, "🔴 Very Busy"),
    (100, "🔴 Packed")
]

@contextmanager
def get_db_connection(db_path: str):
    """Context manager for database connections with proper error handling."""
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_historical_baseline(conn: sqlite3.Connection, park_name: str, hour: int, weekday: int) -> float:
    """Get historical baseline wait times for similar conditions."""
    try:
        # Look at same hour and day of week from past 4 weeks
        query = """
        SELECT AVG(qs.wait_minutes) as avg_wait
        FROM queue_status qs
        JOIN entities e ON qs.entity_id = e.id
        WHERE e.park = ?
          AND e.type = 'ATTRACTION'
          AND qs.status = 'OPERATING'
          AND qs.wait_minutes > 0
          AND qs.wait_minutes < 300
          AND CAST(strftime('%H', qs.timestamp) AS INTEGER) BETWEEN ? AND ?
          AND CAST(strftime('%w', qs.timestamp) AS INTEGER) = ?
          AND qs.timestamp >= datetime('now', '-28 days')
          AND qs.timestamp < datetime('now', '-1 day')
        """
        
        result = conn.execute(query, (park_name, hour-1, hour+1, weekday)).fetchone()
        if result and result[0]:
            return float(result[0])
        
        # Fallback to park baseline
        return PARK_CONFIG.get(park_name, {}).get("baseline_wait", 15)
        
    except sqlite3.Error as e:
        logger.error(f"Error getting historical baseline for {park_name}: {e}")
        return PARK_CONFIG.get(park_name, {}).get("baseline_wait", 15)

def get_key_attraction_weights(conn: sqlite3.Connection, park_name: str, attractions: List[str]) -> Dict[str, float]:
    """Calculate weights for key attractions based on recent popularity."""
    weights = {}
    
    try:
        for attraction in attractions:
            query = """
            SELECT AVG(qs.wait_minutes) as avg_wait, COUNT(*) as data_points
            FROM queue_status qs
            JOIN entities e ON qs.entity_id = e.id
            WHERE e.park = ? 
              AND e.name LIKE ?
              AND e.type = 'ATTRACTION'
              AND qs.status = 'OPERATING'
              AND qs.wait_minutes > 0
              AND qs.timestamp >= datetime('now', '-7 days')
            """
            
            result = conn.execute(query, (park_name, f"%{attraction}%")).fetchone()
            
            if result and result[0] and result[1] >= 5:  # Minimum data points
                avg_wait = float(result[0])
                # Higher average waits indicate more popular attractions
                weights[attraction] = min(avg_wait / 30.0, 3.0)  # Cap at 3x weight
            else:
                weights[attraction] = 1.0  # Default weight
                
    except sqlite3.Error as e:
        logger.error(f"Error calculating attraction weights: {e}")
        # Return default weights
        weights = {attraction: 1.0 for attraction in attractions}
    
    return weights

def calculate_enhanced_crowd_index(conn: sqlite3.Connection, park_name: str, timestamp: str) -> Dict:
    """
    Enhanced crowd index calculation with multiple accuracy improvements.
    """
    try:
        # Parse timestamp and get time context
        base_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if timestamp.endswith('Z') else timestamp)
        start_time = (base_time - timedelta(minutes=TIME_WINDOW_MINUTES)).isoformat()
        end_time = (base_time + timedelta(minutes=TIME_WINDOW_MINUTES)).isoformat()
        
        current_hour = base_time.hour
        current_weekday = base_time.weekday()
        
        # Get park configuration
        park_config = PARK_CONFIG.get(park_name, {})
        key_attractions = park_config.get("key_attractions", [])
        baseline_wait = park_config.get("baseline_wait", 15)
        peak_multiplier = park_config.get("peak_multiplier", 4.0)
        capacity_factor = park_config.get("capacity_factor", 1.0)
        
        # Enhanced query with attraction popularity
        query = """
        SELECT 
            qs.wait_minutes,
            qs.timestamp,
            e.name as attraction_name,
            qs.status,
            -- Add attraction popularity score based on recent average waits
            (SELECT AVG(qs2.wait_minutes) 
             FROM queue_status qs2 
             WHERE qs2.entity_id = e.id 
               AND qs2.timestamp >= datetime('now', '-7 days')
               AND qs2.wait_minutes > 0) as avg_recent_wait
        FROM queue_status qs
        JOIN entities e ON qs.entity_id = e.id
        WHERE e.park = ?
          AND e.type = 'ATTRACTION'
          AND qs.status = 'OPERATING'
          AND qs.timestamp BETWEEN ? AND ?
          AND qs.wait_minutes IS NOT NULL
          AND qs.wait_minutes >= 0
          AND qs.wait_minutes <= 300
        ORDER BY qs.timestamp DESC
        """

        df = pd.read_sql_query(query, conn, params=(park_name, start_time, end_time))

        if df.empty:
            return {
                'crowd_index': 0,
                'avg_wait': 0,
                'max_wait': 0,
                'attractions_operating': 0,
                'attractions_total': 0,
                'data_points': 0,
                'confidence': 'Low',
                'timestamp': timestamp,
                'method': 'enhanced'
            }

        # Remove duplicates, keeping most recent per attraction
        df_latest = df.sort_values('timestamp').groupby('attraction_name').last().reset_index()
        
        # Get historical baseline for comparison
        historical_baseline = get_historical_baseline(conn, park_name, current_hour, current_weekday)
        
        # Calculate weighted scores
        key_attraction_weights = get_key_attraction_weights(conn, park_name, key_attractions)
        
        weighted_waits = []
        total_weight = 0
        
        for _, row in df_latest.iterrows():
            wait_time = row['wait_minutes']
            attraction_name = row['attraction_name']
            
            # Determine if this is a key attraction
            is_key_attraction = any(key in attraction_name for key in key_attractions)
            
            if is_key_attraction:
                # Use calculated weight for key attractions
                weight = max([key_attraction_weights.get(key, 1.0) 
                             for key in key_attractions if key in attraction_name])
                weight *= 2.0  # Key attractions get double weight
            else:
                # Regular attractions get baseline weight
                weight = 1.0
                
            # Apply recent popularity adjustment
            if pd.notna(row['avg_recent_wait']) and row['avg_recent_wait'] > 0:
                popularity_factor = min(row['avg_recent_wait'] / baseline_wait, 3.0)
                weight *= popularity_factor
            
            weighted_waits.append(wait_time * weight)
            total_weight += weight
        
        if total_weight == 0:
            return {
                'crowd_index': 0,
                'avg_wait': 0,
                'max_wait': 0,
                'attractions_operating': len(df_latest),
                'attractions_total': 0,
                'data_points': len(df),
                'confidence': 'Low',
                'timestamp': timestamp,
                'method': 'enhanced'
            }
        
        # Calculate metrics
        weighted_avg_wait = sum(weighted_waits) / total_weight
        max_wait = df_latest['wait_minutes'].max()
        num_operating = len(df_latest)
        
        # Enhanced crowd index calculation
        # Step 1: Compare to historical baseline
        baseline_ratio = weighted_avg_wait / max(historical_baseline, 5)  # Avoid division by zero
        
        # Step 2: Apply time-based adjustments
        hour_adjustment = HOURLY_ADJUSTMENTS.get(current_hour, 1.0)
        day_adjustment = DAY_ADJUSTMENTS.get(current_weekday, 1.0)
        
        # Step 3: Calculate raw crowd score
        raw_score = baseline_ratio * 100
        
        # Step 4: Apply temporal adjustments
        adjusted_score = raw_score / (hour_adjustment * day_adjustment)
        
        # Step 5: Apply park-specific adjustments
        park_weight = park_config.get("weight_factor", 1.0)
        capacity_adjusted_score = adjusted_score * park_weight / capacity_factor
        
        # Step 6: Apply operating attraction ratio
        total_attractions = get_total_attractions(conn, park_name)
        operating_ratio = min(num_operating / max(total_attractions * 0.6, 1), 1.0)  # Expect 60% operating
        
        # Final score with operating ratio consideration
        final_score = capacity_adjusted_score * (0.7 + 0.3 * operating_ratio)
        
        # Cap and round
        crowd_index = max(0, min(round(final_score), 100))
        
        # Enhanced confidence calculation
        confidence_factors = [
            num_operating >= 5,  # Sufficient attractions
            len(df) >= 10,       # Sufficient data points
            operating_ratio >= 0.4,  # Reasonable operating ratio
            weighted_avg_wait > 0    # Valid wait times
        ]
        
        confidence_score = sum(confidence_factors) / len(confidence_factors)
        
        if confidence_score >= 0.8:
            confidence = 'High'
        elif confidence_score >= 0.5:
            confidence = 'Medium'
        else:
            confidence = 'Low'

        return {
            'crowd_index': crowd_index,
            'avg_wait': round(weighted_avg_wait, 1),
            'max_wait': int(max_wait),
            'attractions_operating': num_operating,
            'attractions_total': total_attractions,
            'data_points': len(df),
            'confidence': confidence,
            'timestamp': timestamp,
            'method': 'enhanced',
            'baseline_comparison': round(baseline_ratio, 2),
            'historical_baseline': round(historical_baseline, 1),
            'operating_ratio': round(operating_ratio * 100, 1)
        }

    except Exception as e:
        logger.error(f"Error calculating enhanced crowd index for {park_name}: {e}")
        return {
            'crowd_index': 0,
            'avg_wait': 0,
            'max_wait': 0,
            'attractions_operating': 0,
            'attractions_total': 0,
            'data_points': 0,
            'confidence': 'Error',
            'timestamp': timestamp,
            'method': 'enhanced'
        }

def get_total_attractions(conn: sqlite3.Connection, park_name: str) -> int:
    """Get total number of attractions for a park."""
    try:
        query = """
        SELECT COUNT(*) as total
        FROM entities 
        WHERE park = ? AND type = 'ATTRACTION'
        """
        result = conn.execute(query, (park_name,)).fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        logger.error(f"Error getting total attractions for {park_name}: {e}")
        return 0

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

def get_crowd_level(score: int) -> str:
    """Get crowd level description based on score."""
    for threshold, level in CROWD_THRESHOLDS:
        if score <= threshold:
            return level
    return CROWD_THRESHOLDS[-1][1]

def format_enhanced_crowd_report(park_results: Dict) -> None:
    """Format and display enhanced crowd report."""
    print("\n🌐 Enhanced Disney World Park Crowd Index Report")
    print(f"📅 Timestamp: {park_results[PARKS[0]]['timestamp']}")
    print(f"⏰ Analysis Window: ±{TIME_WINDOW_MINUTES} minutes")
    print("=" * 90)
    
    for park in PARKS:
        result = park_results[park]
        score = result['crowd_index']
        level = get_crowd_level(score)
        
        print(f"\n🏰 {park}")
        print(f"   Crowd Index: {score:>3}% {level}")
        print(f"   Avg Wait: {result['avg_wait']:>5.1f} min  |  Max Wait: {result['max_wait']:>3} min")
        print(f"   Operating: {result['attractions_operating']:>2}/{result['attractions_total']:<2} attractions  |  Ratio: {result.get('operating_ratio', 0):>5.1f}%")
        
        if 'baseline_comparison' in result:
            print(f"   vs Historical: {result['baseline_comparison']:>4.1f}x baseline ({result['historical_baseline']:>4.1f} min)")
        
        print(f"   Data Quality: {result['confidence']:<6} ({result['data_points']} data points)")

def main():
    """Main execution function."""
    try:
        with get_db_connection(DB_PATH) as conn:
            latest_timestamp = get_latest_timestamp(conn)
            
            if not latest_timestamp:
                logger.error("No valid data available in database")
                print("❌ No data available. Please check database connection and data integrity.")
                return
            
            logger.info(f"Processing enhanced crowd data for timestamp: {latest_timestamp}")
            
            # Calculate enhanced crowd index for all parks
            park_results = {}
            for park in PARKS:
                logger.info(f"Calculating enhanced crowd index for {park}")
                park_results[park] = calculate_enhanced_crowd_index(conn, park, latest_timestamp)
            
            # Display results
            format_enhanced_crowd_report(park_results)
            
            # Log summary
            high_confidence_count = sum(1 for r in park_results.values() if r['confidence'] == 'High')
            logger.info(f"Enhanced analysis complete. {high_confidence_count}/{len(PARKS)} parks have high confidence scores")
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Application error: {e}")

if __name__ == "__main__":
    main()