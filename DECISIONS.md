# LỊCH SỬ QUYẾT ĐỊNH KỸ THUẬT (DECISIONS)
**Cập nhật lần cuối:** 2026-11-09

---

> **Lịch sử đầy đủ DEC-001 → DEC-038** (FPGA flow, Candidate 1/2 development, benchmark chuẩn hóa, báo cáo bán kết): xem Git log hoặc `graphify-out/graph.json`.

---

### [DEC-039] Vượt Qua Vòng Bán Kết → Vào Vòng Chung Kết
- **Ngày:** 2026-11-06 | **Trạng thái:** `[MILESTONE]`
- Nhóm chính thức nhận thông báo vượt qua Vòng Bán kết với `candidate2_asic_dadda`. Kích hoạt giai đoạn chuẩn bị Vòng Chung kết: ASIC convolution_unit flow + CNN simulation.

---

### [DEC-040] Tinh Gọn GitHub Main Branch
- **Ngày:** 2026-11-06 | **Trạng thái:** `[DONE]`
- Giữ duy nhất `candidate2_asic_dadda.v` trên nhánh `main`. Toàn bộ 37 bộ nhân thực nghiệm, sweep framework 2,688 biến thể lưu trữ vĩnh viễn tại nhánh `archive/all_multipliers_and_experiments`.

---

### [DEC-041] Khóa Chiến Lược Chung Kết: ASIC Only
- **Ngày:** 2026-11-06 | **Trạng thái:** `[BTC_CONFIRMED & TEAM_DECISION]`
- **Yêu cầu BTC:** Tích hợp bộ nhân vào `convolution_unit`, chạy Yosys v0.52 + OpenSTA v3.1.0 trên Nangate 45nm → PPA; mô phỏng CNN 1,000 ảnh MNIST → Accuracy %.
- **Quyết định nhóm:** Tập trung 100% vào luồng ASIC, không triển khai FPGA. Thiết kế đại diện: `candidate2_asic_dadda`.

---

### [DEC-042] Thông Báo Chung Kết & Slide 16 Trang
- **Ngày:** 2026-11-06 | **Trạng thái:** `[BTC_CONFIRMED & DONE]`
- Tiếp nhận thông báo Top 10 chung kết (tài liệu: `docs/THONG BAO NOP SAN PHAM VA LICH BAO CAO VONG CHUNG KET.pdf`).
- Hạn nộp: 13/11/2026. Báo cáo trực tiếp: 8h00, 14/11/2026, Phòng D102.
- Khởi tạo slide 16 trang Dark Mode trên Canva (Design ID: `DAHaJ4of_SM`).

---

### [DEC-043–DEC-045] Hoàn Thiện Slide Chung Kết
- **Ngày:** 2026-11-06–07 | **Trạng thái:** `[DONE]`
- Tích hợp công thức MAC, Dot Diagram Dadda 5 tầng, Bảng PPA, Pareto Frontier vào slide Dark Mode.
- File PPTX cuối: `reports/Bao_Cao_Chung_Ket_Candidate2_ASIC_Dadda.pptx` (5.37 MB, 16 slide).

---

### [DEC-046] Đo PPA `convolution_unit` & CNN Accuracy 92.40%
- **Ngày:** 2026-11-08 | **Trạng thái:** `[MEASURED & MILESTONE]`
- **ASIC PPA:** Area = **2745.386 µm²** (1,990 cells), Delay = **1.5064 ns**, Power = **0.3150 mW**.
  - Script: `asic/scripts/run_convunit_asic.py`; Báo cáo: `asic/reports/convolution_unit_dadda_*.rpt`
