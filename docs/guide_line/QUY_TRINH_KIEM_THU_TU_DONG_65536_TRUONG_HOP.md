# HƯỚNG DẪN QUY TRÌNH KIỂM THỬ TỰ ĐỘNG BỘ NHÂN SIGNED INT8 (AUTOMATED VERIFICATION FLOW)
**Dự án:** Thiết kế Bộ Nhân 8-bit (Signed INT8) cho Bộ Gia Tốc CNN/DNN  
**Cuộc thi:** AI ACCELERATOR DESIGN CHALLENGE 2026 (HCMUTE)  
**Tài liệu hỗ trợ:** Thuyết trình báo cáo, phản biện kỹ thuật và bàn giao giải pháp.

---

## 1. Tổng Quan & Bài Toán Đặt Ra

Trong cuộc thi thiết kế mạch nhân xấp xỉ (Approximate Multiplier) cho bộ gia tốc AI:
- Mỗi đầu vào là số nguyên 8-bit có dấu (**Signed INT8 — biểu diễn bù 2**): $A, B \in [-128, 127]$.
- Không gian trạng thái đầu vào: $2^8 \times 2^8 = 2^{16} = 65{,}536$ trường hợp kiểm thử.
- **Thách thức:** Nếu dùng phương pháp truyền thống trên GUI Vivado:
  - Bật giao diện đồ họa mất 1–2 phút.
  - Testbench thủ công chạy và vẽ dạng sóng (waveform `.wdb`) cho 65,536 chu kỳ sẽ làm phình dung lượng hàng GB, máy bị đơ giật.
  - Không thể tự động tính toán các chỉ số thống kê sai số học máy ($ER, NMED, MRED, MAE, MaxED$).

👉 **Giải pháp của dự án:** Xây dựng một **Hệ thống Kiểm thử Tự động (Automated CLI Verification Tool)** bằng Python kết hợp Vivado XSim ngầm (Batch Mode). Toàn bộ 65,536 trường hợp được kiểm tra, tính toán sai số và xuất báo cáo chỉ trong **vài giây**.

---

## 2. Kiến Trúc 5 Bước Của Quy Trình Kiểm Thử

```
┌────────────────────────────────────────────────────────┐
│  BƯỚC 1: Sinh Vector Vét Cạn (generators.py)           │
│  Tạo toàn bộ 65,536 cặp (A, B) ∈ [-128, 127]          │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  BƯỚC 2: Tự Động Sinh Testbench Verilog                │
│  Tạo Testbench nạp kích thích (Stimulus) tự động       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  BƯỚC 3: Chạy Mô Phỏng Ngầm (Batch Mode XSim)          │
│  xelab (biên dịch) ──► xsim -R (chạy không GUI, no wave)│
│  Ghi kết quả 16-bit DUT ra file log                    │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  BƯỚC 4: Thẩm Tra & Đo Sai Số (metrics.py)             │
│  So khớp với Golden Model: Exact = A × B               │
│  Tính ER, NMED, MRED, MAE, phát hiện lỗi bit X/Z       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  BƯỚC 5: Tổng Hợp & Báo Cáo (reporting.py)             │
│  Xuất Markdown, CSV, Excel Master & SQLite Vault       │
└────────────────────────────────────────────────────────┘
```

---

## 3. Chi Tiết Từng Thành Phần Kỹ Thuật

### Bước 1: Sinh Vector Toàn Diện (`flow/verification/verifier/generators.py`)
- Hàm `generate_exhaustive()` lặp qua 2 vòng lặp:
  $$\forall A \in [-128, 127], \quad \forall B \in [-128, 127]$$
- Mỗi cặp được gán nhãn thể loại kiểm thử (Corner Cases):
  - **Zero:** Ít nhất một toán hạng bằng 0 ($A=0$ hoặc $B=0$).
  - **Signed Boundary:** Các điểm cực trị biên ($-128, -127, -1, 1, 127$). Đặc biệt cặp $(-128) \times (-128) = +16,384$ là điểm tràn số (overflow) nguy hiểm nhất của INT8.
  - **Sign Combinations:** $(+ \times +), (+ \times -), (- \times +), (- \times -)$.

### Bước 2 & 3: Mô Phỏng Không Waveform (`flow/verification/verifier/simulator.py`)
- **Tự động đóng gói DUT:** Tool tự động đọc module Verilog mục tiêu (ví dụ: `TheMultiplier.v` hoặc `am4cnn_s4l_candidate.v`) qua `inspect_verilog_module()` để nhận diện cổng (`A`, `B`, `Product`).
- **Headless Execution:**
  - Gọi trình biên dịch Vivado: `xelab -prj ... -s sim_snapshot`
  - Kích hoạt mô phỏng: `xsim sim_snapshot -R`
  - Cờ `-R` (Run all) cho phép thực thi toàn bộ 65,536 phép nhân ở tốc độ tối đa của CPU mà không tiêu tốn RAM render đồ họa.
