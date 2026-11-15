# Luồng Tổng hợp và Phân tích ASIC Nangate 45nm

Thư mục này chứa mã nguồn và kịch bản của bộ nhân signed INT8 nộp Vòng Chung kết: **`hwmaj_ilp6t_asic`**. Luồng chạy theo quy định của Ban Tổ chức (BTC): Yosys tổng hợp, OpenSTA phân tích thời gian và công suất, công nghệ Nangate 45nm.

---

## 1. Công cụ và điều kiện đo

- **Yosys 0.52**: tổng hợp logic, quy trình gồm `synth -flatten`, tối ưu, `dfflibmap` và `abc` với `normal.lib`.
- **OpenSTA 3.1.0**: phân tích thời gian và công suất.
- **Thư viện**: Nangate 45nm Open Cell Library, `normal.lib` (góc Typical, 1.1 V, 25 °C).
- **Ràng buộc** (`env/constraints.sdc`): chu kỳ 10.0 ns, trễ vào/ra 2.0 ns, tải đầu ra 0.01 pF, driver `BUF_X1`.
- **Delay tới hạn** = thời điểm đến của dữ liệu − 2.0 ns.

---

## 2. Cấu trúc

```text
asic/
├── env/                                   # Thư viện và ràng buộc (không commit, xem mục 4)
├── rtl/
│   └── hwmaj_ilp6t_asic.v                 # Mã nguồn RTL bài nộp Chung kết
├── scripts/
│   ├── run_single_asic.py                 # Tổng hợp và STA cho một module trong rtl/
│   └── run_convunit_asic.py               # Tổng hợp và STA cho convolution_unit với bộ nhân này
└── reports/
    ├── convolution_unit_hwmaj_ilp6t_area.rpt   # Diện tích convolution_unit (9 bộ nhân)
    └── convolution_unit_hwmaj_ilp6t_sta.rpt    # Thời gian và công suất convolution_unit
```

---

## 3. Kết quả đo

**`convolution_unit` (9 bộ nhân):**

| Chỉ số | Giá trị |
| :--- | :---: |
| Diện tích | 2,889.824 µm² |
| Số cell | 2,557 |
| Delay | 1.4841 ns |
| Công suất | 0.328 mW |

**Bộ nhân riêng:** diện tích 262.010 µm², delay 0.6805 ns, công suất 0.0253 mW. Số này lấy từ [DECISIONS.md](../DECISIONS.md) (DEC-052). Báo cáo riêng chưa có trong repo.

---

## 4. Chạy lại

### 4.1. Tổng hợp và STA cho bộ nhân

```bash
python asic/scripts/run_single_asic.py hwmaj_ilp6t_asic
```

Script tìm module trong `asic/rtl/`, chạy Yosys và OpenSTA, rồi ghi báo cáo vào `asic/reports/area_reports/` và `asic/reports/sta_reports/`. Cần có Yosys 0.52, OpenSTA 3.1.0 và thư mục `asic/env/`.

### 4.2. Tổng hợp convolution_unit

```bash
python asic/scripts/run_convunit_asic.py
```

Script này cần thêm hai thứ:
- File `convolution_unit.v` và các file BTC khác (không kèm theo repo), đặt tại `docs/Training2/ASIC/` hoặc chỉnh đường dẫn trong script.
- Thư mục `asic/env/`.

---

## 5. Lưu ý

- `asic/env/` bị `.gitignore` bỏ qua nên không nằm trong repo. Cần sao chép `normal.lib`, `constraints.sdc`, `synthesis.ys`, `run_sta.tcl` từ gói BTC.
- Kiểm chứng vét cạn 65.536 cặp (0 lệch so với mô hình tham chiếu `hw_maj_s64`, đã gỡ khỏi repo) chạy bằng script không commit. Repo hiện chưa có testbench.
- Các bộ nhân khác đã gỡ khỏi `asic/`. Lịch sử của chúng còn trong git.
