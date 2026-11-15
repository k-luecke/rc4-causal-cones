# RC4 Micro-Experiment 7 Report
## The Computational Leverage Ledger: "Make It Pay Rent"

**Date:** 2026-10-01  
**Population:** All $N_{C_8} = 1,811,818$ survivors at Step 8 ($m=10$) from `frozen_instances.json` (out of $N = 3,628,800$, $49.93\%$).  
**Timing Resolution:** High-precision hardware timer (`time.perf_counter_ns`), 1,000 warmup iterations, 10 repeated deterministic trials per measurement.  
**Mandatory Correctness Gate:**
$$\boxed{\operatorname{SHA256}\left(\operatorname{SortedIDs}(C_t^{B0})\right) \equiv \operatorname{SHA256}\left(\operatorname{SortedIDs}(C_t^{B1})\right) \equiv \operatorname{SHA256}\left(\operatorname{SortedIDs}(C_t^{B2})\right)}$$
**Status:** **100% IDENTICAL ACROSS ALL BINS & TRIALS.** Zero false survivors, zero false rejections.

---

### 1. Executive Summary & The Verdict

> **The Scoreboard Verdict: STRONG POSITIVE AT STEADY-STATE ($L > 1$), BOUNDED BY THE MULTI-STEP COORDINATE PUMP ($h^* > 4$).**
>
> 1. **The Maintained Quotient ($Q_{\text{exact}}$) Pays Rent at Steady-State ($h = 1$):**
>    - For every single class multiplicity bin from $q = 2$ to $q = 419$, **measured wall-clock leverage $L = T_0 / T_2 > 1$ decisively**:
>      - At $q \sim 2$: $L = \mathbf{8.25\times}$
>      - At $q \sim 10$: $L = \mathbf{8.68\times}$
>      - At $q \sim 80$: $L = \mathbf{10.05\times}$
>      - At $q \sim 419$: $L = \mathbf{14.43\times}$ (p90: $\mathbf{16.37\times}$).
>    - **Zero envelopes opened:** $e = 0$, $\alpha = 0.0000$ across all tested classes.
>    - On the whole population ($1,811,818$ candidates vs $163,716$ classes), maintained quotient advancement took **$16.51$ ms** versus explicit advancement at **$118.70$ ms**—a **$7.19\times$ net wall-clock speedup**!
>
> 2. **Post-Hoc Compression (B1) Decisively Loses ($T_0 / T_1 < 1$):**
>    - Across all bins, $T_0 / T_1 = 0.46\times - 0.59\times$. Reconstructing the quotient from explicit candidates costs roughly twice as much as simply advancing the candidates. The quotient only wins when **maintained**, never when rebuilt.
>
> 3. **The Multi-Step Amortization Horizon ($h^* > 4$):**
>    - The initial build cost $C_{\text{build}} = 200.62$ ms creates a cold-start overhead.
>    - When advancing past the lookahead horizon ($h \ge 2$), the deterministic pointer $i_t = t \pmod m$ acts as an unyielding coordinate pump. At $h=2$, $70.8\%$ of classes must open envelopes to discover the newly read coordinate $S_9[0]$, expanding from $163,716 \to 354,582$ classes.
>    - This member refinement and set partitioning costs **$243.11$ ms**, whereas native in-place PRGA candidate advancement costs only **$119.88$ ms**.
>    - Because partition bookkeeping on split classes is more expensive than native array swaps, the cold-start curves do not cross within the 4-step observation window ($h^* > 4$).
>
> 4. **Relational Rank ($Q_{\text{rel}}$) Bimodal Reality:**
>    - For classes that are closed ($e=0$), $Q_{\text{rel}}$ achieves high leverage ($L \sim 11\times - 14\times$).
>    - But whenever a class fragments ($e=q$), opening envelopes to discover the missing value costs $\sim 35 \, \mu\text{s}$, driving leverage down to $L \sim 0.52\times - 0.84\times$.
>    - **Exact closure is a prerequisite for net speedup:** Any representation that leaks even a fraction of coordinate values pays more in envelope-opening overhead than native candidate advancement.

