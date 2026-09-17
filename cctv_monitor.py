#!/usr/bin/env python3
"""CCTV monitor — notifies on new recording, checks services if stale."""
import os, subprocess, time

RECORD_DIR = "/storage1/CCTV/Rekaman/"
SERVICES = ["cctv-motion", "cctv-record-api"]
STATE_FILE = "/tmp/cctv_last_notified.txt"

def get_newest_file():
    files = [f for f in os.listdir(RECORD_DIR) if f.endswith(".mp4")]
    if not files:
        return None, None
    files.sort(key=lambda f: os.path.getmtime(os.path.join(RECORD_DIR, f)))
    newest = files[-1]
    return newest, os.path.getmtime(os.path.join(RECORD_DIR, newest))

def read_state():
    try:
        return open(STATE_FILE).read().strip() or None
    except (FileNotFoundError, PermissionError):
        return None

def write_state(v):
    try:
        with open(STATE_FILE, "w") as f:
            f.write(str(v))
    except (FileNotFoundError, PermissionError):
        pass

def notify(msg):
    print(f"NOTIFY: {msg}")

def check_and_restart_services():
    for svc in SERVICES:
        res = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
        if res.stdout.strip() != "active":
            subprocess.run(["systemctl", "restart", svc])
            notify(f"Service {svc} mati, telah direstart.")

def main():
    now = time.time()
    newest, mtime = get_newest_file()

    if newest:
        # Rule 1+2: baru < 1 menit → notify (idempotent via state)
        if (now - mtime) < 60:
            last_notified = read_state()
            if last_notified != newest:
                notify(f"Rekaman CCTV baru tersimpan: {newest}")
                write_state(newest)
            return  # normal: ada rekaman baru, skip service check

    # Rule 3: tidak ada file baru > 10 menit → cek service
    if newest is None or (now - mtime) > 600:
        check_and_restart_services()

if __name__ == "__main__":
    main()