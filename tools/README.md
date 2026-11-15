# tools/ — scripts used to design and document `hwmaj_ilp6t_asic`

These are the research scripts behind the design (ILP compressor tree, compensation tables, PPA experiments, figures). They are kept as they were used during the competition, with hard-coded paths replaced by paths relative to the repository root. Documents refer to them as `tools/<name>.py`.

Run everything from the repository root, for example `python tools/minimax_comp.py`.

## Group 1 — pure Python, runs anywhere

Needs `numpy`, `matplotlib`, `pulp` (with its bundled HiGHS/CBC solver). No external tools or data.

| Script | Purpose |
| :--- | :--- |
| `hwmaj_ilp.py` | ILP model of the 6-stage compressor tree (matrix of 43 partial products + compensation bits) |
| `ilp6t_slice.py` | Cross-section of the ILP feasible region (used for Figure 22) |
| `minimax_comp.py`, `minimax_cut6.py` | Check of the compensation table over several input distributions |
| `fig06_regression_T_vs_g.py` | Regression of truncated sum T against g (Figure 6) |
| `draw_ilp6t_*.py` | Figures 7–23 of the explanation document (ILP stages, groups, solver, cost floor) |

The figure scripts write into `docs/figures/`. Re-running `fig06`, `draw_ilp6t_region`, `draw_ilp6t_simple_floor`, `draw_ilp6t_solve` and `draw_ilp6t_solver_detail` reproduced the committed images byte for byte.

## Group 2 — needs the organizers' MNIST images

`doc_numbers.py`, `doc_examples.py`, `doc_figures.py`, `col6_feature_test.py`, `cut7pop.py`, `approx_comp.py` read pixel data from `docs/Training2/ASIC/MNIST_Images/` (organizers' package, not included here).

## Group 3 — needs Yosys + OpenSTA through WSL, plus the organizers' flow files

`gen_tree_rtl.py`, `tree_timing.py`, `stage_ilp_tree.py`, `finalize_ilp6t.py`, `standalone_ppa.py`, `hwcut6.py`, `cut6g7.py`, `final_adder_exp.py`, `gen_hw_variants2.py` generate RTL variants and run synthesis and STA. They call `wsl.exe -d Ubuntu` with Yosys 0.52 and OpenSTA 3.1.0 installed in that distribution, and expect the flow files (`normal.lib`, `constraints.sdc`, ...) described in [../asic/README.md](../asic/README.md). Work directories are created under `build/` (ignored by git).

Some of them import `gen_tree_rtl` for helper functions, so keep all scripts in this folder.

## Not included

`run_cnn_variant.py` (CNN accuracy run) depended on the organizers' Vivado/XSim CNN testbench, which is not part of this repository.