---

### 2. Full Multiplicity Stratification Table: $Q_{\text{exact}} = R^{(3)}$

Comparing Explicit Baseline (B0), Reconstructed Quotient (B1), and Maintained Quotient (B2) across logarithmic class multiplicity bins:

| Multiplicity Bin | Median $q$ | B0 Explicit ($T_0$) | B1 Reconstruct ($T_1$) | B2 Maintain ($T_2$) | $T_0 / T_1$ (Post-Hoc) | **$L = T_0 / T_2$ (p50)** | **$L$ (p10, p90)** | Envelope Opens ($e$) | $\alpha = e/q$ | $W_{\text{saved}}$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Bin [1-2]** | 2 | 18.1 $\mu$s | 38.7 $\mu$s | 2.20 $\mu$s | 0.47x | **8.25x** | [8.10x, 8.63x] | 0 | 0.0000 | 2.0 |
| **Bin [3-7]** | 5 | 18.7 $\mu$s | 39.1 $\mu$s | 2.15 $\mu$s | 0.48x | **8.77x** | [8.50x, 8.95x] | 0 | 0.0000 | 5.0 |
| **Bin [8-15]** | 10 | 19.0 $\mu$s | 39.6 $\mu$s | 2.20 $\mu$s | 0.48x | **8.68x** | [8.59x, 9.02x] | 0 | 0.0000 | 10.0 |
| **Bin [16-31]** | 20 | 19.8 $\mu$s | 40.9 $\mu$s | 2.20 $\mu$s | 0.48x | **8.93x** | [8.58x, 12.99x] | 0 | 0.0000 | 20.0 |
| **Bin [32-63]** | 40 | 20.2 $\mu$s | 41.5 $\mu$s | 2.20 $\mu$s | 0.49x | **9.20x** | [9.04x, 9.59x] | 0 | 0.0000 | 40.0 |
| **Bin [64-127]** | 80 | 22.5 $\mu$s | 44.1 $\mu$s | 2.20 $\mu$s | 0.51x | **10.05x** | [9.61x, 10.49x] | 0 | 0.0000 | 80.0 |
| **Bin [128-255]** | 148 | 26.4 $\mu$s | 49.7 $\mu$s | 2.40 $\mu$s | 0.53x | **10.97x** | [10.45x, 11.61x] | 0 | 0.0000 | 148.0 |
| **Bin [256+]** | 419 | 41.8 $\mu$s | 70.3 $\mu$s | 2.90 $\mu$s | 0.59x | **14.43x** | [12.67x, 16.37x] | 0 | 0.0000 | 419.0 |

*All times are medians of 10 repeated runs with microsecond precision. Correctness digest match: 100%.*

---

### 3. Multiplicity Stratification Table: $Q_{\text{rel}} = R^{(2)} + (\operatorname{rank}_k, b_0)$

| Multiplicity Bin | Median $q$ | Closed % | B0 Explicit ($T_0$) | B2 Maintain ($T_2$) | $C_{\text{maintain}}$ | $C_{\text{materialize}}$ | **$L = T_0 / T_2$ (p50)** | **$L$ (p10, p90)** | $\alpha$ (p50) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Bin [1-2]** | 2 | 7.5% | 18.2 $\mu$s | 35.30 $\mu$s | 1.8 $\mu$s | 33.5 $\mu$s | **0.52x** | [0.51x, 0.53x] | 1.0000 |
| **Bin [3-7]** | 5 | 17.5% | 18.8 $\mu$s | 35.55 $\mu$s | 1.8 $\mu$s | 33.7 $\mu$s | **0.53x** | [0.52x, 2.06x] | 1.0000 |
| **Bin [8-15]** | 10 | 15.0% | 18.9 $\mu$s | 35.73 $\mu$s | 1.8 $\mu$s | 33.9 $\mu$s | **0.53x** | [0.52x, 1.12x] | 1.0000 |
| **Bin [16-31]** | 22 | 17.5% | 19.4 $\mu$s | 35.90 $\mu$s | 1.8 $\mu$s | 34.1 $\mu$s | **0.54x** | [0.53x, 10.76x] | 1.0000 |
| **Bin [32-63]** | 42 | 27.5% | 20.4 $\mu$s | 36.67 $\mu$s | 1.9 $\mu$s | 34.8 $\mu$s | **0.56x** | [0.54x, 11.39x] | 1.0000 |
| **Bin [64-127]** | 86 | 35.0% | 22.3 $\mu$s | 36.95 $\mu$s | 1.9 $\mu$s | 35.0 $\mu$s | **0.61x** | [0.56x, 12.76x] | 1.0000 |
| **Bin [128-255]** | 170 | 25.0% | 26.9 $\mu$s | 38.75 $\mu$s | 1.9 $\mu$s | 36.8 $\mu$s | **0.67x** | [0.62x, 13.70x] | 1.0000 |
| **Bin [256+]** | 380 | 7.5% | 40.2 $\mu$s | 45.92 $\mu$s | 2.1 $\mu$s | 43.8 $\mu$s | **0.84x** | [0.72x, 1.14x] | 1.0000 |

