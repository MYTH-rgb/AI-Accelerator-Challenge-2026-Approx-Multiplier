"""Vẽ từng tầng của cây nén hwmaj_ilp6t: khoanh các bit được gom thành FA (và HA nếu có).

Dữ liệu lấy trực tiếp từ asic/rtl/hwmaj_ilp6t_asic.v (đã đối chiếu với lịch ILP: 6, 9, 4, 4, 3, 3 FA).

Chạy từ thư mục gốc dự án:
    PYTHONIOENCODING=utf-8 python tools/draw_ilp6t_groups.py

Đầu ra: docs/figures/fig12_stage1_groups.png ... fig17_stage6_groups.png
"""
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hwmaj_ilp as H  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"
OUT = os.path.join(ROOT, "docs", "figures")
RTL = os.path.join(ROOT, "asic", "rtl", "hwmaj_ilp6t_asic.v")
W = H.W
COLS = list(range(W - 1, 2, -1))  # cột 15 bên trái, cột 3 bên phải
XSP = 1.8  # khoảng cách ngang giữa các cột, đủ chỗ cho nhãn wire
XPOS = {c: i * XSP for i, c in enumerate(COLS)}
STAGE_FA = [6, 9, 4, 4, 3, 3]  # lịch ILP: số FA mỗi tầng (khớp RTL, đã kiểm)

# ---- 1. bit thô ban đầu: tên, cột, loại ----
kind_of, col_of, raw_order = {}, {}, []
for c in range(W):
    for kind, a, b in H.bits[c]:
        if kind in ("and", "nand"):
            name = f"pp_{a}_{b}_{c}"
        elif kind == "sig":
            name = a  # comp[k]
        else:
            name = f"1'b1@{c}"
        kind_of[name], col_of[name] = kind, c
        raw_order.append(name)

# ---- 2. FA từ RTL ----
src = open(RTL, encoding="utf-8").read()
fa = {}  # tên tổng "sN" -> 3 đầu vào
for m in re.finditer(r"wire (s\d+) = ([^;]*);", src):
    ins = [t.strip() for t in m.group(2).split("^")]
    if len(ins) == 3:
        fa[m.group(1)] = ins
ids = sorted(fa, key=lambda s: int(s[1:]))
assert len(ids) == 29, len(ids)
assert not [m for m in re.finditer(r"wire (s\d+) = ([^;^]*\^[^;^]*);", src)], "có HA trong RTL"

stage_of, k = {}, 0
for st, n in enumerate(STAGE_FA, start=1):
    for sid in ids[k:k + n]:
        stage_of[sid] = st
    k += n


def norm(n, fa_col=None):
    return "1'b1@8" if n == "1'b1" else n


# cột của FA và của bit sinh ra
fa_col = {}


def col(n):
    if n in col_of:
        return col_of[n]
    if n.startswith("k"):
        c = col("s" + n[1:]) + 1
    else:
        c = fa_col[n]
    col_of[n] = c
    return c


for sid in ids:
    ins = [norm(x) for x in fa[sid]]
    fa_col[sid] = max(col(x) if not x.startswith("k") or ("s" + x[1:]) in fa_col else 0 for x in ins)
    # nếu có carry của FA chưa gán cột, tính lại theo thứ tự id (id tăng dần nên đã có)
    fa_col[sid] = max(col(x) for x in ins)
    kind_of[sid], kind_of["k" + sid[1:]] = "sum", "carry"
    col_of[sid], col_of["k" + sid[1:]] = fa_col[sid], fa_col[sid] + 1

produced = {n: 0 for n in raw_order}
consumed = {}
for sid in ids:
    st = stage_of[sid]
    produced[sid] = produced["k" + sid[1:]] = st
    for x in fa[sid]:
        x = norm(x)
        assert x not in consumed, f"{x} dùng hai lần"
        consumed[x] = st
        assert produced[x] < st, f"{sid}: đầu vào {x} chưa sẵn sàng ở tầng {st}"

COLOR = {"and": "#3b7dd8", "nand": "#7fb3f0", "sig": "#e0a040", "const": "#9b9b9b",
         "sum": "#2e8b57", "carry": "#8e5ad7"}

for st in range(1, 7):
    groups = [sid for sid in ids if stage_of[sid] == st]
    present = [n for n in produced if produced[n] < st and consumed.get(n, 99) >= st]
    by_col = {c: [] for c in COLS}
    for n in present:
        if col_of[n] in by_col:
            by_col[col_of[n]].append(n)
    layout = {}  # tên -> (cột, hàng)
    boxes = []
    for c in COLS:
        pool = by_col[c]
        row = 0
        for sid in [g for g in groups if fa_col[g] == c]:
            members = [norm(x) for x in fa[sid]]
            for x in members:
                assert x in pool, (sid, x)
                layout[x] = (c, row)
                row += 1
            boxes.append((sid, c, row - 3))
        rest = sorted([n for n in pool if n not in layout], key=lambda n: (produced[n], n))
        for n in rest:
            layout[n] = (c, row)
            row += 1
    maxh = max(r for (_, r) in layout.values()) + 1
    fig, ax = plt.subplots(figsize=(17, 1.0 * maxh * 0.75 + 2.6))
    for n, (c, r) in layout.items():
        ax.add_patch(plt.Circle((XPOS[c], r), 0.31, color=COLOR[kind_of[n]], ec="black", lw=0.5, zorder=3))
    for sid, c, r0 in boxes:
        ax.add_patch(FancyBboxPatch((XPOS[c] - 0.42, r0 - 0.45), 0.84, 2.9, boxstyle="round,pad=0.02,rounding_size=0.25",
                                    fc="none", ec="#c0392b", lw=2.2, zorder=4))
        ax.text(XPOS[c] + 0.5, r0 + 1, sid, fontsize=8, color="#c0392b", va="center", ha="left", zorder=5)
    for c in COLS:
        h = len(by_col[c])
        ax.text(XPOS[c], -1.0, f"c{c}", ha="center", fontsize=9)
    ax.set_xlim(-0.9, (len(COLS) - 1) * XSP + 1.2)
    ax.set_ylim(-1.5, maxh + 0.3)
    ax.set_aspect("equal")
    ax.axis("off")
    n_in = sum(len(by_col[c]) for c in COLS)
    ax.set_title(f"Tầng {st}: {len(groups)} FA, 0 HA. Khoanh đỏ = ba bit gom thành một FA (nhãn là tên wire trong RTL). "
                 f"{n_in} bit vào tầng", fontsize=11)
    handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR[k_], markeredgecolor="black", markersize=9, label=lab)
               for k_, lab in (("and", "tích AND"), ("nand", "phần bù q"), ("sig", "bit bù g, nz"), ("const", "hằng"),
                               ("sum", "bit tổng từ tầng trước"), ("carry", "bit nhớ từ tầng trước"))]
    handles.append(Line2D([0], [0], color="#c0392b", lw=2.2, label="nhóm một FA (3 bit)"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=7, fontsize=8, frameon=False)
    plt.tight_layout()
    path = os.path.join(OUT, f"fig{11 + st}_stage{st}_groups.png")
    plt.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"tầng {st}: {len(groups)} FA", " ".join(f"{sid}@c{fa_col[sid]}" for sid in groups))

print("tổng", len(ids), "FA, 0 HA")
