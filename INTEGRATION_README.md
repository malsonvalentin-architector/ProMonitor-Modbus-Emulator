# ProMonitor - Modbus Emulator Database Integration

## 🎯 Цель

Интеграция эмулятора Modbus с основной dashboard системой через **единую базу данных PostgreSQL**.

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    Railway PostgreSQL Database                  │
├─────────────────────────────────────────────────────────────────┤
│  Emulator Tables:          │  Django Tables:                    │
│  - sensor_readings         │  - data_data                       │
│    (raw sensor data)       │    (processed readings)            │
│                            │  - data_atributes (sensors)        │
│                            │  - data_obj (buildings)            │
└─────────────────────────────────────────────────────────────────┘
         ▲                              ▲
         │                              │
    ┌────┴────────┐              ┌─────┴──────────┐
    │  Emulator   │              │  Main Dashboard│
    │  (Flask)    │              │  (Django)      │
    │             │◄─────────────┤                │
    │ ┌─────────┐ │   Bridge     │                │
    │ │ Data    │ │   Service    │                │
    │ │Generator│ │              │                │
    └─┴─────────┴─┘              └────────────────┘
      sensor_readings        reads data_data
```

## 📊 Компоненты

### 1. **Data Generator** (`data_generator.py`)
- Генерирует реалистичные данные сенсоров
- Пишет в таблицу `sensor_readings`
- Частота: каждые 30 секунд

### 2. **Bridge Service** (`bridge_service.py`) ⭐ НОВЫЙ
- Читает из `sensor_readings` (эмулятор)
- Пишет в `data_data` (Django)
- Синхронизация каждые 30 секунд
- Автоматический mapping между таблицами

### 3. **Flask Dashboard** (`app.py`)
- Web UI для эмулятора
- REST API для управления сценариями
- Работает с `sensor_readings`

### 4. **Main Dashboard** (Django - отдельный проект)
- Профессиональный dashboard
- Читает из `data_data`
- Отображает интегрированные данные

## 🔧 Настройка

### Environment Variables (Railway)

Обе системы используют **одни и те же** переменные окружения:

```bash
POSTGRES_DB=railway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***
PGHOST=postgres.railway.internal
PGPORT=5432
```

### Запуск

```bash
# Автоматический запуск всех компонентов
./start.sh

# Компоненты запускаются:
# 1. Data Generator (background)
# 2. Bridge Service (background) 
# 3. Flask Dashboard (foreground)
```

## 🔄 Как работает синхронизация

### Шаг 1: Emulator генерирует данные
```sql
-- Эмулятор пишет в sensor_readings
INSERT INTO sensor_readings (sensor_id, timestamp, temperature, humidity, co2, pressure, building_id)
VALUES (1, NOW(), 22.5, 45.0, 450, 1013, 1);
```

### Шаг 2: Bridge Service читает и синхронизирует
```python
# Bridge Service каждые 30 секунд:
1. Читает новые записи из sensor_readings
2. Определяет тип сенсора (temperature, humidity, co2, pressure)
3. Находит соответствующий Django sensor (data_atributes)
4. Пишет в data_data таблицу
```

### Шаг 3: Django Dashboard отображает данные
```python
# Django Dashboard читает из data_data:
latest_data = Data.objects.filter(name__modbus_carel=True).order_by('-date')[:100]
# Данные появляются в real-time на графиках
```

## 📈 Пример потока данных

```
Время: 12:00:00
├─ Data Generator → sensor_readings
│  sensor_id=1, temp=22.5°C, humidity=45%, building_id=1
│
├─ Bridge Service (через 30 сек)
│  Reads: sensor_id=1, temp=22.5
│  Maps: building_id=1 → Django sensor_id=15 (Temperature sensor)
│  Writes: data_data(name_id=15, value=22.5, date='12:00:00')
│
└─ Django Dashboard (через 1 сек)
   Query: SELECT * FROM data_data WHERE name_id=15 ORDER BY date DESC LIMIT 1
   Display: "Building 1 Temperature: 22.5°C"
```

## 🎮 Управление сценариями

### Через Emulator Web UI
```
https://emulator.promonitor.kz/
```

**Доступные сценарии:**
1. **Fire Emergency** - Температура +5°C
2. **Pressure Leak** - Давление -1.5 bar
3. **Power Failure** - Все сенсоры 0
4. **Normal Operations** - Нормальные значения

### API Endpoints

```bash
# Trigger scenario
POST /api/scenarios/trigger
{
  "type": "fire",
  "building_id": 1,
  "intensity": 0.8,
  "duration": 300
}

# Stop scenario
POST /api/scenarios/stop
{
  "type": "fire"
}

# Get scenario status
GET /api/scenarios/status
```

## 🔍 Мониторинг интеграции

### Проверка работы Bridge Service

```bash
# Check logs in Railway
# Look for:
✅ Connected to railway
✅ Found 10 Django sensors
📊 Found 25 new readings to sync
✅ Synced 100 data points to Django database
```

### Проверка данных в Dashboard

1. Откройте https://www.promonitor.kz/dashboard/main/
2. Проверьте графики - должны обновляться каждые 30 секунд
3. Измените значения в эмуляторе
4. Через 30 секунд изменения должны отобразиться в dashboard

## 🐛 Troubleshooting

### Проблема: Данные не синхронизируются

**Проверка 1:** Bridge Service запущен?
```bash
# В Railway logs:
grep "Data Bridge Service" /var/log/app.log
```

**Проверка 2:** Sensor mapping настроен?
```python
# Bridge Service должен вывести:
✅ Found 10 Django sensors
   Temperature sensors: 3
   Humidity sensors: 3
   CO2 sensors: 2
   Pressure sensors: 2
```

**Проверка 3:** База данных доступна?
```bash
# Test connection:
python3 -c "import psycopg2; psycopg2.connect(host='...').cursor().execute('SELECT 1')"
```

### Проблема: "No Modbus sensors found"

**Решение:** Создайте сенсоры в Django Admin:
```
1. Login: https://www.promonitor.kz/admin/
2. Go to: Data > Atributes
3. Create sensors with:
   - name: "Temperature Sensor 1"
   - modbus_carel: ✓ (checked)
   - sys: (select a system)
```

## 📝 Важные замечания

1. **Общая БД**: Обе системы используют одну PostgreSQL на Railway
2. **Разные таблицы**: Emulator и Django используют разные таблицы
3. **Bridge Service**: Критичен для интеграции - без него данные не синхронизируются
4. **Delay**: Небольшая задержка 30 секунд между эмулятором и dashboard
5. **Real-time**: Можно уменьшить interval в bridge_service.py для быстрой синхронизации

## 🚀 Деплой на Railway

```bash
# 1. Push changes to GitHub
git add bridge_service.py start.sh INTEGRATION_README.md
git commit -m "feat: Add database bridge service for Django integration"
git push origin main

# 2. Railway auto-deploys
# 3. Check logs for:
#    ✅ Data Generator started
#    ✅ Data Bridge started
#    ✅ Flask Dashboard started
```

## 📚 Дополнительные ресурсы

- **Emulator Repository**: https://github.com/malsonvalentin-architector/ProMonitor-Modbus-Emulator
- **Main Project Repository**: https://github.com/malsonvalentin-architector/rm-saas-platform
- **Railway Dashboard**: https://railway.com/project/[project-id]
- **Emulator URL**: https://emulator.promonitor.kz/
- **Main Dashboard**: https://www.promonitor.kz/dashboard/main/

---

**Версия:** 1.0  
**Дата:** 25 октября 2025  
**Автор:** AI Assistant for ProMonitor.kz
