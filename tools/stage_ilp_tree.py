"""Depth-constrained ILP tree: S reduction stages (FA/HA levels), min cells, then same BTC flow and exhaustive check.
Uses the bit matrix, constant K, zero-bypass and final adder from gen_tree_rtl.py."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pulp

sys.path.insert(0, os.path.dirname(__file__))
import gen_tree_rtl as G

W = G.W
FA_COST, HA_COST = 1.0, 0.6


def solve(S):
    prob = pulp.LpProblem(f"tree_s{S}", pulp.LpMinimize)
    f = {(s, c): pulp.LpVariable(f"f_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S) for c in range(W)}
    h = {(s, c): pulp.LpVariable(f"h_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S) for c in range(W)}
    H = {(s, c): pulp.LpVariable(f"H_{s}_{c}", 0, None, pulp.LpInteger) for s in range(S + 1) for c in range(W)}
    prob += pulp.lpSum(FA_COST * f[k] + HA_COST * h[k] for k in f)
    for c in range(W):
        prob += H[(0, c)] == G.heights[c]
        prob += H[(S, c)] <= 2
    for s in range(S):
        for c in range(W):
            prob += 3 * f[(s, c)] + 2 * h[(s, c)] <= H[(s, c)]
            cin = (f[(s, c - 1)] + h[(s, c - 1)]) if c > 0 else 0
            prob += H[(s + 1, c)] == H[(s, c)] - 2 * f[(s, c)] - h[(s, c)] + cin
    status = prob.solve(pulp.HiGHS(msg=False))
    assert pulp.LpStatus[status] == "Optimal", pulp.LpStatus[status]
    fa = [[int(round(f[(s, c)].value())) for c in range(W)] for s in range(S)]
    ha = [[int(round(h[(s, c)].value())) for c in range(W)] for s in range(S)]
    return fa, ha


def staged_netlist(name, fa, ha):
    S = len(fa)
    pool = {c: [] for c in range(W)}
    lines = []
    for c in range(W):
        for kind, i, j in G.bits[c]:
            n = f"b_{c}_{i}_{j}"
            expr = f"~(ua[{i}] & ub[{j}])" if kind == "nand" else f"(ua[{i}] & ub[{j}])"
            lines.append(f"    wire {n} = {expr};")
            pool[c].append(n)
        if (G.K >> c) & 1:
            pool[c].append("1'b1")
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
        assert len(pool[c]) <= 2, f"column {c} has {len(pool[c])} bits"
    v1 = [pool[c][0] if len(pool[c]) > 0 else "1'b0" for c in range(W)]
    v2 = [pool[c][1] if len(pool[c]) > 1 else "1'b0" for c in range(W)]
    return f"""`timescale 1ns / 1ps
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


def job(args):
    S = args
    fa, ha = solve(S)
    name = f"tree_stage{S}"
    rtl = staged_netlist(name, fa, ha)
    d = os.path.join(G.WORK, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8").write(rtl)
    import re
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    got = {}
    for line in open(os.path.join(d, "eval.txt")):
        m = re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            got[(x, y)] = u
    bad = sum(1 for x, y, e in zip(G.A & 255, G.B & 255, G.EXPECT) if got.get((int(x), int(y))) != int(e))
    import shutil
    for fn in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
        shutil.copy2(os.path.join(G.BTC, fn), d)
    conv = open(os.path.join(G.BTC, "convolution_unit.v"), encoding="utf-8", errors="replace").read().replace("<Ten_Module>", name)
    open(os.path.join(d, "convolution_unit.v"), "w", encoding="utf-8").write(conv)
    open(os.path.join(d, "synthesis.ys"), "w").write(
        f"read_verilog convolution_unit.v\nread_verilog {name}.v\nsynth -top convolution_unit -flatten\nopt -purge\nopt\n"
        "dfflibmap -liberty normal.lib\nabc -liberty normal.lib\nclean\n"
        "tee -o area_report.txt stat -liberty normal.lib\nwrite_verilog -noattr Convolution.v\n")
    G.sh(d, "yosys synthesis.ys > yosys.log")
    sta = G.sh(d, "sta -exit run_sta.tcl")
    area = float(re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
    delay = float(re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
    power = float(re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
    return S, sum(map(sum, fa)), sum(map(sum, ha)), bad, area, delay, power


if __name__ == "__main__":
    os.makedirs(G.WORK, exist_ok=True)
    with ThreadPoolExecutor(2) as ex:
        rows = list(ex.map(job, [4, 5]))
    print(f"{'stages':>6} {'FA':>3} {'HA':>3} {'bad':>5} {'Area':>10} {'Delay':>8} {'Power':>8}")
    for r in rows:
        print(f"{r[0]:>6} {r[1]:>3} {r[2]:>3} {r[3]:>5} {r[4]:>10.3f} {r[5]:>8.4f} {r[6]:>8.4f}")
    print("reference candidate2: 2745.386 um2, 1.5064 ns, 0.3150 mW")
