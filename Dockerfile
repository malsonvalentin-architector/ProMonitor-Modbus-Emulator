FROM python:3.11-slim

WORKDIR /app

# Копируем файлы
COPY app.py .
COPY requirements.txt .

# Устанавливаем зависимости (минимальные)
RUN pip install --no-cache-dir -r requirements.txt

# Открываем порт для Railway
EXPOSE $PORT

# Запускаем эмулятор
CMD ["python", "app.py"]