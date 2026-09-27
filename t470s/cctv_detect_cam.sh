#!/bin/bash
# ============================================================
# CCTV Auto-Detect Webcam Device (T470s)
# ============================================================
# Cari device node yang benar untuk webcam USB MWB-15.
# Meng Abstractsuaikan dengan urutan /dev/video* yang berubah tiap reboot.
#
# Strategi 3 lapis (stabil -> rapuh):
#   1. /dev/v4l/by-id/  -> berbasis USB serial (PALING STABIL)
#   2. /sys/class/video4linux/*/name -> label "MWB-15"
#   3. /dev/v4l/by-path/ -> port USB physik
#
# Output : path device di STDOUT (mis. /dev/video0)
# Exit   : 0 = ditemukan, 1 = tidak ditemukan
# ============================================================

WANT_NAME="MWB-15"
WANT_USB_PORT="0:1"
WANT_INDEX="index0"

log() { echo "[detect-cam] $*" >&2; }

#DEV Found disimpan di variabel global, bukan stdout
FOUND=""

# --- Helper: resolve symlink by-id/by-path dan validasi ---
_try() {
    local link="$1" tag="$2"
    [ -e "$link" ] || return 1
    local dev
    dev=$(readlink -f "$link" 2>/dev/null) || return 1
    [ -n "$dev" ] && [ -c "$dev" ] || return 1
    log "$tag: $link -> $dev"
    FOUND="$dev"
    return 0
}

# --- Strategi 1: /dev/v4l/by-id/ (paling stabil) ---
detect_by_id() {
    local link
    for link in /dev/v4l/by-id/*"${WANT_NAME}"*; do
        [ -e "$link" ] || continue
        case "$link" in
            *-"${WANT_INDEX}") ;;
            *) continue ;;
        esac
        _try "$link" "Strategy 1 (by-id)" && return 0
    done
    return 1
}

# --- Strategi 2: label di /sys ---
detect_by_name() {
    local d dev name
    for d in /sys/class/video4linux/video*; do
        [ -e "$d/name" ] || continue
        name=$(cat "$d/name" 2>/dev/null) || continue
        if printf "%s" "$name" | grep -qi -- "${WANT_NAME}"; then
            dev="/dev/$(basename "$d")"
            if [ -c "$dev" ]; then
                log "Strategy 2 (by-name): $name -> $dev"
                FOUND="$dev"
                return 0
            fi
        fi
    done
    return 1
}

# --- Strategi 3: port USB ---
detect_by_usbport() {
    local link
    for link in /dev/v4l/by-path/*usb*"${WANT_USB_PORT}"*video-"${WANT_INDEX}" \
                /dev/v4l/by-path/*usbv2-"${WANT_USB_PORT}"*video-"${WANT_INDEX}"; do
        [ -e "$link" ] || continue
        _try "$link" "Strategy 3 (usb-port)" && return 0
    done
    return 1
}

main() {
    if detect_by_id;     then printf "%s\n" "$FOUND"; exit 0; fi
    if detect_by_name;   then printf "%s\n" "$FOUND"; exit 0; fi
    if detect_by_usbport; then printf "%s\n" "$FOUND"; exit 0; fi
    log "GAGAL: webcam MWB-15 tidak ditemukan!"
    exit 1
}

main "$@"
