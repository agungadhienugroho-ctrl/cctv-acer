# CCTV Setup — Multi-Server

Arsitektur CCTV rumah yang berjalan per September 2026.

## 🖥️ Topologi

| Server | IP | Peran |
|---|---|---|
| **T470s** | `192.168.110.6` | 🖥️ **Sumber webcam** — HLS live, rekaman, motion, snapshot |
| **Acer (DietPi)** | `192.168.110.7` | 📺 **Presentation** — dashboard + Tapo (Tapo TIDAK boleh disentuh) |
| **Hermes host** | `192.168.110.10` | Agent host (bukan server CCTV) |

> ⚠️ **Penting:** Semua service webcam ada di **T470s**, bukan Acer.
> Acer hanya menyajikan web UI + meng-host unit Tapo.

---

## 📁 Struktur Repo

```
.
├── cctv.html                  # Dashboard (di-host di Acer :8011)
├── recordings.html            # Halaman daftar rekaman
│
├── cctv_record_tapo_api.py    # ✅ Tapo (Acer) — JANGAN DISENTUH
├── cctv_motion_tapo.py        # ✅ Tapo (Acer) — JANGAN DISENTUH
├── cctv-snapshot-tapo.sh      # ✅ Tapo (Acer) — JANGAN DISENTUH
├── record_tapo.sh             # ✅ Tapo (Acer)
├── recordings-tapo.html       # ✅ Tapo (Acer)
│
└── t470s/                     # ⭐ Setup T470s (AKTIF, semua webcam)
    ├── cctv_detect_cam.sh       # Auto-detect device webcam
    ├── cctv_t470_hls.sh         # HLS streaming (VAAPI)
    ├── sync_hls.sh              # Sync HLS → nginx webroot
    ├── cctv-snapshot-t470.sh    # Snapshot JPEG tiap detik
    ├── cctv_record_api.py       # API rekaman (:8091)
    ├── cctv_motion.py           # Motion detection (OpenCV)
    ├── cctv_cleanup_rekaman.sh  # Auto-hapus rekaman > 2 hari
    └── cctv-*.service           # Unit systemd
```

---

## 📹 Webcam — T470s

| ✅ Service | Fungsi |
|---|---|
| `cctv-t470-hls` | Live HLS (H.264 via Intel QuickSync VAAPI) |
| `cctv-sync-hls` | Sync segmen HLS → webroot nginx (dalam Docker) |
| `cctv-snapshot-t470` | Buat `/cctv.jpg` tiap detik untuk mode snapshot |
| `cctv-motion-t470` | Deteksi gerak (OpenCV absdiff) → trigger rekam |
| `cctv-record-api-t470` | REST API rekaman, port **8091** |
| `cctv-cleanup-rekaman.timer` | Hapus rekaman > 2 hari, tiap hari 04:00 |

### Device Detection (WAJIB pakai, jangan hardcode)

`/dev/video*` **urutannya berubah tiap reboot**. Selalu jalankan:

```bash
/root/cctv_detect_cam.sh
# → /dev/video0
```

Strategi 3 lapis:
1. `/dev/v4l/by-id/` — berbasis **serial USB** (paling stabil)
2. `/sys/class/video4linux/*/name` — label `"MWB-15"`
3. `/dev/v4l/by-path/` — port USB fisik

| Device | Identitas |
|---|---|
| `MWB-15` (USB) | ✅ **Webcam yang dipakai** |
| `Integrated Camera` | ❌ Kamera internal laptop — jangan dipakai |

> 💡 **Lampu indikator merah ≠ stream jalan.** LED merah hanya artinya
> kamera aktif. Cek `ps -eo args | grep v4l2` untuk device yang benar-benar dibaca.

### Audio

| ✅ Item | Nilai |
|---|---|
| Mic | USB MWB-15 → `hw:0,0` |
| Gain | `amixer -c 0 set 'Mic' 128` (50%) |
| Filter | `-af volume=1.5` |

> 🔊 **Kresek = gain terlalu tinggi**, bukan masalah digital.
> Gejala: `volumedetect` menunjukkan `max_volume` mendekati `0 dB`.
> Hampir tidak pernah ada ALSA xrun.

---

## 💾 Storage

| ✅ Item | Nilai |
|---|---|
| **Path rekaman (utama)** | `/mnt/wd2tb/CCTV/Rekaman` |
| **Disk utama** | WD 2TB (`ext4`, UUID `40c4a267-…`) |
| **Disk cadangan** | Toshiba 500GB (`exfat`, UUID `894C-6910`) → `/mnt/hdd_toshiba` |
| **Mount** | `/etc/fstab` + `x-systemd.automount` (dua-duanya by UUID) |
| Retensi | **2 hari** (config via `RETENTION_HARI`) |
| Pemakaian | ~2.5–6 GB/hari |

