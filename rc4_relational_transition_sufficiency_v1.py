#!/usr/bin/env python3
"""
RC4 Relational Transition Sufficiency Experiment v1.

Evaluates whether compact current-state relational quantities R_t(A, B)
under the position correspondence psi_t are sufficient to predict whether
an output collision survives or separates at step t+1.

Operates across ALL prefix-colliding state pairs for m in {6, 7, 8}.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path


def prga_step(state, i, j, m):
    """Execute one PRGA step, returning (next_state, next_i, next_j, k, z)."""
    S = list(state)
    i = (i + 1) % m
    j = (j + S[i]) % m
    S[i], S[j] = S[j], S[i]
    k = (S[i] + S[j]) % m
    z = S[k]
    return tuple(S), i, j, k, z


def position_correspondence(state_a, state_b):
    """psi(p) = index in B of A's value at position p."""
    pos_b = {val: pos for pos, val in enumerate(state_b)}
    return tuple(pos_b[val] for val in state_a)


def extract_relational_features(state_a, i_a, j_a, state_b, i_b, j_b, m):
    """
    Candidate relational variables known at time t immediately BEFORE step t+1.
    """
    psi = position_correspondence(state_a, state_b)
    
    # 1. Impending i position
    next_i = (i_a + 1) % m  # same for A and B
    
    # Does B have A's i-payload at position next_i?
    # If yes, S_A[next_i] == S_B[next_i], meaning both add identical values to j.
    i_val_aligned = int(psi[next_i] == next_i)
    
    # Delta j at time t
    delta_j = (j_b - j_a) % m
    
    # Does psi map A's current j to B's current j?
    j_aligned = int(psi[j_a] == j_b)
    
    # Impending next_j values
    val_i_a = state_a[next_i]
    val_i_b = state_b[next_i]
    next_j_a = (j_a + val_i_a) % m
    next_j_b = (j_b + val_i_b) % m
    delta_next_j = (next_j_b - next_j_a) % m
    
    # Does psi map A's impending swap target to B's impending swap target?
    next_j_mapped = int(psi[next_j_a] == next_j_b)

    # Output address correspondence preview:
    # Does the impending swap preserve correspondence at the impending output addresses?
    # S_next[next_i] = S[next_j], S_next[next_j] = S[next_i]
    s_next_i_a, s_next_j_a = state_a[next_j_a], state_a[next_i]
    s_next_i_b, s_next_j_b = state_b[next_j_b], state_b[next_i]
    k_next_a = (s_next_i_a + s_next_j_a) % m
    k_next_b = (s_next_i_b + s_next_j_b) % m
    delta_k = (k_next_b - k_next_a) % m
    
    # Fixed points count
    fixed_points = sum(1 for p in range(m) if psi[p] == p)

    return {
        "i_val_aligned": i_val_aligned,
        "delta_j": delta_j,
        "j_aligned": j_aligned,
        "delta_next_j": delta_next_j,
        "next_j_mapped": next_j_mapped,
        "delta_k": delta_k,
        "fixed_points": fixed_points,
    }


