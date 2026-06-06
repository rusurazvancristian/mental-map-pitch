"""
Mental Map SLAM — Pitch Demo Launcher
  python launcher.py          (dev)
  MentalMapSLAM_Demo.exe      (built)
"""
import os, sys, threading, time
from pathlib import Path
import http.server

# ── Resolve base directory ─────────────────────────────────────────────────
# In dev  → D:\mental_map_slam  (two levels above this file)
# In exe  → sys._MEIPASS  (where PyInstaller extracts bundled data)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "output"
THUMB_DIR  = BASE_DIR / "pitch_demo" / "thumbs"
PORT       = 8765


# ── Thumbnail extraction ───────────────────────────────────────────────────
def extract_thumbnails() -> None:
    """Grab frame 60 of each demo video and save as JPEG thumbnail."""
    try:
        import cv2
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        for i in range(1, 6):
            out = THUMB_DIR / f"video_{i}_thumb.jpg"
            if out.exists():
                continue
            mp4 = OUTPUT_DIR / f"video_{i}_demo.mp4"
            if not mp4.exists():
                continue
            cap = cv2.VideoCapture(str(mp4))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            target = min(60, max(5, total // 3))
            cap.set(cv2.CAP_PROP_POS_FRAMES, target)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
            cap.release()
    except Exception as e:
        print(f"[thumb] {e}")


# ── Local HTTP server ──────────────────────────────────────────────────────
class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
    def log_error(self, *_):   pass


def _start_server() -> None:
    os.chdir(str(BASE_DIR))          # serve files relative to BASE_DIR
    srv = http.server.HTTPServer(("127.0.0.1", PORT), _SilentHandler)
    srv.serve_forever()


# ── Entry point ────────────────────────────────────────────────────────────
def main() -> None:
    extract_thumbnails()

    threading.Thread(target=_start_server, daemon=True).start()
    time.sleep(0.4)                  # let the server bind before opening window

    import webview
    webview.create_window(
        title="Mental Map SLAM — Pitch Demo",
        url=f"http://127.0.0.1:{PORT}/pitch_demo/ui.html",
        width=1460,
        height=920,
        min_size=(1200, 720),
        background_color="#07071a",
        text_select=False,
        zoomable=False,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
