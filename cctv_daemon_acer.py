#!/usr/bin/env python3
import subprocess, os, time, signal, sys

HLS_DIR = "/DATA/AppData/nginx/config/www/hls"
HLS_INDEX = os.path.join(HLS_DIR, "index.m3u8")
VIDEO_DEV = "/dev/video0"
AUDIO_DEV = "hw:0,0"
WIDTH, HEIGHT = 640, 480
pidfile = "/tmp/cctv-daemon.pid"

os.system("killall -9 ffmpeg 2>/dev/null; rm -f /tmp/cctv-daemon.pid")
time.sleep(1)
os.makedirs(HLS_DIR, exist_ok=True)

cmd = [
    "ffmpeg", "-nostdin",
    "-vaapi_device", "/dev/dri/renderD128",
    "-f", "v4l2",
    "-input_format", "mjpeg",
    "-video_size", "%dx%d" % (WIDTH, HEIGHT),
    "-i", VIDEO_DEV,
    "-f", "alsa",
    "-sample_rate", "48000",
    "-ac", "2",
    "-thread_queue_size", "2048",
    "-use_wallclock_as_timestamps", "1",
    "-i", AUDIO_DEV,
    "-af", "volume=2.0,aresample=async=1000",
    "-vf", "format=nv12,hwupload",
    "-c:v", "h264_vaapi", "-qp", "25",
    "-g", "30", "-sc_threshold", "0",
    "-c:a", "aac", "-b:a", "64k",
    "-f", "hls",
    "-hls_time", "6",
    "-hls_list_size", "5",
    "-hls_segment_filename", os.path.join(HLS_DIR, "seg_%05d.ts"),
    "-hls_flags", "delete_segments",
    HLS_INDEX
]

print("CCTV Acer: %dx%d VAAPI | Audio: %s" % (WIDTH, HEIGHT, AUDIO_DEV), flush=True)
err_log = open("/var/log/cctv_err.log", "w")
proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err_log)

def cleanup(sig=None, frame=None):
    proc.kill()
    os.system("killall -9 ffmpeg 2>/dev/null")
    if os.path.exists(pidfile): os.remove(pidfile)
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

while True:
    try:
        if proc.poll() is not None:
            cleanup()
        time.sleep(5)
    except KeyboardInterrupt:
        cleanup()