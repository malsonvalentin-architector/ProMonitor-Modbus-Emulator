#!/usr/bin/env python3
"""
ProMonitor.kz Enhanced Modbus Emulator v3.0 with Web UI
========================================================

Features:
- Modbus TCP Server (port 8000)
- Web Dashboard (port 8080) 
- REST API for manual control
- Scenario simulation (fire, leak, power failure)
- Real-time monitoring

Author: AI Assistant
Date: 2025-10-23
"""

import socket
import struct
import threading
import time
import random
import math
import logging
import os
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ============================================================================
# Logging Configuration
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Sensor Data Manager
# ============================================================================
class SensorDataManager:
    """Управление данными всех датчиков"""
    
    def __init__(self):
        self.sensors = {
            # Температурные датчики (регистры 1000-1006)
            'zone1_temp': {'address': 1000, 'value': 22.5, 'min': 18.0, 'max': 25.0, 'unit': '°C', 'type': 'temp'},
            'zone2_temp': {'address': 1002, 'value': 21.8, 'min': 18.0, 'max': 25.0, 'unit': '°C', 'type': 'temp'},
            'zone3_temp': {'address': 1004, 'value': 23.2, 'min': 18.0, 'max': 25.0, 'unit': '°C', 'type': 'temp'},
            'zone4_temp': {'address': 1006, 'value': 20.1, 'min': 18.0, 'max': 25.0, 'unit': '°C', 'type': 'temp'},
            
            # Датчики влажности (регистры 2000-2004)
            'humidity1': {'address': 2000, 'value': 55.0, 'min': 40.0, 'max': 70.0, 'unit': '%', 'type': 'humidity'},
            'humidity2': {'address': 2002, 'value': 62.5, 'min': 40.0, 'max': 70.0, 'unit': '%', 'type': 'humidity'},
            'humidity3': {'address': 2004, 'value': 48.3, 'min': 40.0, 'max': 70.0, 'unit': '%', 'type': 'humidity'},
            
            # Датчики давления (регистры 3000-3002)
            'pressure1': {'address': 3000, 'value': 8.2, 'min': 1.0, 'max': 12.0, 'unit': 'bar', 'type': 'pressure'},
            'pressure2': {'address': 3002, 'value': 3.5, 'min': 1.0, 'max': 12.0, 'unit': 'bar', 'type': 'pressure'},
            
            # Счётчики мощности (регистры 4000-4004)
            'power1': {'address': 4000, 'value': 12.3, 'min': 2.0, 'max': 15.0, 'unit': 'kW', 'type': 'power'},
            'power2': {'address': 4002, 'value': 8.7, 'min': 2.0, 'max': 15.0, 'unit': 'kW', 'type': 'power'},
            'power3': {'address': 4004, 'value': 5.1, 'min': 2.0, 'max': 15.0, 'unit': 'kW', 'type': 'power'},
        }
        
        self.scenario = 'normal'  # normal, fire, leak, power_failure
        self.manual_mode = {}  # {sensor_id: manual_value}
        self.lock = threading.Lock()
    
    def update_values(self):
        """Автоматическое обновление значений"""
        with self.lock:
            for sensor_id, data in self.sensors.items():
                # Пропустить датчики в ручном режиме
                if sensor_id in self.manual_mode:
                    continue
                
                # Применить сценарии
                if self.scenario == 'fire':
                    if data['type'] == 'temp':
                        # Резкий рост температуры
                        data['value'] = min(data['value'] + random.uniform(2.0, 5.0), 60.0)
                    elif data['type'] == 'power':
                        # Рост энергопотребления
                        data['value'] = min(data['value'] + random.uniform(1.0, 3.0), 25.0)
                
                elif self.scenario == 'leak':
                    if data['type'] == 'pressure':
                        # Падение давления
                        data['value'] = max(data['value'] - random.uniform(0.5, 1.5), 0.1)
                    elif data['type'] == 'temp':
                        # Локальное охлаждение
                        data['value'] = max(data['value'] - random.uniform(0.5, 1.0), 5.0)
                
                elif self.scenario == 'power_failure':
                    if data['type'] == 'power':
                        # Падение мощности
                        data['value'] = max(data['value'] - random.uniform(2.0, 5.0), 0.0)
                
                else:  # normal
                    # Нормальные колебания
                    trend = math.sin(time.time() / 10.0) * 0.5
                    noise = random.uniform(-0.3, 0.3)
                    new_value = data['value'] + trend + noise
                    
                    # Ограничить диапазоном
                    data['value'] = max(data['min'], min(data['max'], new_value))
    
    def set_manual_value(self, sensor_id, value):
        """Установить значение вручную"""
        with self.lock:
            if sensor_id in self.sensors:
                self.manual_mode[sensor_id] = value
                self.sensors[sensor_id]['value'] = value
                logger.info(f"🎮 Manual: {sensor_id} = {value} {self.sensors[sensor_id]['unit']}")
                return True
        return False
    
    def clear_manual_value(self, sensor_id):
        """Снять ручной режим"""
        with self.lock:
            if sensor_id in self.manual_mode:
                del self.manual_mode[sensor_id]
                logger.info(f"🔄 Auto mode restored: {sensor_id}")
                return True
        return False
    
    def set_scenario(self, scenario):
        """Установить сценарий"""
        valid_scenarios = ['normal', 'fire', 'leak', 'power_failure']
        if scenario in valid_scenarios:
            with self.lock:
                self.scenario = scenario
                self.manual_mode = {}  # Сбросить ручной режим
            logger.warning(f"⚠️ Scenario changed: {scenario.upper()}")
            return True
        return False
    
    def get_all_data(self):
        """Получить все данные для JSON"""
        with self.lock:
            return {
                'timestamp': datetime.now().isoformat(),
                'scenario': self.scenario,
                'sensors': {
                    sid: {
                        'address': data['address'],
                        'value': round(data['value'], 2),
                        'unit': data['unit'],
                        'type': data['type'],
                        'manual': sid in self.manual_mode
                    }
                    for sid, data in self.sensors.items()
                }
            }
    
    def read_registers(self, start_address, count):
        """Чтение Modbus регистров"""
        registers = []
        with self.lock:
            for sensor_id, data in self.sensors.items():
                addr = data['address']
                if start_address <= addr < start_address + count * 2:
                    # Float32 = 2 регистра
                    value_bytes = struct.pack('>f', data['value'])
                    reg1, reg2 = struct.unpack('>HH', value_bytes)
                    registers.extend([reg1, reg2])
        
        return registers[:count]


