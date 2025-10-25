#!/usr/bin/env python3
"""
ProMonitor - Modbus Emulator Integration with Main Database
Writes sensor data to Django data_data table instead of sensor_readings
"""

import psycopg2
import os
import time
import random
from datetime import datetime, timedelta
import threading

def get_db_config():
    """Get database configuration from environment variables"""
    # Railway environment variables
    if os.environ.get('POSTGRES_DB'):
        return {
            'host': os.environ.get('PGHOST', 'localhost'),
            'port': os.environ.get('PGPORT', '5432'),
            'database': os.environ.get('POSTGRES_DB', 'railway'),
            'user': os.environ.get('POSTGRES_USER', 'postgres'),
            'password': os.environ.get('POSTGRES_PASSWORD', '')
        }
    # Fallback to DATABASE_URL parsing
    elif os.environ.get('DATABASE_URL'):
        url = os.environ['DATABASE_URL']
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
        if match:
            return {
                'user': match.group(1),
                'password': match.group(2),
                'host': match.group(3),
                'port': match.group(4),
                'database': match.group(5)
            }
    # Development fallback
    return {
        'host': 'localhost',
        'port': '5432',
        'database': 'promonitor',
        'user': 'postgres',
        'password': 'postgres'
    }

def get_db_connection():
    """Create and return database connection"""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    conn.autocommit = True
    return conn

class ModbusIntegrationWriter:
    """
    Writes Modbus emulator data to Django data_data table
    
    Django Data model schema:
    - id (auto)
    - created_at (auto)
    - updated_at (auto)
    - value (float) - sensor reading value
    - date (timestamp) - when reading was taken
    - name_id (foreign key to data_atributes.id) - sensor/attribute ID
    """
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.running = False
        self.sensor_mappings = {}
        
    def connect(self):
        """Connect to database and get sensor mappings"""
        try:
            self.conn = get_db_connection()
            self.cursor = self.conn.cursor()
            print("✅ Connected to ProMonitor database")
            
            # Get available sensors from data_atributes table
            self.cursor.execute("""
                SELECT id, name, sys_id 
                FROM data_atributes 
                WHERE modbus_carel = TRUE
                ORDER BY id
                LIMIT 20
            """)
            sensors = self.cursor.fetchall()
            
            if sensors:
                print(f"✅ Found {len(sensors)} Modbus sensors in database:")
                for sensor in sensors:
                    self.sensor_mappings[sensor[0]] = {
                        'name': sensor[1],
                        'sys_id': sensor[2]
                    }
                    print(f"   - Sensor {sensor[0]}: {sensor[1]} (System {sensor[2]})")
            else:
                print("⚠️  No Modbus sensors found in database")
                print("   Creating demo sensor data...")
                self._create_demo_sensors()
            
            return True
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def _create_demo_sensors(self):
        """Create demo sensors if none exist"""
        # This is a fallback - in production, sensors should be created via Django admin
        print("⚠️  Warning: Demo sensor creation not implemented")
        print("   Please create sensors via Django admin first")
    
    def write_sensor_data(self, sensor_id, value, timestamp=None):
        """
        Write sensor reading to data_data table
        
        Args:
            sensor_id: ID from data_atributes table
            value: Sensor reading value (float)
            timestamp: When reading was taken (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # Check if sensor exists
            if sensor_id not in self.sensor_mappings:
                print(f"⚠️  Sensor {sensor_id} not found in mappings")
                return False
            
            # Insert into data_data table
            self.cursor.execute("""
                INSERT INTO data_data (created_at, updated_at, value, date, name_id)
                VALUES (NOW(), NOW(), %s, %s, %s)
                RETURNING id
            """, (value, timestamp, sensor_id))
            
            result_id = self.cursor.fetchone()[0]
            print(f"✅ Written: Sensor {sensor_id} = {value} at {timestamp} (ID: {result_id})")
            return True
            
        except Exception as e:
            print(f"❌ Error writing sensor data: {e}")
            return False
    
    def start_emulation(self, interval=30):
        """
        Start continuous sensor data emulation
        
        Args:
            interval: Seconds between readings (default 30)
        """
        self.running = True
        print(f"\n🚀 Starting Modbus emulation (interval: {interval}s)")
        
        while self.running:
            try:
                for sensor_id in self.sensor_mappings.keys():
                    # Generate realistic sensor values based on type
                    sensor_name = self.sensor_mappings[sensor_id]['name'].lower()
                    
                    if 'temp' in sensor_name or 'температура' in sensor_name:
                        value = round(random.uniform(18.0, 26.0), 2)
                    elif 'humid' in sensor_name or 'влажность' in sensor_name:
                        value = round(random.uniform(35.0, 65.0), 2)
                    elif 'co2' in sensor_name:
                        value = round(random.uniform(400.0, 800.0), 2)
                    elif 'press' in sensor_name or 'давление' in sensor_name:
                        value = round(random.uniform(1010.0, 1020.0), 2)
                    else:
                        value = round(random.uniform(0.0, 100.0), 2)
                    
                    # Write to database
                    self.write_sensor_data(sensor_id, value)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n⚠️  Stopping emulation...")
                self.running = False
            except Exception as e:
                print(f"❌ Emulation error: {e}")
                time.sleep(5)
    
    def stop(self):
        """Stop emulation and close connection"""
        self.running = False
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Disconnected from database")

# ============================================================
# CLI INTERFACE
# ============================================================

if __name__ == '__main__':
    print("="*60)
    print("🔌 ProMonitor Modbus Emulator - Database Integration")
    print("="*60)
    
    writer = ModbusIntegrationWriter()
    
    if writer.connect():
        print("\n📊 Database integration active")
        print("   Writing to data_data table (Django Data model)")
        print("   Press Ctrl+C to stop\n")
        
        try:
            writer.start_emulation(interval=30)
        except KeyboardInterrupt:
            print("\n")
        finally:
            writer.stop()
    else:
        print("\n❌ Failed to connect to database")
        print("   Check environment variables and database connectivity")
