#!/bin/bash
# Start all servers - designed to be called on container startup
cd /workspace/project

# Kill any existing processes
pkill -f "http.server 12000" 2>/dev/null
pkill -f "auto_replyer.py" 2>/dev/null
pkill -f "keep_alive.py" 2>/dev/null
sleep 1

# Start dashboard server
nohup python3 -m http.server 12000 --directory public > /tmp/dashboard.log 2>&1 &
echo "Dashboard: PID $! on port 12000"

# Start auto-replyer
nohup python3 scripts/auto_replyer.py --watch --interval 300 > data/auto_replyer.log 2>&1 &
echo "Auto-replyer: PID $!"

# Start keep-alive
nohup python3 scripts/keep_alive.py > data/keep_alive.log 2>&1 &
echo "Keep-alive: PID $!"

echo "All services started!"
