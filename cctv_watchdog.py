#!/usr/bin/env python3
"""CCTV watchdog for Acer — auto-heal USB webcam + Tapo streams.
Checks: daemon alive, ffmpeg running, HLS segments fresh, symlink valid.
Auto-repairs; notifies Telegram on action/failure.
ponytail: single-host, no HA. Add Prometheus pushgateway when multi-node.
"""
import os, time, subprocess, json, sys
from datetime import datetime

BOT_TOKEN = "8878308752:AAGH3EIVJzGAnroClPknZ7Ref8SapXp5TZ8"
CHAT_ID   = "1761510066"  # om's Telegram id (Home)
DAEMON    = "/root/cctv_daemon_acer.py"
HLS_USB   = "/DATA/AppData/nginx/config/www/hls"
HLS_TAPO  = "/DATA/AppData/nginx/config/www/hls-tapo"
SYMLINK   = "/dev/video-cctv"
SYMLINK_TARGET = "video0"
LOG       = "/root/cctv_watchdog.log"
STALE_SEC = 60  # segment older than this = not recording

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def notify(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        subprocess.run(["curl", "-s", "-X", "POST", url,
                        "-d", f"chat_id={CHAT_ID}", "-d", f"text={text}"],
                       timeout=10, capture_output=True)
    except Exception as e:
        log(f"notify failed: {e}")

def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return None

def daemon_alive():
    r = run("pgrep -f 'cctv_daemon_acer.py'")
    return bool(r and r.stdout.strip())

def ffmpeg_for(pattern):
    r = run(f"pgrep -f '{pattern}'")
    return bool(r and r.stdout.strip())

def fresh_segment(d, stale=STALE_SEC):
    if not os.path.isdir(d):
        return False
    freshest = stale + 999  # sentinel older than stale
    for fn in os.listdir(d):
        if fn.endswith(".ts") or fn == "index.m3u8":
            try:
                age = time.time() - os.path.getmtime(os.path.join(d, fn))
                freshest = min(freshest, age)
            except OSError:
                pass
    return freshest < stale

def symlink_ok():
    if not os.path.islink(SYMLINK):
        return False
    return os.readlink(SYMLINK) == SYMLINK_TARGET

def fix_symlink():
    try:
        if os.path.islink(SYMLINK) or os.path.exists(SYMLINK):
            os.remove(SYMLINK)
        os.symlink(SYMLINK_TARGET, SYMLINK)
        return True
    except Exception as e:
        log(f"symlink fix failed: {e}")
        return False

def restart_daemon():
    log("restarting CCTV daemon")
    run("pkill -9 -f cctv_daemon_acer.py")
    run("pkill -9 -f 'ffmpeg.*v4l2.*cctv'")
    time.sleep(2)
    subprocess.Popen(["setsid", "python3", DAEMON],
                     stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    time.sleep(6)

def heal_usb():
    """USB webcam stream dead — fix symlink first, then restart daemon."""
    ok = True
    if not symlink_ok():
        log("USB: symlink invalid, fixing")
        ok = fix_symlink()
    if not daemon_alive():
        restart_daemon()
    else:
        # daemon alive but ffmpeg usb dead -> kill stuck ffmpeg, daemon Restart=always
        # will respawn; if not, force restart
        if not ffmpeg_for("ffmpeg.*v4l2.*cctv"):
            log("USB: ffmpeg missing, killing stuck procs + restart")
            run("pkill -9 -f 'ffmpeg.*v4l2.*cctv'")
            time.sleep(2)
            restart_daemon()
    return ok and fresh_segment(HLS_USB, 90)

def heal_tapo():
    """Tapo (RTSP) dead — usually ffmpeg crash; kill + let daemon respawn or restart."""
    if not daemon_alive():
        restart_daemon()
    if not ffmpeg_for("rtsp.*stream1"):
        log("Tapo: ffmpeg missing, killing + restart")
        run("pkill -9 -f 'rtsp.*stream1'")
        time.sleep(2)
        restart_daemon()
    return fresh_segment(HLS_TAPO, 90)

def main():
    issues = []
    # Symlink sanity (prevent the root-cause we already hit)
    if not symlink_ok():
        if fix_symlink():
            issues.append("symlink /dev/video-cctv dipulihkan -> video0")
        else:
            issues.append("GAGAL fix symlink")

    # USB webcam
    usb_ok = ffmpeg_for("ffmpeg.*v4l2.*cctv") and fresh_segment(HLS_USB)
    if not usb_ok:
        log("USB stream down — healing")
        if heal_usb():
            issues.append("USB webcam di-repair & live lagi")
        else:
            issues.append("GAGAL repair USB webcam")

    # Tapo
    tapo_ok = ffmpeg_for("rtsp.*stream1") and fresh_segment(HLS_TAPO)
    if not tapo_ok:
        log("Tapo stream down — healing")
        if heal_tapo():
            issues.append("Tapo di-repair & live lagi")
        else:
            issues.append("GAGAL repair Tapo")

    if issues:
        notify("🔧 CCTV Watchdog (Acer):\n" + "\n".join("• " + i for i in issues))
        log("NOTIFIED: " + " | ".join(issues))
    else:
        log("all streams OK")

if __name__ == "__main__":
    main()
