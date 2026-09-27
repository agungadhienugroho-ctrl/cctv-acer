#!/bin/bash
# ============================================================
# CCTV Auto-Cleanup Rekaman (T470s)
# ============================================================
# Menghapus rekaman CCTV yang lebih lama dari RETENTION_HARI hari.
#
# Default: 2 hari (sesuai permintaan owner)
#
# Keamanan:
#   - Hanya hapus file .mp4 di dalam RECORD_DIR
#   - Tidak pernah hapus file yang mungkin sedang ditulis (< 10 menit)
#   - Ada guard: kalau HDD tidak ter-mount, cleanup dibatalkan
#     (supaya tidak salah hapus / crash karena path hilang)
# ============================================================

RECORD_DIR="/mnt/wd2tb/CCTV/Rekaman"
RETENTION_HARI="${RETENTION_HARI:-2}"
MIN_AGE_MENIT=10          # jangan sentuh file yg mungkin sedang ditulis
MOUNT_POINT="/mnt/wd2tb"

log() { echo "[cleanup] $*"; }

# --- Guard: pastikan HDD benar-benar ter-mount ---
if ! mountpoint -q "$MOUNT_POINT"; then
    log "FATAL: $MOUNT_POINT tidak ter-mount. Cleanup dibatalkan."
    exit 1
fi

if [ ! -d "$RECORD_DIR" ]; then
    log "FATAL: $RECORD_DIR tidak ada. Cleanup dibatalkan."
    exit 1
fi

# --- Cari kandidat file yang boleh dihapus ---
LIST="/tmp/cctv_cleanup_list.txt"

# mtime +N hari (N = retention), DAN tidak lebih baru dari MIN_AGE_MENIT
# makanya pakai: -mtime +$((RETENTION_HARI - 1)) -mmin +$MIN_AGE_MENIT
find "$RECORD_DIR" -maxdepth 1 -type f -name "cctv_*.mp4" \
    -mtime +$((RETENTION_HARI - 1)) -mmin +$MIN_AGE_MENIT \
    > "$LIST" 2>/dev/null

TOTAL=$(wc -l < "$LIST" | tr -d ' ')

if [ "$TOTAL" -eq 0 ]; then
    log "Tidak ada rekaman lebih tua dari ${RETENTION_HARI} hari. Bersih."
    exit 0
fi

# Ukuran yang akan dibebaskan
SIZE_BYTE=$(du -cb $(cat "$LIST") 2>/dev/null | tail -n 1 | cut -f1)
[ -z "$SIZE_BYTE" ] && SIZE_BYTE=0
SIZE_HUMAN=$(numfmt --to=iec --suffix=B "$SIZE_BYTE" 2>/dev/null || echo "${SIZE_BYTE}B")

log "Menemukan $TOTAL file (> ${RETENTION_HARI} hari, total $SIZE_HUMAN)"

# --- Hapus satu per satu, dengan double-check path ---
DELETED=0
while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
        "$RECORD_DIR"/*) ;;
        *) log "SKIP (di luar RECORD_DIR): $f"; continue ;;
    esac
    if rm -f -- "$f"; then
        DELETED=$((DELETED + 1))
    else
        log "GAGAL hapus: $f"
    fi
done < "$LIST"

log "Selesai: $DELETED file dihapus ($SIZE_HUMAN dibebaskan)."

# --- Report disk ---
DISK_LINE=$(df -h "$RECORD_DIR" | tail -n 1)
log "Disk HDD sekarang: $DISK_LINE"
log "Total file tersisa: $(find "$RECORD_DIR" -maxdepth 1 -type f -name 'cctv_*.mp4' | wc -l | tr -d ' ')"
