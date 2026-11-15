import json
import time
import hashlib
import math
import numpy as np
import itertools
from collections import defaultdict
import os
import sys

# -----------------------------------------------------------------------------
# STRICT MODEL PROVENANCE (HASH-FROZEN PRE-EXP-13)
# -----------------------------------------------------------------------------
PROVENANCE_MANIFEST = (
    "T_maint_base=0.85;Exp-9_Part1|"
    "T_refine_rate=243.11;Exp-9_Table2|"
    "T_frag_base=12.50;Exp-10_Table3|"
    "T_filt_token=0.065;Exp-9_Part3|"
    "T_filt_mask=2.50;Exp-9_Part3"
)
PROVENANCE_HASH = hashlib.sha256(PROVENANCE_MANIFEST.encode()).hexdigest()
# Verified hash: c443726f33998dec60e5e40acd3f598277be2579c7f17bcc5b1abc748955b857

def verify_provenance():
    actual_hash = hashlib.sha256(PROVENANCE_MANIFEST.encode()).hexdigest()
    expected_hash = "c443726f33998dec60e5e40acd3f598277be2579c7f17bcc5b1abc748955b857"
    if actual_hash != expected_hash:
        raise ValueError(f"Provenance hash mismatch! Expected {expected_hash}, got {actual_hash}")
    return actual_hash

def predict_immediate_cost(rho_hat, chi_hat, is_token_resolvable, t_est_ms, N_curr, N_total, g=1):
    # Scale base parameters relative to current population N_curr / N_total
    scale = N_curr / N_total if N_total > 0 else 1.0
    t_filt_hat = (0.065 if is_token_resolvable else 2.50) * scale
    t_maint_hat = 0.85 * (1.0 - rho_hat * chi_hat) * scale
    t_refine_hat = 243.11 * (1.0 - rho_hat) * scale * (g if g > 1 else 1.0)
    t_frag_hat = 12.50 * (1.0 - rho_hat * chi_hat) * (1.0 - chi_hat) * scale
    t_down_hat = t_maint_hat + t_refine_hat + t_frag_hat
    t_immediate_hat = t_est_ms + t_filt_hat + t_down_hat
    return t_immediate_hat, t_down_hat, t_filt_hat

# -----------------------------------------------------------------------------
# EXTERNAL BASELINE: DEMAND-DRIVEN DFS (S1) FROM EXP-1
# -----------------------------------------------------------------------------
def rc4_prga_sim(S0, n, m):
    S = list(S0); i = j = 0; out = []
    for _ in range(n):
        i = (i + 1) % m; j = (j + S[i]) % m
        S[i], S[j] = S[j], S[i]
        out.append(S[(S[i] + S[j]) % m])
    return out

def run_s1_demand_driven_dfs(m, observations, block_symbols=4):
    """
    Exact implementation of Solver S1 (Demand-Driven DFS) from rc4_micro_exp1_address_dfs.py
    """
    bps = max(1, (m - 1).bit_length())
    max_puz = max(o['puzzle'] for o in observations) if observations else 0
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
        'obs_checks': 0,
        'parent_ops': 0,
        'refinements': 0,
        't_est_total_ms': 0.0,
        'peak_active': 0,
        'survivors': [],
        'wall_time_s': 0.0
    }

    def compatible_full(S):
        if not observations: return True
        stream = rc4_prga_sim(S, max_steps, m)
        for o in observations:
            block = stream[o['block_start']:o['block_start'] + block_symbols]
            x = 0
            for v in block[1:]: x = (x << bps) | v
            reveal = o['reveal_bits']
            residue = x & ((1 << reveal) - 1) if reveal else 0
            if residue != o['residue']: return False
        return True

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
                    ledger['obs_checks'] += 1
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
        valid, need_idx, reject_step = get_demand(state)
        if not valid:
            return
            
        if need_idx is None:
            remaining_slots = [idx for idx, v in enumerate(state) if v is None]
            remaining_vals = [v for v in range(m) if v not in used]
            if not remaining_slots:
                if compatible_full(state):
                    ledger['survivors'].append(tuple(state))
            else:
                for p in itertools.permutations(remaining_vals):
                    cand = list(state)
                    for idx, v in zip(remaining_slots, p):
                        cand[idx] = v
                    ledger['assign'] += len(remaining_slots)
                    if compatible_full(cand):
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
    t0 = time.perf_counter()
    dfs(state, used)
    ledger['wall_time_s'] = time.perf_counter() - t0
    return ledger

