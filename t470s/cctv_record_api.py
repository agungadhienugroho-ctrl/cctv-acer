#!/usr/bin/env python3
import http.server, json, os, subprocess, time, logging, sys
from datetime import datetime

HLS_URL = "http://127.0.0.1:801/hls/index.m3u8"
RECORD_DIR = "/mnt/wd2tb/CCTV/Rekaman"
LOG_FILE = "/tmp/cctv-record-api.log"
SERVER_PORT = 8091
MAX_DURATION_SECONDS = 60

logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)])
os.makedirs(RECORD_DIR, exist_ok=True)

# --- SAFETY GUARD: pastikan RECORD_DIR benar-benar di HDD, bukan fallback ke root FS ---
if not os.path.ismount("/mnt/wd2tb"):
    print("FATAL: /mnt/wd2tb tidak ter-mount! Rekaman dibatalkan agar tidak "
          "membanjiri disk system.", flush=True)
    raise SystemExit(1)


current_recording_process = None
current_recording_filename = None
recording_start_time = None

class Handler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def log_message(self, format, *args):
        pass  # reduce noise

    def _safe_write(self, data):
        try:
            self.wfile.write(data)
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def _safe_flush(self):
        try:
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def _send_file(self, filepath, start, length):
        with open(filepath, "rb") as f:
            f.seek(start)
            rem = length
            while rem > 0:
                chunk = f.read(min(65536, rem))
                if not chunk:
                    break
                if not self._safe_write(chunk):
                    return False
                rem -= len(chunk)
        return True

    def do_GET(self):
        global current_recording_process, current_recording_filename, recording_start_time
        path = self.path
        response_data = {}
        status_code = 200
        try:
            if path == "/api/record/start":
                if current_recording_process and current_recording_process.poll() is None:
                    response_data = {"status": "already_recording", "file": current_recording_filename}
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    current_recording_filename = os.path.join(RECORD_DIR, "cctv_" + timestamp + ".mp4")
                    script_path = "/root/record_cctv.sh"
                    current_recording_process = subprocess.Popen([script_path, current_recording_filename])
                    recording_start_time = time.time()
                    response_data = {"status": "recording", "file": current_recording_filename}
            elif path == "/api/record/stop":
                if current_recording_process and current_recording_process.poll() is None:
                    current_recording_process.terminate()
                    try:
                        current_recording_process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        try:
                            current_recording_process.kill()
                            current_recording_process.wait()
                        except:
                            pass
                    time.sleep(2)
                    response_data = {"status": "stopped", "file": current_recording_filename}
                    current_recording_process = None
                    recording_start_time = None
                else:
                    response_data = {"status": "not_recording"}
            elif path == "/api/record/status":
                is_rec = current_recording_process and current_recording_process.poll() is None
                elapsed = 0
                if is_rec and recording_start_time:
                    elapsed = int(time.time() - recording_start_time)
                    if elapsed >= MAX_DURATION_SECONDS:
                        try:
                            current_recording_process.terminate()
                            current_recording_process.wait(timeout=5)
                        except:
                            pass
                        is_rec = False
                        current_recording_process = None
                        recording_start_time = None
                        response_data = {"recording": False, "reason": "max_duration_reached", "file": current_recording_filename}
                if is_rec:
                    response_data = {"recording": True, "elapsed": elapsed, "remaining": MAX_DURATION_SECONDS - elapsed, "file": current_recording_filename}
                else:
                    response_data = {"recording": False}
            elif path == "/api/recordings":
                files = []
                for f in os.listdir(RECORD_DIR):
                    filepath = os.path.join(RECORD_DIR, f)
                    if os.path.isfile(filepath) and f.endswith(".mp4"):
                        try:
                            st = os.stat(filepath)
                            files.append({"file": f, "size": st.st_size, "date": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
                        except:
                            pass
                files.sort(key=lambda x: x["date"], reverse=True)
                response_data = files
            elif path.startswith("/api/download/"):
                filename = path.replace("/api/download/", "")
                filename = os.path.basename(filename)
                filepath = os.path.join(RECORD_DIR, filename)
                if os.path.exists(filepath) and filepath.startswith(RECORD_DIR):
                    filesize = os.path.getsize(filepath)
                    range_h = self.headers.get("Range")
                    if range_h and range_h.startswith("bytes="):
                        try:
                            rv = range_h[6:]
                            if "-" in rv:
                                ss, ee = rv.split("-", 1)
                                start = int(ss) if ss else 0
                                end = int(ee) if ee else filesize - 1
                                if end >= filesize:
                                    end = filesize - 1
                                length = end - start + 1
                                self.send_response(206)
                                self.send_header("Content-Type", "video/mp4")
                                self.send_header("Accept-Ranges", "bytes")
                                self.send_header("Content-Range", "bytes " + str(start) + "-" + str(end) + "/" + str(filesize))
                                self.send_header("Content-Length", length)
                                self.send_header("Access-Control-Allow-Origin", "*")
                                self.end_headers()
                                self._send_file(filepath, start, length)
                                return
                        except:
                            pass
                    self.send_response(200)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", filesize)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self._send_file(filepath, 0, filesize)
                    return
                else:
                    status_code = 404
                    response_data = {"error": "File not found"}
            else:
                status_code = 404
                response_data = {"error": "Not Found"}
        except BrokenPipeError:
            return  # Client disconnected, not an error
        except Exception as e:
            logging.error("API Error: %s", str(e), exc_info=True)
            status_code = 500
            response_data = {"error": str(e)}
        try:
            self._set_headers(status_code)
            self._safe_write(json.dumps(response_data).encode("utf-8"))
        except:
            pass

def run_server():
    addr = ("", SERVER_PORT)
    httpd = http.server.HTTPServer(addr, Handler)
    httpd.timeout = 30
    logging.info("Record API listening on port %d", SERVER_PORT)
    while True:
        try:
            httpd.serve_forever()
        except Exception as e:
            logging.error("Server error: %s, restarting...", str(e))
            time.sleep(1)
            continue

if __name__ == "__main__":
    run_server()
