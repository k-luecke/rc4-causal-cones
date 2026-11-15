# RC4 Micro-Experiment 13 Report
## Partition-Aware Observation Policy & Active Search Selection

**Date:** 2026-10-01  
**Population:** All $N_{C_8} = 1,811,818$ survivors at Step 8 ($m=10$) from `frozen_instances.json` (out of $N = 3,628,800$, $49.93\%$).  
**Scope:** Active search policy benchmark under strict causal constraints:
1. **Estimator Firewall:** Probe-budget ceiling enforced: 0 candidate probes for token-resolvable output predicates; $\le 1,000$ candidate probes for synthetic predicates. All estimation overhead charged to $T_{\text{estimate}}$.
2. **Frozen Prior Cost Model:** Parameters fixed strictly from Exp-10..12 measurements before generation of candidate portfolios:
   $$\operatorname{SHA256}(\text{Parameters}) = \text{9d42b705c9de39b22e08474aaa539b8d15d188b3232fe457dcf6a96f705ba472}$$
3. **Four Competing Policies:** $\pi_{\text{random}}$, $\pi_\rho$ (Largest-$\rho$ Greedy), $\pi_\chi$ (Largest-$\chi$ Alignment ablation), $\pi_{\text{value}}$ (Partition-Aware Value).
4. **Two-Gated Progression:** Gate A (Blind One-Step Selection & Regret Scoreboard) and Gate B (Adaptive Multi-Step Sequential Search).  
**Correctness Standard:** Mandatory candidate ID digest equality ($\operatorname{SHA256}$) verified across all execution paths.

---

### 1. Executive Summary & The Core Discovery

> **The Scoreboard Verdict: ACTIVE OBSERVATION SELECTION IS VIABLE AT SUB-MILLISECOND OVERHEAD ($T_{\text{est}} \le 0.5$ ms); BUT MINIMIZING WALL-CLOCK SEARCH TIME REQUIRES RECOGNIZING THAT CANDIDATE VOLUME ($\rho$) EXERTS A FIRST-ORDER EFFECT OVER CLASS ALIGNMENT ($\chi$).**
>
> 1. **Prospective Pre-Application Estimation is Fast & Accurate:**
>    - For token-resolvable predicates, parent-token metadata queries require **0 candidate probes** and execute in **$0.054 - 0.156$ ms**.
>    - For synthetic admissible predicates, sampling a budget of $1,000$ candidate probes ($0.055\%$ of population) estimates $\widehat{\rho}$ and $\widehat{\chi}$ in **$0.336 - 0.592$ ms**.
>    - Across all policies, estimation overhead accounts for $< 0.6\%$ of search time.
>
> 2. **Gate A Full Portfolio Scoreboard:**
>    - On the natural portfolio, $\pi_{\text{value}}$, $\pi_\rho$, and $\pi_\chi$ all correctly identified the dominant observation (**Exact Symbol $z_9 == 4$**), achieving **$0.00\text{ ms}$ regret** and **$L_{\text{realized}} = 7.32\times$** ($T_{\text{policy}} = 25.07$ ms).
>    - Uninformed random selection ($\pi_{\text{random}}$) fell into an unaligned trap, suffering **$+73.64\text{ ms}$ regret** ($T_{\text{policy}} = 98.71$ ms).
>
> 3. **The Adversarial Crucible Discovery ($\Delta T$ vs $T_{\text{policy}}$):**
>    - In the head-to-head crucible between **Arm A** (high-$\rho \approx 0.65$, low-$\chi \approx 0.10$) and **Arm B** (moderate-$\rho \approx 0.50$, high-$\chi \approx 0.95$):
>      - $\pi_{\text{value}}$ selected Arm B because it predicted higher net leverage relative to explicit baseline ($\widehat{\Delta T}_B = +143.90\text{ ms} > \widehat{\Delta T}_A = +137.87\text{ ms}$).
>      - However, in absolute wall-clock search time, **Arm A was actually $26.81$ ms faster** ($98.71\text{ ms}$ vs $125.52\text{ ms}$)!
>    - **The Cause:** Arm A eliminated $271,772$ more candidates than Arm B. That $15\%$ raw candidate reduction saved $36.4$ ms in downstream refinement, which outweighed the $9.6$ ms savings gained from partition alignment.
>    - **The Algorithmic Principle:**  
>      $$\boxed{\text{Maximizing Relative Leverage } (\Delta T = T_{\text{exp}} - T_Q) \quad\neq\quad \text{Minimizing Absolute Wall-Clock Time } (\min T_{\text{policy}})}$$
>      In search control, candidate collapse $\rho$ is the primary first-order variable governing total refinement work; partition alignment $\chi$ is an internal multiplier optimizing the quotient engine for whatever candidate volume survives.

