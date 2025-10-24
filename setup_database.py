#!/usr/bin/env python3
"""
ProMonitor Database Setup - Real-Time Version
Generates readings with CURRENT timestamps (last 5 minutes) for immediate dashboard display
"""

import psycopg2
import os
import random
from datetime import datetime, timedelta

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

def main():
    print("="*60)
    print("🚀 ProMonitor Database Setup - Real-Time Mode")
    print("="*60)
    
    # Connect to database
    config = get_db_config()
    print(f"\n📡 Connecting to {config['host']}:{config['port']}/{config['database']}...")
    conn = psycopg2.connect(**config)
    conn.autocommit = False
    cursor = conn.cursor()
    print("✅ Connected!")
    
    # Drop old table
    print("\n📝 Dropping old table if exists...")
    cursor.execute("DROP TABLE IF EXISTS sensor_readings CASCADE")
    conn.commit()
    print("✅ Old table dropped!")
    
    # Create table
    print("\n📝 Creating sensor_readings table...")
    create_table_sql = """
        CREATE TABLE sensor_readings (
            id SERIAL PRIMARY KEY,
            sensor_id INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            temperature DECIMAL(5,2),
            humidity DECIMAL(5,2),
            co2 DECIMAL(7,2),
            pressure DECIMAL(7,2),
            building_id INTEGER NOT NULL,
            controller_id INTEGER NOT NULL
        )
    """
    cursor.execute(create_table_sql)
    conn.commit()
    print("✅ Table created!")
    
    # Create indexes
    print("\n🔍 Creating indexes...")
    cursor.execute("CREATE INDEX idx_sensor_id ON sensor_readings(sensor_id)")
    cursor.execute("CREATE INDEX idx_timestamp ON sensor_readings(timestamp DESC)")
    cursor.execute("CREATE INDEX idx_building_id ON sensor_readings(building_id)")
    conn.commit()
    print("✅ Indexes created!")
    
    # Check existing data
    print("\n📊 Checking existing data...")
    cursor.execute("SELECT COUNT(*) FROM sensor_readings")
    existing_count = cursor.fetchone()[0]
    print(f"Found {existing_count} existing readings")
    
    # Generate test data with CURRENT timestamps (last 5 minutes)
    print("\n🌱 Seeding database with REAL-TIME test data...")
    print("   (Generating readings for last 5 minutes)")
    
    buildings = [
        {'id': 1, 'controllers': 3, 'temp_base': 20},
        {'id': 2, 'controllers': 3, 'temp_base': 22},
        {'id': 3, 'controllers': 3, 'temp_base': 24},
        {'id': 4, 'controllers': 2, 'temp_base': 25},
        {'id': 5, 'controllers': 2, 'temp_base': 26}
    ]
    
    # Generate readings for last 5 minutes only (current time window)
    now = datetime.now()
    start_time = now - timedelta(minutes=5)  # Last 5 minutes
    
    # Generate 1 reading per sensor every 30 seconds = 10 readings per sensor
    time_interval = timedelta(seconds=30)
    readings_per_sensor = 10
    
    sensor_id = 1
    total_readings = 0
    insert_batch = []
    
    for building in buildings:
        for controller_id in range(1, building['controllers'] + 1):
            # Each controller has 4 sensors
            for sensor_num in range(1, 5):
                # Generate base values for this sensor
                temp_base = building['temp_base'] + random.uniform(-2, 2)
                humidity_base = 45 + building['id'] * 2 + random.uniform(-5, 5)
                co2_base = 400 + building['id'] * 50 + random.uniform(-30, 30)
                pressure_base = 1013 + random.uniform(-5, 5)
                
                # Generate readings over time
                for i in range(readings_per_sensor):
                    timestamp = start_time + (time_interval * i)
                    
                    # Add realistic variations
                    temperature = temp_base + random.uniform(-0.5, 0.5)
                    humidity = humidity_base + random.uniform(-2, 2)
                    co2 = co2_base + random.uniform(-20, 20)
                    pressure = pressure_base + random.uniform(-1, 1)
                    
                    insert_batch.append((
                        sensor_id,
                        timestamp,
                        round(temperature, 2),
                        round(humidity, 2),
                        round(co2, 2),
                        round(pressure, 2),
                        building['id'],
                        controller_id
                    ))
                    
                    total_readings += 1
                    
                    # Insert in batches of 500
                    if len(insert_batch) >= 500:
                        cursor.executemany("""
                            INSERT INTO sensor_readings 
                            (sensor_id, timestamp, temperature, humidity, co2, pressure, building_id, controller_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, insert_batch)
                        conn.commit()
                        insert_batch = []
                        print(f"   Generated {total_readings} readings...")
                
                sensor_id += 1
    
    # Insert remaining
    if insert_batch:
        cursor.executemany("""
            INSERT INTO sensor_readings 
            (sensor_id, timestamp, temperature, humidity, co2, pressure, building_id, controller_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, insert_batch)
        conn.commit()
    
    print(f"\n✅ Successfully generated {total_readings} REAL-TIME readings!")
    
    # Show statistics
    print("\n📈 Final statistics:")
    for building in buildings:
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                AVG(temperature) as avg_temp,
                AVG(humidity) as avg_humidity
            FROM sensor_readings
            WHERE building_id = %s
        """, (building['id'],))
        
        result = cursor.fetchone()
        count, avg_temp, avg_humidity = result
        print(f"  Building {building['id']}: {count} readings, " +
              f"Avg Temp: {avg_temp:.2f}°C, Avg Humidity: {avg_humidity:.2f}%")
    
    # Verify timestamp range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM sensor_readings")
    min_time, max_time = cursor.fetchone()
    print(f"\n⏰ Time range: {min_time} to {max_time}")
    print(f"   Duration: {(max_time - min_time).total_seconds() / 60:.1f} minutes")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("🎉 Database setup complete!")
    print("="*60)
    print("\n🌐 Open dashboard: https://emulator.promonitor.kz")
    print("   Dashboard will now show LIVE data!")
    print("="*60)

if __name__ == '__main__':
    main()