# ============================================================================
# Modbus TCP Server
# ============================================================================
class ModbusTCPServer:
    """Modbus TCP Server для совместимости с ProMonitor"""
    
    def __init__(self, host='0.0.0.0', port=8000, data_manager=None):
        self.host = host
        self.port = port
        self.data_manager = data_manager
        self.running = False
        self.server_socket = None
    
    def start(self):
        """Запустить сервер"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        logger.info(f"✅ Modbus TCP Server Started")
        logger.info(f"📡 Listening on {self.host}:{self.port}")
        
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    logger.error(f"❌ Accept error: {e}")
    
    def handle_client(self, client_socket, address):
        """Обработка клиента"""
        logger.info(f"🔌 Client connected: {address[0]}:{address[1]}")
        
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                response = self.process_modbus_request(data)
                client_socket.send(response)
        
        except Exception as e:
            logger.error(f"❌ Client error: {e}")
        finally:
            client_socket.close()
            logger.info(f"🔌 Client disconnected: {address[0]}")
    
    def process_modbus_request(self, data):
        """Обработка Modbus запроса"""
        if len(data) < 12:
            return self.error_response(data, 0x01)
        
        # Парсинг Modbus TCP
        transaction_id = struct.unpack('>H', data[0:2])[0]
        protocol_id = struct.unpack('>H', data[2:4])[0]
        unit_id = data[6]
        function_code = data[7]
        
        if function_code == 0x03:  # Read Holding Registers
            start_address = struct.unpack('>H', data[8:10])[0]
            count = struct.unpack('>H', data[10:12])[0]
            
            # Читать регистры
            registers = self.data_manager.read_registers(start_address, count)
            
            # Формировать ответ
            byte_count = len(registers) * 2
            response = struct.pack('>HHHBB', transaction_id, protocol_id, byte_count + 3, unit_id, function_code)
            response += struct.pack('B', byte_count)
            for reg in registers:
                response += struct.pack('>H', reg)
            
            return response
        
        return self.error_response(data, 0x01)
    
    def error_response(self, request, exception_code):
        """Ошибка Modbus"""
        transaction_id = struct.unpack('>H', request[0:2])[0]
        return struct.pack('>HHHBBB', transaction_id, 0, 3, request[6], request[7] | 0x80, exception_code)
    
    def stop(self):
        """Остановить сервер"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()


