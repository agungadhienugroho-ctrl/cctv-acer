# CCTV Acer - Server Monitoring & Recording

Sistem CCTV multi-source untuk monitoring dan recording di server Acer (192.168.110.7).

## System Architecture
```
Acer (192.168.110.7)
├── USB Webcam MWB-15 (/dev/video0)
│   ├── cctv-acer-daemon → HLS /hls/ (640×480 VAAPI)
│   ├── cctv-snapshot-acer → snapshot.jpg tiap 1s
│   ├── cctv-motion → motion detection → trigger rekaman
│   ├── cctv-record-api (port 8090)
│   └── Rekaman: /storage1/CCTV/Rekaman/
│
└── Tapo C200C (RTSP 192.168.110.21)
    ├── cctv-tapo-daemon → HLS /hls-tapo/ (1920×1080)
    ├── cctv-snapshot-tapo → snapshot.jpg tiap 1s
    ├── cctv-motion-tapo → motion detection → trigger rekaman
    ├── cctv-record-tapo-api (port 8091)
    └── Rekaman: /storage1/CCTV/Tapo c200c/
```

## System Services
| Service | Fungsi | Status |
|---------|--------|--------|
| `cctv-acer-daemon` | HLS USB Webcam (640×480) | ✅ |
| `cctv-snapshot-acer` | Snapshot USB | ✅ |
| `cctv-motion` | Motion USB + trigger record | ✅ |
| `cctv-record-api` | API port 8090 | ✅ |
| ~~ | ~~ | ~~ |
| `cctv-tapo-daemon` | HLS Tapo C200C (1920×1080) | ✅ |
| `cctv-snapshot-tapo` | Snapshot Tapo | ✅ |
| `cctv-motion-tapo` | Motion Tapo + trigger record | ✅ |
| `cctv-record-tapo-api` | API port 8091 | ✅ |

## Access
- **CCTV Dashboard**: `http://192.168.110.7:8011/cctv.html`
- **Webcam Recordings**: `http://192.168.110.7:8011/recordings.html`
- **Tapo Recordings**: `http://192.168.110.7:8011/recordings-tapo.html`
- **USB HLS**: `http://192.168.110.7:8011/hls/index.m3u8`
- **Tapo HLS**: `http://192.168.110.7:8011/hls-tapo/index.m3u8`

## Files
| File | Fungsi |
|------|--------|
| `cctv_daemon_acer.py` | USB Webcam HLS daemon |
| `cctv_motion_v2.py` | USB motion detection |
| `cctv_record_api.py` | USB record API (port 8090) |
| `record_cctv.sh` | USB recording script |
| `cctv-snapshot-acer.sh` | USB snapshot loop |
| `cctv-tapo-daemon.sh` | Tapo C200C HLS daemon |
| `cctv_motion_tapo.py` | Tapo motion detection |
| `cctv_record_tapo_api.py` | Tapo record API (port 8091) |
| `record_tapo.sh` | Tapo recording script |
| `cctv-snapshot-tapo.sh` | Tapo snapshot loop |
| `cctv.html` | Multi-camera player |
| `recordings.html` | USB recordings list |
| `recordings-tapo.html` | Tapo recordings list |
