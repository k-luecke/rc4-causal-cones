#!/usr/bin/env python3
"""
RC4 First-Pass Boundary Handoff Experiment v1.
Comprehensive autopsy of all 450 pairs at transition 9 -> 10.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


def prga_step_detail(state, i, j, m):
    """Execute one PRGA step with full internal recording."""
    S = list(state)
    i = (i + 1) % m
    pre_i_val = S[i]
    j = (j + pre_i_val) % m
    pre_j_val = S[j]
    
    # Swap
    S[i], S[j] = S[j], S[i]
    
    k = (S[i] + S[j]) % m
    z = S[k]
    
    return {
        "i": i,
        "j": j,
        "pre_i_val": pre_i_val,
        "pre_j_val": pre_j_val,
        "k": k,
        "z": z,
        "post_state": tuple(S),
    }


def full_trace(initial_perm, steps=10, m=9):
    """Computes trace of steps 1..steps."""
    state = tuple(initial_perm)
    i = j = 0
    trace = []
    
    for step in range(1, steps + 1):
        step_info = prga_step_detail(state, i, j, m)
        step_info["step"] = step
        step_info["pre_state"] = state
        trace.append(step_info)
        state = step_info["post_state"]
        i = step_info["i"]
        j = step_info["j"]
        
    return trace


def position_correspondence(state_a, state_b):
    """psi(p) = index in B of value state_a[p]."""
    pos_b = {val: pos for pos, val in enumerate(state_b)}
    return tuple(pos_b[val] for val in state_a)


def cycle_decomposition(perm):
    """Returns list of disjoint cycles as sorted tuples of indices."""
    m = len(perm)
    visited = [False] * m
    cycles = []
    for start in range(m):
        if not visited[start]:
            cycle = []
            curr = start
            while not visited[curr]:
                visited[curr] = True
                cycle.append(curr)
                curr = perm[curr]
            cycles.append(tuple(cycle))
    # canonical order
    canonical = []
    for c in cycles:
        min_idx = c.index(min(c))
        c_rot = c[min_idx:] + c[:min_idx]
        canonical.append(c_rot)
    canonical.sort()
    return canonical


def cycle_containing(cycles, elem):
    for c in cycles:
        if elem in c:
            return c
    return ()


def analyze_position_history(trace, steps_range, m=9):
    """
    Computes history of each position p across trace[step-1] for step in steps_range.
    """
    history = {p: {
        "i_visits": [],
        "j_selections": [],
        "modifications": [],
        "k_selections": []
    } for p in range(m)}
    
    for step_idx in steps_range:
        e = trace[step_idx - 1]
        step = e["step"]
        i_pos = e["i"]
        j_pos = e["j"]
        k_pos = e["k"]
        
        history[i_pos]["i_visits"].append(step)
        history[j_pos]["j_selections"].append(step)
        history[k_pos]["k_selections"].append(step)
        
        # Modifications occur at i and j
        history[i_pos]["modifications"].append(step)
        if j_pos != i_pos:
            history[j_pos]["modifications"].append(step)
            
    return history


def compute_label_permutation_null(labels, class_sizes, num_trials=200, seed=42):
    """
    Permutes labels across partition to compute null mean, std, 5th, 95th percentiles.
    """
    total = len(labels)
    rng = random.Random(seed)
    strict_trials = []
    maj_trials = []
    
    for _ in range(num_trials):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        
        offset = 0
        s_count = 0
        m_count = 0
        for sz in class_sizes:
            chunk = shuffled[offset:offset + sz]
            offset += sz
            ones = sum(chunk)
            if ones == sz or ones == 0:
                s_count += sz
            m_count += max(ones, sz - ones)
            
        strict_trials.append(s_count / total * 100.0)
        maj_trials.append(m_count / total * 100.0)
        
    strict_trials.sort()
    maj_trials.sort()
    
    mean_s = sum(strict_trials) / num_trials
    var_s = sum((x - mean_s) ** 2 for x in strict_trials) / num_trials
    std_s = var_s ** 0.5
    
    mean_m = sum(maj_trials) / num_trials
    var_m = sum((x - mean_m) ** 2 for x in maj_trials) / num_trials
    std_m = var_m ** 0.5
    
    p05_idx = int(0.05 * num_trials)
    p95_idx = int(0.95 * num_trials)
    
    return {
        "strict_mean": mean_s,
        "strict_std": std_s,
        "strict_p05": strict_trials[p05_idx],
        "strict_p95": strict_trials[p95_idx],
        "maj_mean": mean_m,
        "maj_std": std_m,
        "maj_p05": maj_trials[p05_idx],
        "maj_p95": maj_trials[p95_idx]
    }
