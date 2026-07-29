#!/bin/bash
# CCTV Tapo Snapshot - ambil frame dari HLS Tapo setiap 1 detik
while true; do
    /usr/bin/ffmpeg -nostdin \
        -i "http://localhost:8011/hls-tapo/index.m3u8" \
        -vf fps=1 \
        -update 1 \
        -q:v 3 \
        -y /DATA/AppData/nginx/config/www/hls-tapo/snapshot.jpg \
        -nostats -loglevel error 2>/dev/null
    sleep 2
done
