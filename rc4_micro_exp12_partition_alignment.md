# RC4 Micro-Experiment 12 Report
## Partition-Alignment Continuum & Geometry ($L(\chi)$)

**Date:** 2026-10-01  
**Population:** All $N_{C_8} = 1,811,818$ survivors at Step 8 ($m=10$) from `frozen_instances.json` (out of $N = 3,628,800$, $49.93\%$).  
**Scope:** Three-part causal geometry experiment:
1. **Part 1 (The Partition-Alignment Continuum $L(\chi)$):** Fixed candidate reduction ($\rho_{\text{cand}} = 0.5000$, $N_{\text{surv}} = 905,909$ exact) swept across realized whole-class alignment $\chi \in \{0.00, 0.25, 0.50, 0.75, 1.00\}$ with 10 deterministic seed replicates per point.
2. **Part 2 (Class-Size-Matched Scrambling Control):** 10 unconstrained class draws vs. 10 size-stratified class draws at $(\rho = 0.50, \chi \approx 0.50)$ testing whether class identity introduces variance beyond coarse size geometry.
3. **Part 3 (Spacing Coupling $L(\rho, \chi, g)$):** Multi-dimensional response surface across $\rho \in \{0.50, 0.70\} \times \chi \in \{0.0, 0.5, 1.0\} \times g \in \{1, 2, 3\}$.  
**Correctness Standard:** Mandatory candidate ID digest equality ($\operatorname{SHA256}$) and exact survivor count matching verified down to the single candidate.

---

### 1. Executive Summary & The Core Discovery

> **The Scoreboard Verdict: $T_{\text{downstream}}$ FALLS STRICTLY MONOTONICALLY WITH PARTITION ALIGNMENT ($\chi$), AND CLASS-IDENTITY SCRAMBLING INTRODUCES LESS THAN 0.5% VARIANCE.**
>
> 1. **The Smooth $L(\chi)$ Continuum:**
>    - Holding candidate reduction strictly constant at $\rho_{\text{cand}} = 0.5000$ ($N_{\text{surv}} \equiv 905,909$), downstream execution cost falls monotonically as partition alignment increases:
>      $$\chi: 0.00 \longrightarrow 0.25 \longrightarrow 0.50 \longrightarrow 0.75 \longrightarrow 1.00$$
>      $$T_{\text{downstream}}: 134.91\text{ ms} \longrightarrow 130.54\text{ ms} \longrightarrow 126.91\text{ ms} \longrightarrow 124.06\text{ ms} \longrightarrow \mathbf{121.99\text{ ms}}$$
>    - Active parent classes drop linearly from $5,276 \to 2,661$ ($\rho_p: 0\% \to 49.6\%$).
>    - Active child classes drop from $144,237 \to 82,416$ ($\rho_c: 11.9\% \to 49.7\%$).
>    - The downstream cost ratio scales from $R_{\text{postmask}} = 1.11\times \to 1.00\times$, yielding an end-to-end leverage gain from $L_{\text{end}} = 1.10\times \to \mathbf{1.22\times}$.
>
> 2. **Realized $\chi$ is a Sufficient Coarse Predictor:**
>    - In the size-matched scrambling control, 10 independent draws varying parent class identity produced a standard deviation of only **$\pm 0.06$ ms** (coefficient of variation **$\text{CV} = 0.050\%$**).
>    - The ratio of between-draw standard deviation to the systematic $\chi$-delta ($12.92$ ms) is:
>      $$\frac{\sigma_{\text{scramble}}}{\Delta T_{\text{systematic}}} = \mathbf{0.49\%}$$
>    - Because between-draw variation is negligible ($\approx 0.5\%$) relative to the systematic change across $\chi$, **realized $\chi$ is an exceptionally strong, sufficient coarse predictor of quotient acceleration** in the tested population. Class identity and location contribute negligible secondary variance.
>
> 3. **The Multi-Dimensional Hierarchy:**
>    - $\rho$ establishes the scale of candidate reduction.
>    - $\chi$ dictates the internal efficiency of the accelerator (higher alignment reduces downstream cost by eliminating tokens and preventing fragmentation).
>    - $g$ dictates the horizon: at $g=3$, $\rho=0.50$ fails ($L \approx 0.75\times - 0.78\times$), but $\rho=0.70$ achieves leverage across all $\chi$ ($L = \mathbf{1.12\times - 1.19\times}$).

---

### 2. Part 1: The Partition Alignment Continuum at Fixed $\rho = 0.50$

Benchmarked across 10 deterministic seed replicates per nominal target point at $g=2$:

