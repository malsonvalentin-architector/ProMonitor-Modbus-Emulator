#!/usr/bin/env python3
"""Super simple diagnostic"""
import psycopg2
import os

conn = psycopg2.connect(
    host=os.environ.get('PGHOST', 'postgres.railway.internal'),
    port=os.environ.get('PGPORT', '5432'),
    database=os.environ.get('POSTGRES_DB', 'railway'),
    user=os.environ.get('POSTGRES_USER', 'postgres'),
    password=os.environ.get('POSTGRES_PASSWORD')
)

cursor = conn.cursor()

# Check table
cursor.execute("SELECT COUNT(*) FROM sensor_readings")
print(f"Total rows: {cursor.fetchone()[0]}")

# Check without DISTINCT
cursor.execute("SELECT sensor_id, timestamp, temperature FROM sensor_readings ORDER BY timestamp DESC LIMIT 10")
results = cursor.fetchall()
print(f"\nLast 10 readings (no DISTINCT):")
for r in results:
    print(f"  Sensor {r[0]}: {r[1]} - {r[2]}°C")

# Check WITH DISTINCT ON
cursor.execute("""
    SELECT DISTINCT ON (sensor_id) sensor_id, timestamp, temperature 
    FROM sensor_readings 
    ORDER BY sensor_id, timestamp DESC 
    LIMIT 10
""")
results2 = cursor.fetchall()
print(f"\nWith DISTINCT ON (limit 10):")
for r in results2:
    print(f"  Sensor {r[0]}: {r[1]} - {r[2]}°C")

cursor.close()
conn.close()
