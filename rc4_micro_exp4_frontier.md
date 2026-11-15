# RC4 Micro-Experiment 4 Report
## State-Read Frontier Expansion Audit ($F_h$)

**Date:** 2026-10-01  
**Instances:** Frozen instances $m=8$ ($|C_8| = 20,012$) and $m=10$ ($|C_8| = 1,811,818$) from `frozen_instances.json`.  
**Objective:** Measure how the required state-read frontier expands under recursive propagation ($F_h$), determine whether coordinate reuse keeps the frontier compact ($F_h \ll 3h$), and test whether a class's read frontier stays coherent across its members without reopening hidden permutation state.

---

### 1. Executive Summary

> **Core Findings:**  
> 1. **Sublinear Growth & Coordinate Reuse ($F_h \ll 3h$):**
>    - The frontier expands significantly slower than the theoretical maximum ($3h$):
>      - At $m=8$: $F_1 = 2.64 \to F_2 = 4.47 \to F_3 = 5.76 \to F_4 = 6.62 \to \dots \to 8.00$.
>      - At $m=10$: $F_1 = 2.72 \to F_2 = 4.74 \to F_3 = 6.28 \to F_4 = 7.42 \to \dots \to 10.00$.
>    - Newly exposed coordinates per step ($\Delta F_h$) decay monotonically:
>      $$\Delta F_h (m=10): \quad 2.72 \longrightarrow 2.02 \longrightarrow 1.54 \longrightarrow 1.14 \longrightarrow 0.84 \longrightarrow 0.61 \dots$$
>    - Coordinate reuse increases from $\approx 10\%$ at $h=1$ to over $95\%$ by $h=m$.
> 2. **The Deterministic $i$-Pointer Depletion:**
>    - Because $i_t = t \pmod m$, the deterministic pointer visits a distinct position at every step. Even with high $j/k$ reuse, the $i$-pointer steadily forces new coordinates into the frontier until $F_h = m$ at $h = m$.
> 3. **The Frontier Divergence Barrier (The "Leaky Frontier"):**
>    - At $h=1$, class read frontiers are **$100.0\%$ coherent** (all class members access identical $i, j, k$).
>    - At $h=2$, class coherence collapses to **$13.3\%$** ($m=8$) and **$6.6\%$** ($m=10$).
>    - At $h=4$, class coherence drops to **$3.1\%$** ($m=8$) and **$0.0\%$** ($m=10$).
>    - **Root Cause:** To propagate from $R_t^{(3)}$ to $R_{t+1}^{(3)}$ without candidate identities, the class must know the next read $S_t[i_{t+1}]$. If $i_{t+1}$ was not among the 3 coordinates exposed at step $t$, the class has no value for it, causing $j_{t+1}$ and the impending swap to diverge across class members.

---

### 2. Frontier Expansion Ledger: $m=10$ ($|C_8| = 1,811,818$, 5,276 $R^{(3)}$ Classes)

| Horizon $h$ | Step | Mean $F_h$ | $\Delta F_h$ (New Slots) | Reuse Rate | Linear Bound ($3h$) | Saturated ($F_h = 10$) | Coherent Classes (%) | Candidates in Coherent (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $h = 1$ | 9 | 2.72 | 2.72 | 9.5% | 3 | 0.0% | **100.0%** | **100.0%** |
| $h = 2$ | 10 | 4.74 | 2.02 | 32.6% | 6 | 0.0% | 6.6% | 6.6% |
| $h = 3$ | 11 | 6.28 | 1.54 | 48.6% | 9 | 0.0% | 0.2% | 0.2% |
| $h = 4$ | 12 | 7.42 | 1.14 | 61.9% | 10 | 0.9% | 0.0% | 0.0% |
| $h = 5$ | 13 | 8.27 | 0.84 | 71.9% | 10 | 7.5% | 0.0% | 0.0% |
| $h = 6$ | 14 | 8.88 | 0.61 | 79.7% | 10 | 22.9% | 0.0% | 0.0% |
| $h = 7$ | 15 | 9.32 | 0.44 | 85.3% | 10 | 44.0% | 0.0% | 0.0% |
| $h = 8$ | 16 | 9.63 | 0.32 | 89.5% | 10 | 66.2% | 0.0% | 0.0% |
| $h = 9$ | 17 | 9.85 | 0.22 | 92.7% | 10 | 85.2% | 0.0% | 0.0% |
| $h = 10$ | 18 | 10.00 | 0.15 | 95.1% | 10 | 100.0% | 0.0% | 0.0% |

---

### 3. Frontier Expansion Ledger: $m=8$ ($|C_8| = 20,012$, 1,810 $R^{(3)}$ Classes)

| Horizon $h$ | Step | Mean $F_h$ | $\Delta F_h$ (New Slots) | Reuse Rate | Linear Bound ($3h$) | Saturated ($F_h = 8$) | Coherent Classes (%) | Candidates in Coherent (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $h = 1$ | 9 | 2.64 | 2.64 | 12.1% | 3 | 0.0% | **100.0%** | **100.0%** |
| $h = 2$ | 10 | 4.47 | 1.84 | 38.8% | 6 | 0.0% | 13.3% | 7.4% |
| $h = 3$ | 11 | 5.76 | 1.29 | 57.0% | 8 | 1.4% | 4.3% | 0.9% |
| $h = 4$ | 12 | 6.62 | 0.86 | 71.2% | 8 | 13.7% | 3.1% | 0.3% |
| $h = 5$ | 13 | 7.21 | 0.58 | 80.6% | 8 | 36.9% | 3.0% | 0.3% |
| $h = 6$ | 14 | 7.58 | 0.37 | 87.6% | 8 | 61.6% | 2.9% | 0.3% |
| $h = 7$ | 15 | 7.84 | 0.26 | 91.5% | 8 | 83.5% | 2.9% | 0.3% |
| $h = 8$ | 16 | 8.00 | 0.16 | 94.5% | 8 | 100.0% | 2.9% | 0.3% |

---

### 4. Interpretation: Why the Frontier Leaks

The experiment resolves the dilemma between a "compact moving frontier" versus "reading the whole deck":

1. **Within a Short Horizon ($h \le 3$):**  
   Reads overlap heavily. At $h=2$, mean $F_2 = 4.74$ (out of 10), and at $h=3$, mean $F_3 = 6.28$. The state accessed is strictly localized to a subset of $\approx 5$ to $6$ positions.
2. **Across Multi-Step Propagation ($h \ge 4$):**  
   Because the deterministic index $i_{t+1}$ increments mechanically by $1 \pmod m$, it acts as an unyielding coordinate pump. Every step that $i_{t+1}$ steps onto an unexposed coordinate, a new slot value must be provided.
3. **The Coherence Collapse:**  
   Without candidate identities, an $R_t^{(3)}$ class cannot supply the value of an unexposed slot. Thus, propagating the class as a unit requires either:
   - Branching on the unexposed slot (which fragments the class into $|q_{\text{succ}}| = m - |\mathcal{F}|$ subclasses), or
   - Reopening the underlying permutation states of the candidates.

### 5. Definitive Conclusion

A static local state kernel (even with a 3-address lookahead) **cannot maintain recursive closure**. It closes exactly for 1 step by construction, but because the deterministic pointer $i$ constantly sweeps into unexposed territory, the read frontier expands until the entire permutation is exposed.