| Nominal $\chi$ | Realized $\chi$ (mean) | Surviving Parents ($K_p$) | Surviving Children ($K_c$) | Downstream Time ($T_{\text{down}}$) | Cost Ratio ($R_{\text{post}}$) | Leverage Ratio ($L_{\text{post}}$) | End Leverage ($L_{\text{end}}$) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **$\chi = 0.00$** | 0.0000 | 5,276.0 ($\pm 0.0$) | 144,236.5 ($\pm 68.7$) | 134.91 ms ($\pm 0.00$) | 1.11x | 1.00x | 1.10x |
| **$\chi = 0.25$** | 0.2495 | 4,631.8 ($\pm 20.5$) | 130,485.7 ($\pm 654.2$) | 130.54 ms ($\pm 0.04$) | 1.07x | 1.03x | 1.14x |
| **$\chi = 0.50$** | 0.4994 | 3,975.0 ($\pm 31.5$) | 115,751.4 ($\pm 674.1$) | 126.91 ms ($\pm 0.05$) | 1.04x | 1.06x | 1.17x |
| **$\chi = 0.75$** | 0.7496 | 3,324.2 ($\pm 38.2$) | 99,895.4 ($\pm 1,043.5$) | 124.06 ms ($\pm 0.03$) | 1.02x | 1.09x | 1.20x |
| **$\chi = 1.00$** | 0.9994 | 2,661.0 ($\pm 44.6$) | 82,416.4 ($\pm 1,309.0$) | **121.99 ms ($\pm 0.01$)** | **1.00x** | **1.11x** | **1.22x** |

- **$R_{\text{postmask}}(\chi) = T_{\text{downstream}}(\chi) / T_{\text{downstream}}(\chi \approx 1)$:** Decreases strictly monotonically from $1.11\times \to 1.00\times$.
- **$L_{\text{postmask}}(\chi) = T_{\text{downstream}}(\chi \approx 0) / T_{\text{downstream}}(\chi)$:** Increases strictly monotonically from $1.00\times \to 1.11\times$.

---

### 3. Part 2: Class-Size-Matched Scrambling Control

Evaluating whether class identity/location introduces variance beyond coarse size geometry at $(\rho = 0.50, \chi \approx 0.50)$:

- **Size-Bin Template (5 quintile bins):** $[264, 239, 268, 255, 274]$ parent classes deleted per bin.

| Condition | Realized $\chi$ (mean) | Surviving Parents ($K_p$) | Downstream Time ($T_{\text{down}}$) | Between-Draw CV |
|---|:---:|:---:|:---:|:---:|
| **Unconstrained Scramble ($N=10$)** | 0.4996 | 3,977.5 ($\pm 35.8$) | 126.91 ms ($\pm 0.05$) | **0.037%** |
| **Size-Matched Stratified ($N=10$)** | 0.5007 | 3,976.0 ($\pm 0.0$) | 126.90 ms ($\pm 0.06$) | **0.050%** |

- **Systematic change across $\chi$ ($\chi=0 \to \chi=1$):** $\Delta T = \mathbf{12.92\text{ ms}}$.
- **Ratio of Size-Matched Std to Systematic $\Delta T$:** $\frac{0.06\text{ ms}}{12.92\text{ ms}} = \mathbf{0.49\%}$.

> **Diagnostic Verdict:** Between-draw variation is orders of magnitude smaller than the systematic change across $\chi$ ($\approx 0.5\%$). Therefore, **realized $\chi$ is a sufficient coarse predictor** of partition alignment in the tested population.

---

### 4. Part 3: Spacing Coupling $L(\rho, \chi, g)$

Evaluating the multi-dimensional response surface across $\rho \in \{0.50, 0.70\} \times \chi \in \{0.0, 0.5, 1.0\} \times g \in \{1, 2, 3\}$:

