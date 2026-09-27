#!/bin/bash
# ============================================================
# CCTV Auto-Remount HDD (T470s) — multi-disk
# ============================================================
# Untuk kasus: USB HDD ke-disconnect / ke-re-enumerate membuat
# mount point hilang -> record API balas HTTP 500 ->
# recordings.html kosong.
#
# Script ini cek tiap beberapa menit; kalau mount hilang,
# coba mount lagi dari fstab (by UUID). Kalau disknya sendiri
# tidak ada, log errornya.
#
# Env override:
#   RECORD_MOUNTS = default "/mnt/wd2tb /mnt/hdd_toshiba"
#   WAIT_SECONDS  = default 50 (tunggu device re-enumerate)
# ============================================================

RECORD_MOUNTS="${RECORD_MOUNTS:-/mnt/wd2tb /mnt/hdd_toshiba}"
WAIT_SECONDS="${WAIT_SECONDS:-50}"
LOG_FILE="/var/log/cctv_remount.log"

log() {
    local msg="[remount $(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null
}

RECOVERED=0
FAILED=0

for MOUNT_TARGET in $RECORD_MOUNTS; do
    # --- Kasus 1: sudah ter-mount, pastikan folder rekaman ada ---
    if mountpoint -q "$MOUNT_TARGET"; then
        if [ ! -d "$MOUNT_TARGET/CCTV/Rekaman" ]; then
            log "ALERT: $MOUNT_TARGET/CCTV/Rekaman tidak ada. Membuat ulang..."
            mkdir -p "$MOUNT_TARGET/CCTV/Rekaman" 2>/dev/null \
                && log "OK: folder rekaman dibuat ulang."
        fi
        continue
    fi

    # --- Kasus 2: tidak ter-mount ---
    log "WARN: $MOUNT_TARGET tidak ter-mount. Coba mount dari fstab..."

    # Tunggu device re-enumerate (USB butuh waktu)
    for i in $(seq 1 5); do
        # Cari device yang cocok UUID di fstab untuk mount point ini
        UUID=$(awk -v mp="$MOUNT_TARGET" '$2==mp {gsub("UUID=","",$1); print $1}' /etc/fstab 2>/dev/null | head -n 1)
        if [ -n "$UUID" ] && blkid -t UUID="$UUID" >/dev/null 2>&1; then
            break
        fi
        if [ $i -lt 5 ]; then
            log "  Device belum terdeteksi, menunggu... (${i}/5)"
            sleep 10
        fi
    done

    UUID=$(awk -v mp="$MOUNT_TARGET" '$2==mp {gsub("UUID=","",$1); print $1}' /etc/fstab 2>/dev/null | head -n 1)

    if [ -z "$UUID" ]; then
        log "ERROR: tidak ada entry fstab untuk $MOUNT_TARGET. Cek /etc/fstab."
        FAILED=$((FAILED + 1))
        continue
    fi

    if ! blkid -t UUID="$UUID" >/dev/null 2>&1; then
        log "ERROR: disk $UUID tidak ditemukan. Cek kabel USB / power."
        FAILED=$((FAILED + 1))
        continue
    fi

    mkdir -p "$MOUNT_TARGET"
    # mount -a lebih aman: pakai semua opsi dari fstab
    if mount "$MOUNT_TARGET" 2>/dev/null; then
        log "OK: $MOUNT_TARGET berhasil di-mount (UUID $UUID)."
        mkdir -p "$MOUNT_TARGET/CCTV/Rekaman"
        JUMLAH=$(find "$MOUNT_TARGET/CCTV/Rekaman" -maxdepth 1 -type f -name 'cctv_*.mp4' 2>/dev/null | wc -l)
        log "  Isi rekaman: $JUMLAH file"
        RECOVERED=$((RECOVERED + 1))
    else
        log "ERROR: mount $MOUNT_TARGET gagal. Log: journalctl -k -n 20"
        FAILED=$((FAILED + 1))
    fi
done

exit $((FAILED > 0 ? 1 : 0))
