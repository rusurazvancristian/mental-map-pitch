# Mental Map — Pitch Package

Full-stack perception over raw monocular robot video, plus the live on-device
distance pipeline — packaged for the hackathon pitch.

From a single RGB camera we built **two perception engines**:

- **Engine A — Offline 3D Reconstruction.** Turns the 5 raw Unitree Go2 clips into
  an explorable 3D point-cloud map + semantic object distances. Runs on a GPU,
  per clip. *(DepthAnything V2 → ORB + PnP-RANSAC visual odometry → BEV map →
  YOLOv8n object detection → metric distance.)*
- **Engine B — Live On-Device Distance.** On a Raspberry Pi 5 + Hailo-8L NPU,
  measures real-time metric distance to people in front of the camera.
  *(YOLO26m → ByteTrack → pinhole geometry + DepthAnything V2 → Kalman fusion →
  ReID target-lock.)*

---

## Repository layout

| Folder | What it is |
|--------|-----------|
| **`app/`** | The ready-to-run pitch app, zipped (`MentalMapSLAM_Demo.zip`). Self-contained Windows build — **no Python, no GPU, no internet needed**. This is what you run to present. |
| **`src/`** | Source code of the pitch app (SLAM pipeline + the pywebview UI). For reading, modifying, or rebuilding the `.exe`. |
| **`rpi-live/`** | The Raspberry Pi 5 + Hailo-8L live-distance pipeline (deployed on the Pi, not the laptop). |

---

## ▶ Quickstart — run the pitch (Windows laptop)

> **Install Git LFS *before* cloning**, or the app will arrive as a tiny pointer
> file instead of the real 126 MB zip.

```powershell
# 1. one-time: install Git LFS  (https://git-lfs.com)  then:
git lfs install

# 2. clone
git clone https://github.com/rusurazvancristian/mental-map-pitch.git
cd mental-map-pitch

# 3. unzip the app and run it
Expand-Archive app\MentalMapSLAM_Demo.zip -DestinationPath app\run
.\app\run\MentalMapSLAM_Demo\MentalMapSLAM_Demo.exe
```

That's it — the window opens on **Start the Pitch**'s neighbour, **Process &
Results**. Everything (videos, 3D map, Three.js) is bundled and works **offline**.

**Quickstart (RO):** instalează Git LFS, `git lfs install`, clonează, dezarhivează
`app\MentalMapSLAM_Demo.zip`, rulează `MentalMapSLAM_Demo.exe`. Merge 100% offline.

> If the window is blank on a fresh Windows machine, install the **Edge WebView2
> Runtime** (free, from Microsoft) — it's preinstalled on Windows 11.

---

## App tabs

- **Start the Pitch** — cue-card teleprompter for the opening monologue (timer + ← →).
- **Process & Results** — how it was built: both engines, tech stack, results.
- **3D Map Explorer** — per-clip point-cloud viewer (All / V1…V5, RGB/Height).
- **Demo Videos** — side-by-side RGB+ORB / depth / SLAM-BEV with distance labels.
- **Space Explorer** — first-person walk-through of the point cloud.

---

## Run from source (optional)

The `.exe` already contains everything; this is only for development.

```powershell
cd src
pip install -r requirements.txt
python pitch_demo\launcher.py
```

> `src/` ships code only. To show videos / 3D map when running from source, copy the
> media from the unzipped app (`app\run\MentalMapSLAM_Demo\_internal\output\` and
> `…\_internal\vendor\`) into `src\output\` and `src\vendor\`, or rebuild the data
> with `photogrammetry.py` / `rebuild_3d_map.py` (needs the GPU + the raw clips).

Rebuild the standalone exe: `cd src && pyinstaller MentalMapSLAM_Demo.spec`.

---

## `rpi-live/` — the live distance pipeline (Raspberry Pi)

Deployed on a **Raspberry Pi 5 + Hailo-8L**, not the laptop.

```bash
# on the Pi
cd rpi-live
sudo apt install hailo-all          # provides hailo_platform
pip install -r requirements.txt     # picamera2, opencv, numpy, scipy
python main.py
```

Runs YOLO26m + DepthAnything V2 + RepVGG ReID concurrently on the NPU and prints
the live metric distance to the locked person. Has a mock fallback (webcam /
synthetic) so it also runs on a plain PC without the Hailo hardware.

**Note:** wiring this live feed *into* the pitch app (a "Live Demo" tab streaming
from the Pi over MJPEG) is planned but **not yet built** — for now the Pi runs
standalone and the app shows the pre-recorded demos.

---

## Tech stack

Python · PyTorch + CUDA · DepthAnything V2 · YOLOv8n / YOLO26m · OpenCV ·
ORB + PnP-RANSAC · ByteTrack · Kalman fusion · RepVGG ReID · Hailo-8L NPU ·
Raspberry Pi 5 · Three.js / WebGL · pywebview.
