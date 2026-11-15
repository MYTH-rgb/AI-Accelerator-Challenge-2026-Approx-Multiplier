"""Hình minh họa ILP cho bản nộp hwmaj_ilp6t (cùng ma trận bit, cùng lời giải với asic/rtl/hwmaj_ilp6t_asic.v).

Chạy từ thư mục gốc dự án:
    python tools/draw_ilp6t_steps.py

Đầu ra trong docs/figures/:
    fig07_ilp6t_stages.png     : chồng bit từng cột qua 6 tầng (lời giải ILP)
    fig08_ilp6t_column_check.png : kiểm tay công thức chiều cao ở tầng 1
    fig09_ilp_region_example.png : ví dụ 2 biến để thấy solver làm gì
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hwmaj_ilp as H  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"
OUT = os.path.join(ROOT, "docs", "figures")
os.makedirs(OUT, exist_ok=True)

W = H.W
S = 6
fa, ha = H.solve(S)

# Chiều cao cột trước mỗi tầng: Hs[s][c], s = 0..S
Hs = np.zeros((S + 1, W), dtype=int)
Hs[0] = H.heights
for s in range(S):
    for c in range(W):
        cin = (fa[s][c - 1] + ha[s][c - 1]) if c > 0 else 0
        Hs[s + 1][c] = Hs[s][c] - 2 * fa[s][c] - ha[s][c] + cin
assert Hs[S].max() <= 2, "lời giải không đạt đích"
assert sum(map(sum, fa)) == 29 and sum(map(sum, ha)) == 0
assert Hs[0].sum() - sum(map(sum, fa)) == Hs[S].sum() == 21

COLS = list(range(W - 1, 2, -1))  # cột 15 bên trái, cột 3 bên phải (giống Hình 1); cột 0..2 không có bit
KIND_COLOR = {"and": "#3b7dd8", "nand": "#7fb3f0", "sig": "#e0a040", "const": "#9b9b9b"}
BIT_COLOR = "#3b7dd8"


def stage_text(s):
    parts = []
    for c in COLS:
        n = fa[s - 1][c] + ha[s - 1][c]
        if n:
            parts.append(f"c{c}:{fa[s - 1][c]}FA" + (f"+{ha[s - 1][c]}HA" if ha[s - 1][c] else ""))
    return "Tầng %d dùng: " % s + "  ".join(parts)


# ---------------- Hình 7: chồng bit qua 6 tầng ----------------
fig, axes = plt.subplots(2, 4, figsize=(17, 9))
axes = axes.ravel()
for s in range(S + 1):
    ax = axes[s]
    for xi, c in enumerate(COLS):
        for k in range(Hs[s][c]):
            color = KIND_COLOR[H.bits[c][k][0]] if s == 0 else BIT_COLOR
            ax.add_patch(plt.Circle((xi, k), 0.34, color=color, ec="black", lw=0.4))
        if Hs[s][c]:
            ax.text(xi, -0.9, str(c), ha="center", fontsize=8)
    ax.axhline(1.5, color="#c0392b", ls="--", lw=1)  # đích: tối đa 2 bit (k = 0, 1)
    ax.set_xlim(-0.8, len(COLS) - 0.2)
    ax.set_ylim(-1.4, 10.4)
    ax.set_aspect("equal")
    ax.axis("off")
    total = int(Hs[s].sum())
    title = "Ban đầu: %d bit" % total if s == 0 else "Sau tầng %d: %d bit" % (s, total)
    ax.set_title(title, fontsize=12)
    if s > 0:
        ax.text(0, -2.1, stage_text(s), fontsize=7.2, va="top")

ax = axes[S + 1]
ax.axis("off")
legend = (
    "CÁCH ĐỌC HÌNH\n\n"
    "Mỗi chấm là một bit. Một cột = một chồng bit.\n"
    "Số dưới mỗi cột là chỉ số cột (cột 15 bên trái,\n"
    "cột 3 bên phải, giống Hình 1).\n"
    "Đường đỏ đứt: đích, tối đa 2 bit mỗi cột.\n\n"
    "Ban đầu: xanh dương = tích riêng phần,\n"
    "vàng = bit bù g và nz, xám nhạt = hằng số.\n\n"
    "Mỗi FA: lấy 3 bit ở cột c, trả 1 bit ở cột c\n"
    "và 1 nhớ sang cột c+1 (tổng bit giảm 1).\n"
    "Dòng \"Tầng s dùng\" ghi số FA mà solver chọn.\n\n"
    "Tổng: 29 FA, 0 HA. Đây là lời giải tối ưu\n"
    "của mô hình ILP, khớp RTL."
)
ax.text(0, 1, legend, va="top", fontsize=10, family="DejaVu Sans")
fig.suptitle("Hình 7. Lời giải ILP cho bản nộp hwmaj_ilp6t: 6 tầng, 29 FA, 0 HA", fontsize=14)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(OUT, "fig07_ilp6t_stages.png"), dpi=130)
plt.close(fig)

# ---------------- Hình 8: kiểm tay tầng 1 ----------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.2), gridspec_kw={"width_ratios": [1.2, 1]})
show = [6, 7, 8, 9, 10]
x = np.arange(len(show))
ax1.bar(x - 0.2, [Hs[0][c] for c in show], width=0.4, color="#9b9b9b", label="H₀: trước tầng 1")
ax1.bar(x + 0.2, [Hs[1][c] for c in show], width=0.4, color=BIT_COLOR, label="H₁: sau tầng 1")
for i, c in enumerate(show):
    ax1.text(i + 0.2, Hs[1][c] + 0.15, str(Hs[1][c]), ha="center", fontsize=10)
    ax1.text(i - 0.2, Hs[0][c] + 0.15, str(Hs[0][c]), ha="center", fontsize=10)
ax1.axhline(2, color="#c0392b", ls="--", lw=1)
ax1.set_xticks(x)
ax1.set_xticklabels([f"cột {c}" for c in show])
ax1.set_ylabel("số bit trong cột")
ax1.set_title("Chiều cao cột trước và sau tầng 1", fontsize=12)
ax1.legend(fontsize=9)

ax2.axis("off")
lines = [
    "KIỂM TAY (tầng 1, từ lời giải solver)",
    "",
    r"$H_{1,c} = H_{0,c} - 2 f_{0,c} - h_{0,c} + (f_{0,c-1} + h_{0,c-1})$",
    "",
    r"Cột 7: $f_{0,7}=2$, nhớ từ cột 6 là $0$",
    r"   $H_{1,7} = 9 - 2\cdot 2 - 0 + 0 = 5$",
    "",
    r"Cột 8: $f_{0,8}=1$, nhớ từ cột 7 là $2$",
    r"   $H_{1,8} = 9 - 2\cdot 1 - 0 + 2 = 9$",
    "",
    r"Cột 9: $f_{0,9}=0$, nhớ từ cột 8 là $1$",
    r"   $H_{1,9} = 6 - 0 - 0 + 1 = 7$",
    "",
    r"Cột 10: $f_{0,10}=1$, nhớ từ cột 9 là $0$",
    r"   $H_{1,10} = 5 - 2\cdot 1 - 0 + 0 = 3$",
    "",
    "Ràng buộc không dùng quá số bit có:",
    r"   $3 f_{0,c} + 2 h_{0,c} \leq H_{0,c}$",
    "   cột 7: 3·2 = 6 ≤ 9 ✓ ; cột 8: 3·1 = 3 ≤ 9 ✓",
]
ax2.text(0, 1, "\n".join(lines), va="top", fontsize=11)
fig.suptitle("Hình 8. Kiểm tay công thức chiều cao ở tầng 1 (khớp đầu ra solver)", fontsize=13)
plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig(os.path.join(OUT, "fig08_ilp6t_column_check.png"), dpi=130)
plt.close(fig)

# ---------------- Hình 9: ví dụ solver trên 2 biến ----------------
# Một cột 5 bit, cần đưa về tối đa 2 bit trong một tầng (cùng dạng ràng buộc với bản nộp):
#   3f + 2h <= 5      (đủ bit để rút)
#   2f + h >= 3       (còn tối đa 2 bit: 5 - 2f - h <= 2)
#   chi phí 1.0 f + 0.6 h
fig, ax = plt.subplots(figsize=(8.5, 6.5))
fs = np.linspace(0, 2.2, 400)
# miền nới lỏng: 3f+2h<=5 và 2f+h>=3, f,h>=0
hA = (5 - 3 * fs) / 2  # biên trên của 3f+2h<=5
hB = 3 - 2 * fs  # biên dưới của 2f+h>=3
upper = np.minimum(hA, 10)
mask = (hA >= 0) & (np.maximum(hB, 0) <= upper)
ax.fill_between(fs[mask], np.maximum(hB, 0)[mask], upper[mask], color="#7fb3f0", alpha=0.5,
                label="miền nới lỏng (f, h thập phân)")
ax.plot(fs, hA, color="#3b7dd8", lw=1.5)
ax.plot(fs, np.maximum(hB, 0), color="#e0a040", lw=1.5)
ax.text(0.05, 2.45, "3f + 2h ≤ 5", color="#3b7dd8", fontsize=10)
ax.text(1.55, 1.45, "2f + h ≥ 3", color="#c08000", fontsize=10, rotation=-30)

# điểm nguyên trong miền
for f_ in range(0, 3):
    for h_ in range(0, 4):
        ok_a = 3 * f_ + 2 * h_ <= 5
        ok_b = 2 * f_ + h_ >= 3
        if ok_a and ok_b:
            ax.scatter(f_, h_, s=260, color="#2e8b57", zorder=5, label="điểm nguyên hợp lệ")
            ax.annotate(f"(1, 1): chi phí 1.6", (f_, h_), xytext=(1.25, 2.5), fontsize=10,
                        arrowprops=dict(arrowstyle="->"))
        elif ok_a or ok_b:
            ax.scatter(f_, h_, s=60, color="#9b9b9b", zorder=4)
        else:
            ax.scatter(f_, h_, s=60, color="#9b9b9b", zorder=4)
# đỉnh LP tối ưu (f = 1.5, h = 0): chi phí 1.5 < 1.6 nhưng không nguyên
ax.scatter(1.5, 0, s=160, marker="x", color="#c0392b", zorder=6)
ax.annotate("nghiệm LP: (1.5, 0), chi phí 1.5\nkhông nguyên", (1.5, 0), xytext=(1.9, 0.5), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="#c0392b"))
ax.set_xlim(-0.2, 2.4)
ax.set_ylim(-0.3, 3.4)
ax.set_xlabel("f = số FA")
ax.set_ylabel("h = số HA")
ax.set_xticks([0, 1, 2])
ax.set_yticks([0, 1, 2, 3])
ax.grid(alpha=0.3)
ax.set_title("Hình 9. Solver: nới lỏng rồi ép về số nguyên\n(ví dụ 1 cột 5 bit, cùng dạng ràng buộc với bản nộp)",
             fontsize=11)
handles, labels = ax.get_legend_handles_labels()
seen = {}
for hd, lb in zip(handles, labels):
    seen.setdefault(lb, hd)
ax.legend(seen.values(), seen.keys(), fontsize=8, loc="upper right")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig09_ilp_region_example.png"), dpi=130)
plt.close(fig)

print("fa per stage:", [int(sum(fa[s])) for s in range(S)], "total", sum(map(sum, fa)))
print("heights per stage max:", [int(Hs[s].max()) for s in range(S + 1)])
print("saved fig07, fig08, fig09 to", OUT)
