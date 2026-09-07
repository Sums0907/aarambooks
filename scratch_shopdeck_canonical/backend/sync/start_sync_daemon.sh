#!/bin/bash
echo "Starting ShopDeck MCP Sync Daemon (5-minute interval)..."
while true; do
  echo "[$(date)] Triggering sync..."
  python3 backend/sync/sync_shopdeck_mcp_data.py >> shopdeck_sync_daemon.log 2>&1
  sleep 300
done
