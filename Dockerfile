FROM python:3.11-slim

WORKDIR /app

# Copy application files
COPY requirements.txt .
COPY app.py .
COPY setup_database.py .
COPY templates/ ./templates/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Railway provides PORT env variable)
EXPOSE 8080

# Run application
CMD ["python3", "app.py"]
