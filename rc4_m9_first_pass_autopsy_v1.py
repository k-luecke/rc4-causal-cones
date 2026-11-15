#!/usr/bin/env python3
"""
RC4 First-Pass Boundary Handoff Experiment v1.
Comprehensive autopsy script and test suite.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from rc4_autopsy_core import (
    prga_step_detail,
    full_trace,
    position_correspondence,
    cycle_decomposition,
    cycle_containing,
    analyze_position_history,
    compute_label_permutation_null,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_autopsy():
    base_dir = Path(str(Path(__file__).resolve().parent))
    outdir = base_dir / "output" / "m9_autopsy"
    drive_outdir = Path(r"m9_autopsy")
    outdir.mkdir(parents=True, exist_ok=True)
    drive_outdir.mkdir(parents=True, exist_ok=True)
    
    pop_file = base_dir / "output" / "m9_held_out" / "rc4_m9_9to10_pair_population.json"
    with open(pop_file, "r") as f:
        population = json.load(f)
        
    print(f"Loaded {len(population)} pairs from {pop_file}")
    
    m = 9
    autopsy_records = []
    
    for item in population:
        pair_id = item["pair_id"]
        perm_a = item["perm_a"]
        perm_b = item["perm_b"]
        
        trace_a = full_trace(perm_a, steps=10, m=m)
        trace_b = full_trace(perm_b, steps=10, m=m)
        
        # State at t=9
        s9_a = trace_a[8]["post_state"]
        s9_b = trace_b[8]["post_state"]
        j9_a = trace_a[8]["j"]
        j9_b = trace_b[8]["j"]
        psi_9 = position_correspondence(s9_a, s9_b)
        cycles_9 = cycle_decomposition(psi_9)
        cycle_type_9 = tuple(sorted(len(c) for c in cycles_9))
        fixed_points_9 = sum(1 for p in range(m) if psi_9[p] == p)
        support_size_9 = m - fixed_points_9
        
        # State at t=10
        s10_a = trace_a[9]["post_state"]
        s10_b = trace_b[9]["post_state"]
        j10_a = trace_a[9]["j"]
        j10_b = trace_b[9]["j"]
        k10_a = trace_a[9]["k"]
        k10_b = trace_b[9]["k"]
        z10_a = trace_a[9]["z"]
        z10_b = trace_b[9]["z"]
        survives = int(z10_a == z10_b)
        psi_10 = position_correspondence(s10_a, s10_b)
        
        # Frozen R_9 tuple
        # i_10 = 1 (position 1)
        r_i_aligned = int(psi_9[1] == 1)
        delta_j10 = (j10_b - j10_a) % m
        j10_mapped = int(psi_9[j10_a] == j10_b)
        delta_k10 = (k10_b - k10_a) % m
        r_tuple = (r_i_aligned, delta_j10, j10_mapped, delta_k10)
        
        # Position 1 analysis (revisited position)
        orig_val_a_1 = perm_a[1]
        orig_val_b_1 = perm_b[1]
        s9_val_a_1 = s9_a[1]
        s9_val_b_1 = s9_b[1]
        psi9_at_1 = psi_9[1]
        psi9_1_is_fixed = int(psi_9[1] == 1)
        cycle_at_1 = cycle_containing(cycles_9, 1)
        cycle_len_at_1 = len(cycle_at_1)
        
        # History of position 1 across steps 1..9
        hist_a = analyze_position_history(trace_a, range(1, 10), m=m)
        hist_b = analyze_position_history(trace_b, range(1, 10), m=m)
        
        # Position 1 modifications in 1..9
        # (Note: step 1 always touches position 1 via deterministic i=1)
        mods_a_1 = hist_a[1]["modifications"]
        mods_b_1 = hist_b[1]["modifications"]
        last_mod_a_1 = max(mods_a_1) if mods_a_1 else 0
        last_mod_b_1 = max(mods_b_1) if mods_b_1 else 0
        mod_count_a_1 = len(mods_a_1)
        mod_count_b_1 = len(mods_b_1)
        
        # Was position 1 selected by j during steps 1..9?
        j_hits_a_1 = len(hist_a[1]["j_selections"])
        j_hits_b_1 = len(hist_b[1]["j_selections"])
        j_hits_after_step1_a = len([s for s in hist_a[1]["j_selections"] if s > 1])
        j_hits_after_step1_b = len([s for s in hist_b[1]["j_selections"] if s > 1])
        
        p1_disturbed_a = int(mod_count_a_1 > 1)
        p1_disturbed_b = int(mod_count_b_1 > 1)
        p1_disturbed_either = int(p1_disturbed_a or p1_disturbed_b)
        p1_disturbed_both = int(p1_disturbed_a and p1_disturbed_b)
        
        # Impending step 10 swaps under psi_9
        # Swap A is (1, j10_a), Swap B is (1, j10_b)
        swap_a_mapped_to_b = (
            (psi_9[1] == 1 and psi_9[j10_a] == j10_b) or
            (psi_9[1] == j10_b and psi_9[j10_a] == 1)
        )
        
        # Output address exposure test
        # Does correspondence hold at output address before step 10 swap?
        pre_swap_addr_match = int(psi_9[k10_a] == k10_b)
        # Does correspondence hold at output address after step 10 swap?
        post_swap_addr_match = int(psi_10[k10_a] == k10_b)
        
        if pre_swap_addr_match and post_swap_addr_match:
            exposure_class = "MATCH_PRESERVED"
        elif not pre_swap_addr_match and not post_swap_addr_match:
            exposure_class = "PRE_EXISTING_EXPOSED"
        elif pre_swap_addr_match and not post_swap_addr_match:
            exposure_class = "CREATED_BY_SWAP"
        else:
            exposure_class = "REPAIRED_BY_SWAP"
            
        record = {
            "pair_id": pair_id,
            "prefix_id": "_".join(map(str, item["prefix_9"])),
            # Frozen R_9 features
            "r_i_aligned": r_i_aligned,
            "r_delta_j10": delta_j10,
            "r_j10_mapped": j10_mapped,
            "r_delta_k10": delta_k10,
            "r_tuple": str(r_tuple),
            # Step 10 revisit position i=1 features
            "orig_val_a_1": orig_val_a_1,
            "orig_val_b_1": orig_val_b_1,
            "s9_val_a_1": s9_val_a_1,
            "s9_val_b_1": s9_val_b_1,
            "psi9_at_1": psi9_at_1,
            "psi9_1_is_fixed": psi9_1_is_fixed,
            "cycle_len_at_1": cycle_len_at_1,
            "cycle_at_1": str(cycle_at_1),
            # History depth of position 1
            "last_mod_a_1": last_mod_a_1,
            "last_mod_b_1": last_mod_b_1,
            "max_last_mod_1": max(last_mod_a_1, last_mod_b_1),
            "mod_count_a_1": mod_count_a_1,
            "mod_count_b_1": mod_count_b_1,
            "total_mods_1": mod_count_a_1 + mod_count_b_1,
            "j_hits_a_1": j_hits_a_1,
            "j_hits_b_1": j_hits_b_1,
            "p1_disturbed_either": p1_disturbed_either,
            "p1_disturbed_both": p1_disturbed_both,
            # Impending step 10 swap & address
            "j10_a": j10_a,
            "j10_b": j10_b,
            "k10_a": k10_a,
            "k10_b": k10_b,
            "swap_a_mapped_to_b": int(swap_a_mapped_to_b),
            # Exposure vs creation
            "pre_swap_addr_match": pre_swap_addr_match,
            "post_swap_addr_match": post_swap_addr_match,
            "exposure_class": exposure_class,
            # Global psi_9 structure
            "psi9_fixed_points": fixed_points_9,
            "psi9_support_size": support_size_9,
            "psi9_cycle_type": str(cycle_type_9),
            # Targets
            "z10_a": z10_a,
            "z10_b": z10_b,
            "survives": survives
        }
        autopsy_records.append(record)
        
    # Write CSV
    csv_path = outdir / "rc4_m9_9to10_pair_autopsy_v1.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(autopsy_records[0].keys()))
        writer.writeheader()
        writer.writerows(autopsy_records)
    print(f"Wrote autopsy CSV: {csv_path}")
    
    # -------------------------------------------------------------
    # RUN TESTS
    # -------------------------------------------------------------
    labels = [r["survives"] for r in autopsy_records]
    total_pairs = len(autopsy_records)
    
    # 0. Baseline Frozen R_9 Performance on 450 pairs
    r_groups = defaultdict(list)
    for r in autopsy_records:
        r_groups[r["r_tuple"]].append(r["survives"])
    r_class_sizes = [len(v) for v in r_groups.values()]
    r_pure_pairs = sum(len(v) for v in r_groups.values() if all(x == 1 for x in v) or all(x == 0 for x in v))
    r_strict_pct = r_pure_pairs / total_pairs * 100.0
    r_null = compute_label_permutation_null(labels, r_class_sizes, num_trials=500, seed=123)
    
    test_results = {}
    test_results["baseline_R9"] = {
        "num_classes": len(r_groups),
        "pure_pairs": r_pure_pairs,
        "total_pairs": total_pairs,
        "strict_purity_pct": r_strict_pct,
        "null_strict_mean": r_null["strict_mean"],
        "null_strict_std": r_null["strict_std"],
        "null_strict_p05": r_null["strict_p05"],
        "null_strict_p95": r_null["strict_p95"],
        "gain_G_R": r_strict_pct - r_null["strict_mean"],
    }
    
    # Test 1: Revisited-Position Disturbance Test
    # Condition pairs on p1_disturbed_either (was position 1 touched by j in steps 1..9?)
    disturb_groups = defaultdict(list)
    for r in autopsy_records:
        disturb_groups[r["p1_disturbed_either"]].append(r)
        
    t1_data = {}
    for d_val, group in disturb_groups.items():
        g_labels = [x["survives"] for x in group]
        g_r_groups = defaultdict(list)
        for x in group:
            g_r_groups[x["r_tuple"]].append(x["survives"])
        g_class_sizes = [len(v) for v in g_r_groups.values()]
        g_pure = sum(len(v) for v in g_r_groups.values() if all(o == 1 for o in v) or all(o == 0 for o in v))
        g_strict = g_pure / len(group) * 100.0 if group else 0
        g_null = compute_label_permutation_null(g_labels, g_class_sizes, num_trials=300, seed=456)
        t1_data[f"disturbed_{d_val}"] = {
            "count": len(group),
            "survivors": sum(g_labels),
            "separators": len(group) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(group) * 100.0,
            "R_classes": len(g_r_groups),
            "R_strict_purity_pct": g_strict,
            "null_strict_mean": g_null["strict_mean"],
            "gain_G_R": g_strict - g_null["strict_mean"]
        }
    test_results["test1_revisited_disturbance"] = t1_data
    
    # Test 2: Correspondence-at-Revisit Test (psi_9(1) == 1 vs != 1, plus cycle length)
    t2_fixed_groups = defaultdict(list)
    for r in autopsy_records:
        t2_fixed_groups[r["psi9_1_is_fixed"]].append(r)
    t2_data = {}
    for is_fixed, group in t2_fixed_groups.items():
        g_labels = [x["survives"] for x in group]
        t2_data[f"psi9_1_fixed_{is_fixed}"] = {
            "count": len(group),
            "survivors": sum(g_labels),
            "separators": len(group) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(group) * 100.0
        }
    
    # Cycle length containing position 1
    t2_cycle_groups = defaultdict(list)
    for r in autopsy_records:
        t2_cycle_groups[r["cycle_len_at_1"]].append(r["survives"])
    t2_cycle_data = {}
    for clen, g_labels in sorted(t2_cycle_groups.items()):
        t2_cycle_data[f"cycle_len_{clen}"] = {
            "count": len(g_labels),
            "survivors": sum(g_labels),
            "separators": len(g_labels) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(g_labels) * 100.0
        }
    test_results["test2_correspondence_at_revisit"] = {
        "fixed_vs_nonfixed": t2_data,
        "by_cycle_length_at_1": t2_cycle_data
    }
    
    # Test 3: History-Depth Test (last modification step of position 1)
    t3_groups = defaultdict(list)
    for r in autopsy_records:
        t3_groups[r["max_last_mod_1"]].append(r["survives"])
    t3_data = {}
    for last_m, g_labels in sorted(t3_groups.items()):
        t3_data[f"last_mod_step_{last_m}"] = {
            "count": len(g_labels),
            "survivors": sum(g_labels),
            "separators": len(g_labels) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(g_labels) * 100.0
        }
    test_results["test3_history_depth"] = t3_data
    
    # Test 4: Impending-Swap Alignment Test (swap_a_mapped_to_b)
    t4_groups = defaultdict(list)
    for r in autopsy_records:
        t4_groups[r["swap_a_mapped_to_b"]].append(r["survives"])
    t4_data = {}
    for sw_mapped, g_labels in t4_groups.items():
        t4_data[f"swap_mapped_{sw_mapped}"] = {
            "count": len(g_labels),
            "survivors": sum(g_labels),
            "separators": len(g_labels) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(g_labels) * 100.0
        }
    test_results["test4_impending_swap_alignment"] = t4_data
    
    # Test 5: Output-Address Exposure vs Creation
    t5_groups = defaultdict(list)
    for r in autopsy_records:
        t5_groups[r["exposure_class"]].append(r["survives"])
    t5_data = {}
    for exp_cls, g_labels in t5_groups.items():
        t5_data[exp_cls] = {
            "count": len(g_labels),
            "survivors": sum(g_labels),
            "separators": len(g_labels) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(g_labels) * 100.0
        }
    test_results["test5_exposure_vs_creation"] = t5_data
    
    # Test 6: Global psi_9 Structure
    t6_cycle_type = defaultdict(list)
    t6_fp = defaultdict(list)
    for r in autopsy_records:
        t6_cycle_type[r["psi9_cycle_type"]].append(r["survives"])
        t6_fp[r["psi9_fixed_points"]].append(r["survives"])
        
    t6_data_ct = {}
    for ctype, g_labels in sorted(t6_cycle_type.items(), key=lambda x: len(x[1]), reverse=True):
        t6_data_ct[ctype] = {
            "count": len(g_labels),
            "survivors": sum(g_labels),
            "separators": len(g_labels) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(g_labels) * 100.0
        }
    t6_data_fp = {}
    for fp, g_labels in sorted(t6_fp.items()):
        t6_data_fp[f"fixed_points_{fp}"] = {
            "count": len(g_labels),
            "survivors": sum(g_labels),
            "separators": len(g_labels) - sum(g_labels),
            "survival_rate_pct": sum(g_labels) / len(g_labels) * 100.0
        }
    test_results["test6_psi_structure"] = {
        "by_fixed_points": t6_data_fp,
        "by_cycle_type": t6_data_ct
    }

    # Control comparison with adjacent transitions (8 -> 9 and 10 -> 11)
    # Using archived CSV data for exact fidelity
    archived_csv = base_dir / "output" / "m9_held_out" / "rc4_m9_held_out_purity_control.csv"
    adj_data = {}
    with open(archived_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["transition"] in ["8->9", "9->10", "10->11"]:
                adj_data[row["transition"]] = {
                    "total_available_pairs": int(row["total_available_pairs"]),
                    "sampled_pairs": int(row["sampled_pairs"]),
                    "num_classes": int(row["num_classes"]),
                    "observed_strict_pct": float(row["observed_strict_pct"]),
                    "null_strict_pct": float(row["null_strict_pct"]),
                    "gain_strict_G_R": float(row["gain_strict_G_R"]),
                    "observed_majority_pct": float(row["observed_majority_pct"]),
                    "null_majority_pct": float(row["null_majority_pct"]),
                    "gain_majority_G_R": float(row["gain_majority_G_R"]),
                }
    test_results["adjacent_transition_comparison"] = adj_data

    # Data Dictionary
    data_dict = {
        "pair_id": "Unique integer ID (1..450) for the unordered colliding pair {A, B} at t=9.",
        "prefix_id": "Common 9-output prefix z_{1:9} shared by pair A and B.",
        "r_i_aligned": "R_full[0]: Boolean indicator whether psi_9(1) == 1. Evaluated immediately before step 10.",
        "r_delta_j10": "R_full[1]: (j_10^B - j_10^A) mod 9. Intermediate transition quantity computed after reading S_9[1].",
        "r_j10_mapped": "R_full[2]: Boolean indicator whether psi_9(j_10^A) == j_10^B. Intermediate swap target mapping.",
        "r_delta_k10": "R_full[3]: (k_10^B - k_10^A) mod 9. Intermediate output address disparity under step 10 swap.",
        "r_tuple": "Full 4-tuple representation of frozen R_9.",
        "orig_val_a_1": "Initial permutation value S_0^A[1] at position 1.",
        "orig_val_b_1": "Initial permutation value S_0^B[1] at position 1.",
        "s9_val_a_1": "Permutation value S_9^A[1] at position 1 immediately before step 10.",
        "s9_val_b_1": "Permutation value S_9^B[1] at position 1 immediately before step 10.",
        "psi9_at_1": "Value of psi_9(1) (position in B containing A's value at position 1).",
        "psi9_1_is_fixed": "1 if psi_9(1) == 1, 0 otherwise.",
        "cycle_len_at_1": "Length of the cycle containing position 1 in the disjoint cycle decomposition of psi_9.",
        "cycle_at_1": "Exact cycle containing position 1 in psi_9.",
        "last_mod_a_1": "Step in 1..9 during which position 1 was most recently modified (swapped) in A.",
        "last_mod_b_1": "Step in 1..9 during which position 1 was most recently modified (swapped) in B.",
        "max_last_mod_1": "max(last_mod_a_1, last_mod_b_1), indicating temporal depth of position 1 modification.",
        "mod_count_a_1": "Total number of swap modifications to position 1 across steps 1..9 in A.",
        "mod_count_b_1": "Total number of swap modifications to position 1 across steps 1..9 in B.",
        "total_mods_1": "mod_count_a_1 + mod_count_b_1.",
        "j_hits_a_1": "Total times j == 1 during steps 1..9 in A.",
        "j_hits_b_1": "Total times j == 1 during steps 1..9 in B.",
        "p1_disturbed_either": "1 if position 1 was modified more than once (disturbed by j) in either A or B during steps 1..9.",
        "p1_disturbed_both": "1 if position 1 was modified more than once in both A and B.",
        "j10_a": "Step 10 j pointer for A: (j_9^A + S_9^A[1]) mod 9.",
        "j10_b": "Step 10 j pointer for B: (j_9^B + S_9^B[1]) mod 9.",
        "k10_a": "Step 10 output address for A: (S_10^A[1] + S_10^A[j_10^A]) mod 9.",
        "k10_b": "Step 10 output address for B: (S_10^B[1] + S_10^B[j_10^B]) mod 9.",
        "swap_a_mapped_to_b": "1 if psi_9 maps transposition (1, j_10^A) directly to (1, j_10^B), 0 otherwise.",
        "pre_swap_addr_match": "1 if psi_9(k_10^A) == k_10^B (output addresses aligned before step 10 swap), 0 otherwise.",
        "post_swap_addr_match": "1 if psi_10(k_10^A) == k_10^B (output addresses aligned after step 10 swap), 0 otherwise.",
        "exposure_class": "Categorization: MATCH_PRESERVED, PRE_EXISTING_EXPOSED, or CREATED_BY_SWAP.",
        "psi9_fixed_points": "Number of fixed points in psi_9: sum(1 for p in 0..8 if psi_9[p] == p).",
        "psi9_support_size": "Number of moved positions in psi_9: 9 - psi9_fixed_points.",
        "psi9_cycle_type": "Partition of 9 representing the cycle lengths of psi_9.",
        "z10_a": "Step 10 output symbol of A: S_10^A[k_10^A].",
        "z10_b": "Step 10 output symbol of B: S_10^B[k_10^B].",
        "survives": "Binary target: 1 if z10_a == z10_b (collision continues), 0 if z10_a != z10_b (separates)."
    }

    summary_output = {
        "metadata": {
            "experiment": "rc4_m9_9to10_pair_autopsy_v1",
            "date": "2026-10-01",
            "m": 9,
            "transition": "9->10",
            "population_size": total_pairs,
            "survivors": sum(labels),
            "separators": total_pairs - sum(labels),
            "global_survival_rate_pct": sum(labels) / total_pairs * 100.0,
        },
        "tests": test_results,
        "data_dictionary": data_dict
    }
    
    summary_path = outdir / "rc4_m9_9to10_pair_autopsy_summary_v1.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2)
    print(f"Wrote summary JSON: {summary_path}")
    
    return csv_path, summary_path, summary_output


if __name__ == "__main__":
    run_autopsy()
