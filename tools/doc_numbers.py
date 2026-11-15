"""Compute every number used in docs/Giai_thich_bo_nhan_hwmaj_ilp6t.md (single source)."""
import glob, os, re, json, math
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "docs", "Training2", "ASIC", "MNIST_Images")
ROM = os.path.join(ROOT, "build", "work_sim", "cnn_dadda", "conv2d_kernel_rom.v")

# --- weights (signed) and pixels
rw = re.findall(r"\b\d+'d(\d+)\s*:\s*data\s*=\s*(-?)\s*8'sd(\d+);", open(ROM, encoding="utf-8", errors="replace").read())
W = [(-1 if s == "-" else 1) * int(v) for _, s, v in sorted(rw, key=lambda r: int(r[0]))]
files = sorted(glob.glob(os.path.join(IMG, "image_*_bin.txt")))
img0 = np.array([int(l.strip(), 2) for l in open(files[0]) if l.strip()])
allpix = np.concatenate([np.array([int(l.strip(), 2) for l in open(f) if l.strip()]) for f in files[:200]])
print("pixel max (img0)", img0.max(), "n", len(img0), "| all200 max", allpix.max(), "zero frac", round(float((allpix == 0).mean()), 3))
print("weights n", len(W), "min", min(W), "max", max(W), "| first 9 (kernel 0):", W[:9])

# --- models (vectorised, signed a,b in [-128,127])
def tcut(ua, ub, kmax):
    ab = [(ua >> i) & 1 for i in range(8)]; bb = [(ub >> i) & 1 for i in range(8)]
    return sum((ab[i] & bb[j]) << (i + j) for i in range(8) for j in range(8) if i + j <= kmax), ab, bb
TAB = {(1, 1): 1, (1, 2): 1, (2, 1): 1, (2, 2): 2}
def maj3(x, i, j, k): return (x[i] & x[j]) | (x[i] & x[k]) | (x[j] & x[k])
def hwmaj_err(a, b):
    ua, ub = a & 255, b & 255
    T, ab, bb = tcut(ua, ub, 5)
    ma = maj3(ab, 0, 1, 2) + maj3(ab, 3, 4, 5)
    mb = maj3(bb, 0, 1, 2) + maj3(bb, 3, 4, 5)
    nz = ((ua & 63) != 0) & ((ub & 63) != 0)
    g = np.zeros_like(T)
    for (x, y), v in TAB.items(): g = np.where((ma == x) & (mb == y) & nz, v, g)
    comp = 64 * g + 40 * nz
    return comp - T
def cand2_err(a, b):
    ua, ub = a & 255, b & 255
    T, _, _ = tcut(ua, ub, 5)
    e = 81 - T
    return np.where((a == 0) | (b == 0), 0, e)
A, B = [x.ravel() for x in np.meshgrid(np.arange(-128, 128), np.arange(-128, 128), indexing="ij")]
eh = hwmaj_err(A, B); ec = cand2_err(A, B)
print("UNIFORM 65536: hwmaj MAE", round(np.abs(eh).mean(), 2), "ME", round(eh.mean(), 4), "min", eh.min(), "max", eh.max(), "exact", int((eh == 0).sum()))
print("UNIFORM 65536: cand2 MAE", round(np.abs(ec).mean(), 2), "ME", round(ec.mean(), 4), "min", ec.min(), "max", ec.max(), "exact", int((ec == 0).sum()))

# MNIST-like distribution: pixels from 200 images x trained weights
rng = np.random.default_rng(1)
Pa = rng.choice(allpix, 200000); Pb = rng.choice(np.array(W), 200000)
print("MNIST-like: hwmaj MAE", round(np.abs(hwmaj_err(Pa, Pb)).mean(), 2), "| cand2 MAE", round(np.abs(cand2_err(Pa, Pb)).mean(), 2))

# sign test 14 vs 8 (n=22 discordant)
n, k = 22, 8
p2 = 2 * sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
print("sign test two-sided p", round(p2, 3))

# --- verify against netlist eval (tt_s6_arr = hwmaj_ilp6t)
got = {}
for line in open(os.path.join(ROOT, "build", "work_asic", "final_ilp6t", "eval.txt")):
    m = re.findall(r"(\d+)'([01]+)", line)
    if len(m) >= 3:
        x, y, u = (int(q[1], 2) for q in m[:3]); got[(x, y)] = u
mism = 0
for a, b in zip(A, B):
    pm = (a * b + hwmaj_err(np.array([a]), np.array([b]))[0]) % 65536
    if got[(int(a) & 255, int(b) & 255)] != pm: mism += 1
print("model vs netlist mismatches", mism, "/ 65536")
