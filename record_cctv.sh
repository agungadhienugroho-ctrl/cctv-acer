#!/bin/bash
# CCTV Record Script - record dari HLS
OUTPUT="$1"
HLS_URL="http://127.0.0.1:8011/hls/index.m3u8"

exec ffmpeg -y -i "$HLS_URL" \
  -c:v copy \
  -c:a aac -b:a 96k -ar 48000 -ac 2 \
  -af "volume=1.5" \
  -f mp4 -movflags frag_keyframe+empty_moov "$OUTPUT"
