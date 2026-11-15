"""Hình minh họa từng bước giải thích ILP cho bản nộp hwmaj_ilp6t.

Chạy từ thư mục gốc dự án:
    python tools/draw_ilp6t_explain.py

Đầu ra trong docs/figures/:
    fig10_ilp_variables.png : biến f_{s,c} của nghiệm nguyên và của nghiệm nới lỏng (LP)
    fig11_ilp_bound.png     : cận dưới LP so với nghiệm nguyên
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pulp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hwmaj_ilp as H  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"
OUT = os.path.join(ROOT, "docs", "figures")
W, S = H.W, 6
COLS = list(range(W - 1, 2, -1))  # cột 15 bên trái, cột 3 bên phải (giống Hình 1)


def build(cat):
    prob = pulp.LpProblem("hwmaj", pulp.LpMinimize)
    f = {(s, c): pulp.LpVariable(f"f_{s}_{c}", 0, None, cat) for s in range(S) for c in range(W)}
    h = {(s, c): pulp.LpVariable(f"h_{s}_{c}", 0, None, cat) for s in range(S) for c in range(W)}
    Hh = {(s, c): pulp.LpVariable(f"H_{s}_{c}", 0, None, cat) for s in range(S + 1) for c in range(W)}
    prob += pulp.lpSum(1.0 * f[k] + 0.6 * h[k] for k in f)
    for c in range(W):
        prob += Hh[(0, c)] == H.heights[c]
        prob += Hh[(S, c)] <= 2
    for s in range(S):
        for c in range(W):
            prob += 3 * f[(s, c)] + 2 * h[(s, c)] <= Hh[(s, c)]
            cin = (f[(s, c - 1)] + h[(s, c - 1)]) if c > 0 else 0
            prob += Hh[(s + 1, c)] == Hh[(s, c)] - 2 * f[(s, c)] - h[(s, c)] + cin
    prob.solve(pulp.HiGHS(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal"
    fv = np.array([[f[(s, c)].value() for c in COLS] for s in range(S)])
    hv = np.array([[h[(s, c)].value() for c in COLS] for s in range(S)])
    return pulp.value(prob.objective), fv, hv


# nghiệm nguyên (từ solver chính) và nghiệm nới lỏng
int_fa, int_ha = H.solve(S)
int_f = np.array([[int_fa[s][c] for c in COLS] for s in range(S)], dtype=float)
int_h = np.array([[int_ha[s][c] for c in COLS] for s in range(S)], dtype=float)
int_cost = 1.0 * int_f.sum() + 0.6 * int_h.sum()

lp_cost, lp_f, lp_h = build("Continuous")
n_frac = int(np.sum(np.abs(lp_f - np.round(lp_f)) > 1e-6) + np.sum(np.abs(lp_h - np.round(lp_h)) > 1e-6))
print(f"nghiệm nguyên: chi phí {int_cost:.2f}, FA {int_f.sum():.0f}, HA {int_h.sum():.0f}")
print(f"nghiệm LP: chi phí {lp_cost:.2f}, FA {lp_f.sum():.3f}, HA {lp_h.sum():.3f}, giá trị thập phân {n_frac}")


def heat(ax, mat, title, fmt):
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=3, aspect="auto")
    for s in range(S):
        for j in range(len(COLS)):
            v = mat[s, j]
            if v > 1e-6:
                ax.text(j, s, fmt(v), ha="center", va="center", fontsize=8,
                        color="white" if v > 1.8 else "black")
    ax.set_xticks(range(len(COLS)))
    ax.set_xticklabels(COLS, fontsize=8)
    ax.set_yticks(range(S))
    ax.set_yticklabels([f"tầng {s + 1}" for s in range(S)], fontsize=9)
    ax.set_xlabel("cột (15 bên trái, 3 bên phải)")
    ax.set_title(title, fontsize=11)
    return im


# ---------- Hình 10: biến f_{s,c} ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.6))
heat(a1, int_f, f"Nghiệm nguyên: f (số FA), tổng {int_f.sum():.0f} FA, {int_h.sum():.0f} HA", lambda v: f"{v:.0f}")
im = heat(a2, lp_f, f"Nghiệm nới lỏng (LP): f, tổng {lp_f.sum():.2f} FA", lambda v: f"{v:.2f}")
fig.colorbar(im, ax=[a1, a2], shrink=0.8, label="số FA ở ô (tầng, cột)")
fig.suptitle("Hình 10. Biến quyết định f_{s,c}: ô trống là 0. Nghiệm nới lỏng có giá trị thập phân.",
             fontsize=12)
plt.savefig(os.path.join(OUT, "fig10_ilp_variables.png"), dpi=130, bbox_inches="tight")
plt.close(fig)

# ---------- Hình 11: cận dưới LP so với nghiệm nguyên ----------
fig, ax = plt.subplots(figsize=(9, 5.4))
labels = ["Cận dưới LP\n(bỏ điều kiện nguyên)", "Nghiệm nguyên\n(lời giải của bạn)"]
vals = [lp_cost, int_cost]
bars = ax.bar(labels, vals, color=["#7fb3f0", "#3b7dd8"], width=0.5)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}", ha="center", fontsize=13)
ax.set_ylim(0, 36)
ax.set_ylabel("chi phí = 1.0·FA + 0.6·HA")
ax.axhline(29, color="#c0392b", ls="--", lw=1)
ax.set_title("Hình 11. Cận dưới bằng nghiệm nguyên: 29 là tối ưu", fontsize=12)
ax.text(0.5, 32.5, "Với bài toán cực tiểu: cận dưới ≤ mọi nghiệm nguyên.\n"
                "Nghiệm nguyên đạt cận dưới, nên không thể tốt hơn.",
        ha="center", fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig11_ilp_bound.png"), dpi=130)
plt.close(fig)
print("saved fig10, fig11")