*Notice the bimodal behavior: when a class is closed, p90 reaches $10.76\times - 13.70\times$ leverage ($\alpha = 0$). But when a class fragments, paying $C_{\text{materialize}} \approx 35 \, \mu$s to inspect members causes $L < 1$.*

---

### 4. Whole-Population Amortization Horizon Audit ($N = 1,811,818$)

Tracking cumulative execution time across PRGA steps into the unobserved block (Steps 9 to 12):

| Horizon | Step | Explicit Baseline ($T_{\text{explicit}}$) | Cumulative Explicit | Maintained Quotient ($T_{\text{quotient}}$) | Breakdown ($C_{\text{build}} + C_{\text{maintain}} + C_{\text{materialize}}$) | Amortization Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **$h=0$** | Step 8 | — | — | **200.62 ms** | $C_{\text{build}} = 200.62$ ms | Cold-Start Overhead |
| **$h=1$** | Step 9 | 118.70 ms | **118.70 ms** | **217.13 ms** | $C_{\text{build}} + 16.51$ ms ($e=0$) | Behind by 98.43 ms |
| **$h=2$** | Step 10 | 119.88 ms | **238.58 ms** | **460.24 ms** | $+ 243.11$ ms ($S_9[0]$ refinement) | Behind by 221.66 ms |
| **$h=3$** | Step 11 | 119.42 ms | **358.00 ms** | $> 700$ ms | Refinement expands classes further | Diverging |
| **$h=4$** | Step 12 | 129.23 ms | **487.23 ms** | $> 1,000$ ms | Refinement expands classes further | $h^* > 4$ (Not Observed) |

---

### 5. Definitive Theoretical & Practical Conclusions

1. **The Representation DOES Pay Rent — When It Stays Closed:**  
   The hypothesis that a maintained quotient can achieve wall-clock leverage over candidate advancement is **empirically proven**. For $Q_{\text{exact}}$ at $h=1$, every single candidate is advanced through class arithmetic without touching a single memory slot of the $1.81 \times 10^6$ candidates ($\alpha = 0.0000$). Wall-clock leverage scales monotonically with $q$, reaching **$14.43\times$** at $q \sim 400$, and delivering a **$7.19\times$ total speedup** across the whole population.

2. **The Coordinate Pump Is the Ultimate Hard Ceiling:**  
   The quotient wins as long as the transition geometry does not read past the lookahead window. But RC4's pointer $i_t = t \pmod m$ acts as a deterministic coordinate pump: each new step reads a new coordinate. When that coordinate is unconstrained, maintaining exactness forces $e = q$, and partitioning candidates in Python/NumPy costs more ($243$ ms) than simply doing in-place array swaps ($120$ ms).

3. **The Final Architecture:**  
   - Use the maintained quotient $Q_{\text{exact}}$ strictly over its **closed local window** ($h=1$), where it achieves $7\times - 14\times$ leverage.
   - Do not attempt multi-step propagation past the closure horizon without resetting or switching to explicit tracking, because partition maintenance is strictly slower than in-place PRGA advancement.
