# CCTV Acer - Server Monitoring & Recording

Sistem CCTV multi-source untuk monitoring dan recording di server Acer (192.168.110.7).

## Komponen
| File | Fungsi |
|------|--------|
| `cctv_daemon_acer.py` | HLS streaming daemon (USB Webcam MWB-15) |
| `cctv-tapo-daemon.sh` | HLS streaming daemon (Tapo C200C RTSP) |
| `cctv_motion_v2.py` | Motion detection & trigger rekaman |
| `cctv_record_api.py` | HTTP API untuk akses file rekaman |
| `record_cctv.sh` | Script recording ketika motion terdeteksi |
| `cctv-snapshot-acer.sh` | Snapshot berkala dari HLS stream |
| `cctv.html` | HLS Player dashboard (multi-camera) |
| `recordings.html` | Daftar rekaman |

## Service Systemd
| Service | Port/Fungsi |
|---------|-------------|
| `cctv-acer-daemon` | ffmpeg HLS ke webcam USB (640x480) |
| `cctv-tapo-daemon` | ffmpeg HLS ke Tapo C200C (1920x1080) |
| `cctv-motion` | Motion detection + trigger record |
| `cctv-record-api` | API port 8090 |
| `cctv-snapshot-acer` | Snapshot tiap 1 detik |

## Source Saat Ini
- **Source 1**: USB Webcam MWB-15 (/dev/video0) - 640x480 VAAPI HLS
- **Source 2**: Tapo C200C (RTSP) - 1920x1080 Full HD HLS
