FROM python:3.11-slim

WORKDIR /app

# Копируем файлы
COPY app_with_webui.py app.py
COPY requirements.txt .

# Устанавливаем зависимости (минимальные)
RUN pip install --no-cache-dir -r requirements.txt

# Открываем порты
# PORT - для Modbus TCP (Railway динамический)
# 8080 - для Web Dashboard
EXPOSE $PORT
EXPOSE 8080

# Запускаем эмулятор с веб-интерфейсом
CMD ["python", "app.py"]
