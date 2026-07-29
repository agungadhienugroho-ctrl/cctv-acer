#!/bin/bash
# Continuous CCTV snapshot — overwrite /tmp/cctv.jpg every 100ms
while true; do
    ffmpeg -y -f v4l2 -i /dev/video1 -frames:v 1 -q:v 2 /tmp/cctv.jpg 2>/dev/null
    sleep 0.1
done
