#!/usr/bin/env python3
"""CCTV Motion Detection — only trigger on significant movement (person/intense)."""
import time
import urllib.request
import json
from io import BytesIO

SNAPSHOT_URL = "http://localhost:8011/hls/snapshot.jpg"
SNAPSHOT_PATH = "/tmp/motion_snapshot.jpg"
RECORD_START = "http://127.0.0.1:8090/api/record/start"
RECORD_STOP = "http://127.0.0.1:8090/api/record/stop"
RECORD_STATUS = "http://127.0.0.1:8090/api/record/status"

CHECK_INTERVAL = 3       # seconds between checks
MIN_RECORD = 15           # minimum recording duration (sec)
MAX_RECORD = 600          # max recording duration (sec)
COOLDOWN = 30             # sec after stop before new trigger
CHANGE_PCT = 2.0          # minimum % pixels changed (filters small noise/shadows)
PIXEL_THRESHOLD = 30     # per-pixel grayscale diff to count as changed
CONSECUTIVE_FRAMES = 3    # consecutive motion frames before trigger

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def get_snapshot():
    """Fetch snapshot from T470S HTTP, fallback to local."""
    try:
        with urllib.request.urlopen(SNAPSHOT_URL, timeout=5) as r:
            data = r.read()
        if HAS_PIL:
            return Image.open(BytesIO(data)).convert("L")
        return data
    except Exception:
        try:
            with open(SNAPSHOT_PATH, "rb") as f:
                data = f.read()
            if HAS_PIL:
                return Image.open(BytesIO(data)).convert("L")
            return data
        except:
            return None


def compute_change(prev, curr):
    """Compute percentage of pixels that changed significantly."""
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
    else:
        # Fallback
        if isinstance(prev, bytes) and isinstance(curr, bytes):
            diff = abs(len(prev) - len(curr))
            avg = max(len(prev) + len(curr), 2)
            return (diff / avg) * 500  # rough
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
    prev_snapshot = None
    motion_frames = 0
    recording_started_at = 0
    last_stop_at = 0

    engine = "PIL" if HAS_PIL else "fallback"
    print(f"Motion detection started (engine={engine}, threshold={CHANGE_PCT}%, path={SNAPSHOT_PATH})", flush=True)

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
                        print(f"Motion ({change_pct:.1f}%) - recording started", flush=True)
                motion_frames = 0

            if is_recording():
                elapsed = time.time() - recording_started_at
                # Hentikan rekaman jika tidak ada gerakan setelah MIN_RECORD
                if elapsed >= MIN_RECORD and change_pct <= CHANGE_PCT:
                    stop_recording()
                    last_stop_at = time.time()
                    print(f"No motion {elapsed:.0f}s - stopped", flush=True)
                # Atau berhenti otomatis di MAX_RECORD
                elif elapsed >= MAX_RECORD:
                    stop_recording()
                    last_stop_at = time.time()
                    print(f"Max duration {MAX_RECORD}s - stopped", flush=True)

            prev_snapshot = current

        except Exception as e:
            print(f"Error: {e}", flush=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()