"""
Rebuild output/demo_3d.html as a PER-CLIP 3D viewer (no GPU, no re-running SLAM).

Reads the existing per-video point clouds + trajectories from output/ and emits a
single self-contained Three.js viewer with a video selector (All / V1..V5).
Each clip is centered on its own centroid so it reads as one coherent scene;
"All" lays the 5 clips out in a row so they no longer overlap into a soup.

  python rebuild_3d_map.py
"""

import base64
import json
from pathlib import Path
import numpy as np

OUTPUT_DIR = Path(r"D:\mental_map_slam\output")
MAX_PER_VIDEO = 120_000          # cap embedded points per clip (perf)

# Human titles + accent color per clip (matches the pitch UI video list)
VIDEO_META = [
    (1, "Exploration — Area A", 0x00FFFF),
    (2, "Long Traverse — Area B", 0xFF44FF),
    (3, "Corridor Mapping", 0xFFCC00),
    (4, "Close-range Scan", 0x3DFFA0),
    (5, "Detail Pass", 0xFF8844),
]


# ── PLY / npy readers ────────────────────────────────────────────────────────
def read_ply(path: Path):
    """Read a binary PLY of (3×float32 xyz + 3×uint8 rgb) → (xyz Nx3 f32, rgb Nx3 u8)."""
    with open(path, "rb") as f:
        n = 0
        while True:
            line = f.readline()
            if line.startswith(b"element vertex"):
                n = int(line.split()[-1])
            if line.startswith(b"end_header"):
                break
        raw = np.frombuffer(f.read(n * 15), dtype=np.uint8).reshape(n, 15)
    xyz = raw[:, :12].copy().view(np.float32).reshape(n, 3)
    rgb = raw[:, 12:].copy()
    return xyz, rgb


def b64(arr: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode()


# ── Build per-video payloads ─────────────────────────────────────────────────
def build_videos():
    videos = []
    for num, title, color in VIDEO_META:
        cloud = OUTPUT_DIR / f"video_{num}_cloud.ply"
        if not cloud.exists():
            print(f"  skip V{num}: {cloud.name} missing")
            continue

        xyz, rgb = read_ply(cloud)

        # subsample if huge
        if len(xyz) > MAX_PER_VIDEO:
            idx = np.random.choice(len(xyz), MAX_PER_VIDEO, replace=False)
            xyz, rgb = xyz[idx], rgb[idx]

        # center on own centroid so the clip sits at local origin
        centroid = xyz.mean(axis=0)
        xyz_c = (xyz - centroid).astype(np.float32)
        extent = (xyz_c.max(axis=0) - xyz_c.min(axis=0)).astype(np.float32)

        # trajectory: raw (Y not flipped) → flip Y to match the cloud, then center
        traj_b64 = ""
        traj_path = OUTPUT_DIR / f"video_{num}_trajectory.npy"
        if traj_path.exists():
            traj = np.load(str(traj_path)).astype(np.float32)
            if traj.ndim == 2 and traj.shape[1] == 3 and len(traj) > 1:
                traj = traj.copy()
                traj[:, 1] *= -1.0
                traj = (traj - centroid).astype(np.float32)
                traj_b64 = b64(traj)

        videos.append({
            "num": num,
            "title": title,
            "color": color,
            "n": int(len(xyz_c)),
            "extent": [float(extent[0]), float(extent[1]), float(extent[2])],
            "pos": b64(xyz_c),
            "rgb": b64(rgb.astype(np.uint8)),
            "traj": traj_b64,
        })
        print(f"  V{num}: {len(xyz_c):,} pts  extent=({extent[0]:.1f},{extent[1]:.1f},{extent[2]:.1f})")
    return videos


def main():
    videos = build_videos()
    if not videos:
        print("No clips found in", OUTPUT_DIR)
        return
    html = _HTML_TEMPLATE.replace("__VIDEOS_JSON__", json.dumps(videos))
    out = OUTPUT_DIR / "demo_3d.html"
    out.write_text(html, encoding="utf-8")
    kb = out.stat().st_size // 1024
    print(f"\nWrote {out}  ({kb:,} KB)  — {len(videos)} clips")


# ── HTML / Three.js template (literal braces; placeholder = __VIDEOS_JSON__) ──
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mental Map — 3D Point Cloud</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#05050f;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;color:#cdd}
  #c{display:block}
  #hud{position:absolute;top:16px;left:16px;background:rgba(0,0,12,.78);padding:13px 17px;
    border-radius:10px;border:1px solid #223;font-size:12px;line-height:1.9;min-width:240px}
  #hud b{color:#7cf;font-size:13px}
  #hud .scene{color:#9fe7c4;font-weight:600}
  #hud .dim{color:#667;font-size:11px}
  #panel{position:absolute;bottom:16px;left:16px;background:rgba(0,0,12,.78);padding:12px 15px;
    border-radius:10px;border:1px solid #223;font-size:12px}
  .row{display:flex;align-items:center;gap:8px;margin:6px 0}
  input[type=range]{width:110px;accent-color:#7cf}
  .btn{cursor:pointer;background:#0a0a2a;border:1px solid #335;color:#acd;padding:3px 10px;
    border-radius:5px;font-size:11px}
  .btn:hover{background:#112244}
  .tog{cursor:pointer;user-select:none;padding:2px 9px;border-radius:4px;border:1px solid #335;
    font-size:11px;color:#88a}
  .tog.on{background:#113355;color:#7cf;border-color:#3a6}
  #vsel{position:absolute;top:16px;left:50%;transform:translateX(-50%);display:flex;gap:6px;
    background:rgba(0,0,12,.78);padding:7px 9px;border-radius:10px;border:1px solid #223}
  .vbtn{cursor:pointer;user-select:none;min-width:34px;text-align:center;padding:5px 11px;
    border-radius:6px;border:1px solid #335;font-size:12px;font-weight:600;color:#9ab;transition:all .12s}
  .vbtn:hover{background:#112244;color:#cde}
  .vbtn.on{background:#1b4;background:linear-gradient(160deg,#16407a,#0d2a5a);
    color:#cfe7ff;border-color:#4d9dff;box-shadow:0 0 14px rgba(77,157,255,.4)}
  #fps{position:absolute;top:16px;right:16px;font-size:11px;color:#445}
</style>
</head>
<body>
<canvas id="c"></canvas>

<div id="vsel"></div>

<div id="hud">
  <b>Mental Map — 3D Reconstruction</b><br>
  Scene &nbsp;<span class="scene" id="hScene">—</span><br>
  Points &nbsp;<span id="hPts">—</span><br>
  <span class="dim">Drag rotate · Right pan · Scroll zoom</span>
</div>

<div id="panel">
  <div class="row">Point size
    <input type="range" id="sizeSlider" min="0.005" max="0.12" step="0.005" value="0.03">
    <span id="sizeVal">0.03</span>
  </div>
  <div class="row">Color &nbsp;
    <span class="tog on"  id="togRGB"    onclick="setColor('rgb')">RGB</span>
    <span class="tog"     id="togHeight" onclick="setColor('height')">Height</span>
  </div>
  <div class="row">View &nbsp;
    <span class="tog" id="togAuto" onclick="toggleAuto()">Auto-rotate</span>
    <button class="btn" onclick="frameActive()">Reset cam</button>
  </div>
</div>

<div id="fps"></div>

<script type="importmap">
{"imports":{
  "three":"/vendor/three.module.js",
  "three/addons/":"/vendor/addons/"
}}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const VIDEOS = __VIDEOS_JSON__;

function b64F32(s){const r=atob(s),n=r.length,b=new Uint8Array(n);for(let i=0;i<n;i++)b[i]=r.charCodeAt(i);return new Float32Array(b.buffer);}
function b64U8(s){const r=atob(s),n=r.length,b=new Uint8Array(n);for(let i=0;i<n;i++)b[i]=r.charCodeAt(i);return b;}

// ── Renderer / scene ──────────────────────────────────────────────────────
const renderer=new THREE.WebGLRenderer({canvas:document.getElementById('c'),antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setSize(innerWidth,innerHeight);
const scene=new THREE.Scene();
scene.background=new THREE.Color(0x05050f);
scene.fog=new THREE.FogExp2(0x05050f,0.010);
const camera=new THREE.PerspectiveCamera(55,innerWidth/innerHeight,0.05,2000);
const controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;controls.dampingFactor=0.06;
controls.minDistance=0.5;controls.maxDistance=600;

// ── Ground grid (shared) ──────────────────────────────────────────────────
const grid=new THREE.GridHelper(120,60,0x1a1a40,0x12122e);
scene.add(grid);

// ── Height colormap (viridis-ish) from Y ──────────────────────────────────
function heightColors(pos){
  let lo=Infinity,hi=-Infinity;
  for(let i=1;i<pos.length;i+=3){const y=pos[i];if(y<lo)lo=y;if(y>hi)hi=y;}
  const span=Math.max(hi-lo,1e-6),out=new Float32Array(pos.length);
  for(let i=0;i<pos.length;i+=3){
    const t=Math.min(Math.max((pos[i+1]-lo)/span,0),1);
    out[i]  =Math.min(Math.max(t*2.5-0.5,0),1);
    out[i+1]=Math.min(Math.max(Math.sin(t*Math.PI)*1.3,0),1);
    out[i+2]=Math.min(Math.max(1.5-t*2.5,0),1);
  }
  return out;
}

// ── Build a group per clip ─────────────────────────────────────────────────
const SPACING=18;                       // row spacing in "All" mode
const groups=[];
VIDEOS.forEach((v,i)=>{
  const g=new THREE.Group();
  const pos=b64F32(v.pos);
  const rgbU8=b64U8(v.rgb);
  const rgb=new Float32Array(rgbU8.length);
  for(let k=0;k<rgbU8.length;k++)rgb[k]=rgbU8[k]/255;
  const hgt=heightColors(pos);

  const geo=new THREE.BufferGeometry();
  geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
  geo.setAttribute('color',new THREE.BufferAttribute(rgb.slice(),3));
  const mat=new THREE.PointsMaterial({vertexColors:true,size:0.03,sizeAttenuation:true});
  g.add(new THREE.Points(geo,mat));

  if(v.traj){
    const tp=b64F32(v.traj);
    const tg=new THREE.BufferGeometry();
    tg.setAttribute('position',new THREE.BufferAttribute(tp,3));
    g.add(new THREE.Line(tg,new THREE.LineBasicMaterial({color:v.color})));
    const sphere=(idx,col)=>{const m=new THREE.Mesh(new THREE.SphereGeometry(0.18,10,10),
      new THREE.MeshBasicMaterial({color:col}));m.position.set(tp[idx],tp[idx+1],tp[idx+2]);g.add(m);};
    sphere(0,0x00ff55);sphere(tp.length-3,0xff3322);
  }

  g.userData={geo,mat,rgb,hgt,meta:v,rowX:(i-(VIDEOS.length-1)/2)*SPACING};
  groups.push(g);scene.add(g);
});

// ── View state ─────────────────────────────────────────────────────────────
let active='1';            // default: first clip
let colorMode='rgb';

function applyColors(){
  groups.forEach(g=>{
    const arr=colorMode==='rgb'?g.userData.rgb:g.userData.hgt;
    g.userData.geo.attributes.color.array.set(arr);
    g.userData.geo.attributes.color.needsUpdate=true;
  });
}

function showVideo(sel){
  active=sel;
  if(sel==='all'){
    groups.forEach(g=>{g.visible=true;g.position.x=g.userData.rowX;g.position.z=0;});
  }else{
    groups.forEach(g=>{
      const on=String(g.userData.meta.num)===String(sel);
      g.visible=on;g.position.set(0,0,0);
    });
  }
  // selector highlight
  document.querySelectorAll('.vbtn').forEach(b=>b.classList.toggle('on',b.dataset.v===String(sel)));
  // HUD
  if(sel==='all'){
    const tot=VIDEOS.reduce((a,v)=>a+v.n,0);
    document.getElementById('hScene').textContent='All 5 clips (laid out in a row)';
    document.getElementById('hPts').textContent=tot.toLocaleString();
  }else{
    const v=VIDEOS.find(v=>String(v.num)===String(sel));
    document.getElementById('hScene').textContent='V'+v.num+' · '+v.title;
    document.getElementById('hPts').textContent=v.n.toLocaleString();
  }
  frameActive();
}

function frameActive(){
  let cx=0,cz=0,r=10;
  if(active==='all'){
    const span=SPACING*VIDEOS.length;r=span*0.6;
  }else{
    const v=VIDEOS.find(v=>String(v.num)===String(active));
    r=Math.max(v.extent[0],v.extent[2])*1.3+3;
  }
  controls.target.set(cx,0,cz);
  camera.position.set(cx,r*0.7,cz+r*1.15);
  controls.update();
}

// ── Selector buttons ───────────────────────────────────────────────────────
const vsel=document.getElementById('vsel');
const mkBtn=(label,val)=>{const b=document.createElement('div');b.className='vbtn';b.dataset.v=val;
  b.textContent=label;b.onclick=()=>showVideo(val);vsel.appendChild(b);};
mkBtn('All','all');
VIDEOS.forEach(v=>mkBtn('V'+v.num,String(v.num)));

// ── UI wiring ──────────────────────────────────────────────────────────────
const slider=document.getElementById('sizeSlider'),sizeVal=document.getElementById('sizeVal');
slider.addEventListener('input',e=>{const s=parseFloat(e.target.value);
  groups.forEach(g=>g.userData.mat.size=s);sizeVal.textContent=e.target.value;});

window.setColor=m=>{colorMode=m;applyColors();
  document.getElementById('togRGB').classList.toggle('on',m==='rgb');
  document.getElementById('togHeight').classList.toggle('on',m==='height');};

let autoRotate=false;
window.toggleAuto=()=>{autoRotate=!autoRotate;controls.autoRotate=autoRotate;
  controls.autoRotateSpeed=0.6;document.getElementById('togAuto').classList.toggle('on',autoRotate);};

window.frameActive=frameActive;

addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;
  camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});

// ── Init ───────────────────────────────────────────────────────────────────
showVideo('1');

let last=performance.now(),frames=0;const fpsEl=document.getElementById('fps');
(function animate(){requestAnimationFrame(animate);controls.update();
  renderer.render(scene,camera);frames++;const now=performance.now();
  if(now-last>1000){fpsEl.textContent=frames+' fps';frames=0;last=now;}})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
