# ProMonitor v2.0 Interactive Emulator
# Build timestamp: 2025-10-24 06:20:00 UTC
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 8080

# Run startup script (Flask + Data Generator)
CMD ["./start.sh"]
