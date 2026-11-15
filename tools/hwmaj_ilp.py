"""ILP-optimised compressor tree for hw_maj_s64's bit matrix (same function, must match its netlist exactly).
Matrix: 43 retained PPs (cols 6-14) + comp bits (nz at cols 3,5; g[0..2] at cols 6,7,8) + BW constant (cols 8,15)."""
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G

ROOT = G.ROOT
W = 16
FA_COST, HA_COST = 1.0, 0.6
HW_RTL = os.path.join(ROOT, "asic", "rtl", "hw_maj_s64.v")
OUT = os.path.join(ROOT, "build", "work_asic", "hwmaj_ilp")
BTC = G.BTC
TABLE = os.path.join(ROOT, "build", "work_asic", "hw_variants", "hw_maj_s64", "eval.txt")

bits = {c: [] for c in range(W)}
for i in range(8):
    for j in range(8):
        if i + j >= 6:
            bits[i + j].append(("nand" if (i == 7) != (j == 7) else "and", i, j))
for c, name in ((3, "comp[3]"), (5, "comp[5]"), (6, "comp[6]"), (7, "comp[7]"), (8, "comp[8]")):
    bits[c].append(("sig", name, None))
for c in (8, 15):
    bits[c].append(("const", "1'b1", None))
heights = [len(bits[c]) for c in range(W)]


def solve(S):
    prob = pulp.LpProblem(f"hwm_s{S}", pulp.LpMinimize)
    f = {(s, c): pulp.LpVariable(f"f_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S) for c in range(W)}
    h = {(s, c): pulp.LpVariable(f"h_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S) for c in range(W)}
    H = {(s, c): pulp.LpVariable(f"H_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S + 1) for c in range(W)}
    prob += pulp.lpSum(FA_COST * f[k] + HA_COST * h[k] for k in f)
    for c in range(W):
        prob += H[(0, c)] == heights[c]
        prob += H[(S, c)] <= 2
    for s in range(S):
        for c in range(W):
            prob += 3 * f[(s, c)] + 2 * h[(s, c)] <= H[(s, c)]
            cin = (f[(s, c - 1)] + h[(s, c - 1)]) if c > 0 else 0
            prob += H[(s + 1, c)] == H[(s, c)] - 2 * f[(s, c)] - h[(s, c)] + cin
    st = prob.solve(pulp.HiGHS(msg=False))
    assert pulp.LpStatus[st] == "Optimal", pulp.LpStatus[st]
    fa = [[int(round(f[(s, c)].value())) for c in range(W)] for s in range(S)]
    ha = [[int(round(h[(s, c)].value())) for c in range(W)] for s in range(S)]
    return fa, ha


def netlist(name, fa, ha):
    hdr = open(HW_RTL, encoding="utf-8").read().split("    // =========================================================================\n    // DADDA STAGE 1")[0]
    hdr = hdr.replace("module hw_maj_s64", f"module {name}")
    hdr = re.sub(r"\n    // Retained 43.*?\n\n", "\n", hdr, flags=re.S)
    S = len(fa)
    pool = {c: [] for c in range(W)}
    lines = []
    for c in range(W):
        for kind, a, b in bits[c]:
            if kind in ("and", "nand"):
                n = f"pp_{a}_{b}_{c}"
                i, j = a, b
                expr = f"~(ua[{i}] & ub[{j}])" if kind == "nand" else f"(ua[{i}] & ub[{j}])"
                lines.append(f"    wire {n} = {expr};")
                pool[c].append(n)
            else:
                pool[c].append(a)
    uid = 0
    for s in range(S):
        nxt = {c: [] for c in range(W)}
        for c in range(W):
            cur = list(pool[c])
            for _ in range(fa[s][c]):
                x, y, z = cur.pop(0), cur.pop(0), cur.pop(0)
                uid += 1
                lines.append(f"    wire s{uid} = {x} ^ {y} ^ {z};")
                lines.append(f"    wire k{uid} = ({x} & {y}) | ({z} & ({x} ^ {y}));")
                nxt[c].append(f"s{uid}")
                if c + 1 < W:
                    nxt[c + 1].append(f"k{uid}")
            for _ in range(ha[s][c]):
                x, y = cur.pop(0), cur.pop(0)
                uid += 1
                lines.append(f"    wire s{uid} = {x} ^ {y};")
                lines.append(f"    wire k{uid} = {x} & {y};")
                nxt[c].append(f"s{uid}")
                if c + 1 < W:
                    nxt[c + 1].append(f"k{uid}")
            nxt[c] = cur + nxt[c]
        pool = nxt
    for c in range(W):
        assert len(pool[c]) <= 2, f"col {c} has {len(pool[c])}"
    v1 = [pool[c][0] if len(pool[c]) > 0 else "1'b0" for c in range(W)]
    v2 = [pool[c][1] if len(pool[c]) > 1 else "1'b0" for c in range(W)]
    tail = f"""    wire [15:0] v1 = {{{', '.join(reversed(v1))}}};
    wire [15:0] v2 = {{{', '.join(reversed(v2))}}};
    assign p = v1 + v2;
endmodule
"""
    return hdr + "\n".join(lines) + "\n" + tail


def run(S):
    import re as _re
    fa, ha = solve(S)
    name = f"hwm_ilp_s{S}"
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8", newline="\n").write(netlist(name, fa, ha))
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    ref = {}
    for line in open(TABLE):
        m = _re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            ref[(x, y)] = u
    got = {}
    for line in open(os.path.join(d, "eval.txt")):
        m = _re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            got[(x, y)] = u
    bad = sum(1 for k, v in ref.items() if got.get(k) != v)
    for fn in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
        shutil.copy2(os.path.join(BTC, fn), d)
    conv = open(os.path.join(BTC, "convolution_unit.v"), encoding="utf-8", errors="replace").read().replace("<Ten_Module>", name)
    open(os.path.join(d, "convolution_unit.v"), "w", encoding="utf-8").write(conv)
    open(os.path.join(d, "synthesis.ys"), "w").write(
        f"read_verilog convolution_unit.v\nread_verilog {name}.v\nsynth -top convolution_unit -flatten\nopt -purge\nopt\n"
        "dfflibmap -liberty normal.lib\nabc -liberty normal.lib\nclean\n"
        "tee -o area_report.txt stat -liberty normal.lib\nwrite_verilog -noattr Convolution.v\n")
    G.sh(d, "yosys synthesis.ys > yosys.log")
    sta = G.sh(d, "sta -exit run_sta.tcl")
    area = float(_re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
    delay = float(_re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
    power = float(_re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
    return S, sum(map(sum, fa)), sum(map(sum, ha)), bad, area, delay, power


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(2) as ex:
        rows = list(ex.map(run, [4, 5]))
    print(f"{'stages':>6} {'FA':>3} {'HA':>3} {'mismatch/65536':>15} {'Area':>10} {'Delay':>8} {'Power':>8}")
    for r in rows:
        print(f"{r[0]:>6} {r[1]:>3} {r[2]:>3} {r[3]:>15} {r[4]:>10.3f} {r[5]:>8.4f} {r[6]:>8.4f}")
    print("reference hw_maj_s64 (BTC flow): 2962.708 um2, 1.5202 ns, 0.341 mW")
