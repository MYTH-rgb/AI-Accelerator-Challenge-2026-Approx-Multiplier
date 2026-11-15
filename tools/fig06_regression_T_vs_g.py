"""Tạo fig06_regression_T_vs_g.png: hồi quy T theo g trên các cặp (a, b) có nz = 1.

Chạy từ thư mục gốc dự án:
    python tools/fig06_regression_T_vs_g.py

Đầu ra: docs/figures/fig06_regression_T_vs_g.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures" / "fig06_regression_T_vs_g.png"


def maj(x, y, z):
    return (x & y) | (x & z) | (y & z)


G, T, CL = [], [], []
for a in range(-128, 128):
    for b in range(-128, 128):
        ua, ub = a & 255, b & 255
        A = [(ua >> i) & 1 for i in range(8)]
        B = [(ub >> i) & 1 for i in range(8)]
        ma = maj(A[0], A[1], A[2]) + maj(A[3], A[4], A[5])
        mb = maj(B[0], B[1], B[2]) + maj(B[3], B[4], B[5])
        if not ((a & 63) and (b & 63)):  # chỉ lấy nz = 1
            continue
        t = sum((1 << (i + j)) * A[i] * B[j] for i in range(6) for j in range(6) if i + j <= 5)
        G.append(min(ma, mb))
        T.append(t)
        CL.append((ma, mb))

G = np.array(G, float)
T = np.array(T, float)
c1, c0 = np.polyfit(G, T, 1)
r2 = 1 - ((T - (c0 + c1 * G)) ** 2).sum() / ((T - T.mean()) ** 2).sum()
print(f"n = {len(T)}, T ~ {c0:.2f} + {c1:.2f}*g, R2 = {r2:.3f}")

cm = {}
for c in sorted(set(CL)):
    idx = [k for k, x in enumerate(CL) if x == c]
    cm[c] = (min(c), T[idx].mean(), len(idx))

fig, ax = plt.subplots(figsize=(9, 5.6), dpi=150)
rng = np.random.default_rng(0)
for c, (g, mt, cnt) in cm.items():
    ax.scatter(
        g + rng.uniform(-0.07, 0.07), mt, s=20 + cnt / 400,
        color="#2a78d6" if g > 0 else "#888780",
        edgecolor="black", linewidth=0.5, zorder=3,
    )
xs = np.linspace(-0.3, 2.3, 50)
ax.plot(xs, c0 + c1 * xs, color="#2a78d6", lw=2,
        label=f"Hồi quy: T ≈ {c0:.1f} + {c1:.1f}·g  (R² = {r2:.2f})")
ax.plot(xs, 40 + 64 * xs, color="#eb6834", lw=2, ls="--",
        label="Bù của bản nộp: comp = 40 + 64·g")
ax.set_xticks([0, 1, 2])
ax.set_xlabel("g = min(ma, mb)  (chỉ tính khi nz = 1)")
ax.set_ylabel("T (trung bình theo lớp)")
ax.set_title(f"Hồi quy T theo g: {len(T):,} cặp có nz = 1 (96.9% trong 65,536 cặp)")
ax.grid(alpha=0.3)
ax.legend(loc="upper left", fontsize=9)
ax.set_xlim(-0.3, 2.3)
ax.set_ylim(-5, 200)
ax.text(2.25, 8, "Điểm = trung bình T từng lớp (ma,mb); cỡ điểm ∝ số cặp",
        ha="right", fontsize=8, color="#444441")
plt.tight_layout()
OUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT)
print(f"saved {OUT}")
