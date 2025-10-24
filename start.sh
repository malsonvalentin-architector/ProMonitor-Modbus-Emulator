#!/bin/bash
# ProMonitor Startup Script
# Starts both Flask app and Data Generator

echo "🚀 Starting ProMonitor v2.0 with Real-Time Emulator"
echo "============================================================"

# Start data generator in background
echo "📊 Starting Data Generator..."
python3 data_generator.py &
GENERATOR_PID=$!
echo "✅ Data Generator started (PID: $GENERATOR_PID)"

# Wait 3 seconds for generator to initialize
sleep 3

# Start Flask app (foreground)
echo "🌐 Starting Flask Dashboard..."
python3 app.py

# If Flask exits, kill generator
kill $GENERATOR_PID 2>/dev/null
