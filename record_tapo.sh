#!/bin/bash
# Record CCTV Tapo C200C - triggered by motion detection
# Output: /storage1/CCTV/Tapo\ c200c/cctv_YYYYMMDD_HHMMSS.mp4

STORAGE_DIR="/storage1/CCTV/Tapo c200c"
mkdir -p "$STORAGE_DIR"

# Cleanup old recordings > 3 hari
find "$STORAGE_DIR" -name "cctv_*.mp4" -mtime +3 -delete 2>/dev/null

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT="$STORAGE_DIR/cctv_${TIMESTAMP}.mp4"

# Record from Tapo HLS stream for MAX_RECORD duration
# 600 seconds = 10 menit max, actual stop handled by API
exec timeout 610 ffmpeg -nostdin \
    -i "http://localhost:8011/hls-tapo/index.m3u8" \
    -t 600 \
    -c copy \
    -movflags +faststart \
    "$OUTPUT" -nostats -loglevel error 2>/dev/null

echo "Tapo Recording saved: $OUTPUT ($(stat -c%s "$OUTPUT" 2>/dev/null) bytes)"
