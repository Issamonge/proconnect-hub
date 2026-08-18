#!/usr/bin/env python3
"""Keep the dashboard server and auto-replyer alive.

Runs in background, checks every 60 seconds that both processes are running.
If either dies, restarts it automatically.
"""
import subprocess
import time
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '..', 'data', 'keep_alive.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

def is_running(pattern):
    """Check if a process matching pattern is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False

def start_dashboard():
    """Start the dashboard HTTP server on port 12000."""
    logger.info("Starting dashboard server on port 12000...")
    subprocess.Popen(
        ["python3", "-m", "http.server", "12000", "--directory", PUBLIC_DIR],
        stdout=open("/tmp/dashboard_server.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

def start_auto_replyer():
    """Start the auto-replyer in watch mode."""
    script = os.path.join(BASE_DIR, "scripts", "auto_replyer.py")
    log_file = os.path.join(BASE_DIR, "data", "auto_replyer.log")
    logger.info("Starting auto-replyer in watch mode...")
    subprocess.Popen(
        ["python3", script, "--watch", "--interval", "300"],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

def main():
    logger.info("=== Keep-alive monitor started ===")
    logger.info(f"Base dir: {BASE_DIR}")

    while True:
        # Check dashboard server
        if not is_running("http.server 12000"):
            logger.warning("Dashboard server is DOWN — restarting...")
            start_dashboard()
            time.sleep(3)
            if is_running("http.server 12000"):
                logger.info("✅ Dashboard server restarted successfully")
            else:
                logger.error("❌ Dashboard server failed to restart")

        # Check auto-replyer
        if not is_running("auto_replyer.py"):
            logger.warning("Auto-replyer is DOWN — restarting...")
            start_auto_replyer()
            time.sleep(3)
            if is_running("auto_replyer.py"):
                logger.info("✅ Auto-replyer restarted successfully")
            else:
                logger.error("❌ Auto-replyer failed to restart")

        time.sleep(60)

if __name__ == "__main__":
    main()
