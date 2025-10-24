#!/usr/bin/env python3
"""Direct SQL query test"""
import psycopg2
import os
import sys

try:
    conn = psycopg2.connect(
        host=os.environ.get('PGHOST', 'postgres.railway.internal'),
        port=os.environ.get('PGPORT', '5432'),
        database=os.environ.get('POSTGRES_DB', 'railway'),
        user=os.environ.get('POSTGRES_USER', 'postgres'),
        password=os.environ.get('POSTGRES_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    print("="*60)
    print("Direct SQL Query Test")
    print("="*60)
    
    # Same query as app.py
    query = """
        SELECT DISTINCT ON (sensor_id) 
            sensor_id,
            timestamp,
            temperature,
            humidity,
            co2,
            pressure,
            building_id,
            controller_id
        FROM sensor_readings
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        ORDER BY sensor_id, timestamp DESC
    """
    
    cursor.execute(query)
    readings = cursor.fetchall()
    
    print(f"\n✅ Query returned {len(readings)} readings\n")
    
    if readings:
        print("Sample (first 5):")
        for i, r in enumerate(readings[:5]):
            print(f"  {i+1}. Sensor {r[0]}: {r[1]} - Temp: {r[2]}°C, Humidity: {r[3]}%")
    else:
        print("❌ NO READINGS FOUND!")
        
        # Debug: check what's in table
        cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp), NOW() FROM sensor_readings")
        count, min_ts, max_ts, now_ts = cursor.fetchone()
        print(f"\nDebug Info:")
        print(f"  Total readings: {count}")
        print(f"  Oldest: {min_ts}")
        print(f"  Newest: {max_ts}")
        print(f"  Server NOW(): {now_ts}")
        
        if max_ts:
            diff = (now_ts - max_ts).total_seconds() / 3600
            print(f"  Age of newest: {diff:.2f} hours")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