# -----------------------------------------------------------------------------
# QUOTIENT INVERSION ENGINE & FOUR FROZEN SCHEDULERS
# -----------------------------------------------------------------------------
class QuotientInversionEngine:
    def __init__(self, m, observations, block_symbols=4):
        self.m = m
        self.observations = [obs for obs in observations if obs['reveal_bits'] > 0]
        self.block_symbols = block_symbols
        self.bps = max(1, (m - 1).bit_length())
        self.N_factorial = int(math.factorial(m))
        
    def run_inversion(self, policy_name, probe_budget=1000):
        """
        Runs state inversion using the quotient accelerator under the specified policy:
        - 'static': Static chronological ordering
        - 'pi_rho': Fail-first / maximum candidate reduction
        - 'pi_chi': Maximum partition alignment
        - 'pi_cost': Myopic prospective absolute-cost minimization
        """
        t_start = time.perf_counter()
        
        # Phase 1: Initialize all permutations
        perms = np.array(list(itertools.permutations(range(self.m))), dtype=np.int8)
        N = len(perms)
        active_indices = np.arange(N, dtype=np.int32)
        
        # State tracking (maintained incrementally)
        S_curr = perms.copy()
        j_curr = np.zeros(N, dtype=np.int8)
        current_step = 0
        
        # Maximum step across all observations
        max_total_steps = max(obs['block_start'] + self.block_symbols for obs in self.observations)
        stream_buf = np.zeros((N, max_total_steps + 1), dtype=np.int8)
        
        # Ledger
        ledger = {
            'policy': policy_name,
            'm': self.m,
            'nodes': 0,
            'assign': 0,
            'obs_checks': 0,
            'parent_ops': 0,
            'refinements': 0,
            't_est_total_ms': 0.0,
            'peak_active': N,
            'survivors': [],
            'wall_time_s': 0.0,
            'schedule_log': []
        }
        
        unapplied_obs = list(self.observations)
        
        while len(unapplied_obs) > 0 and len(active_indices) > 1:
            ledger['nodes'] += 1
            N_active = len(active_indices)
            if N_active > ledger['peak_active']:
                ledger['peak_active'] = N_active
                
            # Construct candidate actions from available observations
            candidate_actions = []
            
            for obs in unapplied_obs:
                end_step = obs['block_start'] + self.block_symbols
                g_steps = max(0, end_step - current_step)
                is_token_res = (g_steps <= 1)
                candidate_actions.append({
                    'obs': obs,
                    'end_step': end_step,
                    'g_steps': g_steps,
                    'is_token_resolvable': is_token_res
                })
                
            # If policy is static: pick the earliest chronological observation
            if policy_name == 'static':
                selected_action = min(candidate_actions, key=lambda a: a['end_step'])
                t_est_action_ms = 0.0
            else:
                # Estimator Firewall: evaluate candidate actions under probe budget
                t_est_0 = time.perf_counter_ns()
                
                # Choose probe sample
                if N_active <= probe_budget:
                    probe_sub = np.arange(N_active)
                else:
                    rng = np.random.RandomState(42 + ledger['nodes'])
                    probe_sub = rng.choice(N_active, size=probe_budget, replace=False)
                    
                n_probes = len(probe_sub)
                probe_act_idx = active_indices[probe_sub]
                
                for act in candidate_actions:
                    obs = act['obs']
                    end_step = act['end_step']
                    g = act['g_steps']
                    
                    if end_step <= current_step:
                        # Stream is already generated in stream_buf
                        val_probe = np.zeros(n_probes, dtype=np.int64)
                        for b_idx in range(1, self.block_symbols):
                            st_idx = obs['block_start'] + b_idx + 1
                            val_probe = (val_probe << self.bps) | stream_buf[probe_act_idx, st_idx]
                        rev_bits = obs['reveal_bits']
                        mask = (1 << rev_bits) - 1
                        res = obs['residue']
                        probe_surv = ((val_probe & mask) == res)
                        rho_hat = 1.0 - (np.sum(probe_surv) / n_probes)
                        chi_hat = 1.0
                    else:
                        # Simulate probe sample forward to end_step
                        S_probe = S_curr[probe_act_idx].copy()
                        j_probe = j_curr[probe_act_idx].copy()
                        stream_probe = {}
                        
                        for st in range(current_step + 1, end_step + 1):
                            i_s = st % self.m
                            j_probe = (j_probe + S_probe[np.arange(n_probes), i_s]) % self.m
                            j_p = j_probe
                            tmp = S_probe[np.arange(n_probes), i_s].copy()
                            S_probe[np.arange(n_probes), i_s] = S_probe[np.arange(n_probes), j_p]
                            S_probe[np.arange(n_probes), j_p] = tmp
                            k_s = (S_probe[np.arange(n_probes), i_s] + S_probe[np.arange(n_probes), j_p]) % self.m
                            stream_probe[st] = S_probe[np.arange(n_probes), k_s]
                            
                        val_probe = np.zeros(n_probes, dtype=np.int64)
                        for b_idx in range(1, self.block_symbols):
                            st_idx = obs['block_start'] + b_idx + 1
                            if st_idx <= current_step:
                                symbol_val = stream_buf[probe_act_idx, st_idx]
                            else:
                                symbol_val = stream_probe[st_idx]
                            val_probe = (val_probe << self.bps) | symbol_val
                            
                        rev_bits = obs['reveal_bits']
                        mask = (1 << rev_bits) - 1
                        res = obs['residue']
                        probe_surv = ((val_probe & mask) == res)
                        rho_hat = 1.0 - (np.sum(probe_surv) / n_probes)
                        
                        if act['is_token_resolvable']:
                            chi_hat = 1.0
                        else:
                            chi_hat = max(0.05, 1.0 / (1.5 ** max(1, g - 1)))
                            
                    act['rho_hat'] = rho_hat
                    act['chi_hat'] = chi_hat
                    
                t_est_action_ms = (time.perf_counter_ns() - t_est_0) / 1e6
                ledger['t_est_total_ms'] += t_est_action_ms
                
                # Selection according to policy
                if policy_name == 'pi_rho':
                    selected_action = max(candidate_actions, key=lambda a: a['rho_hat'])
                elif policy_name == 'pi_chi':
                    selected_action = max(candidate_actions, key=lambda a: (a['chi_hat'], a['rho_hat']))
                elif policy_name == 'pi_cost':
                    for act in candidate_actions:
                        t_imm_hat, _, _ = predict_immediate_cost(
                            act['rho_hat'], act['chi_hat'], act['is_token_resolvable'],
                            t_est_action_ms, N_active, self.N_factorial, g=act['g_steps']
                        )
                        act['t_immediate_hat'] = t_imm_hat
                    selected_action = min(candidate_actions, key=lambda a: a['t_immediate_hat'])
                else:
                    raise ValueError(f"Unknown policy {policy_name}")
                    
            # -----------------------------------------------------------------
            # EXECUTION OF SELECTED ACTION
            # -----------------------------------------------------------------
            chosen_obs = selected_action['obs']
            target_step = selected_action['end_step']
            unapplied_obs.remove(chosen_obs)
            
            # Step PRGA forward from current_step to target_step (ONLY for active candidates!)
            steps_to_advance = max(0, target_step - current_step)
            if steps_to_advance > 0:
                if selected_action['is_token_resolvable']:
                    ledger['parent_ops'] += 1
                else:
                    ledger['refinements'] += steps_to_advance
                    
                n_act = len(active_indices)
                ar_act = np.arange(n_act)
                
                for st in range(current_step + 1, target_step + 1):
                    i_s = st % self.m
                    j_curr[active_indices] = (j_curr[active_indices] + S_curr[active_indices, i_s]) % self.m
                    j_v = j_curr[active_indices]
                    tmp = S_curr[active_indices, i_s].copy()
                    S_curr[active_indices, i_s] = S_curr[active_indices, j_v]
                    S_curr[active_indices, j_v] = tmp
                    k_s = (S_curr[active_indices, i_s] + S_curr[active_indices, j_v]) % self.m
                    stream_buf[active_indices, st] = S_curr[active_indices, k_s]
                    
                current_step = target_step
                
            # Filter active candidates by chosen_obs
            ledger['obs_checks'] += 1
            
            val = np.zeros(len(active_indices), dtype=np.int64)
            for b_idx in range(1, self.block_symbols):
                st_idx = chosen_obs['block_start'] + b_idx + 1
                val = (val << self.bps) | stream_buf[active_indices, st_idx]
                
            rev_bits = chosen_obs['reveal_bits']
            mask = (1 << rev_bits) - 1
            res = chosen_obs['residue']
            
            match = ((val & mask) == res)
            active_indices = active_indices[match]
            
            ledger['schedule_log'].append({
                'puzzle': chosen_obs['puzzle'],
                'target_step': target_step,
                'reveal_bits': chosen_obs['reveal_bits'],
                'survivors_after': len(active_indices),
                't_est_ms': t_est_action_ms
            })
            
        # Final candidate verification / leaf assignment
        for cand_idx in active_indices:
            ledger['assign'] += self.m
            cand = tuple(int(x) for x in perms[cand_idx])
            ledger['survivors'].append(cand)
            
        ledger['wall_time_s'] = time.perf_counter() - t_start
        return ledger

