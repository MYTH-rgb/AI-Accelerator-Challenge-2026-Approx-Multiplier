"""Hình để trình bày cách solver tìm ra 29 FA (dùng cho slide).

Gồm: (1) ý tưởng hình học trên ví dụ nhỏ 2 biến (minh họa, không phải số bài thật),
     (2) nghiệm nới lỏng LP thật của bản nộp (có giá trị thập phân),
     (3) nghiệm nguyên thật của bản nộp (29 FA, 0 HA),
     (4) so sánh chi phí: cận dưới 29.0 = nghiệm nguyên 29.0.

Chạy từ thư mục gốc dự án:
    PYTHONIOENCODING=utf-8 python tools/draw_ilp6t_solver_slide.py
Đầu ra: docs/figures/fig21_solver_method_slide.png
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
W, S = H.W, 6
COLS = list(range(W - 1, 2, -1))


def build_lp():
    prob = pulp.LpProblem("hwmaj_lp", pulp.LpMinimize)
    f = {(s, c): pulp.LpVariable(f"f_{s}_{c}", 0) for s in range(S) for c in range(W)}
    h = {(s, c): pulp.LpVariable(f"h_{s}_{c}", 0) for s in range(S) for c in range(W)}
    Hh = {(s, c): pulp.LpVariable(f"H_{s}_{c}", 0) for s in range(S + 1) for c in range(W)}
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
    return pulp.value(prob.objective), fv


lp_cost, lp_f = build_lp()
int_fa, int_ha = H.solve(S)
int_f = np.array([[int_fa[s][c] for c in COLS] for s in range(S)], dtype=float)
int_cost = 1.0 * int_f.sum() + 0.6 * sum(map(sum, int_ha))
n_frac = int(np.sum(np.abs(lp_f - np.round(lp_f)) > 1e-6))
print(f"LP {lp_cost:.2f} ({n_frac} ô f thập phân); nguyên {int_cost:.2f}")

fig = plt.figure(figsize=(17, 9.6))
fig.suptitle("Cách solver tìm ra 29 FA: nới lỏng, rồi tìm nghiệm nguyên cùng chi phí", fontsize=17, weight="bold", y=0.975)

# ---------- (1) miền nghiệm thật (lát cắt qua ba nghiệm thật) ----------
import ilp6t_slice as SL  # noqa: E402
ax = fig.add_axes([0.05, 0.54, 0.29, 0.34])
al_, be_, mask_, costs_ = SL.compute()
SL.draw_slice(ax, al_, be_, mask_, costs_, fontsize=8.5)
ax.set_xlabel("a: từ nghiệm nguyên sang nghiệm nới lỏng", fontsize=9)
ax.set_ylabel("b: sang nghiệm 28 FA + 3 HA", fontsize=9)
ax.set_title("Miền nghiệm thật của bài làm (lát cắt qua ba nghiệm thật)", fontsize=10.5)

# ---------- các bước bằng chữ ----------
fig.text(0.37, 0.88, "Solver làm ba việc:", fontsize=15, weight="bold", va="top")
steps = [
    ("1. Nới lỏng.", "Cho số FA, HA được là số thập phân. Miền nghiệm là một khối (vùng xanh;\n"
                       "khối thật có 304 chiều, hình là lát cắt). Đơn hình đi dọc các đỉnh, dừng ở đỉnh rẻ nhất."),
    ("2. Lấy cận dưới.", "Chi phí ở đỉnh đó là cận dưới: không nghiệm nguyên nào rẻ hơn.\n"
                         "Bài làm: đỉnh nới lỏng (dấu X đỏ) cho chi phí 29,0."),
    ("3. Tìm nghiệm nguyên.", "Tìm điểm nguyên rẻ nhất. Chấm xanh nằm cùng cạnh tối ưu với đỉnh nới lỏng,\n"
                              "cùng chi phí 29,0, nên là nghiệm tối ưu và không cần chia nhánh con."),
]
for i, (k, v) in enumerate(steps):
    y = 0.80 - i * 0.105
    fig.text(0.37, y, k, fontsize=13, weight="bold", va="top")
    fig.text(0.37, y - 0.028, v, fontsize=11.3, va="top", linespacing=1.4)

# ---------- (2) nghiệm LP thật ----------
def heat(ax, mat, title, fmt, mark_frac=False):
    ax.imshow(mat, cmap="Blues", vmin=0, vmax=3, aspect="auto")
    for s in range(S):
        for j in range(len(COLS)):
            v = mat[s, j]
            if v > 1e-6:
                frac = mark_frac and abs(v - round(v)) > 1e-6
                ax.text(j, s, fmt(v), ha="center", va="center", fontsize=8.3,
                        color="#c0392b" if frac else ("white" if v > 1.8 else "black"),
                        weight="bold" if frac else "normal")
    ax.set_xticks(range(len(COLS)))
    ax.set_xticklabels(COLS, fontsize=8.5)
    ax.set_yticks(range(S))
    ax.set_yticklabels([f"tầng {s + 1}" for s in range(S)], fontsize=9)
    ax.set_xlabel("cột (15 bên trái, 3 bên phải)", fontsize=9)
    ax.set_title(title, fontsize=11.5)


ax_lp = fig.add_axes([0.045, 0.08, 0.30, 0.33])
heat(ax_lp, lp_f, f"Nghiệm nới lỏng (thật): {n_frac} ô thập phân (chữ đỏ)\nchi phí {lp_cost:.1f} = cận dưới",
     lambda v: f"{v:.2f}", mark_frac=True)

ax_int = fig.add_axes([0.435, 0.08, 0.28, 0.33])
heat(ax_int, int_f, f"Nghiệm nguyên (thật): 29 FA, 0 HA\nchi phí {int_cost:.1f}", lambda v: f"{v:.0f}")

fig.text(0.378, 0.255, "→", fontsize=34, ha="center", va="center")
fig.text(0.372, 0.205, "tìm nghiệm\nnguyên", fontsize=9, ha="center", va="top")

# ---------- (3) so sánh chi phí ----------
ax_c = fig.add_axes([0.785, 0.08, 0.18, 0.33])
bars = ax_c.bar(["cận dưới\n(nới lỏng)", "nghiệm\nnguyên"], [lp_cost, int_cost], color=["#9ec5f4", "#3b7dd8"], width=0.55)
for b, v in zip(bars, [lp_cost, int_cost]):
    ax_c.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}", ha="center", fontsize=13)
ax_c.set_ylim(0, 37)
ax_c.axhline(29, color="#c0392b", ls="--", lw=1)
ax_c.set_ylabel("chi phí")
ax_c.set_title("Hai số bằng nhau\n⇒ 29 là tối ưu", fontsize=11.5, color="#1f6b3a", weight="bold")

fig.text(0.5, 0.012, "Nhật ký HiGHS: nghiệm nguyên 29 tìm được ngay ở nút gốc bằng heuristic làm tròn; "
         "cận dưới 29, gap 0%, 1 nút, 0,02 s.", ha="center", fontsize=11)

plt.savefig(os.path.join(ROOT, "docs", "figures", "fig21_solver_method_slide.png"), dpi=120)
plt.close(fig)
print("saved fig21")
