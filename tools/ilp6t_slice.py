"""Lát cắt thật của miền nghiệm mô hình ILP bản nộp hwmaj_ilp6t.

Miền nghiệm của bài làm nằm trong không gian 304 chiều (96 f, 96 h, 112 H), không vẽ trực tiếp được.
Ta lấy MẶT PHẲNG đi qua ba nghiệm THẬT của chính mô hình này:
  X_INT: nghiệm nguyên tối ưu (29 FA, 0 HA, chi phí 29.0)
  X_LP : nghiệm của bài toán nới lỏng (chi phí 29.0, có giá trị thập phân)
  X_ALT: nghiệm nguyên khi ép giữ 22 bit cuối (28 FA, 3 HA, chi phí 29.8)
Điểm trên mặt phẳng: x = (1 - a - b) X_INT + a X_LP + b X_ALT.
Các ràng buộc đẳng thức luôn thỏa (tổ hợp có tổng hệ số 1), nên chỉ cần kiểm các bất đẳng thức:
  x >= 0, 3f + 2h <= H, H(tầng cuối) <= 2.
Chi phí trên mặt phẳng: 29 + 0.8 b.
"""
import os
import sys

import numpy as np
import pulp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hwmaj_ilp as H  # noqa: E402

W, S = H.W, 6


def _solve(cat, min_total=None):
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
    if min_total:
        prob += pulp.lpSum(Hh[(S, c)] for c in range(W)) >= min_total
    prob.solve(pulp.HiGHS(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal"
    fv = np.array([[f[(s, c)].value() for c in range(W)] for s in range(S)])
    hv = np.array([[h[(s, c)].value() for c in range(W)] for s in range(S)])
    Hv = np.array([[Hh[(s, c)].value() for c in range(W)] for s in range(S + 1)])
    return pulp.value(prob.objective), fv, hv, Hv


def vec(sol):
    _, fv, hv, Hv = sol
    return np.concatenate([fv.ravel(), hv.ravel(), Hv.ravel()])


def unpack(x):
    f = x[: S * W].reshape(S, W)
    h = x[S * W: 2 * S * W].reshape(S, W)
    Hv = x[2 * S * W:].reshape(S + 1, W)
    return f, h, Hv


def feasible(x, tol=1e-7):
    f, h, Hv = unpack(x)
    if x.min() < -tol:
        return False
    if (3 * f + 2 * h - Hv[:S]).max() > tol:
        return False
    return Hv[S].max() <= 2 + tol


def compute(n=241, a_rng=(-0.6, 2.0), b_rng=(-0.4, 1.6)):
    cost_i, *_ = sol_int = _solve(pulp.LpInteger)
    sol_lp = _solve(pulp.LpContinuous)
    sol_alt = _solve(pulp.LpInteger, min_total=22)
    xi, xl, xa = vec(sol_int), vec(sol_lp), vec(sol_alt)
    al = np.linspace(*a_rng, n)
    be = np.linspace(*b_rng, n)
    mask = np.zeros((n, n), dtype=bool)
    for j, b in enumerate(be):
        for i, a in enumerate(al):
            mask[j, i] = feasible((1 - a - b) * xi + a * xl + b * xa)
    costs = (sol_int[0], sol_lp[0], sol_alt[0])
    return al, be, mask, costs


if __name__ == "__main__":
    al, be, mask, costs = compute()
    print("chi phí INT, LP, ALT:", [round(c, 2) for c in costs])
    ys, xs = np.where(mask)
    print("miền: a trong [%.2f, %.2f], b trong [%.2f, %.2f]" % (al[xs.min()], al[xs.max()], be[ys.min()], be[ys.max()]))
    print("điểm (0,0):", mask[np.argmin(abs(be)), np.argmin(abs(al))],
          " (1,0):", mask[np.argmin(abs(be)), np.argmin(abs(al - 1))],
          " (0,1):", mask[np.argmin(abs(be - 1)), np.argmin(abs(al))])


def draw_slice(ax, al, be, mask, costs, fontsize=10):
    """Vẽ lát cắt miền nghiệm thật lên ax."""
    import matplotlib.pyplot as plt  # noqa: F401
    ax.contourf(al, be, mask.astype(float), levels=[0.5, 1.5], colors=["#9ec5f4"], alpha=0.85)
    ax.contour(al, be, mask.astype(float), levels=[0.5], colors=["#3b7dd8"], linewidths=1.6)
    for k in (0.25, 0.5, 0.75):
        ax.plot([0, 1 - k], [k, k], color="#e0a040", lw=1.0, ls="--")
        ax.text(1 - k + 0.03, k, f"{29 + 0.8 * k:.1f}", fontsize=fontsize - 1, color="#a06a00", va="center")
    ax.plot([0, 1], [0, 0], color="#1f6b3a", lw=3.0, solid_capstyle="round")
    ax.scatter([0], [0], s=170, color="#2e8b57", zorder=6, edgecolor="black")
    ax.scatter([1], [0], s=170, marker="X", color="#c0392b", zorder=6, edgecolor="black")
    ax.scatter([0], [1], s=170, marker="s", color="#e0a040", zorder=6, edgecolor="black")
    ax.annotate("nghiệm nguyên tối ưu\n29 FA, 0 HA, chi phí %.1f" % costs[0], (0, 0), xytext=(-0.55, 0.28),
                fontsize=fontsize, color="#1f6b3a", arrowprops=dict(arrowstyle="->", color="#1f6b3a"))
    ax.annotate("nghiệm nới lỏng (LP)\n17 ô thập phân, chi phí %.1f" % costs[1], (1, 0), xytext=(1.02, 0.38),
                fontsize=fontsize, color="#c0392b", arrowprops=dict(arrowstyle="->", color="#c0392b"))
    ax.annotate("28 FA + 3 HA\nchi phí %.1f" % costs[2], (0, 1), xytext=(0.12, 1.08), fontsize=fontsize,
                color="#a06a00", arrowprops=dict(arrowstyle="->", color="#a06a00"))
    ax.text(0.5, -0.07, "cạnh tối ưu: chi phí = 29.0", ha="center", va="top", fontsize=fontsize, color="#1f6b3a")
    ax.set_xlim(-0.65, 2.15)
    ax.set_ylim(-0.25, 1.3)
    ax.set_xlabel("a: hướng từ nghiệm nguyên sang nghiệm nới lỏng")
    ax.set_ylabel("b: hướng sang nghiệm 28 FA + 3 HA")
    ax.grid(alpha=0.25)
