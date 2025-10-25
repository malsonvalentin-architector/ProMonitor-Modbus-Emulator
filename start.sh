#!/bin/bash
# ProMonitor Startup Script
# Starts Flask app, Data Generator, and Bridge Service

echo "🚀 Starting ProMonitor v2.0 with Real-Time Emulator + Django Integration"
echo "============================================================"

# Start data generator in background
echo "📊 Starting Data Generator..."
python3 data_generator.py &
GENERATOR_PID=$!
echo "✅ Data Generator started (PID: $GENERATOR_PID)"

# Start bridge service in background
echo "🌉 Starting Data Bridge Service..."
python3 bridge_service.py &
BRIDGE_PID=$!
echo "✅ Data Bridge started (PID: $BRIDGE_PID)"

# Wait 3 seconds for services to initialize
sleep 3

# Start Flask app (foreground)
echo "🌐 Starting Flask Dashboard..."
python3 app.py

# If Flask exits, kill all background services
echo "\n⚠️  Shutting down background services..."
kill $GENERATOR_PID 2>/dev/null
kill $BRIDGE_PID 2>/dev/null
