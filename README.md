# rc4-causal-cones

Reduced-state RC4 ($m \in \{6, 7, 8, 9, 10, 12, 16\}$) constraint-propagation, causal-cone perturbation, and frontier-controller experiments.

Developed at [Driftbound Labs](https://driftboundlabs.com).

---

## Overview & Empirical Verdicts

This repository studies exact permutation recovery on reduced-modulus RC4 (`S` of size $m$) from partial keystream/state-transition observations, comparing general SMT/Z3 encoding against explicit address-DFS, lazy state revelation, and causal-cone branch ordering (`rc4_micro_exp1` through `rc4_micro_exp16`).

| Question | Verdict | Summary |
|---|---|---|
| Exactness on $m \in \{6, 7, 8\}$ (`rc4_constraint_solver_v1.py`) | **Supported** | Solver solution sets match exhaustive $m!$ enumeration bit-for-bit, recover the planted permutation, and return `UNSAT` under single-bit residue corruption. |
| Lazy address-revelation & causal-cone frontier ordering (`exp8`–`exp16`) | **Mixed** | Reduces live branching factor relative to naive index-order DFS on under-constrained $m \in \{9, 10, 12\}$ instances, but exhibits sharp phase-transition blowup once observation density drops below the breakeven surface (`rc4_exp11_breakeven_surface.py`). |
| Full $m = 256$ RC4 cryptanalytic break | **Not informatively tested / Not claimed** | All experiments operate strictly on reduced-state permutations ($m \le 16$) to isolate combinatorial search mechanics. |

---

## Reproducibility

```bash
# Run Z3 + exhaustive equivalence checks and progressive observation ablations
pip install z3-solver pandas
python3 rc4_constraint_solver_v1.py

# Run held-out transfer benchmark (Experiment 16)
python3 rc4_exp16_transfer_benchmark.py
```

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
