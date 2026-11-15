"""PPA-constrained sweep: extra column-6 pruning pays for Hamming-weight compensation. Limits: candidate2 convolution_unit."""
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTC = ROOT + r"\docs\Training2\ASIC"
WORK = ROOT + r"\build\work_asic\hw_v2"
LIMITS = (2745.386, 1.5064, 0.3150)
DROP_ORDER = [(3, 3), (2, 4), (4, 2), (1, 5), (5, 1), (0, 6), (6, 0)]

A, B = [x.ravel() for x in np.meshgrid(np.arange(-128, 128), np.arange(-128, 128), indexing="ij")]
ab = [((A & 255) >> i) & 1 for i in range(8)]
bb = [((B & 255) >> i) & 1 for i in range(8)]
EXACT = A * B
ZERO = (A == 0) | (B == 0)
maj = lambda x, y, z: (x & y) | (x & z) | (y & z)


def vmaj(n, i):
    return f"(({n}[{i}]&{n}[{i+1}])|({n}[{i}]&{n}[{i+2}])|({n}[{i+1}]&{n}[{i+2}]))"


def build(name, est, d, step):
    dropped = {(i, j) for i in range(8) for j in range(8) if i + j < 6} | set(DROP_ORDER[:d])
    T = sum((ab[i] & bb[j]) << (i + j) for i, j in dropped)
    lw = 6 if d == 0 else 7
    nz = (sum(ab[:lw]) > 0).astype(int) & (sum(bb[:lw]) > 0).astype(int)
    shift = {64: 6, 128: 7}[step]
    nzv = f"wire nz = (|ua[{lw-1}:0]) & (|ub[{lw-1}:0]);"
    if est == "maj":
        ma = maj(ab[0], ab[1], ab[2]) + maj(ab[3], ab[4], ab[5])
        mb = maj(bb[0], bb[1], bb[2]) + maj(bb[3], bb[4], bb[5])
        cls = nz * (1 + ma * 4 + mb)
        pre = f"wire [1:0] ma = {vmaj('ua',0)} + {vmaj('ua',3)};\n    wire [1:0] mb = {vmaj('ub',0)} + {vmaj('ub',3)};"
        sel, width, key = "{nz,ma,mb}", 5, (lambda v: 16 + v - 1 if v else 0)
    elif est == "maj1":
        cls = nz * (1 + maj(ab[0], ab[1], ab[2]) * 2 + maj(bb[0], bb[1], bb[2]))
        pre = f"wire ma = {vmaj('ua',0)};\n    wire mb = {vmaj('ub',0)};"
        sel, width, key = "{nz,ma,mb}", 3, (lambda v: 4 + v - 1 if v else 0)
    elif est == "nz":
        cls, pre, sel, width, key = nz, "", "nz", 1, (lambda v: v)
    else:  # static constant + full zero-bypass mux
        cls, pre, sel, width, key = np.ones_like(A), "", None, 0, None

    means = {int(v): T[cls == v].mean() for v in np.unique(cls)}
    if est == "static":
        means = {1: T[~ZERO].mean()}
    best = None
    for L in range(step):
        if bin(L).count("1") > 2:
            continue
        g = {v: (max(0, int(np.round((m - L) / step))) if v != 0 else 0) for v, m in means.items()}
        gc = np.array([g.get(i, 0) for i in range(int(cls.max()) + 1)])[cls]
        comp = gc * step + (L if est == "static" else L * nz)
        approx = EXACT - T + comp
        if est == "static":
            approx = np.where(ZERO, 0, approx)
        err = approx - EXACT
        score = np.abs(err).mean() + abs(err.mean())
        if best is None or score < best[0]:
            best = (score, L, g, approx)
    _, L, g, approx = best

    wbits = max(1, int(max(g.values())).bit_length())
    if est == "static":
        gblk = f"wire [{wbits-1}:0] g = {wbits}'d{g[1]};"
        low = f"{shift}'d{L}"
    else:
        arms = "\n".join(f"            {width}'d{key(v)}: g = {wbits}'d{g[v]};" for v in sorted(g))
        gblk = f"reg [{wbits-1}:0] g;\n    always @* begin\n        case ({sel})\n{arms}\n            default: g = {wbits}'d0;\n        endcase\n    end"
        low = f"(nz ? {shift}'d{L} : {shift}'d0)"

    lines, cols = [], {c: [] for c in range(16)}
    for i in range(8):
        for j in range(8):
            if (i, j) in dropped:
                continue
            n = f"pp_{i}_{j}"
            expr = f"~(ua[{i}] & ub[{j}])" if (i == 7) != (j == 7) else f"ua[{i}] & ub[{j}]"
            lines.append(f"    wire {n} = {expr};")
            cols[i + j].append(n)
    cols[8].append("1'b1")
    cols[15].append("1'b1")
    for b in range(wbits):
        cols[shift + b].append(f"g[{b}]")

    uid, body = 0, []
    maxh = max(len(v) for v in cols.values())
    for target in [t for t in (13, 9, 6, 4, 3, 2) if t < maxh]:
        nxt, carries = {c: [] for c in range(17)}, {c: [] for c in range(17)}
        for c in range(16):
            cur = list(cols[c])
            while len(cur) + len(nxt[c]) + len(carries[c]) > target:
                uid += 1
                over = len(cur) + len(nxt[c]) + len(carries[c]) - target
                if over == 1:
                    x, y = cur.pop(0), cur.pop(0)
                    body.append(f"    wire s{uid} = {x} ^ {y};\n    wire c{uid} = {x} & {y};")
                else:
                    x, y, z = cur.pop(0), cur.pop(0), cur.pop(0)
                    body.append(f"    wire s{uid} = {x} ^ {y} ^ {z};\n    wire c{uid} = ({x} & {y}) | ({z} & ({x} ^ {y}));")
                nxt[c].append(f"s{uid}")
                carries[c + 1].append(f"c{uid}")
            cols[c] = cur + nxt[c] + carries[c]
    v1 = [(cols[c] + ["1'b0", "1'b0"])[0] for c in range(shift, 16)]
    v2 = [(cols[c] + ["1'b0", "1'b0"])[1] for c in range(shift, 16)]
    w = 16 - shift
    out = "assign p = is_zero ? 16'sd0 : raw;" if est == "static" else "assign p = raw;"
    izero = "wire is_zero = (a == 8'sd0) | (b == 8'sd0);" if est == "static" else ""
    rtl = f"""`timescale 1ns / 1ps
module {name} (
    input  wire signed [7:0]  a,
    input  wire signed [7:0]  b,
    output wire signed [15:0] p
);
    wire [7:0] ua = a;
    wire [7:0] ub = b;
    {izero}
    {nzv if est != 'static' else ''}
    {pre}
    {gblk}
{chr(10).join(lines)}
{chr(10).join(body)}
    wire [{w-1}:0] v1 = {{{', '.join(reversed(v1))}}};
    wire [{w-1}:0] v2 = {{{', '.join(reversed(v2))}}};
    wire [{w-1}:0] hi = v1 + v2;
    wire [15:0] raw = {{hi, {low}}};
    {out}
endmodule
"""
    return rtl, approx


