#!/usr/bin/env python3
"""
RC4 Relational Purity & Matched-Control Experiment v1 (Streamlined).

Attacks the middle-regime phase transition in relational collision prediction:
1. Exact total pair accounting: total_available_pairs = sum(n_g * (n_g - 1) // 2).
2. Efficient direct sampling of pairs without instantiating 100M objects in RAM.
3. Matched-granularity null controls P_matched(t) by permuting survival labels
   across the identical equivalence class partition {n_1, ..., n_k}.
4. Computes the excess purity gain: G_R(t) = P_R(t) - P_matched(t).
5. Tests frozen relational features across m in {6, 7, 8}.
"""

from __future__ import annotations

import csv
import itertools
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path


def prga_step(state, i, j, m):
    """Execute one PRGA step: returns (next_state, next_i, next_j, k, z)."""
    S = list(state)
    i = (i + 1) % m
    j = (j + S[i]) % m
    S[i], S[j] = S[j], S[i]
    k = (S[i] + S[j]) % m
    z = S[k]
    return tuple(S), i, j, k, z


def position_correspondence(state_a, state_b):
    """psi(p) = index in B containing the value that A contains at position p."""
    pos_b = {val: pos for pos, val in enumerate(state_b)}
    return tuple(pos_b[val] for val in state_a)


def extract_relational_tuple(state_a, i_a, j_a, state_b, i_b, j_b, m):
    """
    Evaluates the frozen candidate relational tuple immediately before step t+1.
    R_full = (i_val_aligned, delta_next_j, next_j_mapped, delta_k)
    """
    psi = position_correspondence(state_a, state_b)
    next_i = (i_a + 1) % m
    
    # 1. Does S_A[next_i] == S_B[next_i]?
    i_val_aligned = int(psi[next_i] == next_i)
    
    # 2. Impending next_j values
    val_i_a = state_a[next_i]
    val_i_b = state_b[next_i]
    next_j_a = (j_a + val_i_a) % m
    next_j_b = (j_b + val_i_b) % m
    delta_next_j = (next_j_b - next_j_a) % m
    
    # 3. Does psi map A's impending swap target to B's impending swap target?
    next_j_mapped = int(psi[next_j_a] == next_j_b)
    
    # 4. Impending output address delta
    s_next_i_a, s_next_j_a = state_a[next_j_a], state_a[next_i]
    s_next_i_b, s_next_j_b = state_b[next_j_b], state_b[next_i]
    k_next_a = (s_next_i_a + s_next_j_a) % m
    k_next_b = (s_next_i_b + s_next_j_b) % m
    delta_k = (k_next_b - k_next_a) % m
    
    return (i_val_aligned, delta_next_j, next_j_mapped, delta_k)


def compute_purity_metrics(class_outcomes, num_null_trials=100, rng_seed=42):
    total_pairs = sum(len(outs) for outs in class_outcomes.values())
    if total_pairs == 0:
        return {}

    strict_pure_pairs = sum(len(outs) for outs in class_outcomes.values() if all(o == 1 for o in outs) or all(o == 0 for o in outs))
    majority_pure_pairs = sum(max(sum(outs), len(outs) - sum(outs)) for outs in class_outcomes.values())
    
    obs_strict_pct = (strict_pure_pairs / total_pairs) * 100.0
    obs_majority_pct = (majority_pure_pairs / total_pairs) * 100.0
    
    class_sizes = [len(outs) for outs in class_outcomes.values()]
    all_labels = [o for outs in class_outcomes.values() for o in outs]
    global_survivors = sum(all_labels)
    global_base_rate = (max(global_survivors, total_pairs - global_survivors) / total_pairs) * 100.0
    
    rng = random.Random(rng_seed)
    null_strict_accum = 0.0
    null_majority_accum = 0.0
    
    for _ in range(num_null_trials):
        shuffled = all_labels[:]
        rng.shuffle(shuffled)
        
        offset = 0
        trial_strict = 0
        trial_majority = 0
        
        for sz in class_sizes:
            chunk = shuffled[offset:offset + sz]
            offset += sz
            c_ones = sum(chunk)
            if c_ones == sz or c_ones == 0:
                trial_strict += sz
            trial_majority += max(c_ones, sz - c_ones)
            
        null_strict_accum += trial_strict
        null_majority_accum += trial_majority
        
    null_strict_pct = (null_strict_accum / num_null_trials / total_pairs) * 100.0
    null_majority_pct = (null_majority_accum / num_null_trials / total_pairs) * 100.0
    
    return {
        "total_pairs": total_pairs,
        "num_classes": len(class_outcomes),
        "global_survivors": global_survivors,
        "global_separators": total_pairs - global_survivors,
        "base_rate_majority_pct": global_base_rate,
        "observed_strict_purity_pct": obs_strict_pct,
        "null_strict_purity_pct": null_strict_pct,
        "gain_strict_G_R": obs_strict_pct - null_strict_pct,
        "observed_majority_purity_pct": obs_majority_pct,
        "null_majority_purity_pct": null_majority_pct,
        "gain_majority_G_R": obs_majority_pct - null_majority_pct,
    }


