"""Hình quy trình giải ILP của bản nộp hwmaj_ilp6t: từ mô hình đến nghiệm 29.

Số liệu lấy từ nhật ký thật của HiGHS 1.15.1 khi giải mô hình trong tools/hwmaj_ilp.py:
  304 biến nguyên, 224 ràng buộc; presolve còn 132 cột, 77 hàng;
  cận dưới ở nút gốc = 29; heuristic làm tròn ngẫu nhiên tìm được nghiệm 29 ở nút gốc;
  gap 0%, 1 nút B&B, 54 lần lặp đơn hình, thời gian 0.02 s.

Chạy từ thư mục gốc dự án:
    PYTHONIOENCODING=utf-8 python tools/draw_ilp6t_solve.py
Đầu ra: docs/figures/fig19_ilp_solve_pipeline.png
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.family"] = "DejaVu Sans"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "figures", "fig19_ilp_solve_pipeline.png")

fig, ax = plt.subplots(figsize=(16, 7.8))
ax.set_xlim(0, 16)
ax.set_ylim(0, 7.6)
ax.axis("off")


def box(x, y, w, h, title, lines, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.2",
                                fc=color, ec="#333333", lw=1.2))
    ax.text(x + w / 2, y + h - 0.45, title, ha="center", va="center", fontsize=12, weight="bold")
    for i, t in enumerate(lines):
        ax.text(x + 0.25, y + h - 1.0 - i * 0.46, t, ha="left", va="center", fontsize=10.5)


def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18, lw=1.6, color="#333333"))


box(0.3, 2.9, 3.6, 3.9, "1. Mô hình", [
    "304 biến nguyên:",
    "  f: 96, h: 96, H: 112",
    "224 ràng buộc:",
    "  (R1) 3f + 2h ≤ H",
    "  (R2) H cập nhật + nhớ",
    "  (R3) H ≤ 2 ở tầng cuối",
], "#e8f1fc")

box(4.6, 2.9, 3.6, 3.9, "2. Presolve", [
    "Rút gọn trước khi giải:",
    "bỏ biến và ràng buộc",
    "không ảnh hưởng nghiệm",
    "",
    "224 → 77 ràng buộc",
    "304 → 132 cột",
], "#e8f1fc")

box(8.9, 2.9, 3.6, 3.9, "3. LP nới lỏng", [
    "Bỏ điều kiện nguyên, đơn hình",
    "Cận dưới ở nút gốc: 29",
    "",
    "Cận dưới ≤ mọi nghiệm nguyên",
    "→ không thể dưới 29",
], "#fdf3e1")

box(13.2, 2.9, 2.6, 3.9, "4. Nghiệm", [
    "Heuristic làm tròn",
    "ngẫu nhiên (Src R)",
    "tìm được 29 ở nút gốc",
    "",
    "Gap = 0%",
], "#e6f4ea")

arrow(3.95, 4.85, 4.55, 4.85)
arrow(8.25, 4.85, 8.85, 4.85)
arrow(12.55, 4.85, 13.15, 4.85)

# dải kết luận
ax.add_patch(FancyBboxPatch((0.3, 0.3), 15.5, 2.1, boxstyle="round,pad=0.05,rounding_size=0.2",
                            fc="#f4f4f4", ec="#333333", lw=1.2))
ax.text(8.05, 2.3, "Kết luận: cận dưới = nghiệm tìm được = 29", ha="center", va="center",
        fontsize=13, weight="bold", color="#1f6b3a")
ax.text(8.05, 1.45, "HiGHS báo: Status Optimal, Primal bound 29, Dual bound 29, số nút B&B 1, "
        "54 lần lặp đơn hình, 0.02 s", ha="center", va="center", fontsize=10.5)
ax.text(8.05, 0.85, "Kết quả: 29 FA, 0 HA. Đây là nghiệm nguyên có chi phí nhỏ nhất của mô hình.",
        ha="center", va="center", fontsize=10.5)

ax.text(8.0, 7.25, "Hình 19. Quy trình giải ILP cho bản nộp hwmaj_ilp6t", ha="center", va="center",
        fontsize=14, weight="bold")

plt.savefig(OUT, dpi=130, bbox_inches="tight")
plt.close(fig)
print("saved", OUT)