def wsl(p):
    p = os.path.abspath(p).replace("\\", "/")
    return f"/mnt/{p[0].lower()}{p[2:]}"


def sh(d, cmd):
    return subprocess.run(["wsl.exe", "-d", "Ubuntu", "bash", "-c", f"cd {wsl(d)} && {cmd} 2>&1"], capture_output=True, text=True, timeout=1500).stdout


def run(spec):
    est, dn, step = spec
    name = f"v_{est}_d{dn}_s{step}"
    rtl, approx = build(name, est, dn, step)
    d = os.path.join(WORK, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8").write(rtl)
    for f in ("normal.lib", "constraints.sdc", "run_sta.tcl"):
        shutil.copy2(os.path.join(BTC, f), d)
    conv = open(os.path.join(BTC, "convolution_unit.v"), encoding="utf-8", errors="replace").read().replace("<Ten_Module>", name)
    open(os.path.join(d, "convolution_unit.v"), "w", encoding="utf-8").write(conv)
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    sh(d, "yosys -q eval.ys")
    got = {}
    for line in open(os.path.join(d, "eval.txt")):
        m = re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            got[(x, y)] = u - 65536 if u > 32767 else u
    bad = sum(1 for x, y, e in zip(A & 255, B & 255, approx) if got.get((int(x), int(y))) != int(e))
    open(os.path.join(d, "synthesis.ys"), "w").write(f"read_verilog convolution_unit.v\nread_verilog {name}.v\nsynth -top convolution_unit -flatten\nopt -purge\nopt\ndfflibmap -liberty normal.lib\nabc -liberty normal.lib\nclean\ntee -o area_report.txt stat -liberty normal.lib\nwrite_verilog -noattr Convolution.v\n")
    sh(d, "yosys synthesis.ys > yosys.log")
    sta = sh(d, "sta -exit run_sta.tcl")
    open(os.path.join(d, "sta.log"), "w", encoding="utf-8").write(sta)
    area = float(re.search(r"Chip area for module '\\?convolution_unit':\s+([\d.]+)", open(os.path.join(d, "area_report.txt")).read()).group(1))
    delay = float(re.search(r"([\d.\-]+)\s+data arrival time", sta).group(1)) - 2.0
    power = float(re.search(r"Total\s+[\d.e+\-]+\s+[\d.e+\-]+\s+[\d.e+\-]+\s+([\d.e+\-]+)", sta).group(1)) * 1000
    e = approx - EXACT
    return name, bad, np.abs(e).mean(), e.mean(), int(np.abs(e).max()), area, delay, power


specs = [("static", 0, 64), ("nz", 0, 64), ("maj1", 0, 64), ("maj", 0, 64), ("maj1", 2, 64), ("maj", 2, 64), ("maj1", 4, 64), ("maj", 4, 64), ("maj1", 7, 128), ("maj", 7, 128), ("maj", 7, 64), ("static", 7, 128)]
os.makedirs(WORK, exist_ok=True)
with ThreadPoolExecutor(6) as ex:
    rows = list(ex.map(run, specs))
print(f"{'variant':<20} {'bad':>5} {'MAE':>8} {'ME':>7} {'MaxE':>5} {'Area':>10} {'Delay':>7} {'Power':>7} PASS")
for r in rows:
    ok = r[5] <= LIMITS[0] and r[6] <= LIMITS[1] and r[7] <= LIMITS[2]
    print(f"{r[0]:<20} {r[1]:>5} {r[2]:>8.3f} {r[3]:>7.3f} {r[4]:>5} {r[5]:>10.3f} {r[6]:>7.4f} {r[7]:>7.4f} {'YES' if ok else 'no'}")
