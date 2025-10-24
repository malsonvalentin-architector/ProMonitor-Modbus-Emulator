# ProMonitor v2.0 Interactive Emulator
# Build timestamp: 2025-10-24 06:28:00 UTC
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Run Flask app (includes background data generator thread)
CMD ["python", "app.py"]