def sample_pairs_from_groups(current_groups, max_total_pairs=20000, rng_seed=42):
    """Directly samples up to max_total_pairs across all groups proportional to bucket pair counts."""
    bucket_counts = {}
    for prefix, group in current_groups.items():
        n = len(group)
        if n >= 2:
            bucket_counts[prefix] = n * (n - 1) // 2
            
    total_available = sum(bucket_counts.values())
    if total_available == 0:
        return [], 0
        
    rng = random.Random(rng_seed)
    sampled_pairs = []
    
    if total_available <= max_total_pairs:
        # Take all
        for prefix, group in current_groups.items():
            if len(group) >= 2:
                for i_a, i_b in itertools.combinations(range(len(group)), 2):
                    sampled_pairs.append((group[i_a], group[i_b]))
    else:
        # Allocate sample quota to each bucket proportional to its pair weight
        for prefix, n_pairs in bucket_counts.items():
            quota = max(1, int(round((n_pairs / total_available) * max_total_pairs)))
            group = current_groups[prefix]
            n = len(group)
            
            if quota >= n_pairs:
                for i_a, i_b in itertools.combinations(range(n), 2):
                    sampled_pairs.append((group[i_a], group[i_b]))
            else:
                # Sample random index pairs with replacement then dedup
                seen = set()
                while len(seen) < quota:
                    i_a = rng.randrange(n)
                    i_b = rng.randrange(n)
                    if i_a != i_b:
                        pair = (min(i_a, i_b), max(i_a, i_b))
                        seen.add(pair)
                for i_a, i_b in seen:
                    sampled_pairs.append((group[i_a], group[i_b]))
                    
    return sampled_pairs, total_available


def run_control_study(m_values=(6, 7, 8), max_pairs_per_step=20000, outdir="output/purity_control"):
    out_path = Path(outdir)
    out_path.mkdir(parents=True, exist_ok=True)
    results = []
    
    for m in m_values:
        print(f"\n=======================================================", flush=True)
        print(f"Audited Purity & Matched Control Study for m = {m}", flush=True)
        print(f"=======================================================", flush=True)
        
        all_perms = list(itertools.permutations(range(m)))
        current_groups = defaultdict(list)
        for p in all_perms:
            s1, i1, j1, _, z1 = prga_step(p, 0, 0, m)
            current_groups[(z1,)].append((s1, i1, j1))
            
        max_steps = 12
        for t in range(1, max_steps):
            next_step = t + 1
            next_groups = defaultdict(list)
            
            sampled_pairs, total_available_pairs = sample_pairs_from_groups(
                current_groups, max_total_pairs=max_pairs_per_step, rng_seed=m * 100 + t
            )
            
            if total_available_pairs == 0:
                print(f"  t={t}->{next_step:2d}: 0 colliding pairs remaining.", flush=True)
                break
                
            class_outcomes = defaultdict(list)
            for (state_a, i_a, j_a), (state_b, i_b, j_b) in sampled_pairs:
                _, _, _, _, z_a = prga_step(state_a, i_a, j_a, m)
                _, _, _, _, z_b = prga_step(state_b, i_b, j_b, m)
                survives = int(z_a == z_b)
                r_key = extract_relational_tuple(state_a, i_a, j_a, state_b, i_b, j_b, m)
                class_outcomes[r_key].append(survives)
                
            metrics = compute_purity_metrics(class_outcomes, num_null_trials=100, rng_seed=42 + t)
            
            print(f"  t={t}->{next_step:2d} | Pairs: {metrics['total_pairs']:5d}/{total_available_pairs:<9d} | "
                  f"Strict: {metrics['observed_strict_purity_pct']:5.1f}% (Null: {metrics['null_strict_purity_pct']:5.1f}%, G_R: {metrics['gain_strict_G_R']:+5.1f}%) | "
                  f"Maj: {metrics['observed_majority_purity_pct']:5.1f}% (Null: {metrics['null_majority_purity_pct']:5.1f}%, G_R: {metrics['gain_majority_G_R']:+5.1f}%)",
                  flush=True)
            
            row = {
                "m": m,
                "transition": f"{t}->{next_step}",
                "from_t": t,
                "to_t": next_step,
                "total_available_pairs": total_available_pairs,
                "sampled_pairs": metrics["total_pairs"],
                "num_classes": metrics["num_classes"],
                "global_survivors": metrics["global_survivors"],
                "global_separators": metrics["global_separators"],
                "base_rate_majority_pct": metrics["base_rate_majority_pct"],
                "observed_strict_pct": metrics["observed_strict_purity_pct"],
                "null_strict_pct": metrics["null_strict_purity_pct"],
                "gain_strict_G_R": metrics["gain_strict_G_R"],
                "observed_majority_pct": metrics["observed_majority_purity_pct"],
                "null_majority_pct": metrics["null_majority_purity_pct"],
                "gain_majority_G_R": metrics["gain_majority_G_R"],
            }
            results.append(row)
            
            for prefix, group in current_groups.items():
                for state, i, j in group:
                    next_s, n_i, n_j, _, z = prga_step(state, i, j, m)
                    next_groups[prefix + (z,)].append((next_s, n_i, n_j))
            current_groups = next_groups

    csv_file = out_path / "rc4_relational_purity_control_v1.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
        
    print(f"\nWrote CSV: {csv_file}", flush=True)


if __name__ == "__main__":
    run_control_study()