- **CNN Accuracy:** **92.40%** (924/1000 ảnh MNIST, Vivado XSim, 6'38").
  - Delta = **±0.00%** so với exact multiplier → ME ≈ 0 triệt tiêu hoàn toàn tích lũy sai số qua tất cả lớp MAC.

---

### [DEC-047] Candidate 4 — Column-5 Carry Boundary Recovery
- **Ngày:** 2026-11-08 | **Trạng thái:** `[MEASURED & TEAM_DECISION]`
- Thêm FA-reduce 6 partial products tại cột 5 (ranh giới cắt tỉa của candidate2). Carry inject vào VMA tại bit 6/7. Hằng số bù: 17 → 61.
- **Kết quả:** MAE 41.56 → 28.24 (-32%), NMED 0.001268 → 0.000862 (-32%). ASIC: Area 2745 → 3368 µm² (+22.7%), Delay 1.51 → 3.99 ns (VMA 3-input), Power 0.315 → 0.392 mW.
- **Quyết định:** Candidate 4 không thay thế candidate2 do delay tăng mạnh. Tiếp tục nộp candidate2_asic_dadda.

---

### [DEC-052] Đổi Bài Nộp Sang `hwmaj_ilp6t_asic` (cùng hàm, cây nén 6 tầng theo thời điểm đến)
- **Ngày:** 2026-11-10 | **Trạng thái:** `[CHỐT — TEAM_DECISION & MEASURED]`
- **Quyết định:** nhóm chọn `asic/rtl/hwmaj_ilp6t_asic.v` (từ `tt_s6_arr`, xem DEC-051) thay `hwmaj_ilp5_asic`. Dừng tối ưu, chuyển sang slide và thuyết trình.
- **Bằng chứng:** 0/65,536 sai lệch so với hw_maj_s64; convolution_unit 2889.824 µm², 1.4841 ns, 0.328 mW (2557 cell); mạch riêng 262.010 µm², 0.6805 ns, 0.0253 mW. Report: `asic/reports/convolution_unit_hwmaj_ilp6t_*.rpt`.
- **Hệ quả:** MAE và accuracy giữ nguyên (cùng hàm). Mức cải thiện delay (−1.4%) ngang dao động ABC, không trình bày như cải tiến lớn.

### [DEC-051] Đổi Bài Nộp Sang `hwmaj_ilp5_asic` (kỹ thuật bù mới)
- **Ngày:** 2026-11-10 | **Trạng thái:** `[CHỐT — TEAM_DECISION & MEASURED]`
- **Chốt:** nhóm xác nhận `hwmaj_ilp5_asic` là bài nộp cuối. Các biến thể cắt 7 cột và bù popcount không thay thế.
- **Quyết định:** nhóm chuyển bài nộp sang `asic/rtl/hwmaj_ilp5_asic.v`: bù động theo majority hai toán hạng + cờ nz, cây nén ILP 5 tầng. Chấp nhận diện tích convolution_unit tăng 5.3% so với candidate2 gốc.
- **Lý do:** đây là phương án duy nhất có kỹ thuật bù chưa thấy trong các nguồn đã khảo sát; sai số thấp hơn 34%; accuracy không suy giảm (93.00%); thắng baseline BTC ở diện tích, delay và công suất; đạt quy tắc nhân với 0.
- **Kiểm chứng:** 0/65,536 sai lệch so với hw_maj_s64; minimax bảng bù ổn định trên 5 phân bố (DEC trước).
- **Hệ quả:** cần cập nhật slide và báo cáo; trình bày rõ đây là lai ghép, không phải kiến trúc mới về nguyên lý; nêu rõ các công trình liên quan (patent TI, MajorityNets, scaleTRIM).
- **Cách diễn đạt (2026-11-10):** nói đây là biến thể của candidate2 (giữ BW + cắt cột 0–5; thay bù hằng số bằng bù tra bảng majority hai toán hạng + nz; cây ILP) và thuộc họ bù theo số bit 1 (patent TI). Chưa đọc được LOZDAM và TCSI 2009, nên chỉ nói "trong các nguồn đã khảo sát".
- **Thử ghép (MEASURED, kết quả âm, không đổi bài nộp):** (1) thêm số bit 1 cột 6 vào lớp bù: MAE chỉ giảm 1–6%, không đáng chi phí (`tools/col6_feature_test.py`). (2) bộ nén xấp xỉ (sum = OR3) ở FA cột ≤K của cây ILP 5 (`tools/approx_comp.py`): K=6 → diện tích 2943.0 (+1.8%), delay 1.586, MAE 52.3; K=7 → diện tích 2779.7 (−3.9%), MAE 205.5 (MNIST 143 so với 6.67); K=8 → 2664.0, MAE 826.6. Sai số nhân quá lớn so với phần diện tích tiết kiệm; loại bỏ.
- **Thử cây nén cùng hàm (MEASURED, `tools/tree_timing.py`, tất cả 0/65,536 sai lệch so với hw_maj_s64):** S=5/6/7 tầng × thứ tự gốc / theo thời điểm đến (bit bù đến muộn vào chân z của FA). Tốt nhất `tt_s6_arr`: 2889.824 µm², 1.4841 ns, 0.328 mW (so với 2891.154 / 1.5058 / 0.328: diện tích −0.05%, delay −1.4%). Các biến thể khác dao động ±2% do ABC, không cải thiện đồng thời. Chưa đổi bài nộp — chờ nhóm quyết.

### [DEC-050] Thay Bài Nộp Bằng `candidate2_ilp5_asic`
- **Ngày:** 2026-11-10 | **Trạng thái:** `[TEAM_DECISION & MEASURED]`
- **Quyết định:** nhóm chọn thay candidate2 bằng cây nén ILP 5 tầng (`asic/rtl/candidate2_ilp5_asic.v`), cùng hàm, sai số và accuracy với candidate2. Tiêu chí "PPA không tăng" bị bỏ theo yêu cầu nhóm; diện tích convolution_unit tăng 0.06%.
- **Bằng chứng:** xem bảng trong PROJECT_STATE.md; kiểm chứng vét cạn 0/65,536 lỗi; CNN 92.40%.
- **Hệ quả:** candidate2 gốc vẫn là tham chiếu. Cần cập nhật slide và báo cáo theo số mới trước khi nộp.

### [DEC-048] Bù Theo Trọng Số Hamming Hai Toán Hạng — `hw_maj_s64`
- **Ngày:** 2026-11-09 | **Trạng thái:** `[MEASURED — KHÔNG THAY THẾ: nhóm chốt giữ candidate2, 2026-11-09]`
- **Lý do:** E[T|a] = ½·Σaᵢ(64−2ⁱ) cho thấy các bit thấp dự đoán T gần như ngang nhau, a[5] kém nhất; E[T|p,q] = 321·p·q/36. Bù theo popcount đầy đủ cho MAE 15.63 nhưng tốn diện tích.
- **Thiết kế:** majority hai nhóm 3 bit mỗi toán hạng + `nz`; C = 64·g + L·nz (L=40) để bit thấp gần hằng, tránh phình cây cộng 9 đầu vào; dùng slot cột 6–8 sẵn có; bỏ Zero-Bypass MUX.
- **Bằng chứng:** `convolution_unit` 2962.708 µm², 1.5202 ns, 0.341 mW; MAE 27.29, ME −1.49, MaxE 153; MNIST 93.00% (XSim). Biến thể `hw_pair_s64`: MAE 21.40, 3406.396 µm², 1.822 ns, 92.80%.
- **Kiểm tra minimax bảng bù của `hw_maj_s64` (2026-11-10, `tools/minimax_comp.py`):** trên 5 phân bố (đều, ReLU-Gaussian, Laplace lệch 10/30/60), bảng g hiện tại đã là nghiệm minimax trong không gian 4^9 bảng (MAE xấu nhất 27.97 ở Laplace 60; trung bình 24.59). Đều: 27.28; ReLU-Gaussian: 12.99. Bảng không cần thay đổi; kết quả này là bằng chứng về tính ổn định, không phải phương pháp mới.
- **Bộ cộng cuối prefix trên `candidate2_ilp5_asic` (2026-11-10, `tools/final_adder_exp.py`):** Kogge-Stone 2765.1 µm², 1.4732 ns; Sklansky 2827.3 µm², 1.5062 ns; Brent-Kung 2765.9 µm², 1.4863 ns. Cả ba đúng 65,536/65,536, nhưng đều kém bộ cộng mặc định của Yosys (2747.0 µm², 1.4709 ns). Không cải thiện, giữ nguyên.
- **Accuracy CNN của biến thể cắt cột 6 (2026-11-10):** 92.70% (927/1000), cao hơn exact 92.40%. Cùng với PPA convolution_unit 2653.6 µm², 1.5164 ns, 0.306 mW. Dù MAE tăng lên 64, accuracy không giảm: tập 1000 ảnh không đủ nhạy để phân biệt các mức sai số này.
- **Cắt 7 cột + bù popcount gộp 4 mức, 16 lớp × hằng số 8 bit (2026-11-10, `tools/cut7pop.py`):** netlist khớp mô hình 65,536/65,536. Mô hình MAE 53.1, ME −15.7. convolution_unit: 3510.1 µm², 1.763 ns, 0.434 mW (tăng ~28% diện tích so với hwmaj_ilp5). Mạch nhân riêng 293.4 µm². Một số hằng số bị bão hòa ở 255. Chi phí bảng và bộ đếm popcount vượt xa lợi ích sai số: không dùng. Chưa đo CNN vì quyết định PPA đã rõ.
- **Cắt cột 6 + g ∈ 0..7 (2026-11-10, `tools/cut6g7.py`):** netlist khớp mô hình 65,536/65,536. Mô hình MAE 55.5, ME −3.5. Mạch 6 tầng: conv_unit 2682.6 µm², 1.5829 ns, 0.305 mW; mạch nhân riêng 238.9 µm², 0.871 ns. Accuracy CNN 92.10% (thấp hơn g ∈ 0..3 là 92.70%). Sai số thấp hơn nhưng delay tăng và accuracy không cải thiện: không dùng.
- **Tối ưu bảng bù cho biến thể cắt cột 6 (2026-11-10, `tools/minimax_cut6.py`, `cut6_range.py`):** bảng hiện tại (g ∈ 0..3): MAE uniform 64.2, ME −31.4, worst MAE 77.1. Minimax trong không gian g ∈ 0..3: worst 76.2, uniform 66.0 (chỉ cải thiện nhỏ). Mở rộng g ∈ 0..7 (thêm 1 bit bù ở cột 8): uniform MAE 55.4, ME −3.4, worst 58.9. Giới hạn chính là dải g, không phải cách chọn bảng.
- **Phân tích thêm biến thể cắt cột 6 (2026-11-10):** mạch nhân riêng 224.238 µm², 0.7061 ns, 0.0217 mW (so với candidate2: −8.9% diện tích, −3.6% delay, −10.3% công suất; so với hw_maj_s64 ILP5: −13.4%, −4.8%, −13.2%). So dự đoán từng ảnh: so với exact, 38 ảnh đổi (16 mất đúng, 19 được đúng); so với hw_maj_s64, 39 ảnh đổi (18 vs 15). Chênh ròng nhỏ, không có ý nghĩa thống kê.
- **Thử cắt thêm cột 6 (2026-11-10, `tools/hwcut6.py`):** bỏ 7 tích cột 6, bù L=40, g ∈ 0..3 (2 bit ở cột 6, 7). Netlist khớp mô hình 65,536/65,536. Mô hình: MAE 64.2, ME −31.5, MaxE 537. convolution_unit ILP 5 tầng: 2653.6 µm², 1.5164 ns, 0.306 mW (so với hw_maj ILP5: diện tích −8.2%, delay +0.7%, công suất −6.7%; so với candidate2_ilp5: diện tích −3.4%, delay +3.1%, công suất −2.2%). Sai số tăng mạnh và lệch âm; chưa phải hướng khả thi nếu giữ accuracy.
- **ILP cho cây nén của `hw_maj_s64` (2026-11-10, `tools/hwmaj_ilp.py`):** ma trận gồm 43 tích + bit bù (nz ở cột 3, 5; g ở cột 6–8) + hằng số BW (cột 8, 15). Đúng 0 lỗi so với netlist hw_maj_s64 trên 65,536 ca. 4 tầng: 2908.7 µm², 1.5213 ns, 0.330 mW. 5 tầng: 2891.2 µm², 1.5058 ns, 0.328 mW (so với hw_maj_s64 gốc 2962.7 µm², 1.5202 ns, 0.341 mW: diện tích −2.4%, delay −0.9%, công suất −3.8%). Vẫn lớn hơn candidate2_ilp5_asic khoảng 5% diện tích.
- **Đối chiếu baseline BTC (cùng luồng, 2026-11-10):** `convolution_unit` với `TheMultiplier`: 3789.17 µm², 2.0188 ns, 0.494 mW. `hw_maj_s64` thắng baseline ở cả 3 chỉ số (−21.8% area, −24.7% delay, −31% power). Standalone: 338.352 → 269.724 µm² (−20.3%); delay/power standalone chưa đo.
- **Hệ quả:** so với candidate4 giảm MAE tương đương với chi phí thấp hơn nhiều. Đổi +7.9% area lấy tính mới và sai số; accuracy +0.60% (6 ảnh) không được coi là cải thiện có ý nghĩa.
- **Ràng buộc mới của nhóm (2026-11-09):** PPA không được tăng so với candidate2 (2745.386 µm², 1.5064 ns, 0.3150 mW) → `hw_maj_s64` không đạt. Quét thêm 12 biến thể (cắt thêm cột 6 + ước lượng rẻ; `tools/gen_hw_variants2.py`) và 10 biến thể (tái dùng tín hiệu AND; `gen_hw_variants3.py`): **0 biến thể đạt cả ba giới hạn**. Gần nhất có ý nghĩa: `v_maj1_d4_s64` 2696.708 µm², 1.5292 ns, 0.3140 mW nhưng MAE 63.36. Candidate2 vẫn là thiết kế nộp cho tới khi nhóm quyết định khác.
- **Thử nghiệm cây nén ILP (2026-11-10, `tools/gen_tree_rtl.py`):** cùng ma trận bit và Zero-Bypass của candidate2, 65,536/65,536 đúng, sai số không đổi. Dadda tham lam: 27 FA + 4 HA, 2805.5 µm², 1.6189 ns, 0.316 mW. ILP tối thiểu số ô: 27 FA + 2 HA, 2754.7 µm², 1.5374 ns, 0.312 mW. Candidate2 viết tay: 2745.4 µm², 1.5064 ns, 0.315 mW → **ILP không vượt candidate2**; candidate2 đã gần tối ưu về số ô. Bước tiếp theo nếu làm: ILP có ràng buộc độ sâu.
- **ILP có ràng buộc số tầng (2026-11-10, `tools/stage_ilp_tree.py`):** 4 tầng: 2735.8 µm², 1.5347 ns, 0.314 mW (diện tích −0.36%, delay +1.9%, công suất −0.3%). 5 tầng: 2747.0 µm², 1.4709 ns, 0.313 mW (diện tích +0.06%, delay −2.4%, công suất −0.6%). Cả hai đều đúng 65,536/65,536. Chưa đạt "PPA không tăng" ở 5 tầng vì diện tích tăng 1.6 µm².
  - **Mạch nhân riêng** (`tools/standalone_ppa.py`, cùng SDC; candidate2 tái lập 246.050 µm² / 0.7322 ns / 0.0242 mW): ILP 5 tầng 244.454 µm², 0.7071 ns, 0.0239 mW (−0.6% / −3.4% / −1.2%). ILP 4 tầng 246.582 µm², 0.6917 ns, 0.0242 mW.
  - **CNN MNIST 1000 ảnh** (XSim, `(script chạy CNN, không đi kèm repo)`): 92.40%, Δ = 0.00%. Lưu ý: nhãn "candidate2_asic_dadda" trong log là chuỗi cố định của script; kết quả là của `tree_stage5`.
  - Netlist/RTL nằm trong `build/work_asic/tree_rtl/tree_stage5/`; chưa đưa vào `asic/rtl/`.
- **Đính chính:** "chứng minh Pareto k=6" (script cắt bit tích, 5,000 mẫu) không phải chứng minh; ME≈0 của candidate2 chỉ đúng với phân bố đều (pixel × kernel thật: −3.90).
