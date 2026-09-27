#!/usr/bin/env python3
"""CCTV Motion Detection — rekam hanya saat gerakan. Pakai OpenCV."""
import subprocess, time, os, sys, logging, tempfile, json, urllib.request
from datetime import datetime

HLS_URL = "http://127.0.0.1:801/hls/index.m3u8"
RECORD_DIR = "/mnt/wd2tb/CCTV/Rekaman"
API_URL = "http://127.0.0.1:8091/api"
CHECK_INTERVAL = 3
RECORD_AFTER = 1
NO_MOTION_TIMEOUT = 30
MAX_RECORD_SECONDS = 55
PIXEL_THRESHOLD = 30       # ambang batas per pixel (lebih sensitif)
MIN_PIXEL_CHANGED = 150    # lebih sensitif, minimal pixel berubah
LOG = "/tmp/cctv-motion.log"

# --- SAFETY GUARD: pastikan RECORD_DIR benar-benar di HDD, bukan fallback ke root FS ---
if not os.path.ismount("/mnt/wd2tb"):
    print("FATAL: /mnt/wd2tb tidak ter-mount! Rekaman dibatalkan "
          "agar tidak membanjiri disk system.", flush=True)
    sys.exit(1)

os.makedirs(RECORD_DIR, exist_ok=True)


logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)])

import cv2
import numpy as np


def api_call(endpoint):
    try:
        r = urllib.request.urlopen(f"{API_URL}/{endpoint}", timeout=5)
        return json.loads(r.read())
    except Exception as e:
        logging.error(f"API error: {e}")
        return None


def grab_frame_cv():
    """Ambil frame dari HLS, return grayscale OpenCV image."""
    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-i", HLS_URL,
            "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"
        ], capture_output=True, timeout=5)
        if r.returncode == 0 and len(r.stdout) > 0:
            # 640x480 grayscale
            frame = np.frombuffer(r.stdout, dtype=np.uint8).reshape(480, 640)
            return frame
    except Exception as e:
        logging.error(f"grab_frame error: {e}")
    return None


def detect_motion_cv():
    """Deteksi gerakan pakai OpenCV absdiff + blur."""
    f1 = grab_frame_cv()
    if f1 is None:
        return False
    time.sleep(1)
    f2 = grab_frame_cv()
    if f2 is None:
        return False

    # Blur untuk kurangi noise
    f1_blur = cv2.GaussianBlur(f1, (21, 21), 0)
    f2_blur = cv2.GaussianBlur(f2, (21, 21), 0)

    # Hitung selisih absolut
    diff = cv2.absdiff(f1_blur, f2_blur)

    # Threshold
    _, thresh = cv2.threshold(diff, PIXEL_THRESHOLD, 255, cv2.THRESH_BINARY)

    # Hitung pixel yang berubah
    changed = cv2.countNonZero(thresh)
    total = thresh.shape[0] * thresh.shape[1]

    # Logging detail untuk debug
    logging.debug(f"Pixel berubah: {changed}/{total} ({changed*100//total}%)")

    return changed > MIN_PIXEL_CHANGED


def force_stop():
    result = api_call("record/stop")
    if result:
        logging.info(f"Paksa stop: {result}")


def main():
    logging.info("Motion detector dimulai (OpenCV absdiff)")
    motion_count = 0
    recording = False
    last_motion_time = 0
    recording_start = 0

    while True:
        try:
            motion = detect_motion_cv()
            now = time.time()

            if motion:
                motion_count += 1
                logging.info(f"Gerakan terdeteksi ({motion_count}/{RECORD_AFTER})")
            else:
                motion_count = max(0, motion_count - 1)

            if not recording and motion_count >= RECORD_AFTER:
                result = api_call("record/start")
                if result and result.get("status") == "recording":
                    recording = True
                    recording_start = now
                    last_motion_time = now
                    logging.info(f"Mulai rekam: {result.get('file')}")

            if motion and recording:
                last_motion_time = now

            if recording and (now - last_motion_time) > NO_MOTION_TIMEOUT:
                force_stop()
                recording = False
                motion_count = 0
                logging.info(f"Berhenti (ga ada gerakan {NO_MOTION_TIMEOUT}s)")

            if recording and (now - recording_start) > MAX_RECORD_SECONDS:
                force_stop()
                recording = False
                motion_count = 0
                logging.info(f"Paksa berhenti (max {MAX_RECORD_SECONDS}s)")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
