#!/usr/bin/env python3
import os
import time

# Daftar folder + berapa hari mau keep
FOLDERS = {
    "/storage1/CCTV/Tapo c200c": 2,   # video Tapo, keep 2 hari
    "/storage1/CCTV/Rekaman": 2,      # video webcam, keep 2 hari
}
SECONDS_PER_DAY = 86400

def cleanup():
    now = time.time()
    for cctv_dir, days in FOLDERS.items():
        if not os.path.isdir(cctv_dir):
            continue
        keep_secs = days * SECONDS_PER_DAY
        removed = 0
        for filename in os.listdir(cctv_dir):
            filepath = os.path.join(cctv_dir, filename)
            if not os.path.isfile(filepath):
                continue
            if os.path.getmtime(filepath) < (now - keep_secs):
                os.remove(filepath)
                removed += 1
        print(f"{cctv_dir}: hapus {removed} file (keep {days} hari)")

if __name__ == "__main__":
    cleanup()
