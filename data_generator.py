#!/usr/bin/env python3
"""
ProMonitor Continuous Data Generator
Generates sensor readings every 10 seconds for real-time simulation
"""

import psycopg2
import os
import time
import random
from datetime import datetime

# Global scenario state
ACTIVE_SCENARIOS = {
    'temperature_spike': False,
    'humidity_drop': False,
    'co2_alarm': False,
    'equipment_failure': False,
    'affected_sensor': None
}

def get_db_config():
    """Get database configuration from environment variables"""
    if os.environ.get('POSTGRES_DB'):
        return {
            'host': os.environ.get('PGHOST', 'localhost'),
            'port': os.environ.get('PGPORT', '5432'),
            'database': os.environ.get('POSTGRES_DB', 'railway'),
            'user': os.environ.get('POSTGRES_USER', 'postgres'),
            'password': os.environ.get('POSTGRES_PASSWORD', '')
        }
    return {
        'host': 'localhost',
        'port': '5432',
        'database': 'promonitor',
        'user': 'postgres',
        'password': 'postgres'
    }

def get_db_connection():
    """Create database connection"""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    conn.autocommit = True
    return conn

def generate_sensor_reading(sensor_id, building_id, controller_id):
    """Generate realistic sensor reading with scenario effects"""
    
    # Base values for each building
    base_temps = {1: 20, 2: 21, 3: 23, 4: 25, 5: 26}
    base_humidity = {1: 47, 2: 49, 3: 51, 4: 53, 5: 55}
    
    # Normal readings with small variations
    temperature = base_temps[building_id] + random.uniform(-2, 2)
    humidity = base_humidity[building_id] + random.uniform(-5, 5)
    co2 = random.uniform(400, 600)
    pressure = random.uniform(990, 1020)
    
    # Apply active scenarios
    if ACTIVE_SCENARIOS.get('temperature_spike') and ACTIVE_SCENARIOS.get('affected_sensor') == sensor_id:
        temperature += random.uniform(8, 12)  # Spike +8-12°C
    
    if ACTIVE_SCENARIOS.get('humidity_drop') and ACTIVE_SCENARIOS.get('affected_sensor') == sensor_id:
        humidity -= random.uniform(15, 25)  # Drop 15-25%
    
    if ACTIVE_SCENARIOS.get('co2_alarm') and ACTIVE_SCENARIOS.get('affected_sensor') == sensor_id:
        co2 += random.uniform(600, 800)  # CO2 spike (1000-1400 ppm)
    
    if ACTIVE_SCENARIOS.get('equipment_failure') and ACTIVE_SCENARIOS.get('affected_sensor') == sensor_id:
        # Equipment failure: erratic readings
        temperature += random.uniform(-10, 10)
        humidity = random.uniform(0, 100)
        co2 = random.uniform(0, 2000)
        pressure = random.uniform(900, 1100)
    
    return {
        'sensor_id': sensor_id,
        'temperature': round(temperature, 2),
        'humidity': round(humidity, 2),
        'co2': round(co2, 2),
        'pressure': round(pressure, 2),
        'building_id': building_id,
        'controller_id': controller_id,
        'timestamp': datetime.now()
    }

def generate_all_sensors():
    """Generate readings for all 50 sensors"""
    
    # 5 buildings, each with different number of controllers and sensors
    sensors_config = [
        # Building 1: 3 controllers, 12 sensors (4 per controller)
        *[(1, 1, s) for s in range(1, 5)],
        *[(1, 2, s) for s in range(5, 9)],
        *[(1, 3, s) for s in range(9, 13)],
        
        # Building 2: 3 controllers, 12 sensors
        *[(2, 4, s) for s in range(13, 17)],
        *[(2, 5, s) for s in range(17, 21)],
        *[(2, 6, s) for s in range(21, 25)],
        
        # Building 3: 3 controllers, 12 sensors
        *[(3, 7, s) for s in range(25, 29)],
        *[(3, 8, s) for s in range(29, 33)],
        *[(3, 9, s) for s in range(33, 37)],
        
        # Building 4: 2 controllers, 8 sensors
        *[(4, 10, s) for s in range(37, 41)],
        *[(4, 11, s) for s in range(41, 45)],
        
        # Building 5: 2 controllers, 8 sensors
        *[(5, 12, s) for s in range(45, 49)],
        *[(5, 13, s) for s in range(49, 53)],
    ]
    
    readings = []
    for building_id, controller_id, sensor_id in sensors_config:
        reading = generate_sensor_reading(sensor_id, building_id, controller_id)
        readings.append(reading)
    
    return readings

def insert_readings(readings):
    """Bulk insert readings into database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Bulk insert
        insert_query = """
            INSERT INTO sensor_readings 
            (sensor_id, timestamp, temperature, humidity, co2, pressure, building_id, controller_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = [
            (
                r['sensor_id'],
                r['timestamp'],
                r['temperature'],
                r['humidity'],
                r['co2'],
                r['pressure'],
                r['building_id'],
                r['controller_id']
            )
            for r in readings
        ]
        
        cursor.executemany(insert_query, values)
        
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"❌ Insert error: {e}")
        return False

def cleanup_old_data():
    """Delete readings older than 1 hour to prevent database bloat"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM sensor_readings 
            WHERE timestamp < NOW() - INTERVAL '1 hour'
        """)
        
        deleted = cursor.rowcount
        cursor.close()
        conn.close()
        
        if deleted > 0:
            print(f"🗑️  Cleaned up {deleted} old readings")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

def run_generator():
    """Main generator loop"""
    print("\n" + "="*60)
    print("🚀 ProMonitor Data Generator Started")
    print("="*60)
    print("📊 Generating readings every 10 seconds...")
    print("🔄 Auto-cleanup: deletes data older than 1 hour")
    print("="*60 + "\n")
    
    iteration = 0
    
    while True:
        try:
            iteration += 1
            
            # Generate readings for all sensors
            readings = generate_all_sensors()
            
            # Insert into database
            success = insert_readings(readings)
            
            if success:
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Generated {len(readings)} readings (iteration #{iteration})")
            
            # Cleanup every 10 iterations (every 100 seconds)
            if iteration % 10 == 0:
                cleanup_old_data()
            
            # Wait 10 seconds
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Generator stopped by user")
            break
        except Exception as e:
            print(f"❌ Generator error: {e}")
            time.sleep(10)  # Wait before retry

if __name__ == '__main__':
    # Wait 5 seconds for database to be ready
    print("⏳ Waiting 5 seconds for database initialization...")
    time.sleep(5)
    
    run_generator()