- **Bắt lỗi trạng thái X/Z:** Nếu thiết kế RTL bị lỗi reset, thả nổi dây hoặc ngắn mạch sinh ra bit không xác định (`x`, `z`), bộ parser sẽ gắn cờ cảnh báo vi phạm tính đúng đắn phần cứng ngay lập tức.

### Bước 3: Đánh Giá Bằng Mô Hình Toán Học Chuẩn (`metrics.py` & `arithmetic.py`)
- Python tính toán giá trị chính xác tuyệt đối:
  $$\text{Exact}(A, B) = A \times B$$
- Đo khoảng cách sai số giữa kết quả phần cứng ($\text{DUT}$) và chuẩn ($\text{Exact}$):
  $$\text{Error Distance (ED)} = |\text{DUT} - \text{Exact}|$$
- Tính toán các tiêu chuẩn đo lường của cuộc thi:
  1. **Error Rate ($ER$):** Tỷ lệ % số phép tính có kết quả bị sai lệch:
     $$ER = \frac{\sum [ED > 0]}{65{,}536} \times 100\%$$
  2. **Normalized Mean Error Distance ($NMED$):**
     $$NMED = \frac{1}{65{,}536 \times D_{\max}} \sum_{i=1}^{65{,}536} ED_i \quad \text{với } D_{\max} = 16{,}384$$
  3. **Mean Relative Error Distance ($MRED$):** Sai số tương đối trung bình (chỉ tính trên 65,025 trường hợp mà $\text{Exact} \neq 0$).
  4. **Mean Error ($ME$):** Độ lệch kỳ vọng thống kê. Nếu $ME \approx 0$, sai số có phân phối đối xứng, không làm trôi trọng số bias khi mạng CNN tích luỹ tổng chập (MAC).

### Bước 5: Báo Cáo & Lưu Trữ
- Kết quả được ghi nhận vào cơ sở dữ liệu `reports/benchmark_vault.db` và xuất file Excel `reports/benchmark_master_signed_int8.xlsx`.
- Mỗi bộ nhân đều có một bản tóm tắt Markdown chi tiết các cặp gây sai số lớn nhất (Worst-case Pairs) để nhóm thiết kế RTL tập trung sửa lỗi.

---

## 4. Cách Sử Dụng Công Cụ (CLI Cheatsheet)

Mọi thao tác kiểm thử được thực hiện qua dòng lệnh duy nhất tại thư mục gốc dự án:

```powershell
# 1. Chạy kiểm thử toàn duyệt 65,536 trường hợp cho một bộ nhân bất kỳ
python flow/verification/tool.py verify --dut rtl/candidate2_flagship/Mul_approx_top.v --mode exhaustive

# 2. Chạy kiểm thử nhanh trên các trường hợp biên nguy hiểm (Boundary mode)
python flow/verification/tool.py verify --dut rtl/baseline/TheMultiplier.v --mode boundary

# 3. Xuất báo cáo so sánh ra file Markdown và CSV
python flow/verification/tool.py report --output-dir reports/simulation/
```

---

## 5. Điểm Nhấn Đắt Giá Dành Cho Bài Thuyết Trình / Báo Cáo (Key Highlights)

Khi thuyết trình trước Ban giám khảo hoặc viết báo cáo dự án, hãy nhấn mạnh 3 điểm mạnh cốt lõi này:

1. **Tính Toàn Diện 100% (Exhaustive Coverage):**
   > *"Khác với các phương pháp kiểm thử ngẫu nhiên (random testing) chỉ phủ vài nghìn mẫu, giải pháp của nhóm kiểm toán toàn bộ $100\%$ không gian toán học $2^{16} = 65{,}536$ trường hợp của Signed INT8, đảm bảo không bỏ sót bất kỳ điểm dị biệt nào (như ca tràn số $-128 \times -128$)."*

2. **Tự Động Hóa EDA Hiện Đại (Headless CI/CD Flow):**
   > *"Nhóm đã xây dựng quy trình tự động hóa khép kín: từ sinh testbench, gọi XSim chạy ngầm, đến parse kết quả và đánh giá sai số. Thời gian kiểm thử 65,536 vector chỉ mất dưới 5 giây cho mỗi bộ nhân, cho phép nhóm đối chứng nhanh chóng hàng chục biến thể kiến trúc khác nhau."*

3. **Gắn Liền Với Bản Chất AI (DNN-aware Metrics):**
   > *"Công cụ không chỉ đo số lượng lỗi ($ER$), mà tập trung thẩm tra $NMED$ và $ME$ (Mean Error). Thiết kế được lựa chọn có $ME \approx 0$, giúp đảm bảo khi mạng nơ-ron thực hiện phép tính tích chập hàng triệu lần, các sai số dương và âm tự triệt tiêu lẫn nhau, bảo toàn độ chính xác suy luận mà không cần huấn luyện lại mạng."*
