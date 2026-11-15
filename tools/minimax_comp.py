"""Minimax choice of the compensation table g(ma, mb) for hw_maj_s64 over a family of input distributions.
comp = 64*g + 40*nz. Error for every case: err = comp - T, T = truncated sum of cols 0..5 (zero-bypass is automatic)."""
import itertools
import numpy as np

rng = np.random.default_rng(1)
N = 65536
U = rng.integers(-128, 128, (N, 2))
def clip8(x): return np.clip(np.round(x), -128, 127).astype(int)
dists = {
    "uniform": (U[:, 0], U[:, 1]),
    "relu_gauss": (np.clip(clip8(rng.normal(0, 30, N)), 0, 127), clip8(rng.normal(0, 30, N))),
    "laplace10": (clip8(rng.laplace(0, 10, N)), clip8(rng.laplace(0, 10, N))),
    "laplace30": (clip8(rng.laplace(0, 30, N)), clip8(rng.laplace(0, 30, N))),
    "laplace60": (clip8(rng.laplace(0, 60, N)), clip8(rng.laplace(0, 60, N))),
}

def feats(a, b):
    ua, ub = a & 255, b & 255
    ab = [(ua >> i) & 1 for i in range(8)]
    bb = [(ub >> i) & 1 for i in range(8)]
    maj = lambda x, y, z: (x & y) | (x & z) | (y & z)
    ma = maj(ab[0], ab[1], ab[2]) + maj(ab[3], ab[4], ab[5])
    mb = maj(bb[0], bb[1], bb[2]) + maj(bb[3], bb[4], bb[5])
    nz = ((ua & 63) != 0) & ((ub & 63) != 0)
    T = sum((ab[i] & bb[j]) << (i + j) for i in range(6) for j in range(6) if i + j < 6)
    return nz.astype(int), ma, mb, T

# per distribution, per class (nz=1, ma, mb), mean |err| for each g in 0..3 (err = 64g + 40 - T)
classes = [(ma, mb) for ma in range(3) for mb in range(3)]
tab = {}
for name, (a, b) in dists.items():
    nz, ma, mb, T = feats(a, b)
    w = {}
    for (x, y) in classes:
        m = (nz == 1) & (ma == x) & (mb == y)
        w[(x, y)] = m.sum() / N
        tab[(name, x, y)] = [np.abs(64 * g + 40 - T[m]).mean() if m.sum() else 0.0 for g in range(4)]
    # class nz=0: comp=0 always, error = -T (should be 0 there)
    m0 = nz == 0
    tab[(name, "nz0")] = np.abs(T[m0]).mean() if m0.sum() else 0.0
    tab[(name, "w")] = w

HW = {(0, 0): 0, (1, 1): 1, (1, 2): 1, (2, 1): 1, (2, 2): 2}  # g>0 entries of hw_maj_s64

def mae_dist(name, gmap):
    w = tab[(name, "w")]
    base = tab[(name, "nz0")] * (1 - sum(w.values()))
    return base + sum(w[c] * tab[(name, c[0], c[1])][gmap[c]] for c in classes)

hw_map = {c: HW.get(c, 0) for c in classes}
print("hw_maj_s64 table:")
hw_res = {d: mae_dist(d, hw_map) for d in dists}
for d, v in hw_res.items():
    print(f"  {d:<11} MAE={v:7.3f}")
print(f"  worst={max(hw_res.values()):.3f}  mean={np.mean(list(hw_res.values())):.3f}")

best = None
for combo in itertools.product(range(4), repeat=len(classes)):
    gm = dict(zip(classes, combo))
    res = [mae_dist(d, gm) for d in dists]
    score = max(res)
    if best is None or score < best[0]:
        best = (score, gm, res)
score, gm, res = best
print("\nminimax table (min over g of worst-case MAE):")
for c in classes:
    print(f"  (ma,mb)={c}  g={gm[c]}")
for d, v in zip(dists, res):
    print(f"  {d:<11} MAE={v:7.3f}")
print(f"  worst={score:.3f}  mean={np.mean(res):.3f}")
