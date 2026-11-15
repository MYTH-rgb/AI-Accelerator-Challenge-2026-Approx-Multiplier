"""Standalone PPA of one multiplier (Nangate normal.lib, Yosys + OpenSTA).
Same SDC as BTC (clock 10 ns, input/output delay 2 ns, load 0.05 pF), ports a, b, p.
Validation: candidate2 should reproduce 246.050 um2 / 0.7320 ns / 0.0242 mW from earlier runs."""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTC = ROOT + r"\docs\Training2\ASIC"
OUT = ROOT + r"\build\work_asic\standalone"


def wsl(p):
    p = os.path.abspath(p).replace("\\", "/")
    return f"/mnt/{p[0].lower()}{p[2:]}"


def sh(d, cmd):
    return subprocess.run(["wsl.exe", "-d", "Ubuntu", "bash", "-c", f"cd {wsl(d)} && {cmd} 2>&1"],
                          capture_output=True, text=True, timeout=1500).stdout


def measure(name, rtl_path):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(rtl_path, os.path.join(d, f"{name}.v"))
    shutil.copy2(os.path.join(BTC, "normal.lib"), d)
    open(os.path.join(d, "synth.ys"), "w").write(
        f"read_verilog {name}.v\nsynth -top {name} -flatten\nopt -purge\nopt\ndfflibmap -liberty normal.lib\n"
        "abc -liberty normal.lib\nclean\ntee -o area.txt stat -liberty normal.lib\nwrite_verilog -noattr net.v\n")
    sh(d, "yosys -q synth.ys")
    area = float(re.search(r"Chip area for module '\\?" + name + r"':\s+([\d.]+)", open(os.path.join(d, "area.txt")).read()).group(1))
    sdc = ("create_clock -name vclk -period 10.0\n"
           "set_input_delay -clock vclk 2.0 [get_ports {a[*] b[*]}]\n"
           "set_output_delay -clock vclk 2.0 [get_ports {p[*]}]\n"
           "set_load 0.05 [get_ports {p[*]}]\n"
           "set_driving_cell -lib_cell BUF_X1 [get_ports {a[*] b[*]}]\n")
    open(os.path.join(d, "c.sdc"), "w").write(sdc)
    open(os.path.join(d, "sta.tcl"), "w").write(
        f"read_liberty normal.lib\nread_verilog net.v\nlink_design {name}\nread_sdc c.sdc\n"
        "report_checks -path_delay max -digits 4\nreport_power\nexit\n")
    sta = sh(d, "sta -exit sta.tcl")
    arr = re.search(r"([\d.\-]+)\s+data arrival time", sta)
    pw = re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta)
    delay = float(arr.group(1)) - 2.0 if arr else None
    power = float(pw.group(1)) * 1000 if pw else None
    return area, delay, power


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cases = [
        ("candidate2_asic_dadda", ROOT + r"\asic\rtl\candidate2_asic_dadda.v"),
        ("tree_stage5", ROOT + r"\build\work_asic\tree_rtl\tree_stage5\tree_stage5.v"),
        ("tree_stage4", ROOT + r"\build\work_asic\tree_rtl\tree_stage4\tree_stage4.v"),
    ]
    print(f"{'module':<24} {'Area':>10} {'Delay':>8} {'Power mW':>9}")
    for name, path in cases:
        a, dl, pw = measure(name, path)
        print(f"{name:<24} {a:>10.3f} {dl if dl is None else round(dl,4):>8} {pw if pw is None else round(pw,4):>9}")
    print("earlier reference candidate2 standalone: 246.050 um2, 0.7320 ns, 0.0242 mW")
