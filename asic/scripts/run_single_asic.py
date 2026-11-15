#!/usr/bin/env python3
"""
Single-Module ASIC Synthesis & STA Runner (Nangate 45nm)
Strictly adheres to official BTC rules:
1. Self-contained working folder per module with normal.lib, synthesis.ys, constraints.sdc, run_sta.tcl
2. Exact 7-step synthesis.ys with correct top module definition
3. Exact constraints.sdc with load 0.01, driving BUF_X1, input/output delay 2.0, port-matching
4. Exact run_sta.tcl pointing to Gate_netlist_mult.v
5. Critical Path Delay calculation: Data Arrival Time - 2.0 ns
6. Detailed power breakdown: Internal, Switching, Leakage, Total Power
"""

import os
import sys
import subprocess
import shutil
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASIC_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(ASIC_ROOT)

ENV_DIR = os.path.join(ASIC_ROOT, "env")
RTL_DIR = os.path.join(ASIC_ROOT, "rtl")
REPORTS_DIR = os.path.join(ASIC_ROOT, "reports")
AREA_DIR = os.path.join(REPORTS_DIR, "area_reports")
STA_DIR = os.path.join(REPORTS_DIR, "sta_reports")
WORK_ROOT = os.path.join(PROJECT_ROOT, "build", "work_asic")

os.makedirs(AREA_DIR, exist_ok=True)
os.makedirs(STA_DIR, exist_ok=True)
os.makedirs(WORK_ROOT, exist_ok=True)

def to_wsl(path):
    p = os.path.abspath(path).replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        return f"/mnt/{drive}{p[2:]}"
    return p

