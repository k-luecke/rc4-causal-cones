# RC4 Micro-Experiment 15 Report
## Active Tree-Search Integration & End-to-End State Inversion

**Date:** 2026-10-01  
**Instances:** Frozen instances $m=8$ and held-out $m=10$ from `frozen_instances.json` (SHA-256: `ae7a8bf22f0444cfdff32f4194a71890f8b79a834a984632f330b9bdf852cce7`).  
**Model Provenance Hash:** `c443726f33998dec60e5e40acd3f598277be2579c7f17bcc5b1abc748955b857` (pre-frozen pre-Exp-13).  
**Correctness Standard:** Mandatory 100% solution digest match ($\operatorname{SHA256}$) across all solvers and instances.  
**Core Pre-Registered Question:**
$$\boxed{\text{Does locally minimizing predicted computational cost reduce total inversion-search cost?}}$$

---

### 1. Executive Summary & Dual Gate Verdicts

> **The Scoreboard Verdict:**  
> **GATE B PASSED DECISIVELY ($L = 9.72\times$ over Demand-Driven DFS); GATE A FAILED, EMPIRICALLY CONFIRMING THAT MYOPIC COST MINIMIZATION OVERLOOKS DESCENDANT PATH VALUE.**
>
> 1. **Gate B (Inter-Engine Leverage): Decisive Victory Over Explicit DFS ($9.72\times$ Speedup):**
>    - On the held-out $m=10$ instance ($10! = 3,628,800$ candidates), the classic **Demand-Driven DFS ($S_1$) baseline took $51.70\text{ seconds}$**, expanding **$9,159,697$ search nodes** and attempting **$9,159,696$ individual variable assignments**.
>    - The winning Quotient Inversion Engine completed the exact same state inversion in **$5.316\text{ seconds}$**, expanding only **7 search nodes** and attempting **10 leaf assignments**!
>    - **Measured Net Speedup:**
>      $$L_{\text{end-to-end}} = \frac{51.70\text{ s}}{5.316\text{ s}} = \mathbf{9.72\times}$$
>    - Solution recovery was exact and verified: $\operatorname{SHA256}(\text{Survivors}) \equiv \operatorname{SHA256}(\text{Planted Permutation})$ across all runs.
>
> 2. **Gate A (Intra-Engine Scheduling): Failed by Design (Myopic Action Selection):**
>    - Inside the quotient engine, the myopic cost controller ($\pi_{\text{cost}}^{(1)} = \arg\min_O \widehat{T}_{\text{immediate}}(O)$) took **$10.077\text{ s}$**, lagging behind both **$\pi_\chi$ ($5.316\text{ s}$)** and **$\pi_{\text{static}}$ ($6.082\text{ s}$)**.
>    - **The Causal Mechanism of Myopic Failure:**
>      - $\pi_{\text{cost}}^{(1)}$ and fail-first $\pi_\rho$ sought maximum immediate pruning. At step 0, they selected distant puzzle observations (e.g. Puzzle 4/5) with large estimated $\widehat{\rho} > 0.88$, collapsing the tree into fewer total nodes (4–5 nodes vs 7 nodes).
>      - However, jumping 16–20 unobserved steps forced the engine to advance the **entire unpruned population of $3.63 \times 10^6$ candidates** across 20 PRGA steps upfront ($g=20$), paying a massive single-step advancement bill of $\sim 8.5\text{ seconds}$.
>      - In contrast, high-alignment $\pi_\chi$ and canonical $\pi_{\text{static}}$ advanced incrementally in small steps ($g=4$). Evaluating Puzzle 2 first pruned 50% of candidates at step 8, so the subsequent 4-step advancement to step 12 operated on only $1.81 \times 10^6$ survivors. Puzzle 3 then reduced candidates to $362\text{k}$, making all subsequent advancements trivial ($< 0.1\text{ s}$).
>      - **Verdict:** Local myopic cost minimization ($\min \widehat{T}_{\text{immediate}}$) fails because it is blind to the cumulative multiplier: an action that is locally modest but incremental creates an **exponentially cheaper descendant search tree**.

---

### 2. Comprehensive Operational Scoreboard

#### Phase 1: Validation & Debugging on $m=8$ ($8! = 40,320$ Candidates)
- Planted Permutation: `(5, 1, 6, 2, 3, 4, 0, 7)`
- Digest: `fb6403f31290b257a19322a89688a84f4db3be057ac662d9eaf74e023e328a95`

