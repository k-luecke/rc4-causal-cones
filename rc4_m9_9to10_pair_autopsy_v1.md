# RC4 First-Pass Boundary Autopsy Report (v1)
## Exhaustive Dissection of 450 Colliding Pairs at Held-Out Transition 9 -> 10

**Date:** 2026-10-01  
**Target:** Held-out $m=9$ transition $9 \to 10$ ($N = 450$ prefix-colliding pairs)  
**Status:** Complete Empirical Autopsy  
**Workspace:** `.`  
**Google Drive Destination:** `m9_autopsy`  

---

## 1. Executive Summary & Verdict

### Pre-Stated First-Pass Boundary Hypothesis
> *Hypothesis tested:* The excess organization in $R_t$ strengthens near the first wrap of the deterministic $i$-pointer because post-wrap transitions revisit positions that have already participated in the pair's prior collision history.

### Findings on the Mechanism
1. **Revisited-Position Disturbance is NOT the Driver (Falsified)**:
   - Pairs where revisited position $i=1$ was previously selected/disturbed by $j$ during steps 1..9 have a **$14.38\%$ survival rate** (46 / 320).
   - Pairs where revisited position $i=1$ was untouched by $j$ (only visited by deterministic $i=1$ at step 1) have a **$13.85\%$ survival rate** (18 / 130).
   - The survival rate is essentially indistinguishable ($14.38\%$ vs $13.85\%$). Prior $j$-disturbance or history depth of position 1 does not govern survival.

2. **The Real Mechanism: Pre-Existing Address Mismatch Exposure (Confirmed)**:
   - Out of 386 separating pairs, **380 (98.45%) separated because the output addresses $(k_{10}^A, k_{10}^B)$ selected an address where the correspondence was already broken in $\psi_9$ prior to the step-10 swap**:
     $$\psi_9(k_{10}^A) \neq k_{10}^B$$
   - Only 6 out of 386 separators (1.55%) had their mismatch *created* by the step-10 swap.
   - For all 64 surviving pairs, the output address correspondence held after the swap ($45$ pre-existing matches preserved, $19$ mismatches repaired by swap).

3. **Why $R_9$ Has High Excess Purity ($G_R = +16.8\%$ Points)**:
   - The frozen relational tuple $R_9 = (\psi_9(1) \stackrel{?}{=} 1, \Delta j_{10}, \psi_9(j_{10}^A) \stackrel{?}{=} j_{10}^B, \Delta k_{10})$ directly predicts the impending output address shift $\Delta k_{10}$ and swap mapping.
   - When the impending swaps map under $\psi_9$ (`swap_mapped = 1`), survival jumps to **$70.27\%$** ($26/37$). When unmapped, survival is only **$9.20\%$** ($38/413$).
   - Because 9 sequential output constraints have already filtered the state space, the surviving permutations share a structured $\psi_9$. $R_9$ accurately sorts pairs according to whether their impending output address will point to an aligned payload or expose an existing correspondence fault.

4. **Verdict Under the Pre-Stated Decision Rule**:
   - The $+16.8$ percentage-point excess purity gain at $9 \to 10$ is **confirmed genuine** and significantly exceeds the matched-granularity null model ($73.1\%$ observed vs $56.2\%$ null mean $\pm 2.9\%$, $p < 0.001$).
   - However, the specific hypothesis that this excess is caused by *prior $j$-modification history or disturbance depth of the revisited position 1* is **weakened / rejected**. The effect is driven by **pre-existing relational correspondence fault exposure under the impending address calculation $\Delta k_{10}$**.

---

## 2. Evidence Chain & Traceability

| Stage | Finding / Artifact | Status |
|---|---|---|
| **Experiment A (DFS)** | Demand-driven DFS on reduced RC4. | Negative: pruning occurs only in final slots ($d \ge m-2$). |
| **Experiment B (Z3)** | SMT symbolic unrolling with If-chains. | Negative: exponential slowdown ($>300$s for $m \ge 7$). Archival. |
| **Prefix Equivalence** | Complete-state prefix-equivalence classes. | Exact correspondence $\psi_t$ introduced: $\psi_{t+1} = \tau_B \circ \psi_t \circ \tau_A$. |
| **Causal Cone v1** | Pathwise retrospective initial-coordinate ancestry. | Initial-coordinate cones globalize to $O(m)$; did not falsify current relational state $\psi_t$. |
| **Relational Purity Control** | Matched-granularity null control on $m=6,7,8$. | Late 100% purity recognized as class-collapse artifact; genuine excess purity identified in pre-terminal middle rows. |
| **Pre-$m=9$ Freeze** | Frozen contract locked before observing $m=9$. | SHA-256: `7f9f56f64c17791ab30b20a543e98c452dc877c7eb5effecea3683c6f955556a`. |
| **Held-Out $m=9$ Test** | Untouched evaluation on $9! = 362,880$ space. | $9 \to 10$ yielded $N=450$, $P_{\text{obs}}=73.1\%$, $P_{\text{null}}=56.4\%$, $G_R = +16.8\%$. |
| **Primary Autopsy (Current)** | Complete census of all 450 pairs at $9 \to 10$. | Exact mechanism isolated to pre-existing correspondence fault exposure. |