| Collapse ($\rho$) | Nominal $\chi$ | Realized $\chi$ | Spacing ($g$) | Explicit Time ($T_{\text{exp}}$) | Quotient Time ($T_Q$) | **Leverage ($L$)** | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.50 | 0.00 | 0.0000 | $g=1$ | 148.81 ms | 136.38 ms | **1.09x** | **LEVERAGE** |
| 0.50 | 0.00 | 0.0000 | $g=2$ | 266.02 ms | 147.33 ms | **1.81x** | **LEVERAGE** |
| 0.50 | 0.00 | 0.0000 | $g=3$ | 276.34 ms | 366.26 ms | 0.75x | **FAILS** |
| 0.50 | 0.50 | 0.4990 | $g=1$ | 148.81 ms | 128.42 ms | **1.16x** | **LEVERAGE** |
| 0.50 | 0.50 | 0.4990 | $g=2$ | 266.02 ms | 139.36 ms | **1.91x** | **LEVERAGE** |
| 0.50 | 0.50 | 0.4990 | $g=3$ | 276.34 ms | 358.29 ms | 0.77x | **FAILS** |
| 0.50 | 1.00 | 0.9999 | $g=1$ | 148.81 ms | 123.47 ms | **1.21x** | **LEVERAGE** |
| 0.50 | 1.00 | 0.9999 | $g=2$ | 266.02 ms | 134.42 ms | **1.98x** | **LEVERAGE** |
| 0.50 | 1.00 | 0.9999 | $g=3$ | 276.34 ms | 353.35 ms | 0.78x | **FAILS** |
| **0.70** | **0.00** | **0.0000** | **$g=1$** | **142.36 ms** | **87.17 ms** | **1.63x** | **LEVERAGE** |
| **0.70** | **0.00** | **0.0000** | **$g=2$** | **224.58 ms** | **93.74 ms** | **2.40x** | **LEVERAGE** |
| **0.70** | **0.00** | **0.0000** | **$g=3$** | **251.82 ms** | **225.10 ms** | **1.12x** | **LEVERAGE** |
| **0.70** | **0.50** | **0.4999** | **$g=1$** | **142.36 ms** | **78.48 ms** | **1.81x** | **LEVERAGE** |
| **0.70** | **0.50** | **0.4999** | **$g=2$** | **224.58 ms** | **85.04 ms** | **2.64x** | **LEVERAGE** |
| **0.70** | **0.50** | **0.4999** | **$g=3$** | **251.82 ms** | **216.40 ms** | **1.16x** | **LEVERAGE** |
| **0.70** | **1.00** | **0.9999** | **$g=1$** | **142.36 ms** | **74.09 ms** | **1.92x** | **LEVERAGE** |
| **0.70** | **1.00** | **0.9999** | **$g=2$** | **224.58 ms** | **80.65 ms** | **2.78x** | **LEVERAGE** |
| **0.70** | **1.00** | **0.9999** | **$g=3$** | **251.82 ms** | **212.01 ms** | **1.19x** | **MAX LEVERAGE** |

---

### 5. Definitive Synthesis: The Unified Economic Model

> **Canonical Exp-12 Statement (Frozen):**  
> On the tested $m=10$ population, holding candidate reduction strictly constant at $\rho = 0.50$, downstream quotient execution time falls strictly monotonically as partition alignment increases from $\chi = 0.00$ to $\chi = 1.00$ ($134.91\text{ ms} \to 121.99\text{ ms}$). Class-size-matched scrambling of parent identities introduced less than $0.5\%$ variation ($\pm 0.06$ ms) relative to the systematic $\chi$-effect ($12.92$ ms), showing that realized $\chi$ is a strong coarse predictor of downstream cost in the tested population; after class-size matching, parent identity contributed little additional observed variation. Spacing audits confirm that while $\rho = 0.50$ fails at $g=3$ across all alignments ($L \le 0.78\times$), stronger collapse ($\rho = 0.70$) sustains positive leverage across all alignments ($L = 1.12\times - 1.19\times$), with higher $\chi$ systematically boosting leverage across every spacing regime.

#### The Interaction Hierarchy:
$$\boxed{\text{candidate collapse gets you near/across the boundary;} \quad \text{partition alignment improves the economics within it.}}$$
The tested economic response is well organized by the triad:
$$\boxed{\text{candidate collapse quantity } (\rho) \quad+\quad \text{partition alignment } (\chi) \quad+\quad \text{observation spacing } (g)}.$$

#### The Conceptual Progression (Exp 7 – 12):
$$\begin{aligned}
\text{Exp 7:}&\quad \text{Maintained quotient can actually save work } (L = 7.19\times) \\
\text{Exp 8:}&\quad \text{Blind prospective closure becomes expensive (wandering pointers escape)} \\
\text{Exp 9:}&\quad \text{Evidence can collapse ambiguity before that bill arrives } (L = 4.57\times) \\
\text{Exp 10:}&\quad \text{Profitability depends on evidence schedule } (g \le 2 \text{ profitable, amortizes at cycle 5}) \\
\text{Exp 11:}&\quad \text{Equal candidate pruning can have unequal value } (L_{\text{postmask}} = 1.16\times - 1.63\times) \\
\text{Exp 12:}&\quad \text{Partition alignment causally organizes that difference } (L(\chi) \text{ monotonic, scramble } < 0.5\%).
\end{aligned}$$