# ============================================================================
# Web UI Server
# ============================================================================
class WebUIHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для веб-интерфейса"""
    
    data_manager = None  # Will be set externally
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self.serve_dashboard()
        elif path == '/api/sensors':
            self.serve_sensor_data()
        elif path == '/api/status':
            self.serve_status()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Обработка POST запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path.startswith('/api/sensor/'):
            sensor_id = path.split('/')[-1]
            self.handle_set_sensor(sensor_id, data)
        elif path == '/api/scenario':
            self.handle_set_scenario(data)
        elif path == '/api/clear_manual':
            self.handle_clear_manual(data)
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Главная страница Dashboard"""
        html = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProMonitor Emulator Control Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .status.normal { background: #10b981; color: white; }
        .status.fire { background: #ef4444; color: white; }
        .status.leak { background: #f59e0b; color: white; }
        .status.power_failure { background: #6b7280; color: white; }
        
        .controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin: 5px;
            transition: all 0.3s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .btn-normal { background: #10b981; color: white; }
        .btn-fire { background: #ef4444; color: white; }
        .btn-leak { background: #f59e0b; color: white; }
        .btn-power { background: #6b7280; color: white; }
        
        .sensors-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .sensor-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .sensor-card h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .sensor-value {
            font-size: 32px;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }
        .sensor-unit {
            font-size: 18px;
            color: #666;
        }
        .manual-badge {
            display: inline-block;
            background: #f59e0b;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            margin-left: 10px;
        }
        .sensor-controls {
            margin-top: 15px;
        }
        .sensor-controls input {
            width: 120px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-right: 10px;
        }
        .btn-small {
            padding: 6px 12px;
            font-size: 14px;
        }
        .timestamp {
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎮 ProMonitor Modbus Emulator Control Panel</h1>
            <p>Real-time sensor simulation and scenario testing</p>
            <div class="timestamp" id="timestamp"></div>
        </header>
        
        <div class="controls">
            <h2>⚠️ Scenario Control</h2>
            <p style="margin: 10px 0; color: #666;">Current: <span id="current-scenario" class="status normal">NORMAL</span></p>
            <button class="btn btn-normal" onclick="setScenario('normal')">✅ Normal Operations</button>
            <button class="btn btn-fire" onclick="setScenario('fire')">🔥 Fire Emergency</button>
            <button class="btn btn-leak" onclick="setScenario('leak')">💧 Pressure Leak</button>
            <button class="btn btn-power" onclick="setScenario('power_failure')">⚡ Power Failure</button>
        </div>
        
        <div id="sensors-container" class="sensors-grid"></div>
    </div>
    
    <script>
        const API_BASE = '';
        
        async function fetchSensors() {
            try {
                const response = await fetch('/api/sensors');
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                console.error('Error fetching sensors:', error);
            }
        }
        
        function updateUI(data) {
            // Update timestamp
            document.getElementById('timestamp').textContent = 
                'Last updated: ' + new Date(data.timestamp).toLocaleString();
            
            // Update scenario
            const scenarioElement = document.getElementById('current-scenario');
            scenarioElement.textContent = data.scenario.toUpperCase().replace('_', ' ');
            scenarioElement.className = 'status ' + data.scenario;
            
            // Update sensors
            const container = document.getElementById('sensors-container');
            container.innerHTML = '';
            
            for (const [id, sensor] of Object.entries(data.sensors)) {
                const card = createSensorCard(id, sensor);
                container.appendChild(card);
            }
        }
        
        function createSensorCard(id, sensor) {
            const card = document.createElement('div');
            card.className = 'sensor-card';
            
            const title = id.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            const manualBadge = sensor.manual ? '<span class="manual-badge">MANUAL</span>' : '';
            
            card.innerHTML = `
                <h3>${title} ${manualBadge}</h3>
                <div class="sensor-value">
                    ${sensor.value.toFixed(2)}
                    <span class="sensor-unit">${sensor.unit}</span>
                </div>
                <p style="color: #666; font-size: 14px;">
                    Address: ${sensor.address} | Type: ${sensor.type}
                </p>
                <div class="sensor-controls">
                    <input type="number" 
                           id="input-${id}" 
                           step="0.1" 
                           placeholder="New value"
                           value="${sensor.value.toFixed(1)}">
                    <button class="btn btn-normal btn-small" onclick="setSensor('${id}')">
                        Set Value
                    </button>
                    ${sensor.manual ? `
                    <button class="btn btn-small" style="background: #6b7280; color: white;" 
                            onclick="clearManual('${id}')">
                        Clear Manual
                    </button>
                    ` : ''}
                </div>
            `;
            
            return card;
        }
        
        async function setScenario(scenario) {
            try {
                await fetch('/api/scenario', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scenario })
                });
                fetchSensors();
            } catch (error) {
                console.error('Error setting scenario:', error);
            }
        }
        
        async function setSensor(sensorId) {
            const input = document.getElementById(`input-${sensorId}`);
            const value = parseFloat(input.value);
            
            if (isNaN(value)) {
                alert('Please enter a valid number');
                return;
            }
            
            try {
                await fetch(`/api/sensor/${sensorId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ value })
                });
                fetchSensors();
            } catch (error) {
                console.error('Error setting sensor:', error);
            }
        }
        
        async function clearManual(sensorId) {
            try {
                await fetch('/api/clear_manual', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sensor_id: sensorId })
                });
                fetchSensors();
            } catch (error) {
                console.error('Error clearing manual mode:', error);
            }
        }
        
        // Auto-refresh every 2 seconds
        setInterval(fetchSensors, 2000);
        
        // Initial fetch
        fetchSensors();
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_sensor_data(self):
        """API: Получить данные датчиков"""
        data = self.data_manager.get_all_data()
        self.send_json_response(data)
    
    def serve_status(self):
        """API: Статус системы"""
        status = {
            'status': 'online',
            'timestamp': datetime.now().isoformat(),
            'modbus_port': 8000,
            'web_port': 8080
        }
        self.send_json_response(status)
    
    def handle_set_sensor(self, sensor_id, data):
        """API: Установить значение датчика"""
        value = data.get('value')
        if value is not None:
            success = self.data_manager.set_manual_value(sensor_id, float(value))
            self.send_json_response({'success': success})
        else:
            self.send_error(400)
    
    def handle_set_scenario(self, data):
        """API: Установить сценарий"""
        scenario = data.get('scenario')
        if scenario:
            success = self.data_manager.set_scenario(scenario)
            self.send_json_response({'success': success})
        else:
            self.send_error(400)
    
    def handle_clear_manual(self, data):
        """API: Снять ручной режим"""
        sensor_id = data.get('sensor_id')
        if sensor_id:
            success = self.data_manager.clear_manual_value(sensor_id)
            self.send_json_response({'success': success})
        else:
            self.send_error(400)
    
    def send_json_response(self, data):
        """Отправить JSON ответ"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Подавить лишние логи"""
        pass


# ============================================================================
# Main Application
# ============================================================================
def main():
    """Главная функция"""
    logger.info("=" * 70)
    logger.info("🚀 ProMonitor Enhanced Modbus Emulator v3.0")
    logger.info("=" * 70)
    
    # Получить порты из окружения
    modbus_port = int(os.environ.get('PORT', 8000))
    web_port = int(os.environ.get('WEB_PORT', 8080))
    
    # Создать менеджер данных
    data_manager = SensorDataManager()
    
    # Установить data_manager для WebUIHandler
    WebUIHandler.data_manager = data_manager
    
    # Запустить Modbus сервер
    modbus_server = ModbusTCPServer('0.0.0.0', modbus_port, data_manager)
    modbus_thread = threading.Thread(target=modbus_server.start, daemon=True)
    modbus_thread.start()
    
    # Запустить Web UI сервер
    web_server = HTTPServer(('0.0.0.0', web_port), WebUIHandler)
    logger.info(f"✅ Web Dashboard Started")
    logger.info(f"🌐 Open: http://localhost:{web_port}")
    logger.info(f"📡 API: http://localhost:{web_port}/api/sensors")
    logger.info("=" * 70)
    
    web_thread = threading.Thread(target=web_server.serve_forever, daemon=True)
    web_thread.start()
    
    # Основной цикл обновления данных
    try:
        while True:
            data_manager.update_values()
            time.sleep(1.0)
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
        modbus_server.stop()
        web_server.shutdown()


if __name__ == "__main__":
    main()
