"""Promote tt_s6_arr to asic/rtl/hwmaj_ilp6t_asic.v, re-verify exhaustively vs hw_maj_s64, rerun BTC flow, save reports."""
import os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G
import hwmaj_ilp as H
import standalone_ppa as SP
from tree_timing import load, REF

ROOT, BTC = G.ROOT, G.BTC
NAME = "hwmaj_ilp6t_asic"
srcv = open(os.path.join(ROOT, "build", "work_asic", "tree_timing", "tt_s6_arr", "tt_s6_arr.v"), encoding="utf-8").read()
srcv = srcv.replace("module tt_s6_arr", f"module {NAME}")
dst = os.path.join(ROOT, "asic", "rtl", f"{NAME}.v")
open(dst, "w", encoding="utf-8", newline="\n").write(srcv)

d = os.path.join(ROOT, "build", "work_asic", "final_ilp6t")
os.makedirs(d, exist_ok=True)
shutil.copy2(dst, d)
open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {NAME}.v\nsynth -top {NAME} -flatten\ntee -q -o eval.txt eval -table a,b\n")
G.sh(d, "yosys -q eval.ys")
got = load(os.path.join(d, "eval.txt"))
print("cases:", len(got), "mismatch vs hw_maj_s64:", sum(1 for k, v in REF.items() if got.get(k) != v))
for fn in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
    shutil.copy2(os.path.join(BTC, fn), d)
conv = open(os.path.join(BTC, "convolution_unit.v"), encoding="utf-8", errors="replace").read().replace("<Ten_Module>", NAME)
open(os.path.join(d, "convolution_unit.v"), "w", encoding="utf-8").write(conv)
shutil.copy2(os.path.join(BTC, "synthesis.ys"), os.path.join(d, "synthesis_btc.ys"))
open(os.path.join(d, "synthesis.ys"), "w").write(
    f"read_verilog convolution_unit.v\nread_verilog {NAME}.v\nsynth -top convolution_unit -flatten\nopt -purge\nopt\n"
    "dfflibmap -liberty normal.lib\nabc -liberty normal.lib\nclean\n"
    "tee -o area_report.txt stat -liberty normal.lib\nwrite_verilog -noattr Convolution.v\n")
G.sh(d, "yosys synthesis.ys > yosys.log")
sta = G.sh(d, "sta -exit run_sta.tcl")
rep = os.path.join(ROOT, "asic", "reports")
shutil.copy2(os.path.join(d, "area_report.txt"), os.path.join(rep, "convolution_unit_hwmaj_ilp6t_area.rpt"))
open(os.path.join(rep, "convolution_unit_hwmaj_ilp6t_sta.rpt"), "w", encoding="utf-8").write(sta)
area = float(re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
delay = float(re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
power = float(re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
print(f"convolution_unit: area={area:.3f} delay={delay:.4f} power={power:.4f} mW")
cells = re.search(r"Number of cells:\s+(\d+)", open(os.path.join(d, "area_report.txt")).read())
print("cells:", cells.group(1) if cells else "?")
sa, sd, sp = SP.measure(NAME, dst)
print(f"standalone: area={sa:.3f} delay={sd:.4f} power={sp:.4f} mW")
