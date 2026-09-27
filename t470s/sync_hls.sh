#!/bin/bash
# Sync HLS segments from /var/www/hls to nginx webroot (T470s)
# Dipakai karena nginx jalan di dalam docker container linuxserver-nginx-app-1
while true; do
  rsync -a --delete /var/www/hls/ /srv/lsio/nginx/config/www/hls/ 2>/dev/null
  sleep 1
done
