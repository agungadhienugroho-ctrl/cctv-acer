#!/bin/bash
# CCTV Webcam Snapshot (T470s) - ambil 1 frame per detik dari HLS live
# Output ke webroot Nginx supaya /cctv.jpg selalu fresh
mkdir -p /srv/lsio/nginx/config/www
while true; do
    /usr/bin/ffmpeg -nostdin \
        -i "http://localhost:801/hls/index.m3u8" \
        -vf fps=1 \
        -update 1 \
        -q:v 3 \
        -y /srv/lsio/nginx/config/www/cctv.jpg \
        -nostats -loglevel error 2>/dev/null

    # Kalau ffmpeg keluar (stream putus), tunggu lalu coba lagi
    sleep 2
done
