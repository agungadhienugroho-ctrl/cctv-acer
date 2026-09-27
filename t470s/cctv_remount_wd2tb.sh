#!/bin/bash
# ============================================================
# CCTV Auto-Remount WD 2TB (T470s)
# ============================================================
# Untuk kasus: USB HDD ke-disconnect (kabel goyang / power surge)
# membuat /mnt/wd2tb hilang -> record API balas HTTP 500
# -> recordings.html kosong.
#
# Script ini cek tiap beberapa menit; kalau /mnt/wd2tb tidak
# ter-mount, coba mount lagi. Kalau disk tidak ditemukan,
# log errornya supaya mudah didiagnosis.
#
# Env override:
#   MOUNT_TARGET = default /mnt/wd2tb
#   DISK_UUID    = default 40c4a267-ea8a-4bfe-b419-42c1cf476df3
# ============================================================

MOUNT_TARGET="${MOUNT_TARGET:-/mnt/wd2tb}"
DISK_UUID="${DISK_UUID:-40c4a267-ea8a-4bfe-b419-42c1cf476df3}"
RECORD_DIR="$MOUNT_TARGET/CCTV/Rekaman"
LOG_FILE="/var/log/cctv_remount.log"

log() {
    local msg="[remount $(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null
}

# --- Kasus 1: sudah ter-mount, pastikan folder rekaman ada ---
if mountpoint -q "$MOUNT_TARGET"; then
    if [ ! -d "$RECORD_DIR" ]; then
        log "ALERT: $RECORD_DIR tidak ada padahal mount aktif. Membuat ulang..."
        if mkdir -p "$RECORD_DIR" 2>/dev/null; then
            log "OK: folder rekaman dibuat ulang."
        fi
    fi
    exit 0
fi

# --- Kasus 2: tidak ter-mount, coba mount ---
log "WARN: $MOUNT_TARGET tidak ter-mount. Coba mount disk $DISK_UUID..."

# Tunggu device node muncul kembali (USB re-enumeration butuh waktu)
for i in 1 2 3 4 5; do
    if blkid -t UUID="$DISK_UUID" >/dev/null 2>&1; then
        break
    fi
    log "  Device belum terdeteksi, menunggu... (${i}/5)"
    sleep 10
done

if ! blkid -t UUID="$DISK_UUID" >/dev/null 2>&1; then
    log "ERROR: Disk $DISK_UUID tidak ditemukan. Cek kabel USB / power."
    exit 1
fi

# Coba mount
mkdir -p "$MOUNT_TARGET"
if mount -t ext4 UUID="$DISK_UUID" "$MOUNT_TARGET" 2>/dev/null; then
    log "OK: $MOUNT_TARGET berhasil di-mount dari UUID $DISK_UUID."
    mkdir -p "$RECORD_DIR"
    JUMLAH=$(find "$RECORD_DIR" -maxdepth 1 -type f -name 'cctv_*.mp4' 2>/dev/null | wc -l)
    log "  Isi rekaman: $JUMLAH file"
    exit 0
else
    log "ERROR: mount gagal. Diagnosa: journalctl -k -n 20"
    exit 1
fi
