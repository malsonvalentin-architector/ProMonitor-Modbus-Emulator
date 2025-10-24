# ProMonitor v2.0 Dockerfile
# Build timestamp: 2025-10-24 05:59:30 UTC
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
