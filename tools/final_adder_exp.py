"""Final-adder experiment on the candidate2_ilp5 tree: replace `v1 + v2` with Kogge-Stone / Sklansky / Brent-Kung prefix adders.
Each variant is verified against the original module (exhaustive) and run through the BTC convolution_unit flow."""
import os, re, shutil, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tree_rtl as G

ROOT = G.ROOT
SRC = os.path.join(ROOT, "asic", "rtl", "candidate2_ilp5_asic.v")
OUT = os.path.join(ROOT, "build", "work_asic", "final_adder")
N = 16
LINE = "    wire [15:0] raw = v1 + v2;"


class Prefix:
    def __init__(self):
        self.lines = []
        self.cnt = 0

    def new(self, expr):
        self.cnt += 1
        name = f"t{self.cnt}"
        self.lines.append(f"    wire {name} = {expr};")
        return name

    def combine(self, hi, lo):
        gh, ph = hi
        gl, pl = lo
        g = self.new(f"{gh} | ({ph} & {gl})")
        p = self.new(f"{ph} & {pl}")
        return (g, p)


def adder_body(kind):
    pf = Prefix()
    lines = []
    for i in range(N):
        lines.append(f"    wire pg{i} = v1[{i}] & v2[{i}];")
        lines.append(f"    wire pp{i} = v1[{i}] ^ v2[{i}];")
    cur = {i: (f"pg{i}", f"pp{i}") for i in range(N)}
    if kind == "ks":
        d = 1
        while d < N:
            nxt = dict(cur)
            for i in range(d, N):
                nxt[i] = pf.combine(cur[i], cur[i - d])
            cur = nxt
            d *= 2
    elif kind == "sk":
        for l in range(4):
            nxt = dict(cur)
            for i in range(N):
                if (i >> l) & 1:
                    j = ((i >> l) << l) - 1
                    nxt[i] = pf.combine(cur[i], cur[j])
            cur = nxt
    elif kind == "bk":
        for l in range(4):
            step = 1 << (l + 1)
            for i in range(step - 1, N, step):
                cur[i] = pf.combine(cur[i], cur[i - (1 << l)])
        for l in range(3, 0, -1):
            step = 1 << l
            for i in range(step + (step // 2) - 1, N, step):
                if i - (step // 2) >= 0:
                    cur[i] = pf.combine(cur[i], cur[i - step // 2])
    sums = []
    for i in range(N):
        cin = "1'b0" if i == 0 else cur[i - 1][0]
        sums.append(f"pp{i} ^ {cin}")
    body = "\n".join(lines + pf.lines)
    s_lines = "\n".join(f"    wire sm{i} = {sums[i]};" for i in range(N))
    raw = "    wire [15:0] raw = {" + ", ".join(f"sm{i}" for i in reversed(range(N))) + "};"
    return body + "\n" + s_lines + "\n" + raw


def make(name, kind):
    src = open(SRC, encoding="utf-8").read()
    assert LINE in src
    src = src.replace("module candidate2_ilp5_asic", f"module {name}")
    return src.replace(LINE, adder_body(kind))


def check_and_flow(item):
    kind, name = item
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{name}.v"), "w", encoding="utf-8", newline="\n").write(make(name, kind))
    open(os.path.join(d, "eval.ys"), "w").write(f"read_verilog {name}.v\nsynth -top {name} -flatten\ntee -q -o eval.txt eval -table a,b\n")
    G.sh(d, "yosys -q eval.ys")
    ref_src = SRC
    shutil.copy2(ref_src, os.path.join(d, "ref.v"))
    open(os.path.join(d, "ref.ys"), "w").write("read_verilog ref.v\nsynth -top candidate2_ilp5_asic -flatten\ntee -q -o eval_ref.txt eval -table a,b\n")
    G.sh(d, "yosys -q ref.ys")
    def load(p):
        out = {}
        for line in open(p):
            m = re.findall(r"(\d+)'([01]+)", line)
            if len(m) >= 3:
                x, y, u = (int(q[1], 2) for q in m[:3])
                out[(x, y)] = u
        return out
    got, ref = load(os.path.join(d, "eval.txt")), load(os.path.join(d, "eval_ref.txt"))
    bad = sum(1 for k, v in ref.items() if got.get(k) != v)
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
    return name, bad, area, delay, power


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    jobs = [("ks", "fa_ks"), ("sk", "fa_sk"), ("bk", "fa_bk")]
    with ThreadPoolExecutor(3) as ex:
        rows = list(ex.map(check_and_flow, jobs))
    print("reference candidate2_ilp5_asic: 2746.982 um2, 1.4709 ns, 0.313 mW")
    for r in rows:
        print(f"{r[0]:<8} mismatch={r[1]:>6}  area={r[2]:.3f}  delay={r[3]:.4f}  power={r[4]:.4f}")
