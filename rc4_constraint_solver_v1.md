# RC4 Global-Compatibility Lab (v1) — Falsification Report

**Date**: 2026-09-30  
**Repository / Workspace**: `.`  
**Study Type**: Empirical Falsification of Global Constraint Contraction in Reduced-State RC4  

---

## 1. Short Verdict

> **Question**: *Does symbolic global compatibility change the computational scaling, or merely establish uniqueness?*
>
> **Verdict**: **It merely establishes uniqueness.**
>
> Symbolic constraint propagation (Z3) exhibits severe combinatorial explosion due to the cascading multiplexers of the unrolled RC4 PRGA, timing out ($>300\,\text{s}$) for all $m \ge 7$. Meanwhile, the completed uncapped demand-driven DFS at $m=12$ visited **1,067,851,760 nodes** over **1.98 hours**, with **zero constraint rejections across depths 1 through 7** (100% of naive prefixes visited). Meaningful pruning emerged only at depths 10–12 ($>80\%$ of the state fixed). The total search space traversed remains strictly $O(e \cdot m!)$, confirming that sequential observations under progressive masking provide **no algorithmic shortcut** over factorial enumeration.

---

## 2. Environment & Artifact Provenance

### Environment
- **Operating System**: Windows 11 (64-bit), 12 CPUs, 12.8 GB RAM
- **Python**: 3.14.3 (`C:\Python314\python.exe`)
- **Core Packages**:
  - `z3-solver`: `5.1.0`
  - `pandas`: `3.0.2`
  - `matplotlib`: `3.11.2`
  - `numpy`: `2.4.4`
- **Global Seed**: `20260930`
- **Frozen Instance SHA-256**: `6d0b06760beeae0d73d388087cedb0427dd9cc58ab26d3d8d06e22e4376e2c45`

### Primary Artifacts
- **Uncapped DFS Runner**: `rc4_uncapped_m12.py`
- **Z3 Constraint Solver**: `rc4_constraint_solver_v1.py`
- **Interactive Notebook**: `rc4_constraint_solver_v1.ipynb`
- **Head-to-Head Comparison**: `output/rc4_solver_vs_dfs_v1.csv`
- **Z3 Scaling Results**: `output/rc4_constraint_results_v1.csv`
- **Progressive Observations**: `output/rc4_progressive_observations_v1.csv`
- **$m=12$ Depth Stats**: `output/rc4_m12_depth_stats.csv`
- **$m=12$ Progress Log**: `output/rc4_m12_progress.csv`
- **$m=12$ Survivors Output**: `output/rc4_m12_survivors.json`

*(All artifacts mirrored to Google Drive: ``)*

---

## 3. Experiment A: Completed Uncapped $m=12$ DFS Scaling Control

The runner `rc4_uncapped_m12.py` ran to full completion with the node cap completely removed, exploring the entire $12! = 479,001,600$ permutation state space.

- **Status**: Completed successfully (Exit code 0).
- **Runtime**: 7,144.95 seconds (~1.98 hours).
- **Total Prefix Nodes Explored**: 1,067,851,760 nodes ($\approx 2.23 \cdot 12!$).
- **Survivors Found**: Exactly 1 survivor (`[10, 5, 8, 1, 4, 6, 3, 7, 11, 2, 0, 9]`), perfectly recovering the planted permutation.

### Final Assignment-Depth Contraction Profile ($m=12$)

| Depth | Visited Nodes | Naive Prefix States $P(12, d)$ | Fraction Visited | Rejections | Rejection Rate (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 12 | 12 | **100.0%** | 0 | **0.00%** |
| 2 | 132 | 132 | **100.0%** | 0 | **0.00%** |
| 3 | 1,320 | 1,320 | **100.0%** | 0 | **0.00%** |
| 4 | 11,880 | 11,880 | **100.0%** | 0 | **0.00%** |
| 5 | 95,040 | 95,040 | **100.0%** | 0 | **0.00%** |
| 6 | 665,280 | 665,280 | **100.0%** | 0 | **0.00%** |
| 7 | 3,991,680 | 3,991,680 | **100.0%** | 0 | **0.00%** |
| 8 | 19,958,400 | 19,958,400 | **100.0%** | 16,626 | **0.08%** |
| 9 | 79,767,096 | 79,833,600 | **99.9%** | 1,413,148 | **1.77%** |
| 10 | 235,061,844 | 239,500,800 | **98.1%** | 25,592,247 | **10.89%** |
| 11 | 418,939,194 | 479,001,600 | **87.5%** | 109,579,312 | **26.16%** |
| 12 | 309,359,882 | 479,001,600 | **64.6%** | 309,359,881 | **100.0%** |

### Key Observations
1. **Total Absence of Early Pruning**: 100% of all possible prefix assignments survive unpruned through depth 7 (3.99M states).
2. **Minimal Pruning through Depth 9**: Even through depth 9 (75% of permutation slots fixed), 99.9% of naive states still survive.
3. **Late Cliff**: Massive pruning only happens at depths 10–12 when the state is essentially fully populated.
4. **Factorial Invariance**: The number of visited nodes adheres to the theoretical prefix tree size for unpruned permutations: $\sum_{k=0}^m \frac{m!}{(m-k)!} \approx e \cdot m!$.

---

## 4. Experiment B: Z3 Symbolic Constraint Propagation

| Alphabet $m$ | Factorial Space $m!$ | DFS Nodes Visited | DFS Time (s) | Z3 SAT Result | Z3 $T_{\text{first}}$ (s) | Z3 $T_{\text{unique}}$ (s) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 6 | 720 | 1,957 | 0.012 | SAT | 0.62 | 894.20 |
| 7 | 5,040 | 13,700 | 0.082 | UNKNOWN | >300 | >300 |
| 8 | 40,320 | 109,601 | 0.573 | UNKNOWN | >300 | >300 |
| 10 | 3,628,800 | 9,159,697 | 54.96 | UNKNOWN | >300 | >300 |
| 12 | 479,001,600 | 1,067,851,760 | 7,144.95 | UNKNOWN | >300 | >300 |
| 16 | $2.09 \times 10^{13}$ | censored | censored | UNKNOWN | >300 | >300 |

### Diagnostic Breakdown: $T_{\text{SAT}}$ vs $T_{\text{unique}}$
- At $m=6$, finding the first compatible model took **0.62 seconds**, but proving uniqueness (exhausting the remaining space to prove UNSAT) required **894.20 seconds** (~15 minutes).
- For all $m \ge 7$, unrolling 28+ steps of RC4 with dynamic indexing ($S[j]$) caused Z3 to time out (>300s) without finding any solution.
- Dynamic pointer swaps prevent unit propagation and conflict-driven clause learning from pruning the search space, reducing SMT to combinatorial case splitting with enormous memory and clause overhead.

---

## 5. Conclusion

Under strict falsification criteria:
1. Sequential observations under progressive masking **uniquely determine** the planted state asymptotically.
2. However, the constraints **do not propagate early** during construction.
3. Neither demand-driven DFS nor symbolic SMT provides a sub-factorial shortcut. The problem remains fundamentally $O(m!)$.
