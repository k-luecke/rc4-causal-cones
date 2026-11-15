# RC4 Micro-Experiment 1 Report
## Benchmark: Address-Targeted Constraint DFS (S2) vs Demand-Driven (S1) and Fixed-Slot (S0)

**Date:** 2026-10-01  
**Instances:** Frozen instances $m=8$ and $m=10$ from `frozen_instances.json` (SHA-256 `ae7a8bf22f0444cfdff32f4194a71890f8b79a834a984632f330b9bdf852cce7`).  
**Status:** Completed. Numerical gate evaluated; $m=12$ execution halted as per contract.  

---

### 1. Executive Summary & Gate Verdict

> **Numerical Gate Result: FAILED (Halt at $m=10$, do not run $m=12$).**  
> - **Solution Equivalence Invariant:** Passed. $\text{Survivors}(S_0) \equiv \text{Survivors}(S_1) \equiv \text{Survivors}(S_2) \equiv \{\text{Planted Truth}\}$ for both $m=8$ and $m=10$.
> - **Assignment Reduction ($N_{\text{assign}}$):**
>   - At $m=8$: $N_{\text{assign}}(S_2) = 109,600$ vs $N_{\text{assign}}(S_1) = 109,600$ ($0\%$ reduction).
>   - At $m=10$: $N_{\text{assign}}(S_2) = 8,408,682$ vs $N_{\text{assign}}(S_1) = 9,159,696$ (**$-751,014$ assignments avoided, an $8.20\%$ reduction**).
> - **Median Rejection Depth ($\operatorname{median} D_{\text{reject}}$):**
>   - At $m=8$: $\operatorname{median} D_{\text{reject}} = 8$ for all solvers ($8 < 8$ is False).
>   - At $m=10$: $\operatorname{median} D_{\text{reject}} = 10$ for all solvers ($10 < 10$ is False).
> - **Rejection-Depth Shift:** $S_2$ produced a measurable leftward shift at $m=10$: $P(D \le 8)$ increased from $0.85\%$ to $3.93\%$ ($4.6\times$), and $P(D \le 9)$ increased from $17.02\%$ to $29.90\%$ (+12.88 percentage points). However, $70.10\%$ of rejections remained at depth 10, leaving the median unchanged at 10.
> - **Wall-Clock Leverage:** Wall time for $S_2$ was higher than $S_1$ ($64.81\text{s}$ vs $52.46\text{s}$ at $m=10$) because the per-node overhead of tracking address dependencies exceeded the $8.2\%$ savings in assignments.

---

### 2. Deterministic Operation Ledger

#### Instance $m=8$ ($8! = 40,320$ permutations)
| Metric | S0 (Fixed-Slot) | S1 (Demand-Driven Baseline) | S2 (Address-Targeted DFS) |
|---|:---:|:---:|:---:|
| $N_{\text{nodes}}$ | 69,282 | 109,601 | 109,601 |
| $N_{\text{assign}}$ | 109,600 | 109,600 | 109,600 |
| $N_{\text{addr}}$ | 1,203,283 | 1,474,810 | 1,592,119 |
| $N_{\text{output}}$ | 121,957 | 150,531 | 66,162 |
| $N_{\text{complete}}$ | 40,320 | 1 | 1 |
| Survivors Found | 1 | 1 | 1 |
| Solution Equivalence | Exact Match | Exact Match | Exact Match |
| Wall-Clock Time (s) | 0.458s | 0.541s | 0.695s |