---

## 3. Autopsy Data: Direct Tests of Pre-Stated Mechanisms

### Test 1: Revisited-Position Disturbance Test
Does prior selection/modification of position 1 by $j$ during steps 1..9 alter step-10 survival?

| Group | Total Pairs | Survivors | Separators | Survival Rate (%) | $R_9$ Strict Purity (%) | Matched Null Mean (%) | Gain $G_R$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Disturbed by $j$ in 1..9** (`p1_disturbed = 1`) | 320 | 46 | 274 | **14.38%** | 79.38% | 65.65% | +13.72% |
| **Untouched by $j$ in 1..9** (`p1_disturbed = 0`) | 130 | 18 | 112 | **13.85%** | 83.85% | 64.55% | +19.29% |

*Interpretation:* The survival rate between disturbed and undisturbed position 1 is identical within $\approx 0.5\%$. Prior $j$-disturbance does not modulate collision survival.

---

### Test 2: Correspondence at Revisit Test
How does correspondence at position 1 ($\psi_9(1)$) correlate with survival?

| Condition | Pairs | Survivors | Separators | Survival Rate (%) |
|---|:---:|:---:|:---:|:---:|
| **Fixed point** ($\psi_9(1) = 1$) | 164 | 34 | 130 | **20.73%** |
| **Not fixed** ($\psi_9(1) \neq 1$) | 286 | 30 | 256 | **10.49%** |

*By Cycle Length Containing Position 1:*
* Cycle length 1 (fixed point): $20.73\%$ ($34 / 164$)
* Cycle length 2: $6.82\%$ ($3 / 44$)
* Cycle length 3: $9.38\%$ ($6 / 64$)
* Cycle length 4: $8.77\%$ ($5 / 57$)
* Cycle length 5: $12.50\%$ ($4 / 32$)
* Cycle length 6: $16.00\%$ ($4 / 25$)
* Cycle length 7: $19.05\%$ ($4 / 21$)
* Cycle length 8: $11.76\%$ ($2 / 17$)
* Cycle length 9: $7.69\%$ ($2 / 26$)

*Interpretation:* Pairs where $\psi_9(1) = 1$ have double the survival rate of non-fixed pairs ($20.7\%$ vs $10.5\%$). This condition is already captured directly by the first element of $R_9$ (`r_i_aligned`).

---

### Test 3: History-Depth Test
Does time elapsed since position 1 was last modified correlate with survival?

| Last Modification Step of Pos 1 | Pairs | Survivors | Separators | Survival Rate (%) |
|:---:|:---:|:---:|:---:|:---:|
| Step 1 (only initial visit) | 130 | 18 | 112 | 13.85% |
| Step 2 | 20 | 3 | 17 | 15.00% |
| Step 3 | 23 | 5 | 18 | 21.74% |
| Step 4 | 26 | 1 | 25 | 3.85% |
| Step 5 | 21 | 5 | 16 | 23.81% |
| Step 6 | 40 | 8 | 32 | 20.00% |
| Step 7 | 58 | 9 | 49 | 15.52% |
| Step 8 | 61 | 6 | 55 | 9.84% |
| Step 9 | 71 | 9 | 62 | 12.68% |

*Interpretation:* Survival rates fluctuate between $3.8\%$ and $23.8\%$ across modification steps without any monotonic trend. History depth of position 1 is not the governing factor.

---

### Test 4: Impending-Swap Alignment Test
Does $\psi_9$ map the impending transposition $(1, j_{10}^A)$ directly to $(1, j_{10}^B)$?

| Swap Alignment | Pairs | Survivors | Separators | Survival Rate (%) |
|---|:---:|:---:|:---:|:---:|
| **Mapped under $\psi_9$** (`swap_mapped = 1`) | 37 | 26 | 11 | **70.27%** |
| **Unmapped** (`swap_mapped = 0`) | 413 | 38 | 375 | **9.20%** |

*Interpretation:* When the impending swaps are aligned under the existing position correspondence, the pair survives with **$70.3\%$ probability** (a $7.6\times$ enhancement over unmapped swaps).

---

### Test 5: Output-Address Exposure vs Creation (Decisive Mechanism)
Did the separating mismatch exist before the step-10 swap, or did the swap create it?

