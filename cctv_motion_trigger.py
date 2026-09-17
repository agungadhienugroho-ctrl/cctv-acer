#!/usr/bin/env python3
"""Motion detection — compare JPEG snapshot, trigger recording on change."""
import hashlib
import os
import subprocess
import sys
import time
import urllib.request

SNAPSHOT_URL = "http://127.0.0.1:8011/cctv.jpg"
RECORD_START = "http://127.0.0.1:8090/api/record/start"
RECORD_STOP = "http://127.0.0.1:8090/api/record/stop"
RECORD_STATUS = "http://127.0.0.1:8090/api/record/status"

THRESHOLD = 5000       # pixel diff threshold
CHECK_INTERVAL = 3     # seconds between checks
MIN_RECORD = 10        # minimum recording duration (sec)
MAX_RECORD = 600       # max recording duration (sec)
COOLDOWN = 30          # sec after recording stops before new trigger


def get_snapshot_hash():
    """Fetch JPEG snapshot and return its size (proxy for content change)."""
    try:
        data = urllib.request.urlopen(SNAPSHOT_URL, timeout=5).read()
        return len(data), hashlib.md5(data).hexdigest()
    except Exception:
        return None, None


def is_recording():
    try:
        resp = urllib.request.urlopen(RECORD_STATUS, timeout=3).read()
        import json
        return json.loads(resp).get("recording", False)
    except Exception:
        return False


def start_recording():
    try:
        urllib.request.urlopen(RECORD_START, timeout=5)
        return True
    except Exception:
        return False


def stop_recording():
    try:
        urllib.request.urlopen(RECORD_STOP, timeout=5)
        return True
    except Exception:
        return False


def main():
    prev_hash = None
    recording_started_at = 0
    last_stop_at = 0

    print("Motion detection started", flush=True)

    while True:
        try:
            size, current_hash = get_snapshot_hash()

            if current_hash is None:
                time.sleep(CHECK_INTERVAL)
                continue

            # Motion detected: hash changed significantly
            motion = (prev_hash is not None and current_hash != prev_hash)

            if motion:
                now = time.time()

                if not is_recording() and (now - last_stop_at) > COOLDOWN:
                    if start_recording():
                        recording_started_at = now
                        print(f"� Motion detected — recording started", flush=True)

            elif is_recording():
                # No motion — check if min duration met
                elapsed = time.time() - recording_started_at
                if elapsed >= MIN_RECORD:
                    stop_recording()
                    last_stop_at = time.time()
                    print(f"� Stopped after {elapsed:.0f}s (no motion)", flush=True)
                elif elapsed >= MAX_RECORD:
                    stop_recording()
                    last_stop_at = time.time()
                    print(f"⏹ Max duration reached ({MAX_RECORD}s)", flush=True)

            prev_hash = current_hash

        except Exception as e:
            print(f"Error: {e}", flush=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
