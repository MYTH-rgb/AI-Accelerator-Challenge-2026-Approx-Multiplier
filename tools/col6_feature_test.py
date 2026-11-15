"""Does info from column 6 partial products (kept, already in the tree) improve compensation of the cut 0..5 truncation?
Reference: 9 classes (ma,mb) x nz gate (hw_maj_s64 feature set). Candidates add c6 = #ones among a_i&b_(6-i), i=0..6.
Per class the MAE-optimal constant (median of T) is used -> lower bound for each feature set (no table-resolution limits)."""
import glob, os, re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "docs", "Training2", "ASIC", "MNIST_Images")
ROM = os.path.join(ROOT, "build", "work_sim", "cnn_dadda", "conv2d_kernel_rom.v")
rng = np.random.default_rng(5)
N = 300000
files = sorted(glob.glob(os.path.join(IMG, "image_*_bin.txt")))[:300]
pix = np.concatenate([np.array([int(l.strip(), 2) for l in open(f) if l.strip()]) for f in files])
rw = re.findall(r"\b\d+'d(\d+)\s*:\s*data\s*=\s*(-?)\s*8'sd(\d+);", open(ROM, encoding="utf-8", errors="replace").read())
wts = np.array([(-1 if s == "-" else 1) * int(v) for _, s, v in sorted(rw, key=lambda r: int(r[0]))])
dists = {"uniform": (rng.integers(-128, 128, N), rng.integers(-128, 128, N)),
         "mnist": (rng.choice(pix, N), rng.choice(wts, N))}


def feats(a, b):
    ua, ub = a & 255, b & 255
    ab = [(ua >> i) & 1 for i in range(8)]
    bb = [(ub >> i) & 1 for i in range(8)]
    T = sum((ab[i] & bb[j]) << (i + j) for i in range(8) for j in range(8) if i + j <= 5)
    maj = lambda x, i, j, k: ((x[i] & x[j]) | (x[i] & x[k]) | (x[j] & x[k]))
    ma = maj(ab, 0, 1, 2) + maj(ab, 3, 4, 5)
    mb = maj(bb, 0, 1, 2) + maj(bb, 3, 4, 5)
    nz = ((ua & 63) != 0) & ((ub & 63) != 0)
    c6 = sum(ab[i] & bb[6 - i] for i in range(7))
    c6or = np.minimum(c6, 1)
    return dict(T=T, ma=ma, mb=mb, nz=nz, c6=c6, c6l=np.minimum(c6, 2), c6or=c6or)


F = {n: feats(a, b) for n, (a, b) in dists.items()}


def mae(keyfn):
    out = {}
    for n, f in F.items():
        key = keyfn(f)
        m = f["nz"]
        comp = np.zeros_like(f["T"])
        for k in np.unique(key[m]):
            s = m & (key == k)
            comp[s] = int(np.median(f["T"][s]))
        out[n] = np.abs(comp - f["T"]).mean()
    return out


tests = {
    "ref (ma,mb) 9 classes": lambda f: f["ma"] * 10 + f["mb"],
    "(ma,mb)+c6 in {0,1,2+} 27 classes": lambda f: (f["ma"] * 10 + f["mb"]) * 10 + f["c6l"],
    "(ma,mb)+c6>0 18 classes": lambda f: (f["ma"] * 10 + f["mb"]) * 10 + f["c6or"],
    "c6 only {0,1,2+}": lambda f: f["c6l"],
    "c6 only exact 0..7": lambda f: f["c6"],
    "constant (no class)": lambda f: np.zeros_like(f["ma"]),
}
print(f"{'features':<38}" + "".join(f"{n:>10}" for n in dists))
for name, fn in tests.items():
    r = mae(fn)
    print(f"{name:<38}" + "".join(f"{r[n]:>10.2f}" for n in dists))
