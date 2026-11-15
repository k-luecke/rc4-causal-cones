#!/usr/bin/env python3
"""
RC4 Held-Out m=9 Relational Sufficiency & Matched-Control Test (Boss Fight).

Frozen Evaluation Contract:
- Target state space: m = 9 (9! = 362,880 initial permutations).
- Unchanged relational feature tuple R_full = (i_val_aligned, delta_next_j, next_j_mapped, delta_k).
- Exact pair accounting: unordered pairs {A, B} sharing prefix z_{1:t}.
- Matched-granularity null control: 100 label permutations across the exact observed R_t partition.
- Metric: G_R(t) = P_observed(t) - P_matched(t).
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prga_step(state, i, j, m):
    S = list(state)
    i = (i + 1) % m
    j = (j + S[i]) % m
    S[i], S[j] = S[j], S[i]
    k = (S[i] + S[j]) % m
    z = S[k]
    return tuple(S), i, j, k, z


def position_correspondence(state_a, state_b):
    pos_b = {val: pos for pos, val in enumerate(state_b)}
    return tuple(pos_b[val] for val in state_a)


def extract_relational_tuple(state_a, i_a, j_a, state_b, i_b, j_b, m):
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


def sample_pairs_from_groups(current_groups, max_total_pairs=25000, rng_seed=42):
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
        for prefix, group in current_groups.items():
            if len(group) >= 2:
                for i_a, i_b in itertools.combinations(range(len(group)), 2):
                    sampled_pairs.append((group[i_a], group[i_b]))
    else:
        for prefix, n_pairs in bucket_counts.items():
            quota = max(1, int(round((n_pairs / total_available) * max_total_pairs)))
            group = current_groups[prefix]
            n = len(group)
            
            if quota >= n_pairs:
                for i_a, i_b in itertools.combinations(range(n), 2):
                    sampled_pairs.append((group[i_a], group[i_b]))
            else:
                seen = set()
                while len(seen) < quota:
                    i_a = rng.randrange(n)
                    i_b = rng.randrange(n)
                    if i_a != i_b:
                        seen.add((min(i_a, i_b), max(i_a, i_b)))
                for i_a, i_b in seen:
                    sampled_pairs.append((group[i_a], group[i_b]))
                    
    return sampled_pairs, total_available


def main():
    m = 9
    max_steps = 15
    outdir = Path(r".")
    drive_outdir = Path(r"m9_held_out")
    outdir.mkdir(parents=True, exist_ok=True)
    drive_outdir.mkdir(parents=True, exist_ok=True)
    
    print(f"===========================================================", flush=True)
    print(f"RC4 HELD-OUT TEST: m = {m} (State space: 9! = 362,880)", flush=True)
    print(f"===========================================================", flush=True)
    t0 = time.time()
    
    print("Generating all 9! = 362,880 permutations...", flush=True)
    all_perms = list(itertools.permutations(range(m)))
    
    print("Simulating step 1 to establish initial prefix buckets...", flush=True)
    current_groups = defaultdict(list)
    for p in all_perms:
        s1, i1, j1, _, z1 = prga_step(p, 0, 0, m)
        current_groups[(z1,)].append((s1, i1, j1))
        
    results = []
    
    for t in range(1, max_steps):
        next_step = t + 1
        next_groups = defaultdict(list)
        
        sampled_pairs, total_available_pairs = sample_pairs_from_groups(
            current_groups, max_total_pairs=25000, rng_seed=m * 1000 + t
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
            
        metrics = compute_purity_metrics(class_outcomes, num_null_trials=100, rng_seed=900 + t)
        
        print(f"  t={t:2d}->{next_step:2d} | Pairs: {metrics['total_pairs']:5d}/{total_available_pairs:<10d} | "
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

    elapsed = time.time() - t0
    print(f"\nm=9 run complete in {elapsed:.2f} seconds!", flush=True)

    csv_file = outdir / "rc4_m9_held_out_purity_control.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    json_file = outdir / "rc4_m9_held_out_summary.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({"m": m, "elapsed_seconds": elapsed, "transitions": results}, f, indent=2)

    # Compute artifact hashes
    manifest = {
        "experiment": "rc4_m9_held_out_test_v1",
        "m": m,
        "elapsed_seconds": elapsed,
        "frozen_relational_tuple": "R_full = (i_val_aligned, delta_next_j, next_j_mapped, delta_k)",
        "files": {
            "rc4_m9_held_out_purity_control.csv": sha256_bytes(csv_file.read_bytes()),
            "rc4_m9_held_out_summary.json": sha256_bytes(json_file.read_bytes()),
        }
    }
    manifest_file = outdir / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Mirror all outputs to Google Drive
    for fpath in [csv_file, json_file, manifest_file]:
        dest = drive_outdir / fpath.name
        dest.write_bytes(fpath.read_bytes())
        
    print(f"Results mirrored to: {drive_outdir}", flush=True)


if __name__ == "__main__":
    main()
