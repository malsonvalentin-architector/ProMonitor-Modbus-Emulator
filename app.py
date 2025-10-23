#!/usr/bin/env python3
"""
Modbus Emulator Enhanced v2.0 для Railway
Постоянно работающий сервис с логированием и мониторингом
"""
import time
import socket
import struct
import threading
import random
import math
import logging
import os
from datetime import datetime
import json

# Настройка логирования для Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Для Railway logs
    ]
)
logger = logging.getLogger(__name__)

class ModbusEmulatorEnhanced:
    def __init__(self, host='0.0.0.0', port=5020):
        """
        Инициализация эмулятора
        host='0.0.0.0' - слушаем все интерфейсы (для Railway)
        """
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.clients = []
        
        # Хранилище данных регистров
        self.registers = {}
        
        # Конфигурация датчиков (соответствует БД)
        self.sensor_config = {
            # Температурные датчики (4 зоны)
            1000: {"type": "temperature", "zone": "Zone_1", "min": 18.0, "max": 25.0, "unit": "°C"},
            1002: {"type": "temperature", "zone": "Zone_2", "min": 18.0, "max": 25.0, "unit": "°C"},
            1004: {"type": "temperature", "zone": "Zone_3", "min": 18.0, "max": 25.0, "unit": "°C"},
            1006: {"type": "temperature", "zone": "Zone_4", "min": 18.0, "max": 25.0, "unit": "°C"},
            
            # Датчики влажности (3 датчика)
            2000: {"type": "humidity", "zone": "Zone_1", "min": 40.0, "max": 70.0, "unit": "%RH"},
            2002: {"type": "humidity", "zone": "Zone_2", "min": 40.0, "max": 70.0, "unit": "%RH"},
            2004: {"type": "humidity", "zone": "Zone_3", "min": 40.0, "max": 70.0, "unit": "%RH"},
            
            # Датчики давления (2 датчика)
            3000: {"type": "pressure", "zone": "Compressor_1", "min": 1.0, "max": 12.0, "unit": "bar"},
            3002: {"type": "pressure", "zone": "Compressor_2", "min": 1.0, "max": 12.0, "unit": "bar"},
            
            # Счётчики мощности (3 счётчика)
            4000: {"type": "power", "zone": "HVAC_Unit_1", "min": 2.0, "max": 15.0, "unit": "kW"},
            4002: {"type": "power", "zone": "HVAC_Unit_2", "min": 2.0, "max": 15.0, "unit": "kW"},
            4004: {"type": "power", "zone": "HVAC_Unit_3", "min": 2.0, "max": 15.0, "unit": "kW"},
        }
        
        # Инициализация значений
        self.init_registers()
        
        # Таймер для обновления данных
        self.update_thread = None
        
        logger.info(f"🤖 Modbus Emulator Enhanced v2.0 initialized")
        logger.info(f"📍 Host: {self.host}, Port: {self.port}")
        logger.info(f"🔧 Configured {len(self.sensor_config)} sensors")

    def init_registers(self):
        """Инициализация регистров случайными значениями"""
        for address, config in self.sensor_config.items():
            # Генерируем случайное значение в диапазоне
            value = random.uniform(config["min"], config["max"])
            
            # Float32 -> 2 регистра (High, Low)
            self.registers[address] = value
            
            logger.info(f"📊 {config['zone']} ({config['type']}): {value:.1f} {config['unit']}")

    def update_sensor_data(self):
        """Обновление данных датчиков (реалистичная симуляция)"""
        while self.running:
            try:
                updated_sensors = []
                
                for address, config in self.sensor_config.items():
                    current_value = self.registers.get(address, 0.0)
                    
                    # Реалистичные изменения в зависимости от типа датчика
                    if config["type"] == "temperature":
                        # Температура: медленные плавные изменения ±0.5°C
                        change = random.uniform(-0.5, 0.5)
                        new_value = max(config["min"], min(config["max"], current_value + change))
                        
                    elif config["type"] == "humidity":
                        # Влажность: более быстрые изменения ±2%
                        change = random.uniform(-2.0, 2.0)
                        new_value = max(config["min"], min(config["max"], current_value + change))
                        
                    elif config["type"] == "pressure":
                        # Давление: периодические колебания (симуляция работы компрессора)
                        cycle = math.sin(time.time() / 30) * 2  # 30-секундный цикл
                        noise = random.uniform(-0.3, 0.3)
                        base_pressure = (config["min"] + config["max"]) / 2
                        new_value = max(config["min"], min(config["max"], base_pressure + cycle + noise))
                        
                    elif config["type"] == "power":
                        # Мощность: колебания связанные с нагрузкой
                        base_load = (config["min"] + config["max"]) * 0.7  # 70% базовая нагрузка
                        variation = random.uniform(-1.5, 1.5)
                        new_value = max(config["min"], min(config["max"], base_load + variation))
                    
                    # Обновляем значение
                    self.registers[address] = round(new_value, 2)
                    updated_sensors.append(f"{config['zone']}: {new_value:.1f}{config['unit']}")
                
                # Логируем обновления (каждые 5 секунд)
                logger.info(f"🔄 Updated: {', '.join(updated_sensors)}")
                
                time.sleep(5)  # Обновление каждые 5 секунд
                
            except Exception as e:
                logger.error(f"❌ Error updating sensor data: {e}")
                time.sleep(5)

    def float_to_modbus_registers(self, value):
        """Преобразование Float32 в 2 Modbus регистра"""
        # Упаковываем float в 4 байта (big-endian)
        packed = struct.pack('>f', value)
        # Распаковываем как 2 регистра (16-bit каждый)
        reg1, reg2 = struct.unpack('>HH', packed)
        return reg1, reg2

    def handle_modbus_request(self, data):
        """Обработка Modbus TCP запроса"""
        try:
            if len(data) < 12:
                return None
                
            # Парсим Modbus TCP заголовок
            transaction_id = struct.unpack('>H', data[0:2])[0]
            protocol_id = struct.unpack('>H', data[2:4])[0]
            length = struct.unpack('>H', data[4:6])[0]
            unit_id = data[6]
            function_code = data[7]
            
            if function_code == 0x03:  # Read Holding Registers
                start_address = struct.unpack('>H', data[8:10])[0]
                quantity = struct.unpack('>H', data[10:12])[0]
                
                logger.info(f"📖 Modbus Request: Read {quantity} registers from {start_address}")
                
                # Формируем ответ
                response_data = []
                
                for i in range(quantity):
                    reg_address = start_address + i
                    
                    # Находим базовый адрес датчика (Float32 занимает 2 регистра)
                    base_address = (reg_address // 2) * 2
                    
                    if base_address in self.registers:
                        value = self.registers[base_address]
                        reg1, reg2 = self.float_to_modbus_registers(value)
                        
                        # Возвращаем соответствующий регистр
                        if reg_address % 2 == 0:
                            response_data.append(reg1)  # Высший регистр
                        else:
                            response_data.append(reg2)  # Низший регистр
                    else:
                        response_data.append(0)  # Пустой регистр
                
                # Формируем Modbus TCP ответ
                byte_count = len(response_data) * 2
                response = struct.pack('>HHHBBB', 
                    transaction_id, 0, 3 + byte_count, unit_id, function_code, byte_count)
                
                for reg_value in response_data:
                    response += struct.pack('>H', reg_value)
                
                return response
                
        except Exception as e:
            logger.error(f"❌ Error handling Modbus request: {e}")
            
        return None

    def handle_client(self, client_socket, address):
        """Обработка подключения клиента"""
        logger.info(f"🔌 Client connected: {address}")
        
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                    
                response = self.handle_modbus_request(data)
                if response:
                    client_socket.send(response)
                    
        except Exception as e:
            logger.error(f"❌ Client error: {e}")
        finally:
            client_socket.close()
            logger.info(f"🔌 Client disconnected: {address}")

    def start(self):
        """Запуск эмулятора"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(10)
            
            self.running = True
            
            # Запускаем поток обновления данных
            self.update_thread = threading.Thread(target=self.update_sensor_data)
            self.update_thread.daemon = True
            self.update_thread.start()
            
            logger.info(f"🚀 Modbus Emulator started on {self.host}:{self.port}")
            logger.info(f"🎯 Waiting for connections...")
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    
                    # Обрабатываем каждого клиента в отдельном потоке
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"❌ Error accepting connection: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Failed to start emulator: {e}")
            raise

    def stop(self):
        """Остановка эмулятора"""
        logger.info("🛑 Stopping Modbus Emulator...")
        self.running = False
        
        if self.socket:
            self.socket.close()
            
        logger.info("✅ Modbus Emulator stopped")

def main():
    """Главная функция"""
    # Получаем порт из переменной окружения (для Railway)
    port = int(os.environ.get('PORT', 5020))
    
    # Создаём и запускаем эмулятор
    emulator = ModbusEmulatorEnhanced('0.0.0.0', port)
    
    try:
        emulator.start()
    except KeyboardInterrupt:
        logger.info("🔄 Received interrupt signal")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        emulator.stop()

if __name__ == "__main__":
    main()