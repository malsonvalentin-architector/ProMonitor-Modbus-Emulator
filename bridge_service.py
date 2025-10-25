#!/usr/bin/env python3
"""
ProMonitor Data Bridge Service
Reads from emulator sensor_readings table and writes to Django data_data table
This allows emulator to continue using its own schema while feeding data to main dashboard
"""

import psycopg2
import os
import time
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
    return {
        'host': 'localhost',
        'port': '5432',
        'database': 'promonitor',
        'user': 'postgres',
        'password': 'postgres'
    }

class DataBridge:
    """
    Bridge between emulator sensor_readings and Django data_data
    
    Mapping strategy:
    - Emulator sensor_id 1-50 → Django sensor IDs (data_atributes)
    - Temperature readings → Temperature sensors
    - Humidity readings → Humidity sensors
    - CO2 readings → CO2 sensors
    - Pressure readings → Pressure sensors
    """
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.sensor_map = {}
        self.last_sync_time = None
        
    def connect(self):
        """Connect to database"""
        try:
            config = get_db_config()
            self.conn = psycopg2.connect(**config)
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            print(f"✅ Connected to {config['database']}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def setup_sensor_mapping(self):
        """
        Create mapping between emulator sensors and Django sensors
        
        Strategy:
        1. Get all Modbus sensors from data_atributes
        2. Map emulator sensor_id to Django attribute_id based on type
        3. Store mapping for quick lookups
        """
        try:
            # Get Django sensors
            self.cursor.execute("""
                SELECT a.id, a.name, a.uom, s.sys, o.obj
                FROM data_atributes a
                JOIN data_system s ON a.sys_id = s.id
                JOIN data_obj o ON s.obj_id = o.id
                WHERE a.modbus_carel = TRUE
                ORDER BY a.id
                LIMIT 100
            """)
            django_sensors = self.cursor.fetchall()
            
            if not django_sensors:
                print("⚠️  No Modbus sensors found in Django database")
                print("   Creating automatic sensor mapping...")
                return self._create_automatic_mapping()
            
            print(f"✅ Found {len(django_sensors)} Django sensors")
            
            # Create mapping: emulator_sensor_id → (django_id, type, building)
            # We'll map based on sensor type (temp, humidity, co2, pressure)
            temp_sensors = [s for s in django_sensors if 'temp' in s[1].lower() or 'температ' in s[1].lower()]
            humid_sensors = [s for s in django_sensors if 'humid' in s[1].lower() or 'влаж' in s[1].lower()]
            co2_sensors = [s for s in django_sensors if 'co2' in s[1].lower()]
            pressure_sensors = [s for s in django_sensors if 'press' in s[1].lower() or 'давл' in s[1].lower()]
            
            print(f"   Temperature sensors: {len(temp_sensors)}")
            print(f"   Humidity sensors: {len(humid_sensors)}")
            print(f"   CO2 sensors: {len(co2_sensors)}")
            print(f"   Pressure sensors: {len(pressure_sensors)}")
            
            # Store mapping
            self.sensor_map = {
                'temperature': [s[0] for s in temp_sensors],
                'humidity': [s[0] for s in humid_sensors],
                'co2': [s[0] for s in co2_sensors],
                'pressure': [s[0] for s in pressure_sensors]
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up sensor mapping: {e}")
            return False
    
    def _create_automatic_mapping(self):
        """Fallback: Create basic sensor mapping"""
        self.sensor_map = {
            'temperature': [],
            'humidity': [],
            'co2': [],
            'pressure': []
        }
        print("⚠️  Using empty sensor mapping (no data will be synced)")
        return True
    
    def sync_data(self, time_window_minutes=5):
        """
        Sync data from sensor_readings to data_data
        
        Args:
            time_window_minutes: Sync readings from last N minutes
        """
        try:
            # Get timestamp of last sync
            if self.last_sync_time is None:
                self.last_sync_time = datetime.now() - timedelta(minutes=time_window_minutes)
            
            # Read from emulator sensor_readings
            self.cursor.execute("""
                SELECT sensor_id, timestamp, temperature, humidity, co2, pressure, building_id
                FROM sensor_readings
                WHERE timestamp > %s
                ORDER BY timestamp ASC
            """, (self.last_sync_time,))
            
            readings = self.cursor.fetchall()
            
            if not readings:
                print(f"⏱️  No new readings since {self.last_sync_time}")
                return 0
            
            print(f"📊 Found {len(readings)} new readings to sync")
            
            # Group readings by type and write to Django data_data
            synced_count = 0
            
            for reading in readings:
                sensor_id, timestamp, temp, humidity, co2, pressure, building_id = reading
                
                # Sync temperature
                if temp is not None and self.sensor_map.get('temperature'):
                    django_sensor_id = self._get_django_sensor(building_id, 'temperature')
                    if django_sensor_id:
                        self._write_django_data(django_sensor_id, float(temp), timestamp)
                        synced_count += 1
                
                # Sync humidity
                if humidity is not None and self.sensor_map.get('humidity'):
                    django_sensor_id = self._get_django_sensor(building_id, 'humidity')
                    if django_sensor_id:
                        self._write_django_data(django_sensor_id, float(humidity), timestamp)
                        synced_count += 1
                
                # Sync CO2
                if co2 is not None and self.sensor_map.get('co2'):
                    django_sensor_id = self._get_django_sensor(building_id, 'co2')
                    if django_sensor_id:
                        self._write_django_data(django_sensor_id, float(co2), timestamp)
                        synced_count += 1
                
                # Sync pressure
                if pressure is not None and self.sensor_map.get('pressure'):
                    django_sensor_id = self._get_django_sensor(building_id, 'pressure')
                    if django_sensor_id:
                        self._write_django_data(django_sensor_id, float(pressure), timestamp)
                        synced_count += 1
            
            # Update last sync time
            self.last_sync_time = readings[-1][1]  # timestamp of last reading
            
            print(f"✅ Synced {synced_count} data points to Django database")
            return synced_count
            
        except Exception as e:
            print(f"❌ Sync error: {e}")
            return 0
    
    def _get_django_sensor(self, building_id, sensor_type):
        """Get Django sensor ID for given building and type"""
        sensors = self.sensor_map.get(sensor_type, [])
        if not sensors:
            return None
        
        # Simple round-robin mapping based on building_id
        idx = building_id % len(sensors)
        return sensors[idx]
    
    def _write_django_data(self, django_sensor_id, value, timestamp):
        """Write data point to Django data_data table"""
        try:
            self.cursor.execute("""
                INSERT INTO data_data (created_at, updated_at, value, date, name_id)
                VALUES (NOW(), NOW(), %s, %s, %s)
            """, (value, timestamp, django_sensor_id))
            return True
        except Exception as e:
            print(f"❌ Write error for sensor {django_sensor_id}: {e}")
            return False
    
    def run_continuous_sync(self, interval_seconds=30):
        """Run continuous sync loop"""
        print(f"\n🔄 Starting continuous sync (interval: {interval_seconds}s)")
        print("   Press Ctrl+C to stop\n")
        
        while True:
            try:
                synced = self.sync_data()
                if synced > 0:
                    print(f"⏱️  Waiting {interval_seconds}s for next sync...\n")
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("\n⚠️  Stopping sync service...")
                break
            except Exception as e:
                print(f"❌ Sync loop error: {e}")
                time.sleep(10)
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Disconnected")

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("="*70)
    print("🌉 ProMonitor Data Bridge Service")
    print("   Emulator sensor_readings → Django data_data")
    print("="*70)
    
    bridge = DataBridge()
    
    if bridge.connect():
        if bridge.setup_sensor_mapping():
            try:
                bridge.run_continuous_sync(interval_seconds=30)
            finally:
                bridge.close()
        else:
            print("\n❌ Failed to setup sensor mapping")
    else:
        print("\n❌ Failed to connect to database")
