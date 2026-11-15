# RC4 Relational Representation — Held-Out m=9 Freeze v1

**Date:** 2026-09-30  
**Status:** Frozen Experimental Checkpoint  
**Repository / Workspace:** `.`  
**Google Drive Destination:** ``  

---

## 1. Frozen Defensible Checkpoint

> The relational representation $R_t$, frozen after the $m=6,7,8$ experiments, transferred without modification to held-out $m=9$. It again produced positive excess purity over a matched-granularity control in a pre-terminal collision regime, including $G_R=+16.8$ percentage points at $9\to10$. This supports continued investigation of current-state relational coordinates as a possible reduced representation. It does not yet establish a scaling law, sufficiency, computational advantage, or applicability to full RC4.

---

## 2. Frozen Protocol & Representation Contract

### Relational Representation ($R_{\text{full}}$)
Evaluated immediately before step $t+1$ for two states $X_t^A, X_t^B$ that share output prefix $z_{1:t}$:
$$R_t(A, B) = \big(i_{\text{val\_aligned}},\; \Delta j_{t+1},\; j_{\text{mapped}},\; \Delta k_{t+1}\big)$$
Where:
1. $i_{\text{val\_aligned}} = \mathbb{I}[\psi_t(i_{t+1}) = i_{t+1}]$, checking whether $S_t^A[i_{t+1}] = S_t^B[i_{t+1}]$.
2. $\Delta j_{t+1} = (j_{t+1}^B - j_{t+1}^A) \pmod m$, tracking impending pointer disparity after adding $S[i_{t+1}]$.
3. $j_{\text{mapped}} = \mathbb{I}[\psi_t(j_{t+1}^A) = j_{t+1}^B]$, checking whether $\psi_t$ aligns the impending swap targets.
4. $\Delta k_{t+1} = (k_{t+1}^B - k_{t+1}^A) \pmod m$, tracking impending output address offset under the swap.

### Population & Null Control Protocol
- **Population:** All unordered pairs $\{A, B\}$ sharing output prefix $z_{1:t}$.
- **Sampling:** When available pairs exceed 25,000, uniform stratified sampling across prefix buckets proportional to bucket pair weight; exact enumeration otherwise.
- **Null Control ($P_{\text{matched}}$):** 100 Monte Carlo trials randomly permuting the ground-truth binary labels (survives $\in \{0, 1\}$) across the exact observed equivalence class partition $\{n_1, \dots, n_k\}$.
- **Excess Purity Gain:** $G_R(t) = P_{\text{observed}}(t) - P_{\text{matched}}(t)$.

---

## 3. Held-Out $m=9$ Complete Transition Data

- State space: $9! = 362,880$ permutations.
- Runtime: 20.23 seconds.

| Transition $t \to t+1$ | Total Available Pairs | Sampled Pairs | Classes | Observed Strict Purity | Matched Null Purity ($P_{\text{null}}$) | Excess Purity Gain $G_R(t)$ | Majority Purity |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| $1 \to 2$ | $7,357,469,760$ | 25,002 | 234 | 0.1% | 0.2% | **-0.1%** | 87.2% |
| $2 \to 3$ | $952,991,424$ | 25,006 | 234 | 0.9% | 0.5% | **+0.4%** | 89.1% |
| $3 \to 4$ | $107,675,747$ | 25,009 | 234 | 0.5% | 0.3% | **+0.2%** | 88.6% |
| $4 \to 5$ | $12,520,231$ | 25,204 | 234 | 0.3% | 0.2% | **+0.1%** | 88.2% |
| $5 \to 6$ | $1,520,562$ | 60,568 | 234 | 0.0% | 0.0% | **0.0%** | 88.4% |
| $6 \to 7$ | $201,545$ | 86,995 | 234 | 0.0% | 0.0% | **0.0%** | 88.3% |
| $7 \to 8$ | $29,047$ | 28,737 | 234 | 1.2% | 0.2% | **+1.0%** | 88.5% |
| **$8 \to 9$** | $3,834$ | $3,834$ | 231 | 14.2% | 10.0% | **+4.3%** | 89.4% |
| **$9 \to 10$** | **$450$** | **$450$** | **$162$** | **$73.1\%$** | **$56.4\%$** | **$+16.8\%$** | **$93.3\%$** |
| $10 \to 11$ | 64 | 64 | 43 | 70.3% | 70.6% | **-0.3%** | 89.1% |
| $11 \to 12$ | 15 | 15 | 11 | 100.0% | 81.5% | **+18.5%** | 100.0% |
| $12 \to 13$ | 3 | 3 | 3 | 100.0% | 100.0% | **0.0%** | 100.0% |
| $13 \to 14$ | 1 | 1 | 1 | 100.0% | 100.0% | **0.0%** | 100.0% |

---

## 4. Cross-$m$ Comparative Summary ($m \in \{6, 7, 8, 9\}$)

Tracking the pre-terminal excess purity window across state spaces:
* **$m=6$**: Peak at $t = 3 \to 4$ ($G_R = +7.2\%$) and $t = 4 \to 5$ ($G_R = +5.7\%$).
* **$m=7$**: Peak at $t = 5 \to 6$ ($G_R = +2.8\%$) and $t = 7 \to 8$ ($G_R = +6.2\%$).
* **$m=8$**: Peak at $t = 6 \to 7$ ($G_R = +4.0\%$) and $t = 7 \to 8$ ($G_R = +2.2\%$).
* **$m=9$ (Held Out)**: Peak at $t = 8 \to 9$ ($G_R = +4.3\%$) and $t = 9 \to 10$ ($G_R = +16.8\%$).

---

## 5. Artifact Provenance & Checksums

### Environment
- **Python**: 3.14.3
- **Seed Base**: `900 + t` (Null controls), `m * 1000 + t` (Sampling)
- **Pre-m=9 Freeze SHA-256**: `7f9f56f64c17791ab30b20a543e98c452dc877c7eb5effecea3683c6f955556a`

### Artifact SHA-256 Checksums
| File | Path | SHA-256 |
|---|---|---|
| Runner Script | `rc4_m9_held_out_test_v1.py` | `0d28701e893e22606d21464c2ec384ee66d3a5a8f4c4a5c68b6938a9d1847625` |
| Output CSV | `output/m9_held_out/rc4_m9_held_out_purity_control.csv` | `a4be39279a36b62261f1a3a449fabcd9b9c2fc0de1faf7d3e13ad12f4e15b009` |
| Output Summary JSON | `output/m9_held_out/rc4_m9_held_out_summary.json` | `a019aa5e21c82f0a4de41b5e668faa614d9c57969098a9e936b03471cfdf2514` |
| Manifest JSON | `output/m9_held_out/manifest.json` | `8c6a084df9487b923f66c9ff9ae0357770bc10fef42c16c0fa3706037dafd137` |

---

## 6. Next Research Direction

Rather than scaling blindly to $m=10$, the next investigation is mechanistic:
$$\boxed{\text{What internal algebra within } R_t \text{ produced the } +16.8\% \text{ purity gain at } 9 \to 10?}$$
Analyze the exact structure of the pure versus mixed equivalence classes among those 450 pairs to determine whether $R_t$ can be leveraged algorithmically.
