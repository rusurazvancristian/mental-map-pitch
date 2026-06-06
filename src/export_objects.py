"""
Export detected objects with 3D world positions per video -> output/objects.json
for the Space Explorer audio-tour game (no video rendering, just the data).

Positions are Y-flipped to match the saved point clouds (video_N_cloud.ply,
which photogrammetry.py saves with pts[:,1] *= -1).

  python export_objects.py
"""

import json
from pathlib import Path
import numpy as np
import cv2
from tqdm import tqdm

INPUT_DIR  = Path(r"C:\Users\Razvan\Desktop\inference_sets_contest\mental_map")
OUTPUT_DIR = Path(r"D:\mental_map_slam\output")
MAX_PER_SCENE = 40        # cap markers per scene
MIN_SEEN      = 2         # object must be re-seen at least this many frames (anti-noise)


def main():
    from config import CAMERA, SLAM
    from depth_engine import DepthEngine
    from object_detector import ObjectDetector, ObjectMemory
    from visual_odometry import VisualOdometry
    from data_contract import FrameState

    depth_engine = DepthEngine(SLAM.depth_model_id, SLAM.depth_fallback_id, "cuda",
                               metric_scale=SLAM.depth_metric_scale)
    detector = ObjectDetector("yolov8n.pt", conf_thresh=0.35, device="cuda")

    scene_objects = {}                       # id -> list of {name,x,y,z,dist}
    all_objs = []
    id_map = {1: "v1", 2: "v2", 3: "v3", 4: "v4", 5: "v5"}

    for idx, vp in enumerate(sorted(INPUT_DIR.glob("*.mp4")), start=1):
        sid = id_map.get(idx, f"v{idx}")
        print(f"\n[{sid}] {vp.name}")

        cap = cv2.VideoCapture(str(vp))
        if not cap.isOpened():
            print("  cannot open"); continue
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        vo = VisualOdometry(CAMERA, SLAM)
        mem = ObjectMemory(merge_dist=0.8)
        seen = {}                            # id(obj dict) -> count
        pose = np.eye(4, dtype=np.float64)
        prev = None
        fid = 0
        pbar = tqdm(total=total // SLAM.frame_stride, unit="kf")

        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            if fid % SLAM.frame_stride != 0:
                fid += 1
                continue

            depth = depth_engine.infer(bgr)
            kps, descs = vo.detect(bgr)
            if prev is not None:
                T = vo.estimate_pose(prev, kps, descs)
                if T is not None:
                    pose = prev.pose_c2w @ np.linalg.inv(T)

            dets = detector.detect(bgr)
            detector.measure_distances(dets, depth, camera=CAMERA,
                                       d_min=SLAM.depth_min_m, d_max=SLAM.depth_max_m)
            detector.project_to_world(dets, pose, CAMERA)
            n_before = len(mem.objects)
            mem.update(dets, fid)
            # count re-sightings (object list grows or an existing one updated this frame)
            for o in mem.objects:
                key = id(o)
                seen[key] = seen.get(key, 0) + (1 if o["frame"] == fid else 0)

            prev = FrameState(frame_id=fid, timestamp=fid / CAMERA.fps, image=bgr,
                              depth_map=depth, keypoints=kps, descriptors=descs,
                              pose_c2w=pose.copy())
            fid += 1
            pbar.update(1)
        pbar.close()
        cap.release()

        # keep stable objects, Y-flip to match the cloud, round
        objs = []
        for o in mem.objects:
            if seen.get(id(o), 0) < MIN_SEEN:
                continue
            p = o["pos"]
            objs.append({
                "name": o["name"],
                "x": round(float(p[0]), 3),
                "y": round(float(-p[1]), 3),   # Y-flip to match saved cloud
                "z": round(float(p[2]), 3),
                "dist": round(float(o["dist"]), 2) if o.get("dist") else None,
            })
        # cap: keep the most-seen
        objs = objs[:MAX_PER_SCENE]
        scene_objects[sid] = objs
        all_objs.extend(objs)
        print(f"  -> {len(objs)} objects ({', '.join(sorted({o['name'] for o in objs}))})")

    scene_objects["merged"] = all_objs[:MAX_PER_SCENE * 2]

    out = OUTPUT_DIR / "objects.json"
    out.write_text(json.dumps(scene_objects, indent=1), encoding="utf-8")
    print(f"\nWrote {out}  ({sum(len(v) for v in scene_objects.values())} total markers)")


if __name__ == "__main__":
    main()