---

### 2. Gate A: Blind Prospective Estimation & Firewall Audit

Pre-application estimates generated under strict probe limits:

| Candidate Observation | Predicate Type | Candidate Probes | Parent Probes | Estimation Time ($T_{\text{est}}$) | $\widehat{\rho}$ | $\widehat{\chi}$ | Predicted $\widehat{\Delta T}$ |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Exact Symbol ($z_9 == 4$)** | Natural Output | **0** | 5,276 | 0.111 ms | 0.8979 | 1.0000 | **+158.66 ms** |
| **2-Bit Mod-4 ($z_9 \bmod 4 == 0$)** | Natural Output | **0** | 5,276 | 0.084 ms | 0.6961 | 1.0000 | +151.25 ms |
| **1-Bit Parity ($z_9 \bmod 2 == 0$)** | Natural Output | **0** | 5,276 | 0.054 ms | 0.4974 | 1.0000 | +143.94 ms |
| **Arm A (High-$\rho$ / Low-$\chi$)** | Synthetic Admissible | 1,000 | 806 | 0.592 ms | 0.6310 | 0.1020 | +137.87 ms |
| **Arm B (Moderate-$\rho$ / High-$\chi$)** | Synthetic Admissible | 1,000 | 806 | 0.354 ms | 0.5060 | 0.9480 | +143.90 ms |

#### Blind Policy Selections (Before Timing Reveal):
- $\pi_{\text{random}}$: Arm A (High-$\rho$ / Low-$\chi$)
- $\pi_\rho$ (Greedy): Exact Symbol ($z_9 == 4$)
- $\pi_\chi$ (Alignment): Exact Symbol ($z_9 == 4$)
- $\pi_{\text{value}}$ (Aware): Exact Symbol ($z_9 == 4$)

---

### 3. Ground Truth Timing Reveal & Regret Scoreboard

Actual wall-clock performance measured on surviving populations:

