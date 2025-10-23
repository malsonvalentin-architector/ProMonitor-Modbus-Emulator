# 🎮 ProMonitor Modbus Emulator v3.0 with Web UI

## ✨ Новые Возможности

### 📊 Веб-Dashboard
- **URL:** `http://your-emulator-url:8080`
- **Реалтайм мониторинг** всех 12 датчиков
- **Автообновление** каждые 2 секунды
- **Красивый интерфейс** с градиентами и анимациями

### 🎮 Ручное Управление
Каждый датчик можно:
- ✅ Установить конкретное значение
- ✅ Перевести в ручной режим (MANUAL badge)
- ✅ Вернуть в автоматический режим

### ⚠️ Сценарии Возмущений

#### 1. **🔥 Fire Emergency**
- Температура резко растёт (+2-5°C каждую секунду)
- Энергопотребление увеличивается
- **Использование:** Проверка пожарной сигнализации

#### 2. **💧 Pressure Leak**
- Давление падает (-0.5-1.5 bar/сек)
- Температура локально снижается
- **Использование:** Тестирование утечек хладагента

#### 3. **⚡ Power Failure**
- Мощность падает до нуля
- **Использование:** Проверка резервного питания

#### 4. **✅ Normal Operations**
- Возврат к штатным значениям
- Автоматические колебания в пределах нормы

---

## 🚀 Развёртывание на Railway

### Шаг 1: Обновить Файлы в GitHub

```bash
# Заменить app.py на версию с Web UI
curl -O https://your-storage/app_with_webui.py
mv app_with_webui.py app.py

# Обновить Dockerfile
curl -O https://your-storage/Dockerfile_webui
mv Dockerfile_webui Dockerfile

# Закоммитить
git add app.py Dockerfile
git commit -m "Add Web UI to Modbus Emulator"
git push origin main
```

### Шаг 2: Настроить Railway Networking

#### В Railway Dashboard:
1. Открыть: https://railway.app/project/YOUR_PROJECT_ID
2. Кликнуть на **ProMonitor-Modbus-Emulator**
3. Перейти в **Settings** → **Networking**

#### Public Networking:
- **Generate Domain** для порта 8080 (Web UI)
- Railway выдаст URL типа: `promonitor-emulator-webui.up.railway.app`

#### Environment Variables:
```
PORT=8000          # Modbus TCP (уже должен быть)
WEB_PORT=8080      # Web Dashboard (добавить)
```

### Шаг 3: Дождаться Деплоя

Railway автоматически:
1. Подхватит изменения из GitHub
2. Пересоберёт Docker образ
3. Запустит оба сервера (Modbus + Web)
4. Откроет порт 8080 для публичного доступа

**Время:** ~3-5 минут

---

## 🌐 Доступ к Dashboard

После деплоя откройте в браузере:

```
https://promonitor-emulator-webui.up.railway.app
```

**Что увидите:**
- ✅ 12 карточек датчиков с реалтайм значениями
- ✅ 4 кнопки сценариев (Normal, Fire, Leak, Power)
- ✅ Поля ввода для ручного управления каждым датчиком
- ✅ Индикаторы ручного режима (MANUAL badge)

---

## 📡 REST API

### Получить Все Данные
```bash
GET /api/sensors

Response:
{
  "timestamp": "2025-10-23T15:30:45",
  "scenario": "normal",
  "sensors": {
    "zone1_temp": {
      "address": 1000,
      "value": 22.34,
      "unit": "°C",
      "type": "temp",
      "manual": false
    },
    ...
  }
}
```

### Установить Значение Датчика
```bash
POST /api/sensor/zone1_temp
Content-Type: application/json

{
  "value": 45.5
}

Response:
{
  "success": true
}
```

### Установить Сценарий
```bash
POST /api/scenario
Content-Type: application/json

{
  "scenario": "fire"
}

Response:
{
  "success": true
}
```

Valid scenarios:
- `normal` - Штатный режим
- `fire` - Пожар
- `leak` - Утечка
- `power_failure` - Отключение питания

### Снять Ручной Режим
```bash
POST /api/clear_manual
Content-Type: application/json

{
  "sensor_id": "zone1_temp"
}

Response:
{
  "success": true
}
```

---

## 🎯 Примеры Использования

### Тестирование Пожарной Сигнализации

1. Откройте Dashboard
2. Кликните **🔥 Fire Emergency**
3. Наблюдайте как температура растёт
4. Проверьте в ProMonitor.kz:
   - Dashboard должен показать красные алерты
   - Логи должны содержать "Temperature Critical"
   - Должны прийти уведомления (если настроены)

### Ручная Установка Критичного Значения

