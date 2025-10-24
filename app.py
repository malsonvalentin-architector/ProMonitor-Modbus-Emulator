#!/usr/bin/env python3
"""
# Last Railway deploy trigger: Fri Oct 24 05:58:11 UTC 2025
ProMonitor Real-Time Dashboard v2.0
Flask + SocketIO + PostgreSQL backend
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import psycopg2
import os
import time
import random
from datetime import datetime, timedelta
import threading
import subprocess
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'promonitor-v2-interactive-emulator-2024'
app.config['DEBUG'] = False
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=False)

# Database connection configuration
def get_db_config():
    """Get database configuration from environment variables"""
    # Try POSTGRES_* variables first (Railway style)
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
        # Parse postgresql://user:pass@host:port/db
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
    # CRITICAL FIX: autocommit=True allows seeing data from other transactions!
    conn.autocommit = True
    return conn

# Test database connection on startup
try:
    conn = get_db_connection()
    conn.close()
    print("✅ Database connected")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('dashboard.html')

@app.route('/test')
def test_charts():
    """Test page for chart auto-update debugging"""
    return render_template('test_charts.html')

@app.route('/api/readings/latest')
def get_latest_readings():
    """Get latest readings for all sensors"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SIMPLE QUERY - Get ANY 50 readings (DEBUG)
        query = """
            SELECT 
                sensor_id,
                timestamp,
                temperature,
                humidity,
                co2,
                pressure,
                building_id,
                controller_id
            FROM sensor_readings
            ORDER BY timestamp DESC
            LIMIT 50
        """
        
        cursor.execute(query)
        readings = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not readings:
            return jsonify({'success': False, 'error': 'No data'})
        
        # Format results
        result = []
        for r in readings:
            result.append({
                'sensor_id': r[0],
                'timestamp': r[1].isoformat() if r[1] else None,
                'temperature': float(r[2]) if r[2] else None,
                'humidity': float(r[3]) if r[3] else None,
                'co2': float(r[4]) if r[4] else None,
                'pressure': float(r[5]) if r[5] else None,
                'building_id': r[6],
                'controller_id': r[7]
            })
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"❌ Error fetching latest readings: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/readings/history/<int:sensor_id>')
def get_sensor_history(sensor_id):
    """Get historical readings for specific sensor"""
    try:
        # Get hours parameter (default 24)
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                timestamp,
                temperature,
                humidity,
                co2,
                pressure
            FROM sensor_readings
            WHERE sensor_id = %s
                AND timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp ASC
        """
        
        cursor.execute(query, (sensor_id, hours))
        readings = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format results
        result = []
        for r in readings:
            result.append({
                'timestamp': r[0].isoformat() if r[0] else None,
                'temperature': float(r[1]) if r[1] else None,
                'humidity': float(r[2]) if r[2] else None,
                'co2': float(r[3]) if r[3] else None,
                'pressure': float(r[4]) if r[4] else None
            })
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"❌ Error fetching sensor history: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/alerts')
def get_alerts():
    """Get current alerts (readings outside normal ranges)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest readings that are outside normal ranges
        query = """
            SELECT DISTINCT ON (sensor_id)
                sensor_id,
                timestamp,
                temperature,
                humidity,
                co2,
                pressure,
                building_id,
                controller_id,
                CASE 
                    WHEN temperature < 18 OR temperature > 26 THEN 'Temperature out of range'
                    WHEN humidity < 30 OR humidity > 70 THEN 'Humidity out of range'
                    WHEN co2 > 1000 THEN 'CO2 level high'
                    WHEN pressure < 950 OR pressure > 1050 THEN 'Pressure abnormal'
                    ELSE 'Normal'
                END as alert_type
            FROM sensor_readings

                AND (
                    temperature < 18 OR temperature > 26
                    OR humidity < 30 OR humidity > 70
                    OR co2 > 1000
                    OR pressure < 950 OR pressure > 1050
                )
            ORDER BY sensor_id, timestamp DESC
        """
        
        cursor.execute(query)
        alerts = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format results
        result = []
        for a in alerts:
            result.append({
                'sensor_id': a[0],
                'timestamp': a[1].isoformat() if a[1] else None,
                'temperature': float(a[2]) if a[2] else None,
                'humidity': float(a[3]) if a[3] else None,
                'co2': float(a[4]) if a[4] else None,
                'pressure': float(a[5]) if a[5] else None,
                'building_id': a[6],
                'controller_id': a[7],
                'alert_type': a[8]
            })
        
        return jsonify({'success': True, 'alerts': result, 'count': len(result)})
        
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/debug-db')
def debug_db():
    """Diagnostic endpoint to check database state"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'sensor_readings'
        """)
        table_exists = cursor.fetchone()[0]
        
        # Check row count
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        total_rows = cursor.fetchone()[0]
        
        # Check latest timestamp
        cursor.execute("""
            SELECT MAX(timestamp), MIN(timestamp) 
            FROM sensor_readings
        """)
        times = cursor.fetchone()
        
        # Sample first 5 rows
        cursor.execute("""
            SELECT sensor_id, timestamp, temperature, humidity, co2, pressure
            FROM sensor_readings
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        samples = cursor.fetchall()
        
        # Check distinct sensors
        cursor.execute("SELECT COUNT(DISTINCT sensor_id) FROM sensor_readings")
        unique_sensors = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'table_exists': table_exists > 0,
            'total_rows': total_rows,
            'unique_sensors': unique_sensors,
            'latest_timestamp': str(times[0]) if times[0] else None,
            'oldest_timestamp': str(times[1]) if times[1] else None,
            'sample_data': [
                {
                    'sensor_id': r[0],
                    'timestamp': str(r[1]),
                    'temperature': float(r[2]),
                    'humidity': float(r[3]),
                    'co2': float(r[4]),
                    'pressure': float(r[5])
                }
                for r in samples
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/diagnostic')
def diagnostic():
    """Run diagnostic script"""
    try:
        result = subprocess.run(['python3', 'diagnostic.py'], capture_output=True, text=True, timeout=10)
        return jsonify({'success': result.returncode == 0, 'output': result.stdout, 'error': result.stderr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/db-direct-test')
def db_direct_test():
    """Ultra-simple direct DB test without any helpers"""
    import psycopg2
    import os
    try:
        # Direct connection
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST', 'postgres.railway.internal'),
            port=os.environ.get('PGPORT', '5432'),
            database=os.environ.get('POSTGRES_DB', 'railway'),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ.get('POSTGRES_PASSWORD', '')
        )
        cursor = conn.cursor()
        
        # Simple count
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        count = cursor.fetchone()[0]
        
        # Get first 3 rows
        cursor.execute("SELECT sensor_id, timestamp, temperature FROM sensor_readings LIMIT 3")
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'total_count': count,
            'sample_rows': [{'sensor_id': r[0], 'timestamp': str(r[1]), 'temperature': float(r[2])} for r in rows]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/run-setup', methods=['POST'])
def run_setup():
    """Run database setup script"""
    try:
        result = subprocess.run(
            ['python3', 'setup_database.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Setup script timed out after 120 seconds'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ============================================================
# WEBSOCKET HANDLERS
# ============================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('🔌 Client connected')
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('🔌 Client disconnected')

@socketio.on('request_test_update')
def handle_test_request():
    """🧪 TEST: Manual emission to verify WebSocket works"""
    print('🧪 Received test request - sending test emission')
    test_data = {
        'readings': [
            {'sensor_id': 'TEST', 'temperature': 99.9, 'humidity': 99.9, 'co2': 999, 'pressure': 9.99, 'building_id': 1}
        ]
    }
    emit('sensor_update', test_data, broadcast=True)
    print('✅ Test emission sent')

def broadcast_data():
    """Background thread to broadcast real-time data"""
    print("🔴 Real-time broadcast thread started")
    iteration = 0
    
    while True:
        try:
            iteration += 1
            print(f"🔄 Broadcast iteration #{iteration}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get latest readings (last 5 minutes)
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
                WHERE timestamp > NOW() - INTERVAL '5 minutes'
                ORDER BY sensor_id, timestamp DESC
            """
            
            cursor.execute(query)
            readings = cursor.fetchall()
            print(f"📊 Query returned {len(readings) if readings else 0} readings")
            
            cursor.close()
            conn.close()
            
            # Format and broadcast
            if readings and len(readings) > 0:
                data = []
                for r in readings:
                    data.append({
                        'sensor_id': r[0],
                        'timestamp': r[1].isoformat() if r[1] else None,
                        'temperature': float(r[2]) if r[2] else None,
                        'humidity': float(r[3]) if r[3] else None,
                        'co2': float(r[4]) if r[4] else None,
                        'pressure': float(r[5]) if r[5] else None,
                        'building_id': r[6],
                        'controller_id': r[7]
                    })
                
                print(f"📡 Broadcasting {len(data)} readings via WebSocket...")
                socketio.emit('sensor_update', {'readings': data})
                print(f"✅ Broadcast completed")
            else:
                print("⚠️  No readings to broadcast (query returned empty)")
            
        except Exception as e:
            print(f"❌ Broadcast error: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait 1 second before next broadcast
        time.sleep(1)

# Import data generator functions
try:
    from data_generator import generate_all_sensors, insert_readings, cleanup_old_data
    DATA_GENERATOR_AVAILABLE = True
    print("✅ Data generator module loaded")
except ImportError:
    DATA_GENERATOR_AVAILABLE = False
    print("⚠️  Data generator module not found")

# Background data generation thread
def continuous_data_generation():
    """Generate sensor data every 10 seconds"""
    if not DATA_GENERATOR_AVAILABLE:
        print("❌ Data generator not available")
        return
    
    print("🔴 Continuous data generation started")
    iteration = 0
    
    while True:
        try:
            iteration += 1
            
            # Generate readings
            readings = generate_all_sensors()
            
            # Insert into database
            success = insert_readings(readings)
            
            if success:
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Generated {len(readings)} readings (iteration #{iteration})")
            
            # Cleanup every 10 iterations
            if iteration % 10 == 0:
                cleanup_old_data()
            
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Data generation error: {e}")
            time.sleep(1)

# Start background threads
broadcast_thread = threading.Thread(target=broadcast_data, daemon=True)
broadcast_thread.start()
print("🚀 Background broadcast started")

data_gen_thread = threading.Thread(target=continuous_data_generation, daemon=True)
data_gen_thread.start()
print("🚀 Background data generator started")

# ============================================================
# MAIN
# ============================================================

@app.route('/api/version')
def version():
    """Show current deployment version"""
    import datetime
    return jsonify({
        'version': '2.0.2-interactive-emulator',
        'timestamp': datetime.datetime.now().isoformat(),
        'has_autocommit': 'autocommit=True' in open(__file__).read(),
        'endpoints': [str(rule) for rule in app.url_map.iter_rules() if not rule.rule.startswith('/static')]
    })

# ============================================================
# SCENARIO CONTROL ENDPOINTS
# ============================================================

# Global scenario state (shared with data_generator if integrated)
SCENARIO_STATE = {
    'temperature_spike': {'active': False, 'building_id': None, 'intensity': 10},
    'humidity_drop': {'active': False, 'building_id': None, 'intensity': 15},
    'co2_alarm': {'active': False, 'building_id': None, 'intensity': 400},
    'equipment_failure': {'active': False, 'building_id': None, 'failed_sensors': []}
}

@app.route('/api/scenarios/status')
def get_scenarios_status():
    """Get current status of all scenarios"""
    return jsonify({
        'success': True,
        'scenarios': SCENARIO_STATE
    })

@app.route('/api/scenarios/trigger', methods=['POST'])
def trigger_scenario():
    """Trigger a specific scenario for entire building"""
    try:
        from flask import request
        data = request.get_json()
        
        scenario_type = data.get('type')
        building_id = data.get('building_id', 1)
        intensity = data.get('intensity')
        duration = data.get('duration', 300)  # 5 minutes default
        
        if scenario_type not in SCENARIO_STATE:
            return jsonify({'success': False, 'error': 'Invalid scenario type'})
        
        # Set default intensity if not provided
        if intensity is None:
            if scenario_type == 'temperature_spike':
                intensity = 10
            elif scenario_type == 'humidity_drop':
                intensity = 15
            elif scenario_type == 'co2_alarm':
                intensity = 400
            else:
                intensity = 0
        
        # Get all sensors in this building
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT sensor_id 
            FROM sensor_readings 
            WHERE building_id = %s
            ORDER BY sensor_id
        """, (building_id,))
        
        affected_sensors = [row[0] for row in cursor.fetchall()]
        
        # Activate scenario
        SCENARIO_STATE[scenario_type] = {
            'active': True,
            'building_id': building_id,
            'intensity': intensity,
            'started_at': datetime.now().isoformat(),
            'duration': duration,
            'affected_sensors': affected_sensors
        }
        
        cursor.close()
        conn.close()
        
        # Broadcast update via WebSocket
        socketio.emit('scenario_triggered', {
            'type': scenario_type,
            'building_id': building_id,
            'intensity': intensity,
            'affected_sensors': affected_sensors,
            'message': f'Scenario {scenario_type} activated for Building {building_id} ({len(affected_sensors)} sensors)'
        })
        
        return jsonify({
            'success': True,
            'message': f'Scenario {scenario_type} triggered for Building {building_id}',
            'building_id': building_id,
            'intensity': intensity,
            'affected_sensors': affected_sensors,
            'sensor_count': len(affected_sensors),
            'scenario': SCENARIO_STATE[scenario_type]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scenarios/stop', methods=['POST'])
def stop_scenario():
    """Stop a specific scenario"""
    try:
        from flask import request
        data = request.get_json()
        
        scenario_type = data.get('type')
        
        if scenario_type == 'all':
            for key in SCENARIO_STATE:
                SCENARIO_STATE[key]['active'] = False
                SCENARIO_STATE[key]['building_id'] = None
            message = 'All scenarios stopped'
        elif scenario_type in SCENARIO_STATE:
            SCENARIO_STATE[scenario_type]['active'] = False
            SCENARIO_STATE[scenario_type]['building_id'] = None
            message = f'Scenario {scenario_type} stopped'
        else:
            return jsonify({'success': False, 'error': 'Invalid scenario type'})
        
        socketio.emit('scenario_stopped', {'type': scenario_type})
        
        return jsonify({
            'success': True,
            'message': message,
            'scenarios': SCENARIO_STATE
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/buildings/stats')
def get_buildings_stats():
    """Get statistics for each building"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query to get latest stats per building
        query = """
            SELECT 
                building_id,
                COUNT(DISTINCT sensor_id) as sensor_count,
                AVG(temperature) as avg_temp,
                AVG(humidity) as avg_humidity,
                AVG(co2) as avg_co2,
                AVG(pressure) as avg_pressure,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp
            FROM (
                SELECT DISTINCT ON (sensor_id)
                    sensor_id,
                    building_id,
                    temperature,
                    humidity,
                    co2,
                    pressure
                FROM sensor_readings
                WHERE timestamp > NOW() - INTERVAL '5 minutes'
                ORDER BY sensor_id, timestamp DESC
            ) latest
            GROUP BY building_id
            ORDER BY building_id
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        buildings = []
        for row in results:
            building_id = row[0]
            avg_temp = float(row[2]) if row[2] else 0
            
            # Determine status based on temperature
            if avg_temp < 18 or avg_temp > 27:
                status = 'critical'
            elif avg_temp < 20 or avg_temp > 24:
                status = 'warning'
            else:
                status = 'normal'
            
            # Check active scenarios for this building
            active_scenarios = []
            for scenario_type, scenario_data in SCENARIO_STATE.items():
                if scenario_data.get('active') and scenario_data.get('building_id') == building_id:
                    active_scenarios.append(scenario_type)
            
            buildings.append({
                'building_id': building_id,
                'sensor_count': row[1],
                'avg_temperature': round(avg_temp, 1),
                'avg_humidity': round(float(row[3]), 1) if row[3] else 0,
                'avg_co2': round(float(row[4]), 1) if row[4] else 0,
                'avg_pressure': round(float(row[5]), 1) if row[5] else 0,
                'min_temp': round(float(row[6]), 1) if row[6] else 0,
                'max_temp': round(float(row[7]), 1) if row[7] else 0,
                'status': status,
                'active_scenarios': active_scenarios
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'buildings': buildings,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    
    print("\n" + "="*60)
    print("🚀 ProMonitor Real-Time Dashboard v2.0")
    print("="*60)
    print(f"🌐 Dashboard URL: http://localhost:{port}")
    print(f"📡 WebSocket: ws://localhost:{port}/socket.io/")
    print(f"📊 API Docs: http://localhost:{port}/api/readings/latest")
    print("="*60 + "\n")
    
    # Run with eventlet for WebSocket support
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
