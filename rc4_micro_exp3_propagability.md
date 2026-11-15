# RC4 Micro-Experiment 3 Report
## Quotient Propagability & Closure Audit (Phases A & B)

**Date:** 2026-10-01  
**Target:** Test representation propagability and measure the tradeoff between representation size, compression ratio, and successor fragmentation.  
**Population:** All $N = 20,012$ candidates surviving step 8 ($C_8$) for $m=8$ from `frozen_instances.json`.  

---

### 1. Executive Summary

> **Core Finding:**  
> 1. **Phase A ($\sigma_3$ Fragmentation Confirmed):** $\sigma_3$ alone fails to close under transition. In just 1 step ($h=1$), each parent class shatters into an average of **$9.65$ successor classes** (maximum $106$). Candidate-weighted fragmentation is **$45.0\%$**, and only **$6.3\%$** of classes close ($r_1 = 1$). By $h=4$, classes fragment into an average of $16.3$ descendants with only $0.8\%$ closing.
> 2. **Phase B (Smallest Relational Closure Identified):**
>    - Adding the **impending deterministic read** $S_t[i_{t+1}]$ ($R^{(1)}$) drops mean branching to $r_1 = 2.73$ and boosts closure to $36.3\%$.
>    - Adding the **impending swap read** $S_t[j_{t+1}]$ ($R^{(2)}$) drops mean branching to $r_1 = 1.46$ (max $6$) with **$73.7\%$ of classes perfectly closed** at $3.24\times$ compression.
>    - Adding the **impending output address read** $S_t[k_{t+1}]$ ($R^{(3)}$) achieves **$100.0\%$ DETERMINISTIC CLOSURE ($\bar{r}_1 = 1.00$, max $r_1 = 1$)** while retaining a **$2.22\times$ compression ratio** (mean $q = 2.2$, max $q = 72$).
> 3. **The Mesoscopic Plateau:** $R^{(3)}$ tracks only the **3 addresses touched by the impending transition** $\{i_{t+1}, j_{t+1}, k_{t+1}\}$, quotienting out the remaining $m - 3 = 5$ slots. Even out to a 4-step horizon ($h=4$), median branching in $R^{(3)}$ remains **$1.0$**, with over **$54.0\%$ of classes remaining completely unfragmented**.

---

### 2. Phase A: Single-Step and Multi-Step Fragmentation of $\sigma_3$ ($T_0 = 8$)

Starting from the 933 active $\sigma_3$ classes in $C_8$ ($20,012$ candidates):

| Horizon $h$ (Step) | Mean $r_h$ | Median $r_h$ | Max $r_h$ | Mean $\rho_h$ (Unweighted) | Candidate-Weighted $\bar{\rho}_h^{(w)}$ | Closed Classes ($r_h = 1$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| $h = 1$ (Step 9) | 9.65 | 8.0 | 106 | 54.9% | **45.0%** | 59 / 933 (6.3%) |
| $h = 2$ (Step 10) | 12.68 | 10.0 | 225 | 67.6% | **59.1%** | 18 / 933 (1.9%) |
| $h = 3$ (Step 11) | 14.64 | 11.0 | 292 | 76.0% | **68.3%** | 6 / 933 (0.6%) |
| $h = 4$ (Step 12) | 16.30 | 12.0 | 316 | 82.4% | **76.0%** | 7 / 933 (0.8%) |

*Takeaway:* $\sigma_3$ alone is an observational snapshot; it has zero memory of unread positions and rapidly degenerates toward individual candidate resolution at $\approx 45\%$ per step.

---

### 3. Phase B: Incremental Relational State Hierarchy & The Tradeoff Curve

We evaluated the tradeoff between **representation compression** ($|C_8| / \#\text{classes}$) and **one-step successor fragmentation** ($r_1$):

| Representation Level | Mathematical Formulation | Active Classes | Compression ($|C_8| / \#\text{cls}$) | Mean Class Size $\bar{q}$ | Max Class Size $q_{\max}$ | Mean $r_1$ | Max $r_1$ | Closed Classes ($r_1 = 1$) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **$R^{(0)}$** | $\sigma_3$ alone | 933 | **21.45x** | 21.4 | 623 | 9.65 | 106 | 6.3% |
| **$R^{(1)}$** | $(\sigma_3, S_8[i_9])$ | 3,298 | **6.07x** | 6.1 | 145 | 2.73 | 24 | 36.3% |
| **$R^{(2)}$** | $(\sigma_3, S_8[i_9], S_8[j_9])$ | 6,173 | **3.24x** | 3.2 | 145 | 1.46 | 6 | 73.7% |
| **$R^{(3)}$ (Impending Kernel)** | $(\sigma_3, S_8[i_9], S_8[j_9], S_8[k_9])$ | 9,002 | **2.22x** | 2.2 | 72 | **1.00** | **1** | **100.0%** |
| **$R^{(\text{full})}$ (Full Permutation)** | Full state array $S_8$ | 20,012 | **1.00x** | 1.0 | 1 | 1.00 | 1 | 100.0% (Trivial) |

---

### 4. Multi-Step Persistence of the Kernel Across Horizons $h = 1 \dots 4$

How long do these relational classes remain cohesive as the PRGA advances?

| Representation | Horizon $h=1$ ($r_1$ / Closed) | Horizon $h=2$ ($r_2$ / Closed) | Horizon $h=3$ ($r_3$ / Closed) | Horizon $h=4$ ($r_4$ / Closed) |
|---|:---:|:---:|:---:|:---:|
| **$R^{(0)}$ ($\sigma_3$)** | 9.65 (6.3%) | 12.68 (1.9%) | 14.64 (0.6%) | 16.30 (0.8%) |
| **$R^{(1)}$ ($+S[i]$)** | 2.73 (36.3%) | 3.59 (26.6%) | 4.30 (20.3%) | 4.81 (17.4%) |
| **$R^{(2)}$ ($+S[i], S[j]$)** | 1.46 (73.7%) | 2.27 (48.4%) | 2.60 (41.5%) | 2.83 (38.3%) |
| **$R^{(3)}$ ($+S[i], S[j], S[k]$)** | **1.00 (100.0%)** | **1.72 (62.2%)** | **1.89 (56.9%)** | **2.01 (54.0%)** |

*Key Insight:* In $R^{(3)}$, even after 4 full steps of PRGA evolution ($h=4$), **median $r_4 = 1.0$** and **$54.0\%$ of classes have still not fragmented**.

---

### 5. Answer to the Central Question

> **“What is the smallest current-state relational description that closes under RC4 transition while retaining substantial multiplicity?”**

$$\boxed{R^{(3)}_t = \big(\sigma_{3, t}, \, S_t[i_{t+1}], \, S_t[j_{t+1}], \, S_t[k_{t+1}]\big)}$$

1. **Size:** Requires exactly **3 coordinates** beyond the current transition: the values at the deterministic read $i_{t+1}$, the update target $j_{t+1}$, and the lookup address $k_{t+1}$.
2. **Closure Quality:** **$\bar{r}_1 = 1.00$ ($100.0\%$ closure).** Under 1 step of transition, this representation does not branch at all.
3. **Multiplicity / Compression:** Retains an empirical compression factor of **$2.22\times$** ($20,012$ candidates represented by $9,002$ quotient states), with individual classes containing up to **$q = 72$** candidates.
