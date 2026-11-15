# RC4 Micro-Experiment 8 Report
## Lazy Coordinate Revelation & The Prospective State Frontier

**Date:** 2026-10-01  
**Population:** All $N_{C_8} = 1,811,818$ survivors at Step 8 ($m=10$) from `frozen_instances.json` (out of $N = 3,628,800$, $49.93\%$).  
**Timing Resolution:** Hardware `time.perf_counter_ns()` across the whole population.  
**Reference Baseline:** Whole-population explicit advancement ($118.70$ ms at Step 9, $119.88$ ms at Step 10, total $238.58$ ms).  
**Core Question Investigated:**
$$\boxed{\text{Does paying prospectively for future coordinates avoid the } 243.11\text{ ms refinement bill at } h \ge 2?}$$

---

### 1. Executive Summary & Predeclared Verdict

> **Predeclared Outcome Verdict: OUTCOME 4 (NEGATIVE FOR PROSPECTIVE CARRY; THE STATE-DEPENDENT ESCAPE EFFECT).**
>
> 1. **State-Dependent $j$ Escapes the Prospective Window:**
>    - Carrying deterministic $i_{10} = 0$ ($d=1$) does **not** close Step 10.
>    - While $S_9[0]$ is known, the state-dependent pointer $j_{10} = (j_9 + S_9[0]) \pmod{10}$ lands in the known support only **$38.6\%$ of the time**.
>    - In $61.4\%$ of candidates, $j_{10}$ requests a permutation slot outside $\{9, j_9, k_9, 0\}$. Even with $S[0]$ carried, **$41.4\%$ of classes still fragment at Step 10**.
>
> 2. **Prospective Carry Costs More Than On-Demand Revelation:**
>    - Carrying $S[0]$ expands the quotient from $163,716 \to 354,582$ classes ($5.11\times$ compression).
>    - The incremental maintenance cost alone is $\mathbf{\Delta C_{\text{maintain}} = 522.05\text{ ms}}$, which is **more than double the $243.11$ ms on-demand reveal bill**!
>    - In total, prospective carry takes **$1,318.27$ ms** across Steps 9–10, making it **$5.08\times$ slower** than on-demand revelation ($259.62$ ms) and **$5.53\times$ slower** than explicit candidate advancement ($238.58$ ms).
>
> 3. **The Active Frontier is an Expanding Sponge, Not a Moving Window:**
>    - Across steps $9 \to 12$, cumulative exposed coordinates grow monotonically:
>      $$h=1: \mathbf{2.72} \longrightarrow h=2: \mathbf{4.74} \longrightarrow h=3: \mathbf{6.28} \longrightarrow h=4: \mathbf{7.42} \text{ out of } 10.$$
>    - Because state-dependent pointers $j_t$ and $k_t$ wander dynamically across the deck, every step adds $\sim 1.5 - 2.0$ newly exposed addresses. Coordinates cannot be forgotten without destroying exactness, forcing the required state representation toward the full permutation.

---

### 2. Benchmark 1: Lookahead Depth Study ($d = 0, 1, 2, 3$)

Evaluating prospective carry of the next $d$ deterministic-$i$ coordinates ($i_{10}=0, i_{11}=1, i_{12}=2$):

| Lookahead Depth | Carried Slots | Classes ($K$) | Compression | Build Cost ($C_{\text{build}}$) | $j_{10}$ in Known Support | Step 10 Closure ($r_1=1$) | Mean $r_1$ | Max $r_1$ | Status |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **$d=0$ (Baseline $Q_{\text{exact}}$)** | None | **163,716** | **11.07x** | 243.58 ms | 30.7% | 29.2% | 4.34 | 98 | 1-Step Closed |
| **$d=1$ (Carry $S[0]$)** | $S[0]$ | **354,582** | **5.11x** | 215.29 ms | 38.6% | 58.6% | 2.01 | 37 | $41.4\%$ Unclosed |
| **$d=2$ (Carry $S[0], S[1]$)** | $S[0], S[1]$ | **607,777** | **2.98x** | 211.87 ms | 45.4% | 69.8% | 1.57 | 26 | $30.2\%$ Unclosed |
| **$d=3$ (Carry $S[0], S[1], S[2]$)** | $S[0], S[1], S[2]$ | **907,726** | **2.00x** | 400.59 ms | 53.0% | 79.3% | 1.32 | 14 | $20.7\%$ Unclosed |

*Key finding:* Even when carrying 3 prospective coordinates ($d=3$), class count explodes to $907,726$ ($2\times$ compression), yet $20.7\%$ of classes still fail to close at Step 10 because $j_{10}$ escapes into the remaining unread slots.

