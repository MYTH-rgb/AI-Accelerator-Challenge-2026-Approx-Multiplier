"""Minimax compensation table for the cut-column-6 variant.
comp = 64*g + 40*nz, g in 0..3 per class (nz=1, ma, mb in 0..2). err = comp - T6, T6 = truncated sum of cols 0..6."""
import itertools, json, os
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
    T6 = sum((ab[i] & bb[j]) << (i + j) for i in range(8) for j in range(8) if i + j <= 6)
    return nz.astype(int), ma, mb, T6


classes = [(ma, mb) for ma in range(3) for mb in range(3)]
stats = {}
for name, (a, b) in dists.items():
    nz, ma, mb, T = feats(a, b)
    w = {}
    for c in classes:
        m = (nz == 1) & (ma == c[0]) & (mb == c[1])
        w[c] = m.sum() / N
        stats[(name, c)] = [(np.abs(64 * g + 40 - T[m]).mean() if m.sum() else 0.0,
                             (64 * g + 40 - T[m]).mean() if m.sum() else 0.0) for g in range(4)]
    m0 = nz == 0
    stats[(name, "nz0")] = (np.abs(T[m0]).mean() if m0.sum() else 0.0, (-T[m0]).mean() if m0.sum() else 0.0)
    stats[(name, "w")] = w


def per_dist(name, gm):
    w = stats[(name, "w")]
    z_abs, z_sig = stats[(name, "nz0")]
    frac0 = 1 - sum(w.values())
    mae = z_abs * frac0 + sum(w[c] * stats[(name, c)][gm[c]][0] for c in classes)
    me = z_sig * frac0 + sum(w[c] * stats[(name, c)][gm[c]][1] for c in classes)
    return mae, me


# current hwcut6 table (fitted on uniform only)
cur = {(0, 0): 0, (0, 1): 0, (0, 2): 1, (1, 0): 0, (1, 1): 0, (1, 2): 1, (2, 0): 1, (2, 1): 1, (2, 2): 2}
print("current hwcut6 table (L=40):")
for n in dists:
    m, e = per_dist(n, {c: min(3, cur.get(c, 0)) for c in classes})
    print(f"  {n:<11} MAE={m:7.3f} ME={e:+8.3f}")

best = None
for combo in itertools.product(range(4), repeat=len(classes)):
    gm = dict(zip(classes, combo))
    res = [per_dist(n, gm) for n in dists]
    worst = max(r[0] for r in res)
    if best is None or worst < best[0]:
        best = (worst, gm, res)
worst, gm, res = best
print("\nminimax table (min over g of worst-case MAE):")
for c in classes:
    print(f"  (ma,mb)={c}  g={gm[c]}")
for n, (m, e) in zip(dists, res):
    print(f"  {n:<11} MAE={m:7.3f} ME={e:+8.3f}")
print(f"  worst MAE={worst:.3f}")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cut6_table.json")
json.dump({f"{a},{b}": gm[(a, b)] for a, b in classes}, open(out, "w"))
print("saved", out)
