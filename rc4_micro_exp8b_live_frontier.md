# RC4 Micro-Experiment 8b Report
## Horizon-Dependent Forgetting & Live Frontier Audit (h = 1 .. 10)

**Date:** 2026-10-01  
**Population:** All $N_{C_8} = 1,811,818$ survivors at Step 8 ($m=10$) from `frozen_instances.json` (out of $N = 3,628,800$, $49.93\%$).  
**Scope:** Full $m=10$ PRGA cycle ($h = 1 \dots 10$, Steps 9 through 18).  

---

### 1. Executive Summary & Core Verdict

> **The Scoreboard Verdict: PERSISTENT-STATE BEHAVIOR FOR LONG HORIZONS, BUT MASSIVE LOCAL FORGETTING LEVERAGE AT $h=1$.**
>
> 1. **Historical Coordinates Are 100% Redundant for One Step:**
>    - Forgetting historical $\sigma_{3, 8}$ and retaining strictly the transition support $\{j_8, S_8[i_9], S_8[j_9], S_8[k_9]\}$ compresses the quotient from **$163,716 \to 5,276$ classes** ($343.41\times$ compression).
>    - **Exactness is completely preserved at $h=1$:** **$100.0\%$ deterministic closure** ($\bar{r}_1 = 1.000$)!
>    - Step 8 historical memory can be dropped entirely for the Step 9 transition, yielding a $31\times$ reduction in class count with zero loss of determinism.
>
> 2. **Forgetting Causes Divergence Beyond $h=1$ ($h_{\text{fail}} = 2$):**
>    - At $h=2$, deterministic trajectory survival collapses from $30.3\% \to \mathbf{3.2\%}$ ($\bar{r} = 9.40$), and by $h=3$, only $\mathbf{0.1\%}$ of classes maintain unique trajectory behavior.
>    - Discarding past coordinates creates early divergence because state-dependent pointers ($j_t, k_t$) eventually cycle back into previously written slots.
>
> 3. **The Horizon Retained Support Curve:**
>    - The number of initial permutation coordinates required to reproduce future trajectories grows monotonically to the full deck:
>      $$h=1: \mathbf{2.72} \to h=2: \mathbf{4.74} \to h=4: \mathbf{7.42} \to h=7: \mathbf{9.32} \to h=10: \mathbf{10.00} \text{ out of } 10.$$
>    - At $h=10$, exactly **$100.0\%$ of candidates** require all 10 initial deck slots to reproduce their output stream. Over a full cycle, unconstrained RC4 is an expanding sponge.

---

### 2. Horizon Retained Support Across a Complete Cycle ($h = 1 \dots 10$)

| Horizon ($h$) | Transition Step | Mean Cumulative Addrs Touched | Mean Retained $S_8$ Slots Required ($E[|F_t^{(h)}|]$) | % Population Requiring All 10 Slots |
|:---:|:---:|:---:|:---:|:---:|
| **$h=1$** | Step 9 | 2.72 / 10 | **2.72 / 10** | 0.0% |
| **$h=2$** | Step 10 | 4.74 / 10 | **4.74 / 10** | 0.0% |
| **$h=3$** | Step 11 | 6.28 / 10 | **6.28 / 10** | 0.0% |
| **$h=4$** | Step 12 | 7.42 / 10 | **7.42 / 10** | 0.9% |
| **$h=5$** | Step 13 | 8.27 / 10 | **8.27 / 10** | 7.5% |
| **$h=6$** | Step 14 | 8.88 / 10 | **8.88 / 10** | 22.9% |
| **$h=7$** | Step 15 | 9.32 / 10 | **9.32 / 10** | 44.0% |
| **$h=8$** | Step 16 | 9.63 / 10 | **9.63 / 10** | 66.2% |
| **$h=9$** | Step 17 | 9.85 / 10 | **9.85 / 10** | 85.2% |
| **$h=10$** | Step 18 | 10.00 / 10 | **10.00 / 10** | **100.0%** |

---

### 3. The Forgetting-Survival Curve: Intervention Audit

Comparing exact control against three projected/merged representations:

| Representation | Retained Coordinates | Classes ($K$) | Compression | $h=1$ Closed | $h=2$ Closed | $h=3$ Closed | $h=4$ Closed | $h=10$ Closed | $h_{\text{fail}}$ |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Control ($Q_{\text{exact}}$)** | Full with $\sigma_{3, 8}$ | **163,716** | 11.07x | **100.0%** | 30.3% | 16.7% | 13.1% | 11.2% | — |
| **Intervention 1** | Forget $\sigma_{3, 8}$ (Keep $\{j_8, i_9, j_9, k_9\}$) | **5,276** | **343.41x** | **100.0%** | **3.2%** | 0.1% | 0.0% | 0.0% | **$h=2$** |
| **Intervention 2** | Forget $S_8[k_9]$ (Keep $\{j_8, i_9, j_9\}$) | **809** | **2,239.58x** | **20.5%** | 0.4% | 0.0% | 0.0% | 0.0% | **$h=1$** |
| **Intervention 3** | Forget $S_8[j_9]$ (Keep $\{j_8, i_9\}$) | **99** | **18,301.19x** | **0.0%** | 0.0% | 0.0% | 0.0% | 0.0% | **$h=1$** |

---

### 4. Architectural Synthesis for the Handoff

1. **Local vs Long-Horizon Duality:**  
   - For an immediate 1-step transition ($h=1$), historical permutation state is entirely disposable. The local 4-tuple $(j, S[i], S[j], S[k])$ achieves **$100\%$ closure at $343\times$ compression** (only $5,276$ classes across $1.81 \times 10^6$ candidates).
   - Across multi-step unobserved evolution ($h \ge 2$), historical state cannot be discarded without triggering divergence ($h_{\text{fail}} = 2$).
2. **Direct Implication for Micro-Experiment 9:**  
   We should NOT try to maintain a permanent quotient across unobserved blocks. Instead, we should deploy the quotient as a **scoped local operator** that achieves $343\times$ compression and $100\%$ closure at the observation step, filters candidates, and then collapses or regenerates when evidence arrives.