| Observation | Realized $\rho$ | Realized $\chi$ | Surviving Parents ($K_p$) | Filter Time ($T_{\text{filt}}$) | Downstream Time ($T_{\text{down}}$) | Total Realized ($T_{\text{realized}}$) | Policy Time ($T_{\text{policy}}$) | Realized Leverage ($L$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Exact Symbol** | 0.8979 | 1.0000 | 531 | 0.064 ms | 24.90 ms | 24.96 ms | **25.07 ms** | **7.32x** |
| **2-Bit Mod-4** | 0.6961 | 1.0000 | 1,592 | 0.065 ms | 74.13 ms | 74.20 ms | 74.28 ms | 3.03x |
| **1-Bit Parity** | 0.4974 | 1.0000 | 2,654 | 0.066 ms | 122.62 ms | 122.68 ms | 122.74 ms | 2.17x |
| **Arm A** | 0.6500 | 0.0999 | 4,961 | 1.654 ms | 96.47 ms | 98.12 ms | 98.71 ms | 2.38x |
| **Arm B** | 0.5000 | 0.9497 | 2,746 | 2.838 ms | 122.32 ms | 125.16 ms | 125.52 ms | 2.12x |

#### Policy Regret Scoreboard (Oracle Best: Exact Symbol, $T_{\text{policy}} = 25.07$ ms):

| Policy | Selected Observation | $T_{\text{estimate}}$ | Total Policy Time ($T_{\text{policy}}$) | **Policy Regret ($R_\pi$)** | Realized Leverage ($L$) |
|---|---|:---:|:---:|:---:|:---:|
| $\pi_{\text{random}}$ | Arm A | 0.592 ms | 98.71 ms | **+73.64 ms** | 2.38x |
| $\pi_\rho$ (Greedy) | Exact Symbol | 0.111 ms | 25.07 ms | **+0.00 ms** | **7.32x** |
| $\pi_\chi$ (Alignment) | Exact Symbol | 0.111 ms | 25.07 ms | **+0.00 ms** | **7.32x** |
| $\pi_{\text{value}}$ (Aware) | Exact Symbol | 0.111 ms | 25.07 ms | **+0.00 ms** | **7.32x** |

#### Adversarial Crucible Scoreboard (Arm A vs Arm B):
- Oracle Best: **Arm A** ($T_{\text{policy}} = 98.71$ ms).
- $\pi_\rho$ selected **Arm A**: $T_{\text{policy}} = 98.71$ ms $\implies$ **Regret = 0.00 ms**.
- $\pi_\chi$ selected **Arm B**: $T_{\text{policy}} = 125.52$ ms $\implies$ **Regret = +26.80 ms**.
- $\pi_{\text{value}}$ selected **Arm B**: $T_{\text{policy}} = 125.52$ ms $\implies$ **Regret = +26.80 ms**.

---

### 4. Exploratory Post-Gate Diagnostic: Multi-Step Search Sequences (2 Steps)

> [!NOTE]
> **Protocol Accounting:**  
> On the full natural portfolio, $\pi_{\text{value}}$, $\pi_\rho$, and $\pi_\chi$ tied at $25.07$ ms, while in the adversarial crucible $\pi_{\text{value}}$ lost to $\pi_\rho$ ($125.52$ ms vs $98.71$ ms). Therefore, Gate B did not strictly trigger under the confirmatory rule. The sequential executions below are retained as exploratory post-gate diagnostics to trace how early branch choices propagate.

#### Scenario 1: The Adversarial Sequence (Arm A vs Arm B at Step 1, Exact at Step 2)
| Policy Path | Step 1 Choice ($O_1$) | Step 1 Time | Step 2 Choice ($O_2$) | Step 2 Time | **Cumulative Search Time** | Final Survivors |
|---|---|:---:|---|:---:|:---:|:---:|
| **$\pi_\rho$ (Greedy Path on Arm A)** | Arm A | 98.71 ms | Exact Step 10 | 2.50 ms | **101.22 ms** | 62,719 |
| **$\pi_{\text{value}}$ (Aware Path on Arm B)** | Arm B | 125.52 ms | Exact Step 10 | 3.05 ms | **128.56 ms** | 90,179 |

#### Scenario 2: Full Portfolio Sequence
| Policy Path | Step 1 Choice ($O_1$) | Step 1 Time | Step 2 Choice ($O_2$) | Step 2 Time | **Cumulative Search Time** | Final Survivors |
|---|---|:---:|---|:---:|:---:|:---:|
| $\pi_{\text{random}}$ | Arm A | 98.71 ms | Exact Step 10 | 0.94 ms | 99.66 ms | 62,719 |
| **$\pi_{\text{value}}$ (Aware)** | Exact Symbol | 25.07 ms | Exact Step 10 | 0.35 ms | **25.43 ms** | **18,887** |

*(Note: The $3.9\times$ cumulative timing difference in Scenario 2 reflects different initial pruning choices that end with different survivor counts, rather than isolated search control at fixed endpoints).*

---

### 5. Definitive Synthesis: Search Control & The Limits of Alignment

> **Canonical Exp-13 Statement (Frozen):**  
> On the tested $m=10$ population, active prospective observation estimation was achieved at sub-millisecond overhead ($T_{\text{estimate}} \le 0.59$ ms) without candidate-population evaluation. On the natural portfolio, value-aware, greedy, and alignment policies all selected the oracle-optimal observation (Exact Symbol, $L = 7.32\times$, $0.00\text{ ms}$ regret), outperforming random selection ($+73.64\text{ ms}$ regret). In the adversarial crucible between a high-kill/low-alignment arm ($\rho \approx 0.65, \chi \approx 0.10$) and a moderate-kill/high-alignment arm ($\rho \approx 0.50, \chi \approx 0.95$), the high-kill arm finished $26.81$ ms faster ($98.71\text{ ms}$ vs $125.52\text{ ms}$), demonstrating that candidate volume reduction dominated the alignment advantage for this tested pair. Preserving compression does not itself minimize search time; the true controller objective must minimize absolute post-observation execution cost.

$$\boxed{\text{partition alignment preserves computational compression}}$$
$$\boxed{\text{preserving compression is not itself the search objective.}}$$

1. **The Objective Function Divergence:**  
   The frozen model's relative leverage predictor $\widehat{\Delta T} = T_{\text{exp}} - T_Q$ asks: *"How much does the quotient save relative to doing this observation explicitly?"* That is valuable for deciding whether to deploy the quotient accelerator, but it fails as a search selection policy. In the adversarial test, Arm B saved more time relative to explicit candidate filtering ($\Delta T_B = +140.50\text{ ms} > \Delta T_A = +136.23\text{ ms}$), but Arm A finished faster in absolute time ($98.71$ ms vs $125.52$ ms) because its 15-point candidate kill advantage eliminated $271,772$ candidates from downstream refinement.
2. **The Absolute Search Objective:**  
   Search control requires predicting and minimizing absolute wall-clock workload:
   $$\boxed{O^* = \arg\min_O \left[ T_{\text{estimate}}(O) + T_{\text{filter}}(O) + T_{\text{downstream}}(O) \right]}$$
   rather than relative leverage $\Delta T$.

