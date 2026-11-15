# RC4 Global-Compatibility Lab — Baseline Results

Preserved from initial run on 2026-09-30.

## Environment
- Python 3.14.3
- Seed: `20260930`
- Notebook: `rc4_global_compatibility_lab-2.ipynb` (Google Drive, Driftbound Labs)

## Exhaustive Control (Brute Force)

| m | Factorial Space | Survivors | Planted Truth Found | Time (s) |
|---|---|---|---|---|
| 6 | 720 | 1 | ✅ | 0.012 |
| 7 | 5,040 | 1 | ✅ | 0.082 |
| 8 | 40,320 | 1 | ✅ | 0.711 |

All three uniquely identify the planted permutation.

## Demand-Driven DFS

| m | Factorial Space | DFS Nodes | Nodes / m! | Survivors | Truth Found | Time (s) | Status |
|---|---|---|---|---|---|---|---|
| 8 | 40,320 | 109,601 | 2.718 | 1 | ✅ | 0.573 | **Completed** |
| 10 | 3,628,800 | 9,159,697 | 2.524 | 1 | ✅ | 54.961 | **Completed** |
| 12 | 479,001,600 | 2,000,001 | 0.00418 | 0 | ❌ | 13.145 | **⚠️ CENSORED — 2M node cap** |
| 16 | 20,922,789,888,000 | 2,000,001 | 9.56e-08 | 0 | ❌ | 13.672 | **⚠️ CENSORED — 2M node cap** |

> [!CAUTION]
> The m=12 and m=16 rows were **terminated by the 2,000,001-node safety cap**, not by algorithmic completion. The `nodes/m!` ratios for these rows reflect the cap ceiling divided by factorial space, **not evidence of pruning or contraction**. These are censored data points.

## Depth Contraction (m=10, completed)

| Assigned Slots | DFS Nodes | Naive Prefix States | Fraction of Naive |
|---|---|---|---|
| 0 | 1 | 1 | 1.000 |
| 1 | 10 | 10 | 1.000 |
| 2 | 90 | 90 | 1.000 |
| 3 | 720 | 720 | 1.000 |
| 4 | 5,040 | 5,040 | 1.000 |
| 5 | 30,240 | 30,240 | 1.000 |
| 6 | 151,200 | 151,200 | 1.000 |
| 7 | 604,800 | 604,800 | 1.000 |
| 8 | 1,814,400 | 1,814,400 | 1.000 |
| 9 | 3,567,458 | 3,628,800 | 0.983 |
| 10 | 2,985,738 | 3,628,800 | 0.823 |

Contraction occurs almost entirely at depth 9–10 (the last two slots). Through depth 8, every partial assignment survives — no early pruning.

## Plots (preserved, not overwritten)

- `.`
- `.`

## Frozen Instances

- `.`
- SHA-256 of instances payload: `ae7a8bf22f0444cfdff32f4194a71890f8b79a834a984632f330b9bdf852cce7`
