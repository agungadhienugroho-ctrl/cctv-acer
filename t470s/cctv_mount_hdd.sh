#!/bin/bash
# ============================================================
# CCTV Auto-Detect & Mount HDD Eksternal (T470s)
# ============================================================
# Untuk kasus: om colok HDD baru (Toshiba / disk lain) ke port USB
# yang mana saja, lalu script ini:
#   1. Deteksi disk USB yang baru muncul
#   2. Ambil UUID-nya
#   3. Mount ke /mnt/<nama-disk>
#   4. Log detailnya
#
# Tidak destroy apa pun. Kalau disk sudah mounted, diam.
#
# Manual:  /root/cctv_mount_hdd.sh
# Log:     /var/log/cctv_mount_hdd.log
# ============================================================

LOG_FILE="/var/log/cctv_mount_hdd.log"

log() {
    local msg="[mount-hdd $(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null
}

log "=== Scan disk USB ==="

mounted_any=0

for dev in $(lsblk -d -o NAME 2>/dev/null | grep -E '^sd[a-z]$' | tr -d ' '); do
    full="/dev/$dev"

    # Skip device 0-byte (card reader)
    size_bytes=$(lsblk -b -d -o SIZE "$full" 2>/dev/null | tr -d ' ' | tail -n 1)
    if [ -z "$size_bytes" ] || [ "$size_bytes" = "0" ]; then
        continue
    fi

    # Skip kalau sudah mounted
    already=$(findmnt -n -o TARGET --source "$full" 2>/dev/null | head -n 1)
    if [ -n "$already" ]; then
        log "  $dev -> sudah mounted di $already (skip)"
        continue
    fi

    # Cari partisi pertama yang punya filesystem
    part=$(blkid -o device "/dev/${dev}1" 2>/dev/null | head -n 1)
    if [ -z "$part" ]; then
        alt=$(lsblk -n -o NAME "/dev/$dev" 2>/dev/null | grep -E '^sd[a-z][0-9]$' | head -n 1)
        [ -n "$alt" ] && part="/dev/$alt"
    fi

    if [ -z "$part" ]; then
        log "  $dev -> tidak ada partisi dengan filesystem (skip)"
        continue
    fi

    uuid=$(blkid -s UUID -o value "$part" 2>/dev/null)
    fstype=$(blkid -s TYPE -o value "$part" 2>/dev/null)
    model=$(udevadm info -q property -n "$full" 2>/dev/null | grep -iE 'ID_MODEL_ENC' | cut -d= -f2 | tr '_' ' ' | tr -s ' ' | head -c 40)

    if [ -z "$uuid" ]; then
        log "  $dev -> tidak punya UUID (skip, butuh format manual)"
        continue
    fi

    # Nama folder dari model, fallback ke nama device
    if [ -n "$model" ]; then
        safe=$(echo "$model" | tr -cd 'A-Za-z0-9_-' | head -c 30)
    else
        safe=""
    fi
    [ -z "$safe" ] && safe="disk${dev}"

    target="/mnt/$safe"

    # Kalau target dipakai disk lain, tambah suffix
    if mountpoint -q "$target" 2>/dev/null; then
        target="/mnt/${safe}_${dev}"
    fi

    mkdir -p "$target"

    if mount -t "$fstype" UUID="$uuid" "$target" 2>/dev/null; then
        log "  OK: $dev ($model, $fstype) -> $target"
        log "     UUID=$uuid"
        mounted_any=1
    else
        log "  GAGAL: mount $dev ke $target ($fstype, UUID=$uuid)"
    fi
done

if [ "$mounted_any" -eq 0 ]; then
    log "  (nothing new to mount)"
fi
