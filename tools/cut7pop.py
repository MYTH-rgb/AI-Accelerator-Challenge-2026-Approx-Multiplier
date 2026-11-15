"""Cut columns 0..6 (7 cut) with popcount-grouped compensation: 16 classes (4 levels per operand), 8-bit constant per class.
Partition {0,1},{2},{3,4},{5,6,7} of popcount(7 low bits). Constants fitted on seed-1 data (images 0..199, 4 distributions).
Pipeline: fit -> netlist (ILP tree) -> exhaustive check vs model -> BTC convolution_unit -> standalone PPA."""
import glob, os, re, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G
import hwmaj_ilp as H
import standalone_ppa as SP

ROOT = G.ROOT
NAME = "cut7pop_asic"
OUT = os.path.join(ROOT, "build", "work_asic", "cut7pop")
W = 16
LAB = np.array([0, 0, 1, 2, 2, 3, 3, 3])  # popcount -> level

rng = np.random.default_rng(1)
N = 200000
def clip8(x): return np.clip(np.round(x), -128, 127).astype(int)
files = sorted(glob.glob(os.path.join(G.ROOT, "docs", "Training2", "ASIC", "MNIST_Images", "image_*_bin.txt")))[:200]
pix = np.concatenate([np.array([int(l.strip(), 2) for l in open(f) if l.strip()]) for f in files])
rw = re.findall(r"\b\d+'d(\d+)\s*:\s*data\s*=\s*(-?)\s*8'sd(\d+);",
                open(os.path.join(ROOT, "build", "work_sim", "cnn_dadda", "conv2d_kernel_rom.v"), encoding="utf-8", errors="replace").read())
wts = np.array([(-1 if s == "-" else 1) * int(v) for _, s, v in sorted(rw, key=lambda r: int(r[0]))])
dists = {
    "uniform": (rng.integers(-128, 128, N), rng.integers(-128, 128, N)),
    "relu_gauss": (np.clip(clip8(rng.normal(0, 30, N)), 0, 127), clip8(rng.normal(0, 30, N))),
    "laplace30": (clip8(rng.laplace(0, 30, N)), clip8(rng.laplace(0, 30, N))),
    "mnist": (rng.choice(pix, N), rng.choice(wts, N)),
}


def prep(a, b):
    ua, ub = a & 255, b & 255
    ab = [(ua >> i) & 1 for i in range(8)]
    bb = [(ub >> i) & 1 for i in range(8)]
    T = sum((ab[i] & bb[j]) << (i + j) for i in range(8) for j in range(8) if i + j <= 6)
    pa = sum(ab[i] for i in range(7))
    pb = sum(bb[i] for i in range(7))
    gate = ((ua & 127) != 0) & ((ub & 127) != 0)
    return pa, pb, T, gate


data = {n: prep(a, b) for n, (a, b) in dists.items()}

# fit per-class constants
cls, keys = {}, set()
for n, (pa, pb, T, gate) in data.items():
    cid = LAB[pa] * 10 + LAB[pb]
    cls[n] = (cid, T, gate)
    keys |= set(np.unique(cid[gate]).tolist())
TABLE = {}
for c in sorted(keys):
    sc = np.zeros(256)
    for n in dists:
        cid, T, gate = cls[n]
        m = gate & (cid == c)
        if m.sum():
            sc += np.array([np.abs(C - T[m]).mean() for C in range(256)])
    TABLE[c] = int(np.argmin(sc))
print("class table (la*10+lb -> C):", TABLE)


def model(a, b):
    ua, ub = a & 255, b & 255
    pa = np.array([bin(int(x) & 127).count("1") for x in ua])
    pb = np.array([bin(int(x) & 127).count("1") for x in ub])
    gate = ((ua & 127) != 0) & ((ub & 127) != 0)
    c = LAB[pa] * 10 + LAB[pb]
    comp = np.array([TABLE.get(int(v), 0) for v in c]) * gate
    return comp


# ---- netlist ----
bits = {c: [] for c in range(W)}
for i in range(8):
    for j in range(8):
        if i + j >= 7:
            bits[i + j].append(("nand" if (i == 7) != (j == 7) else "and", i, j))
for c in range(8):
    bits[c].append(("sig", f"comp[{c}]", None))
for c in (8, 15):
    bits[c].append(("const", "1'b1", None))
H.bits.clear(); H.bits.update(bits)
H.heights[:] = [len(bits[c]) for c in range(W)]


