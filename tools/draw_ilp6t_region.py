"""Hình miền nghiệm thật (lát cắt qua ba nghiệm thật) của bản nộp hwmaj_ilp6t.

Chạy từ thư mục gốc dự án:
    PYTHONIOENCODING=utf-8 python tools/draw_ilp6t_region.py
Đầu ra: docs/figures/fig22_ilp6t_feasible_region.png
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import ilp6t_slice as SL  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
al, be, mask, costs = SL.compute()
fig, ax = plt.subplots(figsize=(10.5, 7.5))
SL.draw_slice(ax, al, be, mask, costs, fontsize=11)
ax.set_title("Hình 22. Miền nghiệm thật của bài làm (lát cắt qua ba nghiệm thật)\n"
             "Vùng xanh là mọi điểm thỏa các ràng buộc; đường đứt là chi phí 29.2, 29.4, 29.6", fontsize=12)
fig.text(0.5, 0.01, "Miền nghiệm gốc có 304 chiều nên không vẽ được. Hình lấy mặt phẳng đi qua ba nghiệm thật "
         "của chính mô hình này.", ha="center", fontsize=9.5)
plt.tight_layout(rect=[0, 0.03, 1, 1])
plt.savefig(os.path.join(ROOT, "docs", "figures", "fig22_ilp6t_feasible_region.png"), dpi=130)
print("saved fig22")
