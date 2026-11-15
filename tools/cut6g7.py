"""Cut column 6 + compensation g in 0..7 (3 bits at cols 6,7,8). comp = 64*g + 40*nz.
Table from cut6_range.py (per-class choice over 5 distributions). Netlist verified vs model; then BTC flow, standalone PPA."""
import os, re, shutil, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G
import hwmaj_ilp as H
import standalone_ppa as SP

ROOT = G.ROOT
OUT = os.path.join(ROOT, "build", "work_asic", "cut6g7")
NAME = "cut6g7_ilp5_asic"
W = 16
GTAB = {(0, 0): 0, (0, 1): 1, (0, 2): 2, (1, 0): 1, (1, 1): 2, (1, 2): 4, (2, 0): 2, (2, 1): 4, (2, 2): 6}

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
g_of = np.zeros_like(A)
for (x, y), gv in GTAB.items():
    g_of[nz & (ma == x) & (mb == y)] = gv
COMP = 64 * g_of + 40 * nz.astype(int)
APPROX = EXACT - T6 + COMP
e = APPROX - EXACT
print(f"model: MAE={np.abs(e).mean():.3f} ME={e.mean():+.3f} MaxE={int(np.abs(e).max())}")

bits = {c: [] for c in range(W)}
for i in range(8):
    for j in range(8):
        if i + j >= 7:
            bits[i + j].append(("nand" if (i == 7) != (j == 7) else "and", i, j))
for c, name in ((3, "comp[3]"), (5, "comp[5]"), (6, "comp[6]"), (7, "comp[7]"), (8, "comp[8]")):
    bits[c].append(("sig", name, None))
for c in (8, 15):
    bits[c].append(("const", "1'b1", None))
H.bits.clear(); H.bits.update(bits)
H.heights[:] = [len(bits[c]) for c in range(W)]
print("heights:", H.heights)


def rtl(fa, ha):
    arms = "\n".join(f"            5'd{16 + a * 4 + b}: g = 3'd{v};" for (a, b), v in sorted(GTAB.items()) if v)
    hdr = f"""`timescale 1ns / 1ps
module {NAME} (
    input  wire signed [7:0]  a,
    input  wire signed [7:0]  b,
    output wire signed [15:0] p
);
    wire [7:0] ua = a;
    wire [7:0] ub = b;
    wire [1:0] ma = ((ua[0]&ua[1])|(ua[0]&ua[2])|(ua[1]&ua[2])) + ((ua[3]&ua[4])|(ua[3]&ua[5])|(ua[4]&ua[5]));
    wire [1:0] mb = ((ub[0]&ub[1])|(ub[0]&ub[2])|(ub[1]&ub[2])) + ((ub[3]&ub[4])|(ub[3]&ub[5])|(ub[4]&ub[5]));
    wire nz = (|ua[5:0]) & (|ub[5:0]);
    reg [2:0] g;
    always @* begin
        case ({{nz,ma,mb}})
{arms}
            default: g = 3'd0;
        endcase
    end
    wire [8:0] comp = {{g, nz, 1'b0, nz, 3'b000}};
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


def load(p):
    out = {}
    for line in open(p):
        m = re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            out[(x, y)] = u
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    S = int(os.environ.get("S", "5"))
    fa, ha = H.solve(S)
    NAME_S = f"{NAME}_s{S}"
    d = os.path.join(OUT, NAME_S)
    os.makedirs(d, exist_ok=True)
    src = os.path.join(d, f"{NAME_S}.v")
    open(src, "w", encoding="utf-8", newline="\n").write(rtl(fa, ha).replace(f"module {NAME} ", f"module {NAME_S} "))
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {NAME_S}.v\nsynth -top {NAME_S} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    got = load(os.path.join(d, "eval.txt"))
    exp = APPROX % (1 << 16)
    bad = sum(1 for x, y, v in zip(A & 255, B & 255, exp) if got.get((int(x), int(y))) != int(v))
    print("netlist mismatches vs model:", bad, "/ 65536")
    for fn in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
        shutil.copy2(os.path.join(G.BTC, fn), d)
    conv = open(os.path.join(G.BTC, "convolution_unit.v"), encoding="utf-8", errors="replace").read().replace("<Ten_Module>", NAME_S)
    open(os.path.join(d, "convolution_unit.v"), "w", encoding="utf-8").write(conv)
    open(os.path.join(d, "synthesis.ys"), "w").write(
        f"read_verilog convolution_unit.v\nread_verilog {NAME_S}.v\nsynth -top convolution_unit -flatten\nopt -purge\nopt\n"
        "dfflibmap -liberty normal.lib\nabc -liberty normal.lib\nclean\n"
        "tee -o area_report.txt stat -liberty normal.lib\nwrite_verilog -noattr Convolution.v\n")
    G.sh(d, "yosys synthesis.ys > yosys.log")
    sta = G.sh(d, "sta -exit run_sta.tcl")
    open(os.path.join(d, "sta.log"), "w", encoding="utf-8").write(sta)
    area = float(re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
    delay = float(re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
    power = float(re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
    print(f"convolution_unit: area={area:.3f} delay={delay:.4f} power={power:.4f} mW")
    sa, sd, sp = SP.measure(NAME_S, src)
    print(f"standalone: area={sa:.3f} delay={sd:.4f} power={sp:.4f} mW")