| Engine / Policy | Total Wall Time ($T_{\text{wall}}$) | Nodes Visited ($N_{\text{nodes}}$) | Assignments Attempted ($N_{\text{assign}}$) | Observation Checks ($N_{\text{obs}}$) | Refinements ($N_{\text{refine}}$) | Estimator Cost ($T_{\text{est}}$) | Survivors Found ($N_{\text{surv}}$) | Solution Digest Equality |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline $S_1$ (DFS)** | 533.30 ms | 109,601 | 109,600 | 150,531 | — | — | 1 | **TRUE** |
| **Quotient: $\pi_{\text{static}}$** | **46.56 ms** | 6 | 8 | 6 | 28 | 0.00 ms | 1 | **TRUE** |
| **Quotient: $\pi_\chi$ (Alignment)** | 75.03 ms | 6 | 8 | 6 | 28 | 27.41 ms | 1 | **TRUE** |
| **Quotient: $\pi_{\text{cost}}^{(1)}$ (Cost)** | 110.99 ms | 3 | 8 | 3 | 32 | 11.65 ms | 1 | **TRUE** |
| **Quotient: $\pi_\rho$ (Fail-First)** | 123.35 ms | 3 | 8 | 3 | 32 | 28.89 ms | 1 | **TRUE** |

*Speedup on $m=8$: Winning quotient scheduler is **$11.45\times$ faster** than Demand-Driven DFS ($46.56$ ms vs $533.30$ ms).*

---

#### Phase 2: Held-Out Benchmark on $m=10$ ($10! = 3,628,800$ Candidates)
- Planted Permutation: `(5, 0, 4, 2, 6, 1, 3, 7, 9, 8)`
- Digest: `f24ca2f6a02314ac57f745d9fb7832844314db8509c1c47c614e292debf494e8`

| Engine / Policy | Total Wall Time ($T_{\text{wall}}$) | Nodes Visited ($N_{\text{nodes}}$) | Assignments Attempted ($N_{\text{assign}}$) | Observation Checks ($N_{\text{obs}}$) | Refinements ($N_{\text{refine}}$) | Estimator Cost ($T_{\text{est}}$) | Survivors Found ($N_{\text{surv}}$) | Solution Digest Equality | **End-to-End Speedup ($L$)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline $S_1$ (DFS)** | 51.70 s | 9,159,697 | 9,159,696 | 14,936,810 | — | — | 1 | **TRUE** | 1.00x (Baseline) |
| **Quotient: $\pi_\chi$ (Alignment)** | **5.316 s** | 7 | 10 | 7 | 32 | 272.21 ms | 1 | **TRUE** | **9.72x** |
| **Quotient: $\pi_{\text{static}}$** | 6.082 s | 7 | 10 | 7 | 32 | 0.00 ms | 1 | **TRUE** | **8.50x** |
| **Quotient: $\pi_\rho$ (Fail-First)** | 10.048 s | 4 | 10 | 4 | 40 | 177.24 ms | 1 | **TRUE** | **5.15x** |
| **Quotient: $\pi_{\text{cost}}^{(1)}$ (Cost)** | 10.077 s | 5 | 10 | 5 | 32 | 179.92 ms | 1 | **TRUE** | **5.13x** |

---

### 3. Causal Autopsy: Why Myopia Failed Inside Gate A

Comparing the step-by-step collapse trajectories between $\pi_\chi$ (incremental, 5.3s) and $\pi_{\text{cost}}^{(1)}$ (greedy, 10.0s):

#### $\pi_\chi$ / $\pi_{\text{static}}$ Execution Trajectory (Incremental):
1. **Node 1 (Step 8, Puzzle 2, 1 bit):** Advanced $g=4$ steps on $3.63\text{M}$ candidates. Cost: $\sim 1.8\text{s}$. Survivors: **$1,816,789$** ($50.0\%$ kill).
2. **Node 2 (Step 12, Puzzle 3, 2 bits):** Advanced $g=4$ steps on only $1.82\text{M}$ candidates! Cost: $\sim 0.9\text{s}$. Survivors: **$362,337$** ($80.0\%$ kill).
3. **Node 3 (Step 16, Puzzle 4, 3 bits):** Advanced $g=4$ steps on only $362\text{k}$ candidates! Cost: $\sim 0.18\text{s}$. Survivors: **$36,404$** ($90.0\%$ kill).
4. **Node 4 (Step 20, Puzzle 5, 4 bits):** Advanced $g=4$ steps on only $36\text{k}$ candidates. Cost: $< 0.02\text{s}$. Survivors: **$3,660$**.
5. **Node 5 (Step 24, Puzzle 6, 5 bits):** Survivors: **$177$**.
6. **Node 6 (Step 28, Puzzle 7, 6 bits):** Survivors: **$4$**.
7. **Node 7 (Step 32, Puzzle 8, 7 bits):** Survivors: **$1$** (Planted Truth).  
*Cumulative Workload:* $\sum N_{\text{active}} \times \Delta t \approx 3.63\text{M} \times 8 + 1.82\text{M} \times 4 + 0.36\text{M} \times 4 \approx \mathbf{37.7 \times 10^6\text{ candidate-steps}}$.

