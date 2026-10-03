#!/bin/bash
# ============================================================
# CCTV Webcam HLS Streaming (T470s)
# Video: MWB-15 USB webcam (auto-detect device)
# Encode: VAAPI (Intel QuickSync)
# Audio: mic dari webcam USB MWB-15 (hw:0,0)
# ============================================================
set -e

mkdir -p /var/www/hls

# ---- Auto-detect device webcam ----
# Kalau device tidak ketemu, coba lagi 5x dengan jeda (webcam mungkin
# belum siap setelah reboot / belum di-enumerate kernel)
CAM_DEV=""
for attempt in 1 2 3 4 5; do
    if CAM_DEV=$(/root/cctv_detect_cam.sh 2>/dev/null); then
        break
    fi
    echo "[hls] percobaan $attempt: webcam belum siap, tunggu 10 detik..." >&2
    CAM_DEV=""
    sleep 10
done

if [ -z "$CAM_DEV" ]; then
    echo "[hls] FATAL: tidak menemukan webcam MWB-15 setelah 5 percobaan" >&2
    exit 1
fi

echo "[hls] memakai webcam: $CAM_DEV" >&2

# ---- Streaming HLS ----
ffmpeg -nostdin \
    -thread_queue_size 8192 \
    -vaapi_device /dev/dri/renderD128 \
    -f v4l2 -input_format mjpeg -video_size 640x480 -i "$CAM_DEV" \
    -f alsa -thread_queue_size 8192 -ac 2 -ar 48000 -i hw:0,0 \
    -vf "format=nv12,hwupload" \
    -c:v h264_vaapi -qp 25 \
    -c:a aac -b:a 96k -ar 48000 -ac 2 \
    -af "volume=1.5,aresample=async=1:first_pts=0" \
    -g 30 \
    -f hls -hls_time 4 -hls_list_size 3 -hls_flags delete_segments \
    -hls_segment_filename "/var/www/hls/seg_%05d.ts" \
    "/var/www/hls/index.m3u8"