def find_module_files(module_name):
    # Search under asic/rtl/
    found_files = []
    top_file = None
    for root, dirs, files in os.walk(RTL_DIR):
        for f in files:
            if f.endswith(".v"):
                full_p = os.path.join(root, f)
                with open(full_p, "r", encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read()
                if re.search(rf"\bmodule\s+{module_name}\b", txt):
                    top_file = full_p
                    break
        if top_file:
            break
            
    if not top_file:
        return None, None
        
    folder = os.path.dirname(top_file)
    cat = os.path.basename(folder)
    
    # Chỉ có một module trong repo, nên không cần danh sách file phụ thuộc riêng
    return [os.path.basename(top_file)], folder

def main():
    if len(sys.argv) < 2:
        print("Usage: python asic/scripts/run_single_asic.py <module_name>")
        sys.exit(1)
        
    module_name = sys.argv[1].replace(".v", "")
    files, folder = find_module_files(module_name)
    if not files:
        print(f"[!] Error: Could not find module '{module_name}' under {RTL_DIR}")
        sys.exit(1)
        
    print(f"[*] Found module '{module_name}' with component files: {files}")
    
    # 1. Create self-contained module run folder
    run_dir = os.path.join(WORK_ROOT, module_name)
    os.makedirs(run_dir, exist_ok=True)
    
    # 2. Copy normal.lib
    shutil.copy2(os.path.join(ENV_DIR, "normal.lib"), os.path.join(run_dir, "normal.lib"))
    
    # 3. Copy component files
    for f in files:
        shutil.copy2(os.path.join(folder, f), os.path.join(run_dir, f))
        
    # 4. Generate synthesis.ys strictly following BTC 7 steps
    ys_lines = [
        "# 1. Đọc các file Verilog"
    ]
    for vf in files:
        ys_lines.append(f"read_verilog {vf}")
        
    ys_lines.extend([
        "",
        f"# 2. Tổng hợp high-level",
        f"synth -top {module_name} -flatten",
        "",
        "# 3. Tối ưu hóa",
        "opt",
        "opt -purge",
        "",
        "# 4. Map sang thư viện Nangate45",
        "dfflibmap -liberty normal.lib",
        "abc -liberty normal.lib",
        "",
        "# 5. Dọn dẹp",
        "clean",
        "",
        "# 6. BÁO CÁO DIỆN TÍCH",
        "tee -o area_report.txt stat -liberty normal.lib",
        "",
        "# 7. Xuất file netlist",
        "write_verilog Gate_netlist_mult.v"
    ])
    
    with open(os.path.join(run_dir, "synthesis.ys"), "w", encoding="utf-8") as f:
        f.write("\n".join(ys_lines) + "\n")
        
    # 5. Generate constraints.sdc
    if module_name == "TheMultiplier":
        sdc_content = """create_clock -name vclk -period 10.0

set_input_delay -clock vclk 2.0 [get_ports {a[*]}]
set_input_delay -clock vclk 2.0 [get_ports {b[*]}]
set_output_delay -clock vclk 2.0 [get_ports {S[*]}]

set_load 0.01 [get_ports {S[*]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {a[*] b[*]}]
"""
    elif module_name == "mul8s_1L2D":
        sdc_content = """create_clock -name vclk -period 10.0

set_input_delay -clock vclk 2.0 [get_ports {A[*]}]
set_input_delay -clock vclk 2.0 [get_ports {B[*]}]
set_output_delay -clock vclk 2.0 [get_ports {O[*]}]

set_load 0.01 [get_ports {O[*]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {A[*] B[*]}]
"""
    elif module_name == "hybrid_opt_twin_precision_1carry":
        sdc_content = """create_clock -name vclk -period 10.0

set_input_delay -clock vclk 2.0 [get_ports {a[*]}]
set_input_delay -clock vclk 2.0 [get_ports {b[*]}]
set_input_delay -clock vclk 2.0 [get_ports {mode_twin}]
set_output_delay -clock vclk 2.0 [get_ports {p[*]}]

set_load 0.01 [get_ports {p[*]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {a[*] b[*] mode_twin}]
"""
    else:
        sdc_content = """create_clock -name vclk -period 10.0

set_input_delay -clock vclk 2.0 [get_ports {a[*]}]
set_input_delay -clock vclk 2.0 [get_ports {b[*]}]
set_output_delay -clock vclk 2.0 [get_ports {p[*]}]

set_load 0.01 [get_ports {p[*]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {a[*] b[*]}]
"""

    with open(os.path.join(run_dir, "constraints.sdc"), "w", encoding="utf-8") as f:
        f.write(sdc_content)
        
    # 6. Generate run_sta.tcl
    sta_content = f"""# --- Cấu hình ---
set lib_file "normal.lib"
set ver_file "Gate_netlist_mult.v"
set sdc_file "constraints.sdc"
set top_module "{module_name}"

# --- Chạy OpenSTA ---
read_liberty $lib_file
read_verilog $ver_file
link_design $top_module
read_sdc $sdc_file

# --- BÁO CÁO KẾT QUẢ ---
puts "\\n--- WORST-CASE TIMING PATHS ---"
report_checks -path_delay max -group_count 1 -fields {{slew cap input_pins nets fanout}} -digits 4

puts "\\n--- POWER ANALYSIS ---"
report_power
exit
"""
    with open(os.path.join(run_dir, "run_sta.tcl"), "w", encoding="utf-8") as f:
        f.write(sta_content)
        
    wsl_run_dir = to_wsl(run_dir)
    
    # 7. Execute Yosys
    print(f"[*] [YOSYS] Running synthesis on {module_name}...")
    cmd_y = ["wsl.exe", "-d", "Ubuntu", "bash", "-c", f"cd {wsl_run_dir} && yosys synthesis.ys"]
    res_y = subprocess.run(cmd_y, capture_output=True, text=True)
    
    # 8. Execute OpenSTA
    print(f"[*] [STA] Running OpenSTA on {module_name}...")
    cmd_s = ["wsl.exe", "-d", "Ubuntu", "bash", "-c", f"cd {wsl_run_dir} && sta run_sta.tcl"]
    res_s = subprocess.run(cmd_s, capture_output=True, text=True)
    
    # Copy reports
    area_rpt_dst = os.path.join(AREA_DIR, f"{module_name}_area.rpt")
    sta_rpt_dst = os.path.join(STA_DIR, f"{module_name}_sta.rpt")
    if os.path.exists(os.path.join(run_dir, "area_report.txt")):
        shutil.copy2(os.path.join(run_dir, "area_report.txt"), area_rpt_dst)
    with open(sta_rpt_dst, "w", encoding="utf-8") as f:
        f.write(res_s.stdout)
        
    # Parse
    area = 0.0
    cells = 0
    if os.path.exists(area_rpt_dst):
        with open(area_rpt_dst, "r") as f:
            t = f.read()
        ma = re.search(r"Chip area for module '.*?':\s+([\d\.]+)", t)
        if ma: area = float(ma.group(1))
        mc = re.search(r"Number of cells:\s+(\d+)", t)
        if mc: cells = int(mc.group(1))
        
    arr = 0.0
    m_arr = re.search(r"([\d\.\-]+)\s+data arrival time", res_s.stdout)
    if m_arr: arr = float(m_arr.group(1))
    delay = arr - 2.0
    
    pwr_w = 0.0
    m_pwr = re.search(r"Total\s+[\d\.e\-\+]+\s+[\d\.e\-\+]+\s+[\d\.e\-\+]+\s+([\d\.e\-\+]+)", res_s.stdout)
    if m_pwr: pwr_w = float(m_pwr.group(1))
    pwr_mw = pwr_w * 1000.0
    
    print(f"[+] Synthesis complete: Area = {area:.3f} um2, Cells = {cells}")
    print(f"[+] STA complete: Data Arrival = {arr:.4f} ns -> Critical Path Delay = {delay:.4f} ns, Total Power = {pwr_mw:.4f} mW")
    print(f"[+] Reports saved to:")
    print(f"    - Area: {area_rpt_dst}")
    print(f"    - STA:  {sta_rpt_dst}")

if __name__ == "__main__":
    main()
