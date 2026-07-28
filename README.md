# CCTV Acer

Backup konfigurasi CCTV di server Acer (192.168.110.7).

## Service
| File | Fungsi |
|---|---|
| `cctv_daemon_acer.py` | Streaming HLS (VAAPI + Audio AAC) |
| `cctv_motion_v2.py` | Deteksi gerakan (threshold 3%) |
| `cctv_record_api.py` | API Record & Download (port 8090) |
| `record_cctv.sh` | Script rekaman (dipanggil API) |
| `cctv-snapshot-acer.sh` | Snapshot JPG periodik |
| `cctv.html` | Dashboard live streaming |
| `recordings.html` | Daftar rekaman |
| `default.conf` | Konfigurasi nginx |
