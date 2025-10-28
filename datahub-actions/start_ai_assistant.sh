#!/bin/bash
# Start AI Assistant FastAPI server

echo "Starting AI Assistant API server..."

# Set defaults
export DATAHUB_GMS_URL=${DATAHUB_GMS_URL:-"http://datahub-gms:8080"}
export LLM_PROVIDER=${LLM_PROVIDER:-"gemini"}
export GEMINI_MODEL=${GEMINI_MODEL:-"gemini-2.0-flash-exp"}

# Check for API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY environment variable is required"
    exit 1
fi

# Start FastAPI server
python -m uvicorn datahub_actions.plugin.action.ai_assistant.api:create_app \
    --factory \
    --host 0.0.0.0 \
    --port 8082 \
    --log-level info
