#!/usr/bin/env python3
"""CCTV daemon — MWB-15 → ffmpeg → JPEG + HLS"""
import subprocess, os, time, signal, sys

SNAPSHOT_JPEG = "/DATA/AppData/nginx/config/www/cctv.jpg"
HLS_DIR = "/DATA/AppData/nginx/config/www/hls"
HLS_INDEX = os.path.join(HLS_DIR, "index.m3u8")
VIDEO_DEV = "/dev/video-cctv"
AUDIO_DEV = "hw:0,0"
WIDTH, HEIGHT = 640, 480
FPS = 25
pidfile = "/tmp/cctv-daemon.pid"

os.system('killall -9 ffmpeg 2>/dev/null')
time.sleep(1)

if os.path.exists(pidfile):
    try:
        with open(pidfile, 'r') as f:
            old_pid = f.read().strip()
        if old_pid and os.path.exists(f"/proc/{old_pid}"):
            print(f"Existing {old_pid} running.", flush=True)
            sys.exit(0)
        else:
            os.remove(pidfile)
    except:
        pass

with open(pidfile, "w") as f:
    f.write(str(os.getpid()))

os.makedirs(HLS_DIR, exist_ok=True)

cmd = [
    'ffmpeg', '-nostdin',
    # Video input
    '-f', 'v4l2',
    '-video_size', f'{WIDTH}x{HEIGHT}',
    '-framerate', str(FPS),
    '-i', VIDEO_DEV,
    # Audio input — buffer besar supaya ga xrun
    '-f', 'alsa',
    '-sample_rate', '48000',
    '-thread_queue_size', '8192',
    '-i', AUDIO_DEV,
    # Filter: split video ke snapshot + HLS
    '-filter_complex', '[0:v]split=2[v_snap][v_hls]',
    '-map', '[v_snap]', '-update', '1', '-y', SNAPSHOT_JPEG,
    '-map', '[v_hls]',
    '-map', '1:a',
    # Video codec
    '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
    '-b:v', '800k', '-pix_fmt', 'yuv420p', '-g', '25',
    # Audio codec
    '-c:a', 'aac', '-b:a', '64k', '-ar', '48000',
    # HLS output
    '-f', 'hls',
    '-hls_time', '4',
    '-hls_list_size', '3',
    '-hls_segment_filename', os.path.join(HLS_DIR, 'segment_%05d.ts'),
    '-hls_flags', 'delete_segments',
    HLS_INDEX
]

print("Starting ffmpeg...", flush=True)
print(f"Video: {VIDEO_DEV} | Audio: {AUDIO_DEV}", flush=True)

err_log = open('/root/cctv_err.log', 'w')
proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err_log)


def cleanup(sig=None, frame=None):
    print("Cleanup...", flush=True)
    proc.kill()
    os.system('killall -9 ffmpeg 2>/dev/null')
    if os.path.exists(pidfile):
        os.remove(pidfile)
    print("Done.", flush=True)
    sys.exit(0)


signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

while True:
    try:
        if proc.poll() is not None:
            cleanup()
            break
        time.sleep(5)
    except KeyboardInterrupt:
        cleanup()
        break