def rtl(name, fa, ha):
    la_case = "\n".join(f"            3'd{p}: la = 2'd{LAB[p]};" for p in range(8))
    lb_case = la_case.replace("la =", "lb =")
    tab = "\n".join(f"            4'd{k}: cval = 8'd{TABLE.get(((k // 4) * 10) + (k % 4), 0)};" for k in range(16)) \
        if False else ""
    arms = []
    for la_ in range(4):
        for lb_ in range(4):
            c = la_ * 10 + lb_
            arms.append(f"            4'd{la_ * 4 + lb_}: cval = 8'd{TABLE.get(c, 0)};")
    arms = "\n".join(arms)
    hdr = f"""`timescale 1ns / 1ps
module {name} (
    input  wire signed [7:0]  a,
    input  wire signed [7:0]  b,
    output wire signed [15:0] p
);
    wire [7:0] ua = a;
    wire [7:0] ub = b;
    wire [2:0] pa = ua[0] + ua[1] + ua[2] + ua[3] + ua[4] + ua[5] + ua[6];
    wire [2:0] pb = ub[0] + ub[1] + ub[2] + ub[3] + ub[4] + ub[5] + ub[6];
    reg [1:0] la, lb;
    always @* begin
        case (pa)
{la_case}
            default: la = 2'd0;
        endcase
        case (pb)
{lb_case}
            default: lb = 2'd0;
        endcase
    end
    wire gate = (|ua[6:0]) & (|ub[6:0]);
    reg [7:0] cval;
    always @* begin
        case ({{la, lb}})
{arms}
            default: cval = 8'd0;
        endcase
    end
    wire [7:0] comp = gate ? cval : 8'd0;
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
            elif kind == "sig":
                pool[c].append(f"comp[{c}]")
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
    fa, ha = H.solve(5)
    d = os.path.join(OUT, NAME)
    os.makedirs(d, exist_ok=True)
    src = os.path.join(d, f"{NAME}.v")
    open(src, "w", encoding="utf-8", newline="\n").write(rtl(NAME, fa, ha))
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {NAME}.v\nsynth -top {NAME} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    got = load(os.path.join(d, "eval.txt"))
    A, B = [x.ravel() for x in np.meshgrid(np.arange(-128, 128), np.arange(-128, 128), indexing="ij")]
    ua, ub = A & 255, B & 255
    ab = [(ua >> i) & 1 for i in range(8)]
    bb = [(ub >> i) & 1 for i in range(8)]
    T = sum((ab[i] & bb[j]) << (i + j) for i in range(8) for j in range(8) if i + j <= 6)
    comp = model(A, B)
    exp = (A * B - T + comp) % (1 << 16)
    bad = sum(1 for x, y, v in zip(A & 255, B & 255, exp) if got.get((int(x), int(y))) != int(v))
    print("netlist mismatches vs model:", bad, "/ 65536")
    err = (exp.astype(np.int64) - (A * B) % (1 << 16))
    err = np.where(err > 32767, err - 65536, err)
    print(f"model (signed error): MAE={np.abs(err).mean():.3f} ME={err.mean():+.3f} MaxE={int(np.abs(err).max())}")
    for fn in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
        shutil.copy2(os.path.join(G.BTC, fn), d) if False else None
    import shutil
    for fn in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
        shutil.copy2(os.path.join(G.BTC, fn), d)
    conv = open(os.path.join(G.BTC, "convolution_unit.v"), encoding="utf-8", errors="replace").read().replace("<Ten_Module>", NAME)
    open(os.path.join(d, "convolution_unit.v"), "w", encoding="utf-8").write(conv)
    open(os.path.join(d, "synthesis.ys"), "w").write(
        f"read_verilog convolution_unit.v\nread_verilog {NAME}.v\nsynth -top convolution_unit -flatten\nopt -purge\nopt\n"
        "dfflibmap -liberty normal.lib\nabc -liberty normal.lib\nclean\n"
        "tee -o area_report.txt stat -liberty normal.lib\nwrite_verilog -noattr Convolution.v\n")
    G.sh(d, "yosys synthesis.ys > yosys.log")
    sta = G.sh(d, "sta -exit run_sta.tcl")
    open(os.path.join(d, "sta.log"), "w", encoding="utf-8").write(sta)
    area = float(re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
    delay = float(re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
    power = float(re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
    print(f"convolution_unit: area={area:.3f} delay={delay:.4f} power={power:.4f} mW")
    sa, sd, sp = SP.measure(NAME, src)
    print(f"standalone: area={sa:.3f} delay={sd:.4f} power={sp:.4f} mW")
