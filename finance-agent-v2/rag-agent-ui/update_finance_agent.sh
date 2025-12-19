#!/bin/bash
set -e

# Change this to your actual project root if different
PROJECT_ROOT="$(pwd)"

echo "Using project root: $PROJECT_ROOT"

echo "Backing up existing orchestrator, intents, and static/app.js..."
ts=$(date +%s)
cp -R "$PROJECT_ROOT/orchestrator" "$PROJECT_ROOT/orchestrator_backup_$ts"
cp -R "$PROJECT_ROOT/intents" "$PROJECT_ROOT/intents_backup_$ts"
cp "$PROJECT_ROOT/static/app.js" "$PROJECT_ROOT/static/app_backup_$ts.js"

echo "Applying updates from finance_agent_update_final.zip..."
unzip -o finance_agent_update_final.zip -d "$PROJECT_ROOT"

echo "Removing old __pycache__ for orchestrator and intents..."
find "$PROJECT_ROOT/orchestrator" -name '__pycache__' -type d -exec rm -rf {} +
find "$PROJECT_ROOT/intents" -name '__pycache__' -type d -exec rm -rf {} +

echo "Done. Restart your uvicorn server if it's running."