#### Instance $m=10$ ($10! = 3,628,800$ permutations)
| Metric | S0 (Fixed-Slot) | S1 (Demand-Driven Baseline) | S2 (Address-Targeted DFS) |
|---|:---:|:---:|:---:|
| $N_{\text{nodes}}$ | 5,889,176 | 9,159,697 | 8,408,683 |
| $N_{\text{assign}}$ | 9,517,974 | 9,159,696 | **8,408,682** ($-8.20\%$) |
| Rejections at Depth 8 | 0 | 30,671 | **137,168** ($+347\%$) |
| Rejections at Depth 9 | 346,126 | 581,720 | **906,746** ($+55.9\%$) |
| Rejections at Depth 10 | 3,282,673 | 2,985,737 | **2,447,717** ($-18.0\%$) |
| Total Rejections | 3,628,799 | 3,598,128 | 3,491,631 |
| Survivors Found | 1 | 1 | 1 |
| Solution Equivalence | Exact Match | Exact Match | Exact Match |
| Wall-Clock Time (s) | 42.89s | 52.46s | 64.81s |

---

### 3. Rejection-Depth Distribution: $P(D_{\text{reject}} \le d)$

#### $m=8$:
| Depth $d$ | S0 CDF | S1 CDF | S2 CDF | Shift ($S_2 - S_1$) |
|:---:|:---:|:---:|:---:|:---:|
| $d \le 7$ | 0.00% | 0.00% | 0.00% | 0.00% |
| $d \le 8$ | 100.00% | 100.00% | 100.00% | 0.00% |

#### $m=10$:
| Depth $d$ | S0 CDF | S1 CDF | S2 CDF | Shift ($S_2 - S_1$) |
|:---:|:---:|:---:|:---:|:---:|
| $d \le 7$ | 0.00% | 0.00% | 0.00% | 0.00% |
| $d \le 8$ | 0.00% | 0.85% | **3.93%** | **+3.08%** |
| $d \le 9$ | 9.54% | 17.02% | **29.90%** | **+12.88%** |
| $d \le 10$ | 100.00% | 100.00% | 100.00% | 0.00% |

---

### 4. Audit & Operational Semantics
- **Rejection Depth Definition ($D_{\text{reject}}$):** In both $S_1$ and $S_2$, $D_{\text{reject}}$ measures the exact number of committed permutation assignments (`len(used)`) at the moment a branch fails a constraint check. The leftward shift at $m=10$ reflects genuine earlier constraint exposure in terms of committed permutation assignments.
- **The Ledger Trade-off:**
  At $m=8$, $S_2$ evaluated $56\%$ fewer output residue checks ($66,162$ vs $150,531$) by avoiding unconstrained output slots, but performed more address lookups ($1,592,119$ vs $1,474,810$). $S_2$ trades fewer output checks for additional address/pointer tracking. At $m=8$, this trade produced no assignment savings; at $m=10$, it began saving assignments ($-8.20\%$), but did not overcome the overhead of the Python data structures in this implementation.
- **Completion Accounting ($N_{\text{complete}}$):**
  $S_0$ branches strictly through all slots, visiting all $40,320$ full permutation leaves before filtering. $S_1$ and $S_2$ prune prior to full assignment, completing only $1$ state (the unique valid survivor).

---

### 5. Architectural Verdict & Transition to Path B

> **Frozen Summary:**  
> Micro-Experiment 1 failed its predeclared advancement gate ($\operatorname{median} D_{\text{reject}}(S_2) = \operatorname{median} D_{\text{reject}}(S_1) = 10$), so $m=12$ was not run. On $m=8$, address-targeted search produced no assignment savings. On $m=10$, however, $S_2$ preserved the exact solution set while reducing assignments by $8.20\%$ and increasing the fraction of rejections occurring by assignment depth 9 from $17.02\%$ to $29.90\%$ (with depth-8 rejections increasing $4.47\times$). These savings did not translate into wall-clock improvement in the tested Python implementation ($64.81\text{ s}$ versus $52.46\text{ s}$). Thus address-targeted branching demonstrates earlier constraint exposure, but not net computational leverage as implemented.

**Implication for Path B:**  
The constraint-exposure effect is real, but paying per-candidate bookkeeping to discover it individually in each search branch cannot deliver net leverage. This directly motivates **Path B**: rather than advancing individual candidates through address chains, can a single transition computation be shared across an equivalence class of $q > 1$ candidates?

