"""Hình đơn giản: 'sàn chi phí 29.0' - không cách xếp hợp lệ nào rẻ hơn.

Chạy từ thư mục gốc dự án:
    PYTHONIOENCODING=utf-8 python tools/draw_ilp6t_simple_floor.py
Đầu ra: docs/figures/fig23_ilp6t_cost_floor.png

Số liệu (đã có trong tài liệu, xem mục 16-17 của Ghi_chu_slide_va_hoi_dap_hwmaj_ilp6t.md):
  - cận dưới LP = 29.0 (solver nới lỏng)
  - 29 FA + 0 HA   -> 29.0 (lời giải nguyên tối ưu)
  - 28 FA + 3 HA   -> 28 + 3*0.6 = 29.8 (ép giữ 22 bit cuối)
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "DejaVu Sans"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FLOOR = 29.0
fig, ax = plt.subplots(figsize=(10, 6.2))

# vùng dưới sàn: không có cách xếp nào
ax.axhspan(28.4, FLOOR, color="#e6e6e6", hatch="//", edgecolor="#bdbdbd", lw=0)
ax.text(2.0, 28.72, "Vùng này TRỐNG: không có cách xếp hợp lệ nào\n(solver đã chứng minh bằng cận dưới LP = 29.0)",
        ha="center", va="center", fontsize=11, color="#555555")

# đường sàn
ax.axhline(FLOOR, color="#c0392b", lw=2.2, ls="--")
ax.text(3.95, FLOOR + 0.03, "SÀN = 29.0", ha="right", va="bottom", fontsize=12, color="#c0392b", fontweight="bold")

# hai cách xếp hợp lệ (xây được)
ax.scatter([1], [29.0], s=420, color="#2e8b57", edgecolor="black", zorder=6)
ax.text(1, 29.12, "29 FA + 0 HA\nchi phí 29.0\nĐƯỢC CHỌN (chạm sàn)", ha="center", va="bottom", fontsize=11,
        color="#1f6b3a", fontweight="bold")

ax.scatter([3], [29.8], s=420, marker="s", color="#e0a040", edgecolor="black", zorder=6)
ax.text(3, 29.92, "28 FA + 3 HA\nchi phí 28 + 3×0.6 = 29.8\nđắt hơn, bị loại", ha="center", va="bottom",
        fontsize=11, color="#a06a00")

ax.annotate("", xy=(3, 29.04), xytext=(3, 29.76), arrowprops=dict(arrowstyle="<->", color="#a06a00"))
ax.text(3.07, 29.4, "+0.8", fontsize=11, color="#a06a00", va="center")

ax.set_xlim(0.2, 4.0)
ax.set_ylim(28.4, 30.45)
ax.set_xticks([])
ax.set_ylabel("chi phí = 1.0·FA + 0.6·HA")
ax.set_title("Hình 23. Mọi cách xếp hợp lệ đều nằm TRÊN sàn 29.0, lời giải chọn chạm đúng sàn", fontsize=12)
ax.grid(axis="y", alpha=0.25)
for side in ("top", "right", "bottom"):
    ax.spines[side].set_visible(False)

fig.text(0.5, 0.01, "Mỗi điểm là một cách xếp FA/HA xây được thành mạch. Sàn 29.0 là chi phí của bài toán nới lỏng "
         "(cho phép số thập phân): không cách nguyên nào thấp hơn.", ha="center", fontsize=9)
plt.tight_layout(rect=[0, 0.04, 1, 1])
out = os.path.join(ROOT, "docs", "figures", "fig23_ilp6t_cost_floor.png")
plt.savefig(out, dpi=130)
print("saved", out)
