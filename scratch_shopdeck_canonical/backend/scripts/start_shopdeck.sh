#!/bin/bash

echo "Starting ShopDeck Business System - Local Development"

# Export local DB URL explicitly for the backend if missing
if [ -f ../.env ]; then
  export $(grep -v '^#' ../.env | xargs)
fi
if [ -z "$DATABASE_URL" ]; then
  # Local development fallback
  export DATABASE_URL="postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"
fi

# Start the API backend in the background
echo "Starting FastAPI backend on port ${PORT:-8200}..."
cd ../backend && uvicorn api.main:app --host ${HOST:-127.0.0.1} --port ${PORT:-8200} --reload &
API_PID=$!

# Start the React frontend
echo "Starting React frontend on port 3100..."
cd ../frontend && npm run dev &
FRONTEND_PID=$!

# Wait and catch sigint to kill both
trap "kill $API_PID $FRONTEND_PID; exit" SIGINT SIGTERM

echo "ShopDeck running locally! Press Ctrl+C to stop."
wait
