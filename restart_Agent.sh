#!/bin/bash

# Script to restart finance-agent safely on port 8001

PORT=8001

echo "🔍 Checking if anything is running on port $PORT..."
PID=$(lsof -ti tcp:$PORT)

if [ -n "$PID" ]; then
  echo "⚠️ Found process $PID on port $PORT. Killing..."
  kill -9 $PID
else
  echo "✅ No process running on port $PORT."
fi

echo "🚀 Starting finance-agent with uvicorn on port $PORT..."
source venv/bin/activate
uvicorn app:app --reload --port $PORT