# -----------------------------------------------------------------------------
# BENCHMARK SUITE FOR EXP-15
# -----------------------------------------------------------------------------
def run_exp15():
    print("=" * 125)
    print("RC4 MICRO-EXPERIMENT 15: ACTIVE TREE-SEARCH INTEGRATION & END-TO-END INVERSION")
    print("=" * 125)
    
    prov_hash = verify_provenance()
    print(f"Model Provenance Hash Verified: {prov_hash}")
    
    with open('frozen_instances.json', 'r') as f:
        frozen_data = json.load(f)
        
    expected_inst_hash = "ae7a8bf22f0444cfdff32f4194a71890f8b79a834a984632f330b9bdf852cce7"
    actual_inst_hash = frozen_data.get("metadata", {}).get("sha256")
    if actual_inst_hash != expected_inst_hash:
        raise ValueError(f"Instance hash mismatch! Expected {expected_inst_hash}, got {actual_inst_hash}")
    print(f"Frozen Instances Hash Verified: {actual_inst_hash}\n")
    
    all_results = {}
    
    # =========================================================================
    # PHASE 1: VALIDATION & DEBUGGING ON m=8
    # =========================================================================
    print("=" * 125)
    print("PHASE 1: VALIDATION & DEBUGGING ON m=8 (40,320 CANDIDATES)")
    print("=" * 125)
    
    inst8 = frozen_data['instances']['8']
    m8 = inst8['m']
    obs8 = inst8['observations']
    bs8 = inst8['block_symbols']
    def compute_digest(sol_list):
        return hashlib.sha256(str(sorted([tuple(int(x) for x in s) for s in sol_list])).encode()).hexdigest()
        
    planted8 = tuple(inst8['planted_permutation'])
    planted8_digest = compute_digest([planted8])
    
    print(f"Planted Permutation (m=8): {planted8}")
    print(f"Planted Digest: {planted8_digest}\n")
    
    # 1. External Baseline: Demand-Driven DFS (S1)
    print("Running External Baseline: Demand-Driven DFS (S1)...")
    s1_ledger_8 = run_s1_demand_driven_dfs(m8, obs8, bs8)
    s1_digest_8 = compute_digest(s1_ledger_8['survivors'])
    print(f"  S1 DFS Complete: {s1_ledger_8['wall_time_s']:.4f}s | Nodes: {s1_ledger_8['nodes']} | Assign: {s1_ledger_8['assign']} | Surv: {len(s1_ledger_8['survivors'])}")
    print(f"  S1 Digest Match: {s1_digest_8 == planted8_digest}\n")
    
    # 2. Four Schedulers inside Quotient Engine
    quot_engine_8 = QuotientInversionEngine(m8, obs8, bs8)
    schedulers = ['static', 'pi_rho', 'pi_chi', 'pi_cost']
    q_results_8 = {}
    
    for pol in schedulers:
        print(f"Running Quotient Engine [{pol}]...")
        res = quot_engine_8.run_inversion(pol, probe_budget=1000)
        sol_digest = compute_digest(res['survivors'])
        res['digest_match'] = (sol_digest == planted8_digest)
        res['sol_digest'] = sol_digest
        q_results_8[pol] = res
        print(f"  [{pol:<7}] Time: {res['wall_time_s']*1000:.2f} ms | Nodes: {res['nodes']} | Parent Ops: {res['parent_ops']} | Refine: {res['refinements']} | Est: {res['t_est_total_ms']:.2f} ms | Surv: {len(res['survivors'])} | Match: {res['digest_match']}")
        
    all_results['m8'] = {
        'baseline_s1': s1_ledger_8,
        'quotient_schedulers': q_results_8
    }
    
    # Print m=8 Scoreboard
    print("\n" + "-" * 125)
    print(f"{'Engine / Policy':<22} | {'Time (ms)':<10} | {'Nodes':<8} | {'Assign':<8} | {'Obs Checks':<11} | {'Parent Ops':<11} | {'Refine':<8} | {'T_est (ms)':<10} | {'Surv':<5} | {'Digest Match'}")
    print("-" * 125)
    print(f"{'Baseline S1 (DFS)':<22} | {s1_ledger_8['wall_time_s']*1000:>8.2f} ms | {s1_ledger_8['nodes']:<8} | {s1_ledger_8['assign']:<8} | {s1_ledger_8['obs_checks']:<11} | {'—':<11} | {'—':<8} | {'—':<10} | {len(s1_ledger_8['survivors']):<5} | {s1_digest_8 == planted8_digest}")
    for pol in schedulers:
        r = q_results_8[pol]
        print(f"{'Quotient: ' + pol:<22} | {r['wall_time_s']*1000:>8.2f} ms | {r['nodes']:<8} | {r['assign']:<8} | {r['obs_checks']:<11} | {r['parent_ops']:<11} | {r['refinements']:<8} | {r['t_est_total_ms']:>8.2f} ms | {len(r['survivors']):<5} | {r['digest_match']}")
    print("-" * 125)
    
    # =========================================================================
    # PHASE 2: HELD-OUT BENCHMARK ON m=10 (3,628,800 CANDIDATES)
    # =========================================================================
    print("\n" + "=" * 125)
    print("PHASE 2: HELD-OUT BENCHMARK ON m=10 (3,628,800 CANDIDATES)")
    print("=" * 125)
    
    inst10 = frozen_data['instances']['10']
    m10 = inst10['m']
    obs10 = inst10['observations']
    bs10 = inst10['block_symbols']
    planted10 = tuple(inst10['planted_permutation'])
    planted10_digest = compute_digest([planted10])
    
    print(f"Planted Permutation (m=10): {planted10}")
    print(f"Planted Digest: {planted10_digest}\n")
    
    # 1. External Baseline: Demand-Driven DFS (S1)
    print("Running External Baseline: Demand-Driven DFS (S1) on m=10...")
    s1_ledger_10 = run_s1_demand_driven_dfs(m10, obs10, bs10)
    s1_digest_10 = compute_digest(s1_ledger_10['survivors'])
    print(f"  S1 DFS Complete: {s1_ledger_10['wall_time_s']:.2f}s | Nodes: {s1_ledger_10['nodes']:,} | Assign: {s1_ledger_10['assign']:,} | Surv: {len(s1_ledger_10['survivors'])}")
    print(f"  S1 Digest Match: {s1_digest_10 == planted10_digest}\n")
    
    # 2. Four Schedulers inside Quotient Engine on m=10
    quot_engine_10 = QuotientInversionEngine(m10, obs10, bs10)
    q_results_10 = {}
    
    for pol in schedulers:
        print(f"Running Quotient Engine [{pol}] on m=10...")
        res = quot_engine_10.run_inversion(pol, probe_budget=1000)
        sol_digest = compute_digest(res['survivors'])
        res['digest_match'] = (sol_digest == planted10_digest)
        res['sol_digest'] = sol_digest
        q_results_10[pol] = res
        print(f"  [{pol:<7}] Time: {res['wall_time_s']:.3f}s | Nodes: {res['nodes']} | Parent Ops: {res['parent_ops']} | Refine: {res['refinements']} | Est: {res['t_est_total_ms']:.2f} ms | Surv: {len(res['survivors'])} | Match: {res['digest_match']}")
        
    all_results['m10'] = {
        'baseline_s1': s1_ledger_10,
        'quotient_schedulers': q_results_10
    }
    
    # Print m=10 Scoreboard
    print("\n" + "-" * 135)
    print(f"{'Engine / Policy':<22} | {'Time (s)':<10} | {'Nodes':<10} | {'Assign':<10} | {'Obs Checks':<11} | {'Parent Ops':<11} | {'Refine':<8} | {'T_est (ms)':<10} | {'Surv':<5} | {'Digest Match'}")
    print("-" * 135)
    print(f"{'Baseline S1 (DFS)':<22} | {s1_ledger_10['wall_time_s']:>8.2f} s  | {s1_ledger_10['nodes']:<10} | {s1_ledger_10['assign']:<10} | {s1_ledger_10['obs_checks']:<11} | {'—':<11} | {'—':<8} | {'—':<10} | {len(s1_ledger_10['survivors']):<5} | {s1_digest_10 == planted10_digest}")
    for pol in schedulers:
        r = q_results_10[pol]
        print(f"{'Quotient: ' + pol:<22} | {r['wall_time_s']:>8.3f} s  | {r['nodes']:<10} | {r['assign']:<10} | {r['obs_checks']:<11} | {r['parent_ops']:<11} | {r['refinements']:<8} | {r['t_est_total_ms']:>8.2f} ms | {len(r['survivors']):<5} | {r['digest_match']}")
    print("-" * 135)
    
    # =========================================================================
    # GATE EVALUATION
    # =========================================================================
    print("\n" + "=" * 125)
    print("GATE EVALUATION")
    print("=" * 125)
    
    # Gate A: pi_cost beats alternative schedulers inside the same engine
    t_cost_10 = q_results_10['pi_cost']['wall_time_s']
    t_static_10 = q_results_10['static']['wall_time_s']
    t_rho_10 = q_results_10['pi_rho']['wall_time_s']
    t_chi_10 = q_results_10['pi_chi']['wall_time_s']
    
    gate_a_passed = (t_cost_10 <= min(t_static_10, t_rho_10, t_chi_10))
    print(f"Gate A (Intra-Engine Scheduling): {'PASSED' if gate_a_passed else 'FAILED'}")
    print(f"  pi_cost: {t_cost_10:.4f}s")
    print(f"  static:  {t_static_10:.4f}s (delta: {t_cost_10 - t_static_10:+.4f}s)")
    print(f"  pi_rho:  {t_rho_10:.4f}s (delta: {t_cost_10 - t_rho_10:+.4f}s)")
    print(f"  pi_chi:  {t_chi_10:.4f}s (delta: {t_cost_10 - t_chi_10:+.4f}s)")
    
    # Gate B: winning engine beats external baseline S1
    best_quot_time = min(t_cost_10, t_static_10, t_rho_10, t_chi_10)
    t_s1_10 = s1_ledger_10['wall_time_s']
    leverage_gate_b = t_s1_10 / best_quot_time
    gate_b_passed = (leverage_gate_b > 1.0)
    print(f"\nGate B (Inter-Engine Leverage vs S1): {'PASSED' if gate_b_passed else 'FAILED'}")
    print(f"  S1 Demand-Driven DFS: {t_s1_10:.2f}s")
    print(f"  Winning Quotient Engine: {best_quot_time:.3f}s")
    print(f"  End-to-End Speedup Leverage L: {leverage_gate_b:.2f}x")
    
    all_results['gate_evaluation'] = {
        'gate_a_passed': gate_a_passed,
        'gate_b_passed': gate_b_passed,
        'leverage_over_s1': leverage_gate_b,
        't_cost_10': t_cost_10,
        't_s1_10': t_s1_10
    }
    
    # Serialize summary JSON
    os.makedirs('output', exist_ok=True)
    summary_path = 'output/rc4_micro_exp15_summary.json'
    
    # Convert tuples/numpy types for json serialization
    def clean_json(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: clean_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_json(v) for v in obj]
        return obj

    with open(summary_path, 'w') as f:
        json.dump(clean_json(all_results), f, indent=2)
    print(f"\nSummary JSON exported to {summary_path}")

if __name__ == '__main__':
    run_exp15()
