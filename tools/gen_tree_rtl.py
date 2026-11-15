"""Generate candidate2-equivalent multipliers from (a) Dadda greedy and (b) ILP-optimal per-column FA/HA counts.
Same bit matrix, same zero-bypass, same final adder. Exhaustively verified, then BTC flow."""
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pulp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTC = ROOT + r"\docs\Training2\ASIC"
WORK = ROOT + r"\build\work_asic\tree_rtl"
W = 16
FA_COST, HA_COST = 1.0, 0.6

bits = {c: [] for c in range(W)}
for i in range(8):
    for j in range(8):
        if i + j >= 6:
            bits[i + j].append(("nand" if (i == 7) != (j == 7) else "and", i, j))
A, B = [x.ravel() for x in np.meshgrid(np.arange(-128, 128), np.arange(-128, 128), indexing="ij")]
ua, ub = A & 255, B & 255
ab = [(ua >> i) & 1 for i in range(8)]
bb = [(ub >> i) & 1 for i in range(8)]
T = sum((ab[i] & bb[j]) << (i + j) for i in range(6) for j in range(6) if i + j < 6)
S = np.zeros_like(A)
for c, lst in bits.items():
    for kind, i, j in lst:
        v = ab[i] & bb[j]
        S += (1 - v if kind == "nand" else v) << c
nz = (A != 0) & (B != 0)
K = int(np.unique(((A * B - T + 81) - S)[nz] % (1 << W))[0])
const_cols = [c for c in range(W) if (K >> c) & 1]
heights = [len(bits[c]) + (1 if (K >> c) & 1 else 0) for c in range(W)]
EXPECT = np.where(nz, (A * B - T + 81) % (1 << W), 0)


def dadda_per_column():
    h = list(heights)
    fa_c, ha_c = [0] * W, [0] * W
    target = [2]
    while target[-1] < max(h):
        target.append(int(target[-1] * 3 / 2))
    for t in reversed(target[:-1]):
        carry = [0] * (W + 1)
        for c in range(W):
            n = h[c] + carry[c]
            while n > t:
                if n - t >= 2:
                    fa_c[c] += 1
                    n -= 2
                else:
                    ha_c[c] += 1
                    n -= 1
                carry[c + 1] += 1
            h[c] = n
    return fa_c, ha_c


def ilp_per_column():
    prob = pulp.LpProblem("tree", pulp.LpMinimize)
    f = {c: pulp.LpVariable(f"f{c}", 0, None, pulp.LpInteger) for c in range(W)}
    hv = {c: pulp.LpVariable(f"h{c}", 0, None, pulp.LpInteger) for c in range(W)}
    prob += pulp.lpSum(FA_COST * f[c] + HA_COST * hv[c] for c in range(W))
    for c in range(W):
        cin = (f[c - 1] + hv[c - 1]) if c > 0 else 0
        out = heights[c] + cin - 2 * f[c] - hv[c]
        prob += out <= 2
        prob += out >= 0
    prob.solve(pulp.HiGHS(msg=False))
    return [int(round(f[c].value())) for c in range(W)], [int(round(hv[c].value())) for c in range(W)]