| Exposure Classification | Pairs | Survivors | Separators | Survival Rate (%) | Mechanism Description |
|---|:---:|:---:|:---:|:---:|---|
| **`PRE_EXISTING_EXPOSED`** | **380** | **0** | **380** | **0.0%** | $\psi_9(k_{10}^A) \neq k_{10}^B$ and $\psi_{10}(k_{10}^A) \neq k_{10}^B$. Mismatch existed before swap and was exposed. |
| **`MATCH_PRESERVED`** | **45** | **45** | **0** | **100.0%** | $\psi_9(k_{10}^A) = k_{10}^B$ and $\psi_{10}(k_{10}^A) = k_{10}^B$. Pre-existing address match preserved by swap. |
| **`REPAIRED_BY_SWAP`** | **19** | **19** | **0** | **100.0%** | $\psi_9(k_{10}^A) \neq k_{10}^B$ but $\psi_{10}(k_{10}^A) = k_{10}^B$. Swap fixed an existing address fault. |
| **`CREATED_BY_SWAP`** | **6** | **0** | **6** | **0.0%** | $\psi_9(k_{10}^A) = k_{10}^B$ but $\psi_{10}(k_{10}^A) \neq k_{10}^B$. Swap broke an existing address match. |

*Takeaway:* **380 out of 386 separations (98.45%) were pre-existing correspondence failures in $\psi_9$ that were exposed by address selection $k_{10}$.**

---

### Test 6: Global $\psi_9$ Structure & Support Size

| Fixed Points in $\psi_9$ | Pairs | Survivors | Separators | Survival Rate (%) |
|:---:|:---:|:---:|:---:|:---:|
| 0 | 85 | 9 | 76 | 10.59% |
| 1 | 71 | 9 | 62 | 12.68% |
| 2 | 47 | 4 | 43 | 8.51% |
| 3 | 26 | 3 | 23 | 11.54% |
| 4 | 31 | 3 | 28 | 9.68% |
| 5 | 100 | 16 | 84 | 16.00% |
| 6 | 70 | 12 | 58 | 17.14% |
| 7 | 20 | 8 | 12 | **40.00%** |

*Dominant Cycle Types at $t=9$:*
1. `(1, 1, 1, 1, 1, 4)`: 89 pairs (12 survivors, 13.5%)
2. `(1, 1, 1, 1, 1, 1, 3)`: 70 pairs (12 survivors, 17.1%)
3. `(9,)`: 26 pairs (2 survivors, 7.7%)
4. `(1, 8)`: 22 pairs (2 survivors, 9.1%)
5. `(1, 1, 1, 1, 1, 1, 1, 2)`: 20 pairs (8 survivors, 40.0%)

---

## 4. Adjacent Transition Control Comparison

Using the identical frozen $R_t$ specification on adjacent transitions:

| Transition | Total Colliding Pairs | Sampled Pairs | Classes | Observed Strict Purity | Matched Null Mean ($\pm \sigma$) | Excess Gain $G_R$ | Majority Purity |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $8 \to 9$ | 3,834 | 3,834 | 231 | 14.24% | $9.96\% \pm 0.9\%$ | **+4.28%** | 89.36% |
| **$9 \to 10$** | **450** | **450** | **162** | **73.11%** | **$56.20\% \pm 2.9\%$** | **+16.91%** | **93.33%** |
| $10 \to 11$ | 64 | 64 | 43 | 70.31% | $70.63\% \pm 5.1\%$ | **-0.31%** | 89.06% |

The gain peak at $9 \to 10$ ($+16.9\%$) stands out sharply against the pre-wrap transition ($8 \to 9$: $+4.3\%$) and the post-wrap transition ($10 \to 11$: $-0.3\%$).

---

## 5. Artifact Provenance & SHA-256 Checksums

### Environment
- Python 3.14.3 (Windows 64-bit)
- Input: `rc4_m9_9to10_pair_population.json`
- Frozen pre-$m=9$ seed: `20260930`

### File Checksums
| Artifact | Path | SHA-256 |
|---|---|---|
| Autopsy Runner | `rc4_m9_first_pass_autopsy_v1.py` | `6603cc6a3fb0cf5d0ee234a9e08b9a95bc69d57e13dfa3403e7f532878a405c3` |
| Autopsy Core Lib | `rc4_autopsy_core.py` | `d38e6f5bc81ea5039ac41b24aca38063503f8ba6ed4f2e720da1f55c17c7500a` |
| Pair Autopsy CSV | `output/m9_autopsy/rc4_m9_9to10_pair_autopsy_v1.csv` | `bfec422ec1b182541ee11915ec5dfc8e68ea6c25986c51e663bd052943097c5d` |
| Autopsy Summary JSON | `output/m9_autopsy/rc4_m9_9to10_pair_autopsy_summary_v1.json` | `452cd2338bd724dfd1a51d163675601c1494a6beadec650c848b5e2ad7cb0d05` |
| Pair Population JSON | `output/m9_held_out/rc4_m9_9to10_pair_population.json` | `37807ec1725b8b982ba63f350c31ccbe54848332d73ff5dfda54bfd27d7406c7` |

*(All files mirrored to `m9_autopsy\`)*
