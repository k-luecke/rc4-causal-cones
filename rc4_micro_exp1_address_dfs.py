import json
import time
import os
import csv
import itertools
from collections import defaultdict

def verify_frozen_instances(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    expected_hash = "ae7a8bf22f0444cfdff32f4194a71890f8b79a834a984632f330b9bdf852cce7"
    actual_hash = data.get("metadata", {}).get("sha256")
    if actual_hash != expected_hash:
        raise ValueError(f"Hash mismatch! Expected {expected_hash}, got {actual_hash}")
    return data

def rc4_prga(S0, n):
    S = list(S0); m = len(S); i = j = 0; out = []
    for _ in range(n):
        i = (i + 1) % m; j = (j + S[i]) % m
        S[i], S[j] = S[j], S[i]
        out.append(S[(S[i] + S[j]) % m])
    return out

def compatible(S, observations, m, block_symbols=4):
    if not observations: return True
    bps = max(1, (m - 1).bit_length())
    max_puz = max(o['puzzle'] for o in observations)
    stream = rc4_prga(S, block_symbols * max_puz)
    for o in observations:
        block = stream[o['block_start']:o['block_start'] + block_symbols]
        x = 0
        for v in block[1:]: x = (x << bps) | v
        reveal = o['reveal_bits']
        residue = x & ((1 << reveal) - 1) if reveal else 0
        if residue != o['residue']: return False
    return True

# --- Solver S0: Ordinary Fixed-Slot Permutation DFS ---
def run_s0(m, observations, block_symbols=4):
    bps = max(1, (m - 1).bit_length())
    max_puz = max(o['puzzle'] for o in observations)
    max_steps = block_symbols * max_puz
    
    obs_by_end_step = defaultdict(list)
    for o in observations:
        end_step = o['block_start'] + block_symbols
        obs_by_end_step[end_step].append(o)

    ledger = {
        'nodes': 0,
        'assign': 0,
        'addr': 0,
        'output': 0,
        'reject_by_step': defaultdict(int),
        'd_reject': defaultdict(int),
        'complete': 0,
        'survivors': []
    }

    def check_partial_prga(state):
        S = list(state)
        i = 0
        j = 0
        stream = []
        for step in range(1, max_steps + 1):
            i = (i + 1) % m
            if S[i] is None:
                return True, None
            ledger['addr'] += 1
            j = (j + S[i]) % m
            if S[j] is None:
                return True, None
            S[i], S[j] = S[j], S[i]
            ledger['addr'] += 1
            k = (S[i] + S[j]) % m
            if S[k] is None:
                return True, None
            stream.append(S[k])
            
            if step in obs_by_end_step:
                for obs in obs_by_end_step[step]:
                    ledger['output'] += 1
                    block = stream[obs['block_start']:obs['block_start'] + block_symbols]
                    x = 0
                    for v in block[1:]: x = (x << bps) | v
                    reveal = obs['reveal_bits']
                    residue = x & ((1 << reveal) - 1) if reveal else 0
                    if residue != obs['residue']:
                        return False, step
        return True, None

    def dfs(slot, state, used):
        ledger['nodes'] += 1
        depth = len(used)
        if slot == m:
            ledger['complete'] += 1
            if compatible(state, observations, m, block_symbols):
                ledger['survivors'].append(tuple(state))
            return

        candidates = [v for v in range(m) if v not in used]
        for val in candidates:
            ledger['assign'] += 1
            state[slot] = val
            used.add(val)
            
            valid, reject_step = check_partial_prga(state)
            if not valid:
                ledger['reject_by_step'][reject_step] += 1
                ledger['d_reject'][depth + 1] += 1
            else:
                dfs(slot + 1, state, used)
                
            state[slot] = None
            used.remove(val)

    state = [None] * m
    used = set()
    t0 = time.time()
    dfs(0, state, used)
    ledger['wall_time'] = time.time() - t0
    return ledger

# --- Solver S1: Demand-Driven DFS (Baseline) ---
def run_s1(m, observations, block_symbols=4):
    bps = max(1, (m - 1).bit_length())
    max_puz = max(o['puzzle'] for o in observations)
    max_steps = block_symbols * max_puz
    
    obs_by_end_step = defaultdict(list)
    for o in observations:
        end_step = o['block_start'] + block_symbols
        obs_by_end_step[end_step].append(o)

    ledger = {
        'nodes': 0,
        'assign': 0,
        'addr': 0,
        'output': 0,
        'reject_by_step': defaultdict(int),
        'd_reject': defaultdict(int),
        'complete': 0,
        'survivors': []
    }

    def get_demand(state):
        S = list(state)
        i = 0
        j = 0
        stream = []
        for step in range(1, max_steps + 1):
            i = (i + 1) % m
            if S[i] is None:
                return True, i, None
            ledger['addr'] += 1
            j = (j + S[i]) % m
            if S[j] is None:
                return True, j, None
            S[i], S[j] = S[j], S[i]
            ledger['addr'] += 1
            k = (S[i] + S[j]) % m
            if S[k] is None:
                return True, k, None
            stream.append(S[k])
            
            if step in obs_by_end_step:
                for obs in obs_by_end_step[step]:
                    ledger['output'] += 1
                    block = stream[obs['block_start']:obs['block_start'] + block_symbols]
                    x = 0
                    for v in block[1:]: x = (x << bps) | v
                    reveal = obs['reveal_bits']
                    residue = x & ((1 << reveal) - 1) if reveal else 0
                    if residue != obs['residue']:
                        return False, None, step
        return True, None, None

    def dfs(state, used):
        ledger['nodes'] += 1
        depth = len(used)
        
        valid, need_idx, reject_step = get_demand(state)
        if not valid:
            ledger['reject_by_step'][reject_step] += 1
            ledger['d_reject'][depth] += 1
            return
            
        if need_idx is None:
            remaining_slots = [idx for idx, v in enumerate(state) if v is None]
            remaining_vals = [v for v in range(m) if v not in used]
            if not remaining_slots:
                ledger['complete'] += 1
                if compatible(state, observations, m, block_symbols):
                    ledger['survivors'].append(tuple(state))
            else:
                for p in itertools.permutations(remaining_vals):
                    ledger['complete'] += 1
                    cand = list(state)
                    for idx, v in zip(remaining_slots, p):
                        cand[idx] = v
                    if compatible(cand, observations, m, block_symbols):
                        ledger['survivors'].append(tuple(cand))
            return

        candidates = [v for v in range(m) if v not in used]
        for val in candidates:
            ledger['assign'] += 1
            state[need_idx] = val
            used.add(val)
            dfs(state, used)
            state[need_idx] = None
            used.remove(val)

    state = [None] * m
    used = set()
    t0 = time.time()
    dfs(state, used)
    ledger['wall_time'] = time.time() - t0
    return ledger

# --- Solver S2: Address-Targeted Constraint DFS (Candidate Shortcut 1) ---
def run_s2(m, observations, block_symbols=4):
    bps = max(1, (m - 1).bit_length())
    max_puz = max(o['puzzle'] for o in observations)
    max_steps = block_symbols * max_puz
    
    relevant_steps = set()
    obs_by_end_step = defaultdict(list)
    
    for obs in observations:
        end_step = obs['block_start'] + block_symbols
        obs_by_end_step[end_step].append(obs)
        reveal = obs['reveal_bits']
        if reveal > 0:
            start = obs['block_start']
            for k in range(1, block_symbols):
                shift = (block_symbols - 1 - k) * bps
                if shift < reveal:
                    step_num = start + k + 1
                    relevant_steps.add(step_num)

    ledger = {
        'nodes': 0,
        'assign': 0,
        'addr': 0,
        'output': 0,
        'reject_by_step': defaultdict(int),
        'd_reject': defaultdict(int),
        'complete': 0,
        'survivors': []
    }

    def get_demand_s2(state):
        S = list(state)
        orig_of_pos = list(range(m))
        i = 0
        j = 0
        stream = [None] * max_steps
        
        for step in range(1, max_steps + 1):
            i = (i + 1) % m
            if S[i] is None:
                orig_slot = orig_of_pos[i]
                return True, orig_slot, None
            ledger['addr'] += 1
            j = (j + S[i]) % m
            if S[j] is None:
                orig_slot = orig_of_pos[j]
                return True, orig_slot, None
                
            S[i], S[j] = S[j], S[i]
            orig_of_pos[i], orig_of_pos[j] = orig_of_pos[j], orig_of_pos[i]
            
            ledger['addr'] += 1
            k = (S[i] + S[j]) % m
            
            if step in relevant_steps:
                if S[k] is None:
                    orig_slot = orig_of_pos[k]
                    return True, orig_slot, None
                stream[step - 1] = S[k]
            else:
                if S[k] is not None:
                    stream[step - 1] = S[k]
                    
            if step in obs_by_end_step:
                for obs in obs_by_end_step[step]:
                    start = obs['block_start']
                    reveal = obs['reveal_bits']
                    if reveal == 0:
                        continue
                    needed = []
                    for k_sym in range(1, block_symbols):
                        if (block_symbols - 1 - k_sym) * bps < reveal:
                            needed.append(start + k_sym)
                    
                    if all(stream[idx] is not None for idx in needed):
                        ledger['output'] += 1
                        x = 0
                        for k_sym in range(1, block_symbols):
                            v = stream[start + k_sym] if stream[start + k_sym] is not None else 0
                            x = (x << bps) | v
                        residue = x & ((1 << reveal) - 1)
                        if residue != obs['residue']:
                            return False, None, step
                            
        return True, None, None

    def dfs(state, used):
        ledger['nodes'] += 1
        depth = len(used)
        
        valid, need_slot, reject_step = get_demand_s2(state)
        if not valid:
            ledger['reject_by_step'][reject_step] += 1
            ledger['d_reject'][depth] += 1
            return
            
        if need_slot is None:
            remaining_slots = [idx for idx, v in enumerate(state) if v is None]
            remaining_vals = [v for v in range(m) if v not in used]
            if not remaining_slots:
                ledger['complete'] += 1
                if compatible(state, observations, m, block_symbols):
                    ledger['survivors'].append(tuple(state))
            else:
                for p in itertools.permutations(remaining_vals):
                    ledger['complete'] += 1
                    cand = list(state)
                    for idx, v in zip(remaining_slots, p):
                        cand[idx] = v
                    if compatible(cand, observations, m, block_symbols):
                        ledger['survivors'].append(tuple(cand))
            return

        candidates = [v for v in range(m) if v not in used]
        for val in candidates:
            ledger['assign'] += 1
            state[need_slot] = val
            used.add(val)
            dfs(state, used)
            state[need_slot] = None
            used.remove(val)

    state = [None] * m
    used = set()
    t0 = time.time()
    dfs(state, used)
    ledger['wall_time'] = time.time() - t0
    return ledger

def compute_cdf(d_reject, m):
    total = sum(d_reject.values())
    if total == 0:
        return {}
    cum = 0
    cdf = {}
    for d in range(1, m + 1):
        cum += d_reject.get(d, 0)
        cdf[d] = cum / total
    return cdf

def compute_median_depth(d_reject):
    items = []
    for d, cnt in sorted(d_reject.items()):
        items.extend([d] * cnt)
    if not items:
        return 0
    mid = len(items) // 2
    if len(items) % 2 == 1:
        return items[mid]
    else:
        return (items[mid - 1] + items[mid]) / 2.0
