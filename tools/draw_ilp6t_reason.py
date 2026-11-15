"""Hình giải thích vì sao ILP chọn 29 FA, 0 HA cho bản nộp hwmaj_ilp6t.

Chạy từ thư mục gốc dự án:
    PYTHONIOENCODING=utf-8 python tools/draw_ilp6t_reason.py

Đầu ra: docs/figures/fig18_ilp_why_fa.png
Số liệu được giải lại bằng cùng mô hình với tools/hwmaj_ilp.py.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pulp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hwmaj_ilp as H  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"
W = H.W
COLS = list(range(W - 1, 2, -1))


def solve(S, min_total=None):
    prob = pulp.LpProblem("m", pulp.LpMinimize)
    f = {(s, c): pulp.LpVariable(f"f_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S) for c in range(W)}
    h = {(s, c): pulp.LpVariable(f"h_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S) for c in range(W)}
    Hh = {(s, c): pulp.LpVariable(f"H_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S + 1) for c in range(W)}
    prob += pulp.lpSum(1.0 * f[k] + 0.6 * h[k] for k in f)
    for c in range(W):
        prob += Hh[(0, c)] == H.heights[c]
        prob += Hh[(S, c)] <= 2
    for s in range(S):
        for c in range(W):
            prob += 3 * f[(s, c)] + 2 * h[(s, c)] <= Hh[(s, c)]
            cin = (f[(s, c - 1)] + h[(s, c - 1)]) if c > 0 else 0
            prob += Hh[(s + 1, c)] == Hh[(s, c)] - 2 * f[(s, c)] - h[(s, c)] + cin
    if min_total:
        prob += pulp.lpSum(Hh[(S, c)] for c in range(W)) >= min_total
    st = prob.solve(pulp.HiGHS(msg=False))
    if pulp.LpStatus[st] != "Optimal":
        return None
    nf = sum(int(round(v.value())) for v in f.values())
    nh = sum(int(round(v.value())) for v in h.values())
    final = [int(round(Hh[(S, c)].value())) for c in range(W)]
    return pulp.value(prob.objective), nf, nh, final


base = solve(6)
assert base[1] == 29 and base[2] == 0
costs = {S: solve(S) for S in range(2, 10)}
alt = solve(6, min_total=22)
print("S -> chi phí:", {S: (None if v is None else round(v[0], 2)) for S, v in costs.items()})
print("ép 22 bit cuối:", alt[:3])

fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))

# (a) đếm bit: số bit cuối từng cột
ax = axes[0]
final = [base[3][c] for c in COLS]
ax.bar(range(len(COLS)), final, color="#3b7dd8")
for i, v in enumerate(final):
    ax.text(i, v + 0.05, str(v), ha="center", fontsize=9)
ax.axhline(2, color="#c0392b", ls="--", lw=1)
ax.set_xticks(range(len(COLS)))
ax.set_xticklabels(COLS, fontsize=8)
ax.set_xlabel("cột (15 bên trái, 3 bên phải)")
ax.set_ylabel("số bit còn lại sau tầng 6")
ax.set_ylim(0, 3.2)
ax.set_title("(a) 50 bit - 29 FA = 21 bit cuối\nMỗi FA bớt đúng 1 bit, HA bớt 0 bit", fontsize=11)

# (b) chi phí tối ưu theo số tầng
ax = axes[1]
xs = list(costs)
vals = [0 if v is None else v[0] for v in costs.values()]
cols_ = ["#c0392b" if v is None else "#3b7dd8" for v in costs.values()]
ax.bar(xs, [29 if v is None else v for v in vals], color=cols_)
for s, v in zip(xs, costs.values()):
    ax.text(s, 29.4, "vô\nnghiệm" if v is None else f"{v[0]:.0f}", ha="center",
            fontsize=8 if v is None else 9, color="black")
ax.set_ylim(0, 33)
ax.set_xticks(xs)
ax.set_xlabel("số tầng S cho phép")
ax.set_ylabel("chi phí tối ưu")
ax.set_title("(b) Từ 4 tầng trở lên, chi phí tối ưu luôn là 29\nS = 2, 3 không đạt đích", fontsize=11)

# (c) FA thuần so với thêm HA để giữ 22 bit
ax = axes[2]
labels = ["29 FA, 0 HA\n(lời giải)", f"{alt[1]} FA, {alt[2]} HA\n(ép giữ 22 bit)"]
vals = [base[0], alt[0]]
ax.bar(labels, vals, color=["#3b7dd8", "#e0a040"], width=0.5)
for i, v in enumerate(vals):
    ax.text(i, v + 0.1, f"{v:.1f}", ha="center", fontsize=12)
ax.set_ylim(0, 35)
ax.text(1, 31.6, "+0.8", ha="center", fontsize=11, color="#c0392b")
ax.set_ylabel("chi phí 1.0·FA + 0.6·HA")
ax.set_title("(c) Giảm 1 FA nhưng phải thêm HA: đắt hơn", fontsize=11)

fig.suptitle("Hình 18. Vì sao ILP chọn toàn FA và đúng 29 bộ", fontsize=14)
plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig(os.path.join(ROOT, "docs", "figures", "fig18_ilp_why_fa.png"), dpi=130)
plt.close(fig)
print("saved fig18")