def netlist(name, fa_c, ha_c):
    lines, carries_in = [], {c: [] for c in range(W + 1)}
    uid = [0]
    final = {c: [] for c in range(W)}
    for c in range(W):
        pool = [f"pp_{k}_{i}_{j}" for k, i, j in []]
        pool = []
        for kind, i, j in bits[c]:
            n = f"b_{c}_{i}_{j}"
            expr = f"~(ua[{i}] & ub[{j}])" if kind == "nand" else f"(ua[{i}] & ub[{j}])"
            lines.append(f"    wire {n} = {expr};")
            pool.append(n)
        if (K >> c) & 1:
            pool.append("1'b1")
        pool += carries_in[c]
        for _ in range(fa_c[c]):
            x, y, z = pool.pop(0), pool.pop(0), pool.pop(0)
            uid[0] += 1
            u = uid[0]
            lines.append(f"    wire s{u} = {x} ^ {y} ^ {z};")
            lines.append(f"    wire k{u} = ({x} & {y}) | ({z} & ({x} ^ {y}));")
            pool.append(f"s{u}")
            if c + 1 < W:
                carries_in[c + 1].append(f"k{u}")
        for _ in range(ha_c[c]):
            x, y = pool.pop(0), pool.pop(0)
            uid[0] += 1
            u = uid[0]
            lines.append(f"    wire s{u} = {x} ^ {y};")
            lines.append(f"    wire k{u} = {x} & {y};")
            pool.append(f"s{u}")
            if c + 1 < W:
                carries_in[c + 1].append(f"k{u}")
        assert len(pool) <= 2, f"column {c} left {len(pool)} bits"
        final[c] = pool
    v1 = [final[c][0] if len(final[c]) > 0 else "1'b0" for c in range(W)]
    v2 = [final[c][1] if len(final[c]) > 1 else "1'b0" for c in range(W)]
    rtl = f"""`timescale 1ns / 1ps
module {name} (
    input  wire signed [7:0]  a,
    input  wire signed [7:0]  b,
    output wire signed [15:0] p
);
    wire [7:0] ua = a;
    wire [7:0] ub = b;
    wire is_zero = (a == 8'sd0) | (b == 8'sd0);
{chr(10).join(lines)}
    wire [15:0] v1 = {{{', '.join(reversed(v1))}}};
    wire [15:0] v2 = {{{', '.join(reversed(v2))}}};
    wire [15:0] raw = v1 + v2;
    assign p = is_zero ? 16'sd0 : raw;
endmodule
"""
    return rtl


def wsl(p):
    p = os.path.abspath(p).replace("\\", "/")
    return f"/mnt/{p[0].lower()}{p[2:]}"


def sh(d, cmd):
    return subprocess.run(["wsl.exe", "-d", "Ubuntu", "bash", "-c", f"cd {wsl(d)} && {cmd} 2>&1"],
                          capture_output=True, text=True, timeout=1500).stdout


def run(item):
    name, (fa_c, ha_c) = item
    d = os.path.join(WORK, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8").write(netlist(name, fa_c, ha_c))
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    sh(d, "yosys -q eval.ys")
    got = {}
    for line in open(os.path.join(d, "eval.txt")):
        m = re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            got[(x, y)] = u
    bad = sum(1 for x, y, e in zip(A & 255, B & 255, EXPECT) if got.get((int(x), int(y))) != int(e))
    fa, ha = sum(fa_c), sum(ha_c)
    for f in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
        shutil.copy2(os.path.join(BTC, f), d)
    conv = open(os.path.join(BTC, "convolution_unit.v"), encoding="utf-8", errors="replace").read().replace("<Ten_Module>", name)
    open(os.path.join(d, "convolution_unit.v"), "w", encoding="utf-8").write(conv)
    open(os.path.join(d, "synthesis.ys"), "w").write(
        f"read_verilog convolution_unit.v\nread_verilog {name}.v\nsynth -top convolution_unit -flatten\nopt -purge\nopt\n"
        "dfflibmap -liberty normal.lib\nabc -liberty normal.lib\nclean\n"
        "tee -o area_report.txt stat -liberty normal.lib\nwrite_verilog -noattr Convolution.v\n")
    sh(d, "yosys synthesis.ys > yosys.log")
    sta = sh(d, "sta -exit run_sta.tcl")
    area = float(re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
    delay = float(re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
    power = float(re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
    return name, fa, ha, bad, area, delay, power


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    dfa, dha = dadda_per_column()
    ifa, iha = ilp_per_column()
    jobs = [("tree_dadda", (dfa, dha)), ("tree_ilp", (ifa, iha))]
    with ThreadPoolExecutor(2) as ex:
        rows = list(ex.map(run, jobs))
    print(f"{'variant':<12} {'FA':>3} {'HA':>3} {'bad/65536':>10} {'Area':>10} {'Delay':>8} {'Power mW':>9}")
    for r in rows:
        print(f"{r[0]:<12} {r[1]:>3} {r[2]:>3} {r[3]:>10} {r[4]:>10.3f} {r[5]:>8.4f} {r[6]:>9.4f}")
    print("reference candidate2 (BTC flow): 2745.386 um2, 1.5064 ns, 0.3150 mW")
