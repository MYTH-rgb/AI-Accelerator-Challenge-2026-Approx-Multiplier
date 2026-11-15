#!/usr/bin/env python3
"""
Convolution Unit ASIC Flow Runner
Tích hợp hwmaj_ilp6t_asic vào convolution_unit và chạy Yosys + OpenSTA.
Tuân thủ 100% quy tắc BTC (dùng constraints.sdc và run_sta.tcl do BTC cung cấp).
"""

import os
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BTC_ASIC_DIR  = os.path.join(PROJECT_ROOT, "docs", "Training2", "ASIC")
MULT_RTL      = os.path.join(PROJECT_ROOT, "asic", "rtl", "hwmaj_ilp6t_asic.v")
WORK_DIR      = os.path.join(PROJECT_ROOT, "build", "work_asic", "convolution_unit_hwmaj_ilp6t")
REPORTS_DIR   = os.path.join(PROJECT_ROOT, "asic", "reports")

MULT_MODULE = "hwmaj_ilp6t_asic"
TOP_MODULE  = "convolution_unit"


def to_wsl(path: str) -> str:
    p = os.path.abspath(path).replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        return f"/mnt/{drive}{p[2:]}"
    return p


def main():
    os.makedirs(WORK_DIR,    exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    print(f"[*] Work dir : {WORK_DIR}")
    print(f"[*] Multiplier: {MULT_MODULE}")

    # 1. Copy BTC files (normal.lib, constraints.sdc, run_sta.tcl)
    for fname in ["normal.lib", "constraints.sdc", "run_sta.tcl"]:
        src = os.path.join(BTC_ASIC_DIR, fname)
        shutil.copy2(src, os.path.join(WORK_DIR, fname))
        print(f"[*] Copied BTC file: {fname}")

    # 2. Patch convolution_unit.v: thay <Ten_Module> → hwmaj_ilp6t_asic
    conv_src = os.path.join(BTC_ASIC_DIR, "convolution_unit.v")
    with open(conv_src, "r", encoding="utf-8") as f:
        conv_text = f.read()

    if "<Ten_Module>" in conv_text:
        conv_text = conv_text.replace("<Ten_Module>", MULT_MODULE)
        print(f"[*] Patched convolution_unit.v: replaced <Ten_Module> with {MULT_MODULE}")
    else:
        print("[!] WARNING: <Ten_Module> placeholder not found — checking existing module name...")
        existing = re.search(r"(\w+)\s+mult0\s*\(", conv_text)
        if existing:
            current = existing.group(1)
            if current != MULT_MODULE:
                conv_text = re.sub(rf"\b{re.escape(current)}\b(?=\s+mult\d)", MULT_MODULE, conv_text)
                print(f"[*] Replaced existing module '{current}' with '{MULT_MODULE}'")

    with open(os.path.join(WORK_DIR, "convolution_unit.v"), "w", encoding="utf-8") as f:
        f.write(conv_text)

    # 3. Copy multiplier RTL
    shutil.copy2(MULT_RTL, os.path.join(WORK_DIR, f"{MULT_MODULE}.v"))
    print(f"[*] Copied RTL: {MULT_MODULE}.v")

    # 4. Ghi synthesis.ys (đúng template BTC, top = convolution_unit)
    ys_content = f"""# 1. Đọc các file Verilog
read_verilog convolution_unit.v
read_verilog {MULT_MODULE}.v

# 2. Tổng hợp High-level
synth -top {TOP_MODULE} -flatten

# 3. Tối ưu hóa
opt -purge
opt

# 4. Map sang thư viện Nangate45
# Map Flip-Flop
dfflibmap -liberty normal.lib

# Map các cổng Logic (ABC)
abc -liberty normal.lib

# 5. Dọn dẹp
clean

# 6. --- BÁO CÁO DIỆN TÍCH ---
tee -o area_report.txt stat -liberty normal.lib

# 7. Xuất file netlist
write_verilog -noattr Convolution.v
"""
    with open(os.path.join(WORK_DIR, "synthesis.ys"), "w", encoding="utf-8") as f:
        f.write(ys_content)
    print("[*] Generated synthesis.ys")

    wsl_dir = to_wsl(WORK_DIR)

    # 5. Chạy Yosys qua WSL
    print("\n[*] Running Yosys synthesis...")
    cmd_y = ["wsl.exe", "-d", "Ubuntu", "bash", "-c",
             f"cd {wsl_dir} && yosys synthesis.ys 2>&1"]
    res_y = subprocess.run(cmd_y, capture_output=True, text=True, timeout=180)

    with open(os.path.join(WORK_DIR, "yosys.log"), "w", encoding="utf-8") as f:
        f.write(res_y.stdout + "\n" + res_y.stderr)

    if res_y.returncode != 0:
        print(f"[!] Yosys FAILED (exit {res_y.returncode})")
        print(res_y.stdout[-3000:])
        sys.exit(1)
    print("[+] Yosys OK")

    # 6. Chạy OpenSTA qua WSL
    print("[*] Running OpenSTA...")
    cmd_s = ["wsl.exe", "-d", "Ubuntu", "bash", "-c",
             f"cd {wsl_dir} && sta run_sta.tcl 2>&1"]
    res_s = subprocess.run(cmd_s, capture_output=True, text=True, timeout=120)

    with open(os.path.join(WORK_DIR, "sta.log"), "w", encoding="utf-8") as f:
        f.write(res_s.stdout + "\n" + res_s.stderr)
    print("[+] OpenSTA done")

    # 7. Parse Area từ area_report.txt
    area, cells = 0.0, 0
    area_rpt = os.path.join(WORK_DIR, "area_report.txt")
    if os.path.exists(area_rpt):
        with open(area_rpt, "r") as f:
            txt = f.read()
        m = re.search(r"Chip area for module '\\?convolution_unit':\s+([\d\.]+)", txt)
        if m:
            area = float(m.group(1))
        m = re.search(r"Number of cells:\s+(\d+)", txt)
        if m:
            cells = int(m.group(1))

    # 8. Parse Delay và Power từ OpenSTA stdout
    sta_out = res_s.stdout
    arr = 0.0
    m = re.search(r"([\d\.\-]+)\s+data arrival time", sta_out)
    if m:
        arr = float(m.group(1))
    delay = arr - 2.0

    pwr_w = 0.0
    m = re.search(
        r"Total\s+[\d\.e\+\-]+\s+[\d\.e\+\-]+\s+[\d\.e\+\-]+\s+([\d\.e\+\-]+)", sta_out
    )
    if m:
        pwr_w = float(m.group(1))
    pwr_mw = pwr_w * 1000.0

    # 9. Lưu báo cáo
    if os.path.exists(area_rpt):
        shutil.copy2(area_rpt,
                     os.path.join(REPORTS_DIR, "convolution_unit_hwmaj_ilp6t_area.rpt"))
    with open(os.path.join(REPORTS_DIR, "convolution_unit_hwmaj_ilp6t_sta.rpt"), "w", encoding="utf-8") as f:
        f.write(sta_out)

    # 10. In kết quả
    print("\n" + "=" * 60)
    print(f"  ASIC PPA — {TOP_MODULE} + {MULT_MODULE}")
    print("=" * 60)
    print(f"  Area (Chip):    {area:.3f} µm²  ({cells} cells)")
    print(f"  Critical Delay: {delay:.4f} ns  (arrival {arr:.4f} - 2.0 ns)")
    print(f"  Total Power:    {pwr_mw:.4f} mW  ({pwr_w:.4e} W)")
    print("=" * 60)
    print(f"[+] Reports saved to {REPORTS_DIR}")
    print(f"[+] Full logs at {WORK_DIR}")


if __name__ == "__main__":
    main()
