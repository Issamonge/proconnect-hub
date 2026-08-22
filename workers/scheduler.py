"""Scheduler container — runs workers on a fixed schedule using simple loops.
All schedules in UTC. No cron needed inside containers.
"""
import os
import time
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCHEDULE = [
    ("discover_buyers", 12 * 3600),   # every 12h
    ("discover_businesses", 24 * 3600),
    ("match", 6 * 3600),
    ("backup", 24 * 3600),
    ("cleanup", 24 * 3600),
]


def loop():
    last = {name: 0 for name, _ in SCHEDULE}
    while True:
        now = time.time()
        for name, interval in SCHEDULE:
            if now - last[name] >= interval:
                print(f"[scheduler] running {name}", flush=True)
                subprocess.run([sys.executable, "-m", "workers.runner", name])
                last[name] = now
        time.sleep(60)


if __name__ == "__main__":
    loop()