---

### 3. Benchmark 2: Strategy 3 — Address Coincidence & Exclusion Audit

At Step 8, auditing address collisions between the candidate read $p_0 = 0$ and the active transition addresses $\{i_9, j_9, k_9\}$:

- $p_0 == j_9$: **$9.28\%$**
- $p_0 == k_9$: **$10.27\%$**
- **Any coincidence ($p_0 \in \{j_9, k_9\}$):** **$18.84\%$**
- **Strictly disjoint ($p_0 \notin \{i_9, j_9, k_9\}$):** **$81.16\%$**

When $p_0$ is disjoint, $S_8[0] \notin \{S_8[i_9], S_8[j_9], S_8[k_9]\}$.
Carrying the relative rank of $S_8[0]$ among the remaining available values yields:
- Class count: **$242,610$ classes** (vs $354,582$ for raw 10-ary carry).
- Permutation exclusion compresses class expansion by **$31.6\%$**, confirming that relational order is more compact than raw coordinate values.

---

### 4. Benchmark 3: The Moving Frontier Audit (Window vs Sponge)

Tracking cumulative distinct permutation coordinates accessed across the unobserved block (Steps 9 to 12):

| Horizon | Transition Step | Mean Coordinates Accessed | 10th Percentile | 90th Percentile | % Population with 100% Deck Exposed |
|---|:---:|:---:|:---:|:---:|:---:|
| **$h=1$** | Step 9 | **2.72 / 10** | 2 | 3 | 0.00% |
| **$h=2$** | Step 10 | **4.74 / 10** | 4 | 6 | 0.00% |
| **$h=3$** | Step 11 | **6.28 / 10** | 5 | 7 | 0.00% |
| **$h=4$** | Step 12 | **7.42 / 10** | 6 | 9 | 0.95% |

**The Verdict:** The frontier is an **expanding sponge**. Coordinates cannot be forgotten, and unread slots are continuously pulled into the active support by the feedback coupling of $j_t$ and $k_t$.

---

### 5. Benchmark 4: Incremental Carry Accounting

Comparing the two strategies across Steps 9 and 10 on the $1.81 \times 10^6$ population:

| Strategy | Step 9 Time | Step 10 Time | Total Steps 9–10 Time | Whole-Population Speedup vs Explicit ($238.58$ ms) |
|---|:---:|:---:|:---:|:---:|
| **Explicit Baseline (B0)** | 118.70 ms | 119.88 ms | **238.58 ms** | 1.00x (Baseline) |
| **Strategy 1: On-Demand Revelation** | **16.51 ms** | **243.11 ms** | **259.62 ms** | **0.92x** |
| **Strategy 2: Prospective Carry ($d=1$)** | **538.56 ms** | **779.71 ms** | **1,318.27 ms** | **0.18x** |

$$\boxed{\Delta C_{\text{maintain}} = 522.05\text{ ms} \gg C_{\text{reveal}} = 243.11\text{ ms}}$$

**Conclusion:** Prospective carry is strictly worse than on-demand revelation. Paying to maintain extra coordinates in advance costs more than letting the quotient advance cheaply and revealing members only when an observation demands it.

---

### 6. Architectural Synthesis Across the Entire Arc

The progression across Micro-Experiments 1–8 now provides a complete, mathematically closed picture:

1. **Where Leverage Lives:**
   - A maintained quotient $Q_{\text{exact}}$ achieves **true, measured wall-clock leverage ($7.19\times$ population speedup, up to $14.43\times$ per class)** over a **single closed transition step** ($h=1$).
   - Within that local window, zero envelopes are opened ($\alpha = 0$).

2. **Where Leverage Dies:**
   - It dies at multi-step propagation ($h \ge 2$) because RC4's state-dependent pointers ($j_t, k_t$) act as coordinate pumps that pull unread slots into the active support.
   - Carrying coordinates prospectively causes class explosion ($163\text{k} \to 355\text{k} \to 608\text{k} \to 908\text{k}$) and inflates maintenance costs ($538$ ms vs $16$ ms).
   - Once a quotient leaks even a fraction of unclosed coordinates, the cost of opening envelopes and partitioning members ($243$ ms) exceeds the cost of native in-place PRGA array swaps ($120$ ms).

3. **The Final Engineering Blueprint:**
   - **Local quotient advancement is an effective single-step filter**, avoiding $85\%$ of PRGA arithmetic.
   - For multi-step unobserved horizons, **in-place explicit candidate advancement remains Pareto-superior** to quotient partition maintenance.
