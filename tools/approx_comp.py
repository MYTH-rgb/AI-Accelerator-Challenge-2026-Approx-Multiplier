"""Approximate compressors in the low columns of the hwmaj ILP-5 tree.
Types: FA 'or'  -> sum = x|y|z, carry = exact majority  (errors only when exactly two inputs are 1: +2^c)
       HA 'or'  -> sum = x|y,   carry = x&y             (error only when both 1: +2^c)
Variants apply the approximation to all FA/HA with column <= K. Metrics: exhaustive 65,536 error + weighted pixel x weight error
+ BTC convolution_unit PPA."""
import glob, os, re, shutil, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G
import hwmaj_ilp as H

ROOT, BTC = G.ROOT, G.BTC
OUT = os.path.join(ROOT, "build", "work_asic", "approx_comp")
W = 16


def netlist(name, fa, ha, kfa, kha):
    hdr = open(H.HW_RTL, encoding="utf-8").read().split("    // =========================================================================\n    // DADDA STAGE 1")[0]
    hdr = hdr.replace("module hw_maj_s64", f"module {name}")
    hdr = re.sub(r"\n    // Retained 43.*?\n\n", "\n", hdr, flags=re.S)
    pool, lines, uid = {c: [] for c in range(W)}, [], 0
    for c in range(W):
        for kind, a, b in H.bits[c]:
            if kind in ("and", "nand"):
                n = f"pp_{a}_{b}_{c}"
                lines.append(f"    wire {n} = " + (f"~(ua[{a}] & ub[{b}]);" if kind == "nand" else f"(ua[{a}] & ub[{b}]);"))
                pool[c].append(n)
            else:
                pool[c].append(a)
    napx = 0
    for s in range(len(fa)):
        nxt = {c: [] for c in range(W)}
        for c in range(W):
            cur = list(pool[c])
            for _ in range(fa[s][c]):
                x, y, z = cur.pop(0), cur.pop(0), cur.pop(0)
                uid += 1
                if c <= kfa:
                    lines.append(f"    wire s{uid} = {x} | {y} | {z};")
                    napx += 1
                else:
                    lines.append(f"    wire s{uid} = {x} ^ {y} ^ {z};")
                lines.append(f"    wire k{uid} = ({x} & {y}) | ({z} & ({x} ^ {y}));" if c > kfa else f"    wire k{uid} = ({x} & {y}) | ({x} & {z}) | ({y} & {z});")
                nxt[c].append(f"s{uid}")
                if c + 1 < W:
                    nxt[c + 1].append(f"k{uid}")
            for _ in range(ha[s][c]):
                x, y = cur.pop(0), cur.pop(0)
                uid += 1
                if c <= kha:
                    lines.append(f"    wire s{uid} = {x} | {y};")
                    napx += 1
                else:
                    lines.append(f"    wire s{uid} = {x} ^ {y};")
                lines.append(f"    wire k{uid} = {x} & {y};")
                nxt[c].append(f"s{uid}")
                if c + 1 < W:
                    nxt[c + 1].append(f"k{uid}")
            nxt[c] = cur + nxt[c]
        pool = nxt
    v1 = [pool[c][0] if len(pool[c]) > 0 else "1'b0" for c in range(W)]
    v2 = [pool[c][1] if len(pool[c]) > 1 else "1'b0" for c in range(W)]
    tail = f"    wire [15:0] v1 = {{{', '.join(reversed(v1))}}};\n    wire [15:0] v2 = {{{', '.join(reversed(v2))}}};\n    assign p = v1 + v2;\nendmodule\n"
    return hdr + "\n".join(lines) + "\n" + tail, napx


# weights for MNIST-like pair distribution
files = sorted(glob.glob(os.path.join(ROOT, "docs", "Training2", "ASIC", "MNIST_Images", "image_*_bin.txt")))[:300]
pix = np.concatenate([np.array([int(l.strip(), 2) for l in open(f) if l.strip()]) for f in files])
rw = re.findall(r"\b\d+'d(\d+)\s*:\s*data\s*=\s*(-?)\s*8'sd(\d+);",
                open(os.path.join(ROOT, "build", "work_sim", "cnn_dadda", "conv2d_kernel_rom.v"), encoding="utf-8", errors="replace").read())
wts = np.array([(-1 if s == "-" else 1) * int(v) for _, s, v in sorted(rw, key=lambda r: int(r[0]))])
hp = np.bincount(pix & 255, minlength=256) / len(pix)
hw = np.bincount(wts & 255, minlength=256) / len(wts)
PW = np.outer(hp, hw)  # P(a=ua, b=ub)


def load(p):
    out = {}
    for line in open(p):
        m = re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            out[(x, y)] = u
    return out


def run(cfg):
    name, kfa, kha = cfg
    fa, ha = H.solve(5)
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    src, napx = netlist(name, fa, ha, kfa, kha)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8", newline="\n").write(src)
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    got = load(os.path.join(d, "eval.txt"))
    err_u, err_w, mx = 0.0, 0.0, 0
    for (x, y), u in got.items():
        sa = x - 256 if x > 127 else x
        sb = y - 256 if y > 127 else y
        e = ((u - sa * sb + 32768) % 65536) - 32768
        err_u += abs(e)
        err_w += abs(e) * PW[x, y]
        mx = max(mx, abs(e))
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
    area = float(re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
    delay = float(re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
    power = float(re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
    return name, napx, err_u / 65536, err_w, mx, area, delay, power


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cfgs = [("ax_none", -1, -1), ("ax_fa6", 6, -1), ("ax_fa6_ha6", 6, 6), ("ax_fa7_ha7", 7, 7), ("ax_fa8_ha8", 8, 8)]
    with ThreadPoolExecutor(2) as ex:
        rows = list(ex.map(run, cfgs))
    print(f"{'variant':<12}{'#apx':>5}{'MAE_unif':>10}{'MAE_mnist':>10}{'MaxE':>7}{'Area':>10}{'Delay':>8}{'Power':>8}")
    for r in rows:
        print(f"{r[0]:<12}{r[1]:>5}{r[2]:>10.2f}{r[3]:>10.2f}{r[4]:>7}{r[5]:>10.3f}{r[6]:>8.4f}{r[7]:>8.4f}")
    print("reference hwmaj_ilp5_asic: 2891.154 um2, 1.5058 ns, 0.328 mW; MAE uniform 27.29")
