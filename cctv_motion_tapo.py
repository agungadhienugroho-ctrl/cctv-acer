#!/usr/bin/env python3
"""CCTV Tapo C200C Motion Detection v2 - with logging & lower threshold."""
import json
import logging
import sys
import time
import urllib.request
from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

SNAPSHOT_URL = "http://localhost:8011/hls-tapo/snapshot.jpg"
SNAPSHOT_PATH = "/tmp/motion_snapshot_tapo.jpg"
RECORD_START = "http://127.0.0.1:8091/api/record/start"
RECORD_STOP = "http://127.0.0.1:8091/api/record/stop"
RECORD_STATUS = "http://127.0.0.1:8091/api/record/status"

CHECK_INTERVAL = 2          # seconds between checks
CHANGE_PCT = 2.0            # min % pixels changed (above noise ~0.6%)
PIXEL_THRESHOLD = 50        # per-pixel diff (noise at 25 was 0.6%)
CONSECUTIVE_FRAMES = 3      # consecutive motion frames before trigger
MIN_RECORD = 10             # minimum recording duration (sec)
MAX_RECORD = 600            # max recording duration (sec)
COOLDOWN = 15               # sec after stop before new trigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler("/var/log/cctv-motion-tapo.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("motion-tapo")


def get_snapshot():
    try:
        with urllib.request.urlopen(SNAPSHOT_URL, timeout=5) as r:
            data = r.read()
        if HAS_PIL:
            return Image.open(BytesIO(data)).convert("L")
        return data
    except Exception as e:
        log.warning(f"get_snapshot HTTP error: {e}")
        try:
            with open(SNAPSHOT_PATH, "rb") as f:
                data = f.read()
            if HAS_PIL:
                return Image.open(BytesIO(data)).convert("L")
            return data
        except Exception:
            return None


def compute_change(prev, curr):
    if prev is None or curr is None:
        return 0.0
    if HAS_PIL and isinstance(prev, Image.Image) and isinstance(curr, Image.Image):
        pixels1 = list(prev.getdata())
        pixels2 = list(curr.getdata())
        total = len(pixels1)
        if total == 0:
            return 0.0
        changed = sum(1 for p1, p2 in zip(pixels1, pixels2) if abs(int(p1) - int(p2)) > PIXEL_THRESHOLD)
        return (changed / total) * 100
    return 0.0


def is_recording():
    try:
        resp = urllib.request.urlopen(RECORD_STATUS, timeout=3).read()
        return json.loads(resp).get("recording", False)
    except Exception:
        return False


def start_recording():
    try:
        urllib.request.urlopen(RECORD_START, timeout=5)
        log.info("start_recording called")
        return True
    except Exception as e:
        log.error(f"start_recording failed: {e}")
        return False


def stop_recording():
    try:
        urllib.request.urlopen(RECORD_STOP, timeout=5)
        log.info("stop_recording called")
        return True
    except Exception:
        return False


def main():
    prev_snapshot = None
    motion_frames = 0
    recording_started_at = 0
    last_stop_at = 0
    engine = "PIL" if HAS_PIL else "fallback"
    log.info(f"Tapo Motion v2 started (engine={engine}, threshold={CHANGE_PCT}%)")

    while True:
        try:
            current = get_snapshot()
            if current is None:
                time.sleep(CHECK_INTERVAL)
                continue

            change_pct = compute_change(prev_snapshot, current)

            if change_pct > CHANGE_PCT:
                motion_frames += 1
            else:
                motion_frames = 0

            if motion_frames >= CONSECUTIVE_FRAMES:
                now = time.time()
                if not is_recording() and (now - last_stop_at) > COOLDOWN:
                    if start_recording():
                        recording_started_at = now
                        log.info(f"Motion ({change_pct:.2f}%) - recording STARTED")
                motion_frames = 0

            if is_recording():
                elapsed = time.time() - recording_started_at
                if elapsed >= MIN_RECORD and change_pct <= CHANGE_PCT:
                    stop_recording()
                    last_stop_at = time.time()
                    log.info(f"No motion {elapsed:.0f}s - recording STOPPED")
                elif elapsed >= MAX_RECORD:
                    stop_recording()
                    last_stop_at = time.time()
                    log.info(f"Max duration {MAX_RECORD}s - recording STOPPED")

            prev_snapshot = current

        except Exception as e:
            log.error(f"Loop error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
