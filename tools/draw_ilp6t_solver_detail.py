"""Hình chi tiết các bước HiGHS đã làm khi giải mô hình hwmaj_ilp6t.

Số liệu lấy từ nhật ký thật (chạy tools/hwmaj_ilp.py mô hình với msg=True):
  khởi đầu: 304 cột nguyên, 224 hàng, 884 phần tử khác 0
  presolve 3 vòng: (137 hàng, 170 cột) -> (85, 140) -> (77, 132)
  hệ số mục tiêu nhân 5 đều là số nguyên, nên cận dưới được làm tròn lên số nguyên
  nút gốc:
    dòng 1: cận dưới 0 (tầm thường)
    dòng 2: LP gốc cho cận dưới 29 sau 35 lần lặp đơn hình, chưa có nghiệm nào
    dòng 3: heuristic làm tròn ngẫu nhiên (Src R) tìm nghiệm 29; 218 cắt sinh ra,
            17 cắt nằm trong LP, 11 xung đột, tổng 54 lần lặp
  nút 1: khám phá 100%, cận dưới = cận trên = 29, gap 0%
  kết thúc: Optimal, 0.02 s

Chạy từ thư mục gốc dự án:
    PYTHONIOENCODING=utf-8 python tools/draw_ilp6t_solver_detail.py
Đầu ra: docs/figures/fig20_ilp_solver_detail.png
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.family"] = "DejaVu Sans"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "figures", "fig20_ilp_solver_detail.png")

fig = plt.figure(figsize=(17, 10.5))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 17)
ax.set_ylim(0, 10.5)
ax.axis("off")
ax.text(8.5, 10.1, "Hình 20. Solver (HiGHS) giải mô hình hwmaj_ilp6t từng bước như thế nào",
        ha="center", va="center", fontsize=15, weight="bold")

STEPS = [
    ("A. Đọc mô hình", "#e8f1fc", [
        "304 biến, đều nguyên",
        "224 ràng buộc",
        "884 hệ số khác 0",
        "Hệ số mục tiêu 1.0 và 0.6",
    ]),
    ("B. Presolve", "#e8f1fc", [
        "Vòng 1: 137 hàng, 170 cột",
        "Vòng 2: 85 hàng, 140 cột",
        "Vòng 3: 77 hàng, 132 cột",
        "Mục tiêu nhân 5 đều nguyên,",
        "nên cận dưới làm tròn lên",
    ]),
    ("C. LP gốc", "#fdf3e1", [
        "Bỏ điều kiện nguyên",
        "Đơn hình: 35 lần lặp",
        "Cận dưới = 29",
        "Chưa có nghiệm nguyên nào",
    ]),
    ("D. Cắt và heuristic", "#fdf3e1", [
        "Sinh 218 bất đẳng thức cắt",
        "17 cắt đưa vào LP, 11 xung đột",
        "Heuristic làm tròn ngẫu nhiên",
        "tìm nghiệm nguyên = 29",
        "Tổng 54 lần lặp đơn hình",
    ]),
    ("E. Nhánh và cận", "#e6f4ea", [
        "Nút gốc là nút duy nhất",
        "Khám phá 100% (1 nút)",
        "Cận dưới = cận trên = 29",
        "Gap 0%, không cần nhánh con",
    ]),
    ("F. Kết thúc", "#e6f4ea", [
        "Status: Optimal",
        "Primal bound 29, dual bound 29",
        "Thời gian 0.02 s",
        "Lời giải: 29 FA, 0 HA",
    ]),
]

# hàng trên: sáu bước, mỗi bước một khung
W_BOX, GAP = 2.45, 0.3
for i, (title, color, lines) in enumerate(STEPS):
    x = 0.35 + i * (W_BOX + GAP)
    y = 6.0
    ax.add_patch(FancyBboxPatch((x, y), W_BOX, 3.5, boxstyle="round,pad=0.04,rounding_size=0.15",
                                fc=color, ec="#333333", lw=1.1))
    ax.text(x + W_BOX / 2, y + 3.1, title, ha="center", va="center", fontsize=11.5, weight="bold")
    for j, t in enumerate(lines):
        ax.text(x + 0.12, y + 2.5 - j * 0.46, t, ha="left", va="center", fontsize=9.3)
    if i < len(STEPS) - 1:
        ax.add_patch(FancyArrowPatch((x + W_BOX + 0.02, y + 1.75), (x + W_BOX + GAP - 0.02, y + 1.75),
                                     arrowstyle="-|>", mutation_scale=12, lw=1.3, color="#333333"))

# hàng dưới trái: biểu đồ cận qua các mốc
ax2 = fig.add_axes([0.06, 0.09, 0.38, 0.33])
labels = ["bắt đầu", "sau LP gốc", "sau cắt và\nheuristic", "kết thúc"]
dual = [0, 29, 29, 29]
primal = [None, None, 29, 29]
x = list(range(len(labels)))
ax2.step(x, dual, where="mid", color="#3b7dd8", lw=2.2, label="cận dưới (dual bound)")
ax2.scatter(x, dual, color="#3b7dd8", zorder=3)
ax2.step([2, 3], [29, 29], where="mid", color="#2e8b57", lw=2.2, label="cận trên (nghiệm tốt nhất)")
ax2.scatter([2, 3], [29, 29], color="#2e8b57", zorder=3)
ax2.axhline(29, color="#c0392b", ls="--", lw=1)
ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=9)
ax2.set_ylim(-2, 34)
ax2.set_ylabel("chi phí")
ax2.set_title("Cận dưới tăng từ 0 lên 29; cận trên xuất hiện ở dòng heuristic và gặp cận dưới",
              fontsize=11)
ax2.text(0.02, 3, "cận trên chưa có ở hai mốc đầu (vô hạn)", fontsize=8.5, color="#555555")
ax2.legend(fontsize=9, loc="center right")
ax2.grid(alpha=0.3)

# hàng dưới phải: ý nghĩa từng con số
ax.add_patch(FancyBboxPatch((8.0, 0.35), 8.7, 4.0, boxstyle="round,pad=0.04,rounding_size=0.15",
                            fc="#f4f4f4", ec="#333333", lw=1.1))
notes = [
    ("Cận dưới", "chi phí thấp nhất mà nghiệm có thể đạt, tính từ bài toán nới lỏng."),
    ("Cận trên", "chi phí của nghiệm nguyên tốt nhất đã tìm được."),
    ("Gap", "khoảng cách giữa hai cận, 0% nghĩa là đã chứng minh tối ưu."),
    ("Cắt", "bất đẳng thức thêm vào để thu hẹp miền nới lỏng, làm cận dưới chặt hơn."),
    ("Heuristic", "cách tìm nghiệm nguyên nhanh bằng làm tròn, không cần chứng minh."),
    ("Nhánh", "chia bài toán thành hai bài nhỏ hơn. Ở đây không cần, vì cận đã trùng."),
]
ax.text(8.25, 4.0, "Các thuật ngữ trong nhật ký", fontsize=11.5, weight="bold", va="center")
for i, (k, v) in enumerate(notes):
    ax.text(8.25, 3.45 - i * 0.52, f"{k}: {v}", fontsize=9.6, va="center")

plt.savefig(OUT, dpi=120)
plt.close(fig)
print("saved", OUT)