1. В карточке "Zone 1 Temperature"
2. Введите значение: `60.0`
3. Кликните **Set Value**
4. Датчик переключится в ручной режим (MANUAL badge)
5. Значение останется фиксированным на 60°C
6. Проверьте реакцию ProMonitor системы

### Симуляция Утечки Хладагента

1. Кликните **💧 Pressure Leak**
2. Давление начнёт падать
3. Температура локально снизится
4. Проверьте:
   - Алерты о низком давлении
   - Корреляцию температуры и давления
   - Работу emergency shutdown

### Возврат к Норме

1. Кликните **✅ Normal Operations**
2. Все ручные режимы сбросятся
3. Система вернётся к штатным колебаниям

---

## 🔧 Технические Детали

### Архитектура:
```
┌─────────────────────────────────────┐
│  Web Browser (Dashboard)            │
│  http://your-url:8080                │
└──────────────┬──────────────────────┘
               │ HTTP/REST API
┌──────────────┴──────────────────────┐
│  Python HTTP Server (port 8080)     │
│  - Serve HTML/CSS/JS                │
│  - REST API endpoints               │
│  - Real-time sensor data            │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│  Sensor Data Manager                │
│  - 12 virtual sensors               │
│  - Scenario engine                  │
│  - Manual mode control              │
│  - Thread-safe access               │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│  Modbus TCP Server (port 8000)      │
│  - Function Code 0x03               │
│  - Float32 registers                │
│  - ProMonitor compatible            │
└─────────────────────────────────────┘
```

### Порты:
- **8000** - Modbus TCP (для ProMonitor Celery)
- **8080** - Web Dashboard (для ручного управления)

### Threading:
- **Main Thread** - Обновление значений датчиков (1 Hz)
- **Modbus Thread** - Обработка Modbus клиентов
- **Web Thread** - HTTP сервер для Dashboard

### Безопасность:
- ⚠️ Нет аутентификации (для внутреннего использования)
- ✅ Thread-safe доступ к данным (locks)
- ✅ Валидация входных данных API

---

## 📊 Мониторинг

### Логи Railway

Искать строки:
```bash
✅ Modbus TCP Server Started
📡 Listening on 0.0.0.0:8000

✅ Web Dashboard Started
🌐 Open: http://localhost:8080
📡 API: http://localhost:8080/api/sensors

🔌 Client connected: 10.0.1.5:54321
🎮 Manual: zone1_temp = 45.5 °C
⚠️ Scenario changed: FIRE
🔄 Auto mode restored: zone1_temp
```

### Проверка Работоспособности

#### Test Modbus (внутри Railway):
```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('promonitor-modbus-emulator.railway.internal', port=5020)
result = client.read_holding_registers(1000, 2)  # Zone 1 Temperature
print(f"Temperature: {result.registers}")
```

#### Test Web UI:
```bash
curl http://your-emulator-url:8080/api/sensors
```

---

## 🎨 Кастомизация

### Добавить Новый Датчик

В `SensorDataManager.__init__()`:
```python
self.sensors['new_sensor'] = {
    'address': 5000,
    'value': 100.0,
    'min': 0.0,
    'max': 200.0,
    'unit': 'rpm',
    'type': 'speed'
}
```

### Добавить Новый Сценарий

В `SensorDataManager.update_values()`:
```python
elif self.scenario == 'my_scenario':
    # Ваша логика
    data['value'] = custom_calculation()
```

В HTML добавить кнопку:
```html
<button class="btn" onclick="setScenario('my_scenario')">
    🎯 My Scenario
</button>
```

---

## 🐛 Troubleshooting

### Dashboard не открывается

**Проблема:** 404 Not Found

**Решение:**
1. Проверить что порт 8080 открыт в Railway
2. Проверить что WEB_PORT=8080 в environment variables
3. Проверить логи: должно быть "Web Dashboard Started"

### Modbus не отвечает

**Проблема:** Connection refused

**Решение:**
1. Проверить что PORT установлен в Railway
2. Проверить логи: должно быть "Modbus TCP Server Started"
3. Использовать Railway private networking (не public URL)

### Данные не обновляются

**Проблема:** Dashboard статичный

**Решение:**
1. Открыть DevTools (F12) → Console
2. Проверить ошибки JavaScript
3. Проверить что `/api/sensors` возвращает данные

---

## 📞 Поддержка

Если нужна помощь:
1. Проверьте Railway логи
2. Проверьте Browser DevTools Console
3. Покажите текст ошибки

---

**Версия:** 3.0  
**Автор:** AI Assistant  
**Дата:** 2025-10-23  
**Лицензия:** MIT