def run_experiment(m_values=(6, 7, 8), max_steps=12, max_pairs_per_bucket=5000, outdir="output/relational_sufficiency"):
    out_path = Path(outdir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    summary_by_m = {}

    for m in m_values:
        print(f"\n==========================================", flush=True)
        print(f"Running Relational Sufficiency for m = {m}", flush=True)
        print(f"==========================================", flush=True)
        t0 = time.time()
        
        all_perms = list(itertools.permutations(range(m)))
        
        # Advance all permutations through step 1 to establish initial output buckets
        # Map: output_tuple -> list of (state, i, j)
        current_groups = defaultdict(list)
        for p in all_perms:
            s1, i1, j1, k1, z1 = prga_step(p, 0, 0, m)
            current_groups[(z1,)].append((s1, i1, j1))
            
        step_metrics = []
        
        for t in range(1, max_steps):
            next_step = t + 1
            pair_transitions = []
            next_groups = defaultdict(list)
            
            for prefix, group in current_groups.items():
                if len(group) < 2:
                    continue
                
                # Pairwise comparison within this colliding prefix group
                n_members = len(group)
                if n_members * (n_members - 1) // 2 > max_pairs_per_bucket:
                    # Deterministic sub-sampling
                    rng = random.Random(42 + t)
                    sampled_indices = rng.sample(range(n_members), min(n_members, 100))
                    pairs_to_test = list(itertools.combinations(sampled_indices, 2))
                else:
                    pairs_to_test = list(itertools.combinations(range(n_members), 2))
                
                for idx_a, idx_b in pairs_to_test:
                    state_a, i_a, j_a = group[idx_a]
                    state_b, i_b, j_b = group[idx_b]
                    
                    next_s_a, n_i_a, n_j_a, k_a, z_next_a = prga_step(state_a, i_a, j_a, m)
                    next_s_b, n_i_b, n_j_b, k_b, z_next_b = prga_step(state_b, i_b, j_b, m)
                    
                    survives = int(z_next_a == z_next_b)
                    features = extract_relational_features(state_a, i_a, j_a, state_b, i_b, j_b, m)
                    
                    pair_transitions.append({
                        "features": features,
                        "survives": survives,
                    })

                # Now advance all group members to form next prefix groups
                for state, i, j in group:
                    next_s, n_i, n_j, _, z_next = prga_step(state, i, j, m)
                    next_groups[prefix + (z_next,)].append((next_s, n_i, n_j))

            current_groups = next_groups
            total_pairs = len(pair_transitions)
            
            if total_pairs == 0:
                print(f"  Step {next_step:2d}: 0 colliding pairs remaining.", flush=True)
                break
                
            surviving_pairs = sum(1 for pt in pair_transitions if pt["survives"] == 1)
            separating_pairs = total_pairs - surviving_pairs
            
            # Candidate models:
            models = {
                # Model 1: Full local relational state
                "R_full": lambda f: (f["i_val_aligned"], f["delta_next_j"], f["next_j_mapped"], f["delta_k"]),
                # Model 2: Delta-k and swap mapping
                "R_k_and_swap": lambda f: (f["delta_k"], f["next_j_mapped"]),
                # Model 3: Address delta only
                "R_delta_k_only": lambda f: (f["delta_k"],),
                # Model 4: Impending j alignment only
                "R_next_j_only": lambda f: (f["delta_next_j"], f["next_j_mapped"]),
                # Model 5: Scalar fixed-points baseline
                "R_fixed_points": lambda f: (f["fixed_points"],),
            }
            
            purity_results = {}
            for name, extractor in models.items():
                equiv_classes = defaultdict(list)
                for pt in pair_transitions:
                    r_val = extractor(pt["features"])
                    equiv_classes[r_val].append(pt["survives"])
                
                pure_classes = 0
                pure_pairs = 0
                for r_val, outcomes in equiv_classes.items():
                    if all(o == 1 for o in outcomes) or all(o == 0 for o in outcomes):
                        pure_classes += 1
                        pure_pairs += len(outcomes)
                
                pct_pure_pairs = (pure_pairs / total_pairs) * 100
                purity_results[name] = {
                    "num_classes": len(equiv_classes),
                    "pure_classes": pure_classes,
                    "pure_pairs": pure_pairs,
                    "pct_deterministic": pct_pure_pairs
                }
            
            print(f"  Transition t={t}->{next_step:2d}: {total_pairs:6d} pairs (Surv: {surviving_pairs:5d}, Sep: {separating_pairs:5d}) | "
                  f"R_full: {purity_results['R_full']['pct_deterministic']:5.1f}% det ({purity_results['R_full']['num_classes']} cls) | "
                  f"R_k_swap: {purity_results['R_k_and_swap']['pct_deterministic']:5.1f}% | "
                  f"R_fixed: {purity_results['R_fixed_points']['pct_deterministic']:5.1f}%", flush=True)
            
            step_metrics.append({
                "m": m,
                "transition": f"{t}->{next_step}",
                "from_step": t,
                "to_step": next_step,
                "total_pairs": total_pairs,
                "surviving_pairs": surviving_pairs,
                "separating_pairs": separating_pairs,
                "models": purity_results
            })
            
        elapsed = time.time() - t0
        summary_by_m[m] = {"elapsed": elapsed, "transitions": step_metrics}
        print(f"m={m} finished in {elapsed:.2f}s", flush=True)

    with open(out_path / "sufficiency_summary.json", "w") as f:
        json.dump(summary_by_m, f, indent=2)

    csv_rows = []
    for m, data in summary_by_m.items():
        for s in data["transitions"]:
            row = {
                "m": m,
                "transition": s["transition"],
                "total_pairs": s["total_pairs"],
                "surviving_pairs": s["surviving_pairs"],
                "separating_pairs": s["separating_pairs"],
                "R_full_deterministic_pct": s["models"]["R_full"]["pct_deterministic"],
                "R_full_classes": s["models"]["R_full"]["num_classes"],
                "R_k_swap_deterministic_pct": s["models"]["R_k_and_swap"]["pct_deterministic"],
                "R_delta_k_only_pct": s["models"]["R_delta_k_only"]["pct_deterministic"],
                "R_next_j_only_pct": s["models"]["R_next_j_only"]["pct_deterministic"],
                "R_fixed_points_pct": s["models"]["R_fixed_points"]["pct_deterministic"],
            }
            csv_rows.append(row)
            
    with open(out_path / "relational_sufficiency.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
        
    print(f"\nWrote CSV: {out_path / 'relational_sufficiency.csv'}", flush=True)
    print(f"Wrote JSON: {out_path / 'sufficiency_summary.json'}", flush=True)


if __name__ == "__main__":
    run_experiment()
