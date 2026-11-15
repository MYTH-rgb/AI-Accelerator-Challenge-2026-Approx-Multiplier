import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doc_numbers import img0, W, tcut, maj3, TAB
import numpy as np
def show(a, b, tag):
    ua, ub = a & 255, b & 255
    T, ab, bb = tcut(ua, ub, 5)
    ma = maj3(ab,0,1,2) + maj3(ab,3,4,5); mb = maj3(bb,0,1,2) + maj3(bb,3,4,5)
    nz = int(((ua & 63) != 0) and ((ub & 63) != 0))
    g = TAB.get((int(ma), int(mb)), 0) if nz else 0
    comp = 64 * g + 40 * nz
    print(f"== {tag}: a={a} (bits {ua:08b}), b={b} (bits {ub:08b})")
    print(f"exact a*b={a*b}  T(cut i+j<=5)={T}  ma={ma} mb={mb} nz={nz} g={g} comp={comp}")
    print(f"approx = a*b - T + comp = {a*b - T + comp}   error = {comp - T}")
    return ab, bb
# candidates from real data
cands = [(int(p), int(w)) for p in img0 for w in W if p>0]
pix_mid = [int(p) for p in img0 if 40 <= p <= 90 and p>0][:3]
print("pixel values in img0 (nonzero, first 15):", [int(p) for p in img0 if p>0][:15])
print("weights:", W)
print("low6-zero pixels:", sorted(set(int(p) for p in img0 if p>0 and (int(p)&63)==0))[:5])
print("kernel 0 weights:", W[:9])
show(45, -51, "EX1 pixel 45 x weight -51")
show(64, -51, "EX2 pixel 64 (low 6 bits zero) -> nz=0")
show(127, -127, "EX3 max pixel x min weight")
