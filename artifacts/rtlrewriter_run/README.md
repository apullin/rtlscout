# RTLRewriter campaigns

Launcher for the RTLRewriter campaigns (cell-count and transistor-count
objectives; model and settings per `profiles/*.yaml`). It drives
`experiments/rtl_rewriter_multirun.py`, the table scripts and the CEC engine
(`artifacts/rtlrewriter_benchmark_results/cec_engine.py`).

```bash
python run_all.py --profile reduced --new-run   # rehearsal: cases 7+9, n=1, 12 steps
python run_all.py --new-run                     # full: all 14 cases, n=1, 30/60 steps
python run_all.py                               # resume the latest run
python run_all.py --report-only
python run_all.py --campaigns cells             # subset (or via enabled: in the profile)
```

| file | what |
|---|---|
| `rr_config.py` | profile load, `data/<tag>_<datetime>/` run layout |
| `profiles/*.yaml` | model, cases, runs, steps, CEC sim-cases, vector target |
| `augment_vectors.py` | ≥10k stimuli/case, golden-simulated expected outputs |
| `run_all.py` | setup, then the enabled campaigns — cells / transistors (runner → tables → CEC evidence), report |
| `common.py` | logged subprocess runner, manifest, markers |

Benchmark mutations (augmented `vectors.dat`, both trees) are global and
idempotent; everything else lands under `data/<run>/`.
