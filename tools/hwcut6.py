"""Experiment: also truncate column 6 (7 AND products), refit compensation, ILP tree (5 stages), exhaustive check, BTC flow.
Compensation: comp = 64*g + L*nz with g in 0..3 (bits 6,7) and L (bits 3,5 when L=40)."""
import os, re, shutil, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G
import hwmaj_ilp as H

ROOT = G.ROOT
OUT = os.path.join(ROOT, "build", "work_asic", "hwcut6")
W = 16
A, B = [x.ravel() for x in np.meshgrid(np.arange(-128, 128), np.arange(-128, 128), indexing="ij")]
ua, ub = A & 255, B & 255
ab = [(ua >> i) & 1 for i in range(8)]
bb = [(ub >> i) & 1 for i in range(8)]
EXACT = A * B
nz = ((ua & 63) != 0) & ((ub & 63) != 0)
maj = lambda x, y, z: (x & y) | (x & z) | (y & z)
ma = maj(ab[0], ab[1], ab[2]) + maj(ab[3], ab[4], ab[5])
mb = maj(bb[0], bb[1], bb[2]) + maj(bb[3], bb[4], bb[5])
T6 = sum((ab[i] & bb[j]) << (i + j) for i in range(8) for j in range(8) if i + j <= 6)
cls = nz.astype(int) * (1 + ma * 4 + mb)

best = None
for L in [40]:
    means = {int(v): T6[cls == v].mean() for v in np.unique(cls)}
    g = {v: (max(0, min(3, int(np.round((m - L) / 64)))) if v != 0 else 0) for v, m in means.items()}
    gc = np.array([g.get(i, 0) for i in range(int(cls.max()) + 1)])[cls]
    comp = 64 * gc + L * nz
    approx = EXACT - T6 + comp
    err = approx - EXACT
    score = np.abs(err).mean() + abs(err.mean())
    if best is None or score < best[0]:
        best = (score, L, g, approx)
_, LBEST, GTAB, APPROX = best
print("best L =", LBEST, "g table =", GTAB)
e = APPROX - EXACT
print(f"model: MAE={np.abs(e).mean():.3f} ME={e.mean():+.3f} MaxE={int(np.abs(e).max())}")

# ---- bit matrix: PPs cols 7..14, nz at 3,5, g0 at 6, g1 at 7, BW constants at 8, 15 ----
bits = {c: [] for c in range(W)}
for i in range(8):
    for j in range(8):
        if i + j >= 7:
            bits[i + j].append(("nand" if (i == 7) != (j == 7) else "and", i, j))
for c, name in ((3, "comp[3]"), (5, "comp[5]"), (6, "comp[6]"), (7, "comp[7]")):
    bits[c].append(("sig", name, None))
for c in (8, 15):
    bits[c].append(("const", "1'b1", None))
H.bits.clear(); H.bits.update(bits)
H.heights[:] = [len(bits[c]) for c in range(W)]
print("heights:", H.heights)


def rtl(name, fa, ha):
    gcase = "\n".join(
        f"            5'd{(1 << 4) | (a << 2) | b}: g = 2'd{GTAB.get(a * 4 + b + 0, 0) if False else 0};"
        for a in range(3) for b in range(3))
    arms = []
    for a_ in range(3):
        for b_ in range(3):
            v_key = None
    # explicit table over (nz, ma, mb)
    arms = []
    for a_ in range(3):
        for b_ in range(3):
            key = a_ * 4 + b_  # cls index used in fit: 1 + ma*4 + mb
            gv = GTAB.get(1 + a_ * 4 + b_, 0)
            if gv:
                arms.append(f"            5'd{16 + a_ * 4 + b_}: g = 2'd{gv};")
    armstxt = "\n".join(arms)
    hdr = f"""`timescale 1ns / 1ps
module {name} (
    input  wire signed [7:0]  a,
    input  wire signed [7:0]  b,
    output wire signed [15:0] p
);
    wire [7:0] ua = a;
    wire [7:0] ub = b;
    wire [1:0] ma = ((ua[0]&ua[1])|(ua[0]&ua[2])|(ua[1]&ua[2])) + ((ua[3]&ua[4])|(ua[3]&ua[5])|(ua[4]&ua[5]));
    wire [1:0] mb = ((ub[0]&ub[1])|(ub[0]&ub[2])|(ub[1]&ub[2])) + ((ub[3]&ub[4])|(ub[3]&ub[5])|(ub[4]&ub[5]));
    wire nz = (|ua[5:0]) & (|ub[5:0]);
    reg [1:0] g;
    always @* begin
        case ({{nz,ma,mb}})
{armstxt}
            default: g = 2'd0;
        endcase
    end
    wire [7:0] comp = {{g, nz, 1'b0, nz, 3'b000}};
"""
    lines, uid = [], 0
    pool = {c: [] for c in range(W)}
    for c in range(W):
        for kind, x, y in H.bits[c]:
            if kind in ("and", "nand"):
                n = f"pp_{x}_{y}_{c}"
                expr = f"~(ua[{x}] & ub[{y}])" if kind == "nand" else f"(ua[{x}] & ub[{y}])"
                lines.append(f"    wire {n} = {expr};")
                pool[c].append(n)
            else:
                pool[c].append(x)
    for s in range(len(fa)):
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
    v1 = [pool[c][0] if len(pool[c]) > 0 else "1'b0" for c in range(W)]
    v2 = [pool[c][1] if len(pool[c]) > 1 else "1'b0" for c in range(W)]
    tail = f"""    wire [15:0] v1 = {{{', '.join(reversed(v1))}}};
    wire [15:0] v2 = {{{', '.join(reversed(v2))}}};
    assign p = v1 + v2;
endmodule
"""
    return hdr + "\n".join(lines) + "\n" + tail


def run():
    fa, ha = H.solve(5)
    name = "hwcut6_ilp5"
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8", newline="\n").write(rtl(name, fa, ha))
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    got = {}
    for line in open(os.path.join(d, "eval.txt")):
        m = re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            got[(x, y)] = u
    expect = (EXACT - T6 + (64 * np.array([GTAB.get(1 + 4 * 0, 0)] * 0 + [0] * 0 or [0]) if False else 0))
    expect = APPROX % (1 << 16)
    bad = sum(1 for x, y, e_ in zip(A & 255, B & 255, expect) if got.get((int(x), int(y))) != int(e_) % (1 << 16))
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
    return bad, area, delay, power


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    bad, area, delay, power = run()
    print(f"netlist mismatches vs model: {bad}/65536")
    print(f"convolution_unit: area={area:.3f} delay={delay:.4f} power={power:.4f} mW")
    print("ref hw_maj_s64 ILP5: 2891.154 / 1.5058 / 0.328 ; candidate2_ilp5: 2746.982 / 1.4709 / 0.313")