> ⚠️ **Selalu cek mount sebelum diagnosa:**
> ```bash
> mountpoint -q /mnt/wd2tb && echo "OK" || echo "GAGAL"
> ```
> `/mnt/hdd_toshiba` (HDD lama) **tidak lagi terpasang** — fstab entry
> masih ada tapi UUID `894C-6910` sudah hilang dari sistem.
>
> ### 🔴 Kenapa devmon dimatikan
>
> Pada 27 Sep 14:58, HDD **re-enumerate** (bridge JMicron reset sendiri).
> `devmon`/`udevil` (CasaOS) langsung **unmount `/mnt/wd2tb`** lalu plan
> remount ke `/media/devmon/`. Karena disk kembali sebagai `/dev/sda`
> (dari `sdb`), fstab `x-systemd.automount` gagal detect → `/mnt/wd2tb`
> tidak pernah mount lagi → record API balas **HTTP 500** → halaman
> rekaman kosong.
>
> `devmon@devmon.service` sudah di-**disable** supaya tidak berebut mount.
> Mounting HDD sekarang murni ditangani systemd + `cctv-remount-wd2tb.timer`.
> Disk lain yang pernah di-mount devmon tidak terpengaruh — `devmon`
> hanya managing device yang belum punya entry fstab.

### Safety Guard

`cctv_record_api.py` & `cctv_motion.py` punya guard: kalau `/mnt/wd2tb`
tidak ter-mount, proses **exit** — bukan diam-diam menulis ke disk system.

---

## 🔗 URL Penting

| ✅ Layanan | URL |
|---|---|
| Dashboard | `http://192.168.110.7:8011/cctv.html` |
| Rekaman | `http://192.168.110.7:8011/recordings.html` |
| HLS webcam | `http://192.168.110.6:801/hls/index.m3u8` |
| Snapshot | `http://192.168.110.6:801/cctv.jpg` |
| API rekaman | `http://192.168.110.6:8091/api/recordings` |
| HLS Tapo | `http://192.168.110.7:8011/hls-tapo/index.m3u8` |

---

## 🛠️ Perintah Sering Dipakai

```bash
# Status semua service T470s
for s in cctv-t470-hls cctv-sync-hls cctv-snapshot-t470 \
         cctv-motion-t470 cctv-record-api-t470; do
  printf '%-24s %s\n' "$s" "$(systemctl is-active $s)"
done

# Cek device webcam yang sedang dipakai
ps -eo args | grep v4l2 | grep -v grep | grep -oE '\-i /dev/video[0-9]+'

# Cek device mana itu apa
for d in /sys/class/video4linux/video*; do
  echo "$(basename $d) = $(cat $d/name)"
done

# Hapus rekaman lama sekarang juga
/root/cctv_cleanup_rekaman.sh

# Log
journalctl -u cctv-t470-hls -f
tail -f /var/log/cctv_err.log
```

---

## 📌 Riwayat Perubahan

| Tanggal | Perubahan |
|---|---|
| 2026-09-26 | HLS sync moved ke systemd service (`cctv-sync-hls`) |
| 2026-09-27 | Webcam moved Acer → **T470s**; Acer jadi presentation-only |
| 2026-09-27 | Bug fix: `-i /dev/video2` (kamera internal) → **MWB-15** |
| 2026-09-27 | Tambah **auto-detect device** (`cctv_detect_cam.sh`) |
| 2026-09-27 | Audio fix: mic laptop → **mic USB**, gain 93% → 50% |
| 2026-09-27 | Rekaman pindah ke **WD 2TB** (`/mnt/wd2tb`) + safety guard |
| 2026-09-27 | Tambah **auto-cleanup** rekaman > 2 hari (timer 04:00) |

---

## 🔒 Troubleshooting

| Gejala | Penyebab | Fix |
|---|---|---|
| Live mati, halaman kosong | `index.m3u8` 0 byte | `systemctl restart cctv-sync-hls` |
| Stream jalan tapi ≠ webcam yang benar | hardcode `/dev/videoN` | Pakai `cctv_detect_cam.sh` |
| LED merah tapi live ga kelihatan | ffmpeg baca kamera internal | Cek `ps -eo args \| grep v4l2` |
| Suara kresek | mic gain tinggi + `volume` ffmpeg | `volumedetect` → turunkan gain |
| Rekaman tidak bertambah | HDD tidak ter-mount | `mountpoint -q /mnt/wd2tb` |
| Rekaman makan disk system | Guard tidak ada / path salah | Cek `RECORD_DIR` di script |
