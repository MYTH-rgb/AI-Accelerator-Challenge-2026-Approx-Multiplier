"""hwmaj tree variants, same function as hw_maj_s64:
 - ILP stage count S in {5,6,7}
 - order 'orig' (as hwmaj_ilp5) or 'arr' (timing-aware: each column pool sorted by estimated arrival; the latest of each
   FA triple goes to the z input, which has the shorter path through the FA). comp bits get a later arrival estimate.
Verify 0/65,536 vs hw_maj_s64 table, then BTC convolution_unit PPA."""
import os, re, shutil, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G
import hwmaj_ilp as H

ROOT, BTC, W = G.ROOT, G.BTC, 16
OUT = os.path.join(ROOT, "build", "work_asic", "tree_timing")
T_PP, T_COMP = 1.0, 3.5  # NAND/AND ~1 level; majority + add + table ~3-4 levels


def netlist(name, fa, ha, order):
    hdr = open(H.HW_RTL, encoding="utf-8").read().split("    // =========================================================================\n    // DADDA STAGE 1")[0]
    hdr = hdr.replace("module hw_maj_s64", f"module {name}")
    hdr = re.sub(r"\n    // Retained 43.*?\n\n", "\n", hdr, flags=re.S)
    pool, lines, uid, t = {c: [] for c in range(W)}, [], 0, {}
    for c in range(W):
        for kind, a, b in H.bits[c]:
            if kind in ("and", "nand"):
                n = f"pp_{a}_{b}_{c}"
                lines.append(f"    wire {n} = " + (f"~(ua[{a}] & ub[{b}]);" if kind == "nand" else f"(ua[{a}] & ub[{b}]);"))
                t[n] = T_PP
            else:
                n = a
                t[n] = T_COMP if kind == "sig" else 0.0
            pool[c].append(n)
    for s in range(len(fa)):
        nxt = {c: [] for c in range(W)}
        for c in range(W):
            cur = list(pool[c])
            if order == "arr":
                cur.sort(key=lambda n: t[n])
            for _ in range(fa[s][c]):
                x, y, z = cur.pop(0), cur.pop(0), cur.pop(0)
                uid += 1
                lines.append(f"    wire s{uid} = {x} ^ {y} ^ {z};")
                lines.append(f"    wire k{uid} = ({x} & {y}) | ({z} & ({x} ^ {y}));")
                ts = max(max(t[x], t[y]) + 2.0, t[z] + 1.0)
                t[f"s{uid}"], t[f"k{uid}"] = ts, ts
                nxt[c].append(f"s{uid}")
                if c + 1 < W:
                    nxt[c + 1].append(f"k{uid}")
            for _ in range(ha[s][c]):
                x, y = cur.pop(0), cur.pop(0)
                uid += 1
                lines.append(f"    wire s{uid} = {x} ^ {y};")
                lines.append(f"    wire k{uid} = {x} & {y};")
                t[f"s{uid}"] = t[f"k{uid}"] = max(t[x], t[y]) + 1.0
                nxt[c].append(f"s{uid}")
                if c + 1 < W:
                    nxt[c + 1].append(f"k{uid}")
            nxt[c] = cur + nxt[c]
        pool = nxt
    v1 = [pool[c][0] if len(pool[c]) > 0 else "1'b0" for c in range(W)]
    v2 = [pool[c][1] if len(pool[c]) > 1 else "1'b0" for c in range(W)]
    tail = f"    wire [15:0] v1 = {{{', '.join(reversed(v1))}}};\n    wire [15:0] v2 = {{{', '.join(reversed(v2))}}};\n    assign p = v1 + v2;\nendmodule\n"
    return hdr + "\n".join(lines) + "\n" + tail


def load(p):
    out = {}
    for line in open(p):
        m = re.findall(r"(\d+)'([01]+)", line)
        if len(m) >= 3:
            x, y, u = (int(q[1], 2) for q in m[:3])
            out[(x, y)] = u
    return out


REF = load(H.TABLE)


def run(cfg):
    S, order = cfg
    name = f"tt_s{S}_{order}"
    fa, ha = H.solve(S)
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8", newline="\n").write(netlist(name, fa, ha, order))
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    got = load(os.path.join(d, "eval.txt"))
    bad = sum(1 for k, v in REF.items() if got.get(k) != v)
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
    return name, sum(map(sum, fa)), sum(map(sum, ha)), bad, area, delay, power


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cfgs = [(S, o) for S in (5, 6, 7) for o in ("orig", "arr")]
    with ThreadPoolExecutor(3) as ex:
        rows = list(ex.map(run, cfgs))
    print(f"{'variant':<14}{'FA':>4}{'HA':>4}{'mismatch':>10}{'Area':>10}{'Delay':>8}{'Power':>8}")
    for r in rows:
        print(f"{r[0]:<14}{r[1]:>4}{r[2]:>4}{r[3]:>10}{r[4]:>10.3f}{r[5]:>8.4f}{r[6]:>8.4f}")
    print("reference hwmaj_ilp5_asic: 2891.154 um2, 1.5058 ns, 0.328 mW")
