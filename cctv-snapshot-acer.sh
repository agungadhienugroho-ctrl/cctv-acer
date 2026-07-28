#!/bin/bash
while true; do
    /usr/bin/ffmpeg -nostdin -i "http://localhost:8011/hls/index.m3u8" -vf fps=1 -update 1 -q:v 3 -y /DATA/AppData/nginx/config/www/hls/snapshot.jpg 2>/dev/null
    sleep 1
done