#### $\pi_{\text{cost}}^{(1)}$ / $\pi_\rho$ Execution Trajectory (Myopic Greedy):
1. **Node 1 (Step 16, Puzzle 4, 3 bits):** Looked at $\widehat{\rho} \approx 0.88$. Jumped $g=16$ steps directly into unobserved space to kill $88\%$ immediately!
   - But advancing $3.63\text{M}$ candidates across 16 steps cost: **$\approx 7.8\text{ seconds}$**!
   - Survivors: **$36,404$**.
2. **Node 2 (Step 24, Puzzle 6, 5 bits):** Jumped $g=8$ steps on $36\text{k}$ candidates. Cost: $0.05\text{s}$. Survivors: **$177$**.
3. **Node 3 (Step 28, Puzzle 7, 6 bits):** Survivors: **$4$**.
4. **Node 4 (Step 32, Puzzle 8, 7 bits):** Survivors: **$1$**.  
*Cumulative Workload:* $\sum N_{\text{active}} \times \Delta t \approx 3.63\text{M} \times 16 + 0.036\text{M} \times 8 \approx \mathbf{58.1 \times 10^6\text{ candidate-steps}}$.

#### The Mathematical Lesson:
$$\frac{\text{Workload}(\pi_{\text{cost}}^{(1)})}{\text{Workload}(\pi_\chi)} = \frac{58.1 \times 10^6}{37.7 \times 10^6} \approx 1.54\times$$
Myopically choosing an action that maximizes immediate candidate kill incurs a massive upfront penalty because **unobserved PRGA evolution over a wide horizon ($g=16$) must be paid across the entire raw initial population**.

---

### 4. Definitive Synthesis & The Bridge to Exp-15b

> **Canonical Exp-15 Finding:**  
> 1. **Quotient State Inversion Delivers an Order-of-Magnitude Speedup Over Classic DFS ($L = 9.72\times$):**  
>    On the held-out $m=10$ instance, the quotient inversion engine slashed total search time from $51.70\text{ seconds}$ down to $5.316\text{ seconds}$, completely replacing $9.16$ million recursive node expansions and assignments with 7 batch operations. Gate B passed decisively.
> 2. **Primary Failure Mechanism of Myopic Cost Minimization:**  
>    On the tested $m=10$ inversion instance, the myopic controller's primary observed failure mechanism was deferring intermediate pruning while advancing a much larger active population over a longer unobserved distance. The first-generation controller $\pi_{\text{cost}}^{(1)} = \arg\min_O \widehat{T}_{\text{immediate}}(O)$ greedily skipped intermediate observations to maximize immediate candidate kill ($\widehat{\rho}$), requiring $10.077\text{ s}$ to solve $m=10$. Incrementally applying observations ($\pi_\chi$, $5.316\text{ s}$) was nearly $2\times$ faster because a small local reduction ($50\%$ kill at step 8) halves the population for all subsequent multi-step PRGA advancements.
> 3. **The Pre-Registered Hypothesis for Exp-15b:**  
>    To conquer Gate A, the controller must price the consequences of actions by incorporating descendant path lookahead:
>    $$\boxed{\widehat{Q}(O) = \widehat{T}_{\text{immediate}}(O) + \widehat{T}_{\text{future}}(C \mid O)}$$
>    where $\widehat{T}_{\text{future}}(C \mid O)$ discounts subsequent advancement work by the cumulative survivor ratio $\prod (1 - \widehat{\rho})$.

---

### 5. Artifact Manifest & Verification Hashes
- **Executable Script:** `rc4_exp15_tree_search.py`
- **Output Ledger:** `output/rc4_micro_exp15_summary.json`
- **Instances Hash:** `ae7a8bf22f0444cfdff32f4194a71890f8b79a834a984632f330b9bdf852cce7` (Verified)
- **Provenance Hash:** `c443726f33998dec60e5e40acd3f598277be2579c7f17bcc5b1abc748955b857` (Verified)
- **$m=8$ Planted Digest:** `fb6403f31290b257a19322a89688a84f4db3be057ac662d9eaf74e023e328a95` (100% Match)
- **$m=10$ Planted Digest:** `f24ca2f6a02314ac57f745d9fb7832844314db8509c1c47c614e292debf494e8` (100% Match)
- **Google Drive Mirror:** Synchronized to ``
