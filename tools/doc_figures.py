import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import hwmaj_ilp as H
from doc_numbers import hwmaj_err, cand2_err, A, B, TAB
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 10, "figure.dpi": 130})

# ---- fig01: partial-product matrix with cut, BW and compensation
cols = {}
for i in range(8):
    for j in range(8):
        c = i + j
        kind = "nand" if (i == 7) != (j == 7) else "and"
        if i == 7 and j == 7: kind = "and"
        cols.setdefault(c, []).append((i, j, kind))
fig, ax = plt.subplots(figsize=(10, 4.6))
col_color = {"cut": "#c9c9c9", "and": "#2b6cb0", "nand": "#dd6b20"}
for c in range(16):
    items = cols.get(c, [])
    for k, (i, j, kind) in enumerate(items):
        y = k
        if c <= 5: color = col_color["cut"]
        else: color = col_color[kind]
        ax.add_patch(plt.Circle((15 - c, y), 0.32, color=color, ec="k", lw=0.4))
    for k in range(len(items), 8):
        pass
    if c in (8, 15):
        ax.add_patch(plt.Circle((15 - c, len(items)), 0.32, color="#38a169", ec="k", lw=0.4))
    if c in (3, 5, 6, 7, 8):
        ax.add_patch(plt.Circle((15 - c, len(items) + (1 if c in (8, 15) else 0)), 0.32, color="#805ad5", ec="k", lw=0.4))
ax.set_xlim(-0.8, 15.8); ax.set_ylim(-1, 10)
ax.set_xticks(range(16)); ax.set_xticklabels([str(15 - x) for x in range(16)])
ax.set_xlabel("Cột trọng số (bit 15 bên trái, bit 0 bên phải)")
ax.set_yticks([]); ax.set_aspect("equal")
for x, lab in [(15 - 5.5, "cắt 0–5"), (15 - 8, "")]:
    pass
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=col_color["cut"], label="Tích bị cắt (i+j ≤ 5)"),
                   Patch(color=col_color["and"], label="Tích AND giữ lại"),
                   Patch(color=col_color["nand"], label="NAND (Baugh-Wooley)"),
                   Patch(color="#38a169", label="Hằng Baugh-Wooley"),
                   Patch(color="#805ad5", label="Bit bù nz / g")],
          loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
ax.set_title("Hình 1. Ma trận tích riêng phần 8×8 sau Baugh-Wooley và cắt cột")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig01_pp_matrix.png")); plt.close()

# ---- fig02: majority table g(ma, mb) for nz=1
fig, ax = plt.subplots(figsize=(4.4, 4))
M = np.zeros((3, 3), int)
for (x, y), v in TAB.items(): M[x, y] = v
im = ax.imshow(M, cmap="Blues", vmin=0, vmax=2)
for x in range(3):
    for y in range(3):
        ax.text(y, x, str(M[x, y]), ha="center", va="center", fontsize=14, color="k")
ax.set_xticks(range(3)); ax.set_yticks(range(3))
ax.set_xlabel("m_b (0–2)"); ax.set_ylabel("m_a (0–2)")
ax.set_title("Hình 2. Bảng g(m_a, m_b) khi nz = 1")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig02_majority_table.png")); plt.close()

# ---- fig03: error histograms on uniform 65,536 pairs
fig, ax = plt.subplots(figsize=(7.5, 4))
bins = np.arange(-250, 120, 5)
ax.hist(ec := cand2_err(A, B), bins=bins, alpha=0.55, label="candidate2 (hằng +81)", color="#718096")
ax.hist(eh := hwmaj_err(A, B), bins=bins, alpha=0.55, label="hwmaj_ilp6t (bù động)", color="#2b6cb0")
ax.set_xlabel("Sai số = xấp xỉ − đúng"); ax.set_ylabel("Số cặp (trên 65,536)")
ax.set_yscale("log"); ax.legend(frameon=False)
ax.set_title(f"Hình 3. Phân bố sai số, 65,536 cặp: MAE {np.abs(ec).mean():.2f} → {np.abs(eh).mean():.2f}")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig03_error_hist.png")); plt.close()

# ---- fig04: column heights per ILP stage (6 stages)
fa, ha = H.solve(6)
heights = list(H.heights)
rows = [heights[:]]
for s in range(6):
    h = rows[-1]; new = [0] * 16
    for c in range(16):
        f_, h_ = fa[s][c], ha[s][c]
        cin = (fa[s][c - 1] + ha[s][c - 1]) if c > 0 else 0
        new[c] = h[c] - 2 * f_ - h_ + cin
    rows.append(new)
fig, axs = plt.subplots(1, 7, figsize=(13, 3.2), sharey=True)
for s in range(7):
    axs[s].bar(range(16), rows[s], color="#2b6cb0")
    axs[s].set_title("Đầu vào" if s == 0 else f"Sau tầng {s}", fontsize=9)
    axs[s].set_xticks(range(0, 16, 3)); axs[s].axhline(2, color="#dd6b20", ls="--", lw=1)
axs[0].set_ylabel("Số bit trong cột")
fig.suptitle("Hình 4. Chiều cao cột qua 6 tầng ILP (đường cam: đích ≤ 2)")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig04_ilp_heights.png")); plt.close()
print("heights per stage (max):", [max(r) for r in rows], "| FA per stage:", [sum(x) for x in fa], "| total FA", sum(map(sum, fa)))

# ---- fig05: PPA vs error (measured numbers only)
pts = [("candidate2", 2745.386, 41.24, "#718096"), ("cand2 + ILP5", 2746.982, 41.24, "#a0aec0"),
       ("hwmaj ILP5", 2891.154, 27.29, "#2c5282"), ("hwmaj ILP6t (nộp)", 2889.824, 27.29, "#2b6cb0")]
fig, ax = plt.subplots(figsize=(6.4, 4))
for n, x, y, c in pts:
    ax.scatter(x, y, s=90, color=c); ax.annotate(n, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=9)
ax.set_xlabel("Diện tích convolution_unit (µm²)"); ax.set_ylabel("MAE (65,536 cặp)")
ax.set_title("Hình 5. Đánh đổi: diện tích tăng nhẹ, sai số giảm 34%")
ax.set_ylim(20, 46); ax.set_xlim(2730, 2910)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig05_ppa_tradeoff.png")); plt.close()
print("ok")
