from pathlib import Path
"""
RC4 Micro-Experiment 16: Out-of-Sample Transfer Benchmark
Evaluates whether the frozen path-cost lookahead controller (Exp-15b)
transfers out-of-sample to three fresh untouched m=10 instances without parameter re-tuning.
"""
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
# STRICT MODEL PROVENANCE FOR EXP-16 (FROZEN FROM EXP-15B)
# -----------------------------------------------------------------------------
PROVENANCE_16_MANIFEST = (
    "c_advance=6.50e-5;Exp-7_Table4|"
    "c_frag=6.90e-6;Exp-10_Table3|"
    "c_filt=1.38e-6;Exp-9_Part3"
)
PROVENANCE_16_HASH = "484298d1ae91976608ff140423c66df88f449309bf363b5ef7b1a0fd5cdf281b"

C_ADVANCE = 6.50e-5  # ms / cand-step
C_FRAG = 6.90e-6     # ms / cand
C_FILT = 1.38e-6     # ms / cand

def verify_provenance():
    actual_hash = hashlib.sha256(PROVENANCE_16_MANIFEST.encode()).hexdigest()
    if actual_hash != PROVENANCE_16_HASH:
        raise ValueError(f"Provenance hash mismatch! Expected {PROVENANCE_16_HASH}, got {actual_hash}")
    return actual_hash

def compute_digest(sol_list):
    return hashlib.sha256(str(sorted([tuple(int(x) for x in s) for s in sol_list])).encode()).hexdigest()

def pearson_r(x, y):
    x = np.array(x, dtype=np.float64)
    y = np.array(y, dtype=np.float64)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])

def spearman_rho(x, y):
    x = np.array(x, dtype=np.float64)
    y = np.array(y, dtype=np.float64)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    rx = np.argsort(np.argsort(x)).astype(np.float64)
    ry = np.argsort(np.argsort(y)).astype(np.float64)
    return float(np.corrcoef(rx, ry)[0, 1])

# -----------------------------------------------------------------------------
# DEMAND-DRIVEN DFS BASELINE (S1)
# -----------------------------------------------------------------------------
def rc4_prga_sim(S0, n, m):
    S = list(S0); i = j = 0; out = []
    for _ in range(n):
        i = (i + 1) % m
        j = (j + S[i]) % m
        S[i], S[j] = S[j], S[i]
        out.append(S[(S[i] + S[j]) % m])
    return out

def run_s1_demand_driven_dfs(m, observations, block_symbols):
    bps = max(1, (m - 1).bit_length())
    max_steps = max(obs['block_start'] + block_symbols for obs in observations)
    
    obs_by_end_step = defaultdict(list)
    for obs in observations:
        end_step = obs['block_start'] + block_symbols
        obs_by_end_step[end_step].append(obs)
        
    ledger = {
        'nodes': 0,
        'assign': 0,
        'obs_checks': 0,
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
            j = (j + S[i]) % m
            if S[j] is None:
                return True, j, None
            S[i], S[j] = S[j], S[i]
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
# ROLLING STREAM EXECUTION SEMANTICS
# -----------------------------------------------------------------------------
def execute_schedule(m, observations, block_symbols, schedule_puzzles, perms):
    t_start = time.perf_counter()
    N = len(perms)
    active_indices = np.arange(N, dtype=np.int32)
    bps = max(1, (m - 1).bit_length())
    
    obs_by_puz = {obs['puzzle']: obs for obs in observations}
    
    # State tracking
    S_curr = perms.copy()
    j_curr = np.zeros(N, dtype=np.int8)
    current_step = 0
    
    max_total_steps = max(obs['block_start'] + block_symbols for obs in observations)
    stream_buf = np.zeros((N, max_total_steps + 1), dtype=np.int8)
    
    ledger = {
        'schedule': schedule_puzzles,
        'wall_time_s': 0.0,
        'realized_workload': 0,
        'stage_metrics': [],
        'survivors': []
    }
    
    total_cand_steps = 0
    
    for puz in schedule_puzzles:
        obs = obs_by_puz[puz]
        target_step = obs['block_start'] + block_symbols
        g = max(0, target_step - current_step)
        
        n_act = len(active_indices)
        stage_work = n_act * g
        total_cand_steps += stage_work
        
        # Advance active candidates
        if g > 0:
            for st in range(current_step + 1, target_step + 1):
                i_s = st % m
                j_curr[active_indices] = (j_curr[active_indices] + S_curr[active_indices, i_s]) % m
                j_v = j_curr[active_indices]
                tmp = S_curr[active_indices, i_s].copy()
                S_curr[active_indices, i_s] = S_curr[active_indices, j_v]
                S_curr[active_indices, j_v] = tmp
                k_s = (S_curr[active_indices, i_s] + S_curr[active_indices, j_v]) % m
                stream_buf[active_indices, st] = S_curr[active_indices, k_s]
            current_step = target_step
            
        # Apply observation filter
        val = np.zeros(n_act, dtype=np.int64)
        for b_idx in range(1, block_symbols):
            st_idx = obs['block_start'] + b_idx + 1
            val = (val << bps) | stream_buf[active_indices, st_idx]
            
        rev_bits = obs['reveal_bits']
        mask = (1 << rev_bits) - 1
        res = obs['residue']
        
        match = ((val & mask) == res)
        active_indices = active_indices[match]
        
        ledger['stage_metrics'].append({
            'puzzle': puz,
            'g': g,
            'n_before': n_act,
            'n_after': len(active_indices),
            'workload': stage_work
        })
        
    for idx in active_indices:
        ledger['survivors'].append(tuple(int(x) for x in perms[idx]))
        
    ledger['wall_time_s'] = time.perf_counter() - t_start
    ledger['realized_workload'] = total_cand_steps
    return ledger

# -----------------------------------------------------------------------------
# PROSPECTIVE PATH LOOKAHEAD EVALUATOR
# -----------------------------------------------------------------------------
def evaluate_schedule_prospectively(schedule, obs_by_puz, block_symbols, n_probes, obs_pass_masks, N_0):
    current_probe_mask = np.ones(n_probes, dtype=bool)
    current_s = 0
    N_k = float(N_0)
    
    total_w_pred = 0.0
    total_c_candstep = 0.0
    total_c_chi = 0.0
    
    for puz in schedule:
        obs = obs_by_puz[puz]
        target_step = obs['block_start'] + block_symbols
        g = max(0, target_step - current_s)
        
        w_stage = N_k * g
        total_w_pred += w_stage
        
        c_adv = w_stage * C_ADVANCE
        c_flt = N_k * C_FILT
        total_c_candstep += (c_adv + c_flt)
        
        # Geometry penalty
        chi_hat = 1.0 if g <= 1 else max(0.05, 1.0 / (1.5 ** max(1, g - 1)))
        c_frag_pen = C_FRAG * N_k * (1.0 - chi_hat)
        total_c_chi += (c_adv + c_flt + c_frag_pen)
        
        # Advance probe mask
        current_probe_mask = current_probe_mask & obs_pass_masks[puz]
        surv_count = np.sum(current_probe_mask)
        surv_fraction = surv_count / n_probes
        N_k = max(1.0, N_k * surv_fraction)
        
        if g > 0:
            current_s = target_step
            
    return total_w_pred, total_c_candstep, total_c_chi

# -----------------------------------------------------------------------------
# DYNAMIC MYOPIC AND GREEDY POLICY EVALUATION
# -----------------------------------------------------------------------------
def derive_greedy_and_myopic_schedules(active_puzzles, obs_by_puz, block_symbols, n_probes, obs_pass_masks, N_0):
    """
    Dynamically computes the exact schedules chosen by:
    - pi_rho: greedy domain reduction
    - pi_chi: greedy partition alignment
    - pi_cost_myopic: single-step immediate cost minimization
    """
    def run_policy(pol_name):
        unapplied = list(active_puzzles)
        schedule = []
        current_probe_mask = np.ones(n_probes, dtype=bool)
        current_s = 0
        N_k = float(N_0)
        
        while unapplied:
            best_puz = None
            best_score = None
            
            for puz in unapplied:
                obs = obs_by_puz[puz]
                target_step = obs['block_start'] + block_symbols
                g = max(0, target_step - current_s)
                
                # Conditional rho on probe sample
                n_active_probe = np.sum(current_probe_mask)
                if n_active_probe > 0:
                    cand_pass = current_probe_mask & obs_pass_masks[puz]
                    surv_p = np.sum(cand_pass)
                    rho_hat = 1.0 - (surv_p / n_active_probe)
                else:
                    rho_hat = 0.5
                    
                chi_hat = 1.0 if g <= 1 else max(0.05, 1.0 / (1.5 ** max(1, g - 1)))
                
                if pol_name == 'pi_rho':
                    score = rho_hat
                    if best_score is None or score > best_score:
                        best_score = score
                        best_puz = puz
                elif pol_name == 'pi_chi':
                    score = (chi_hat, rho_hat)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_puz = puz
                elif pol_name == 'pi_cost_myopic':
                    # Single-step immediate cost
                    t_imm = N_k * g * C_ADVANCE + N_k * C_FILT + C_FRAG * N_k * (1.0 - chi_hat)
                    score = t_imm
                    if best_score is None or score < best_score:
                        best_score = score
                        best_puz = puz
                        
            # Apply chosen puzzle
            chosen_obs = obs_by_puz[best_puz]
            chosen_target = chosen_obs['block_start'] + block_symbols
            g_chosen = max(0, chosen_target - current_s)
            
            current_probe_mask = current_probe_mask & obs_pass_masks[best_puz]
            surv_frac = np.sum(current_probe_mask) / n_probes
            N_k = max(1.0, N_k * surv_frac)
            if g_chosen > 0:
                current_s = chosen_target
                
            schedule.append(best_puz)
            unapplied.remove(best_puz)
            
        return schedule

    sched_rho = run_policy('pi_rho')
    sched_chi = run_policy('pi_chi')
    sched_cost = run_policy('pi_cost_myopic')
    return sched_rho, sched_chi, sched_cost

# -----------------------------------------------------------------------------
# BENCHMARK SUITE FOR EXP-16
# -----------------------------------------------------------------------------
def run_exp16():
    print("=" * 125)
    print("RC4 MICRO-EXPERIMENT 16: OUT-OF-SAMPLE TRANSFER BENCHMARK")
    print("Evaluating Frozen Exp-15b Path Controller on Untouched Held-Out Instances")
    print("=" * 125)
    
    prov_hash = verify_provenance()
    print(f"Verified Model Provenance: {prov_hash}")
    print(f"Frozen Coefficients: c_adv={C_ADVANCE:.2e}, c_frag={C_FRAG:.2e}, c_filt={C_FILT:.2e}\n")
    
    # Load transfer instances
    transfer_file = str(Path(__file__).resolve().parent / "transfer_instances.json")
    with open(transfer_file, "r") as f:
        transfer_data = json.load(f)
        
    instances = transfer_data['instances']
    panel_keys = ["10-A", "10-B", "10-C", "10-Ref"]
    
    # Generate all candidate permutations for m=10 (N_0 = 3,628,800)
    print("Generating full permutation space for m=10 (N = 3,628,800)...")
    t_perm0 = time.perf_counter()
    all_perms = np.array(list(itertools.permutations(range(10))), dtype=np.int8)
    N_0 = len(all_perms)
    print(f"Generated {N_0:,} permutations in {time.perf_counter() - t_perm0:.2f}s.\n")
    
    # Active puzzles: Puzzles 2 through 8 (7 puzzles, 7! = 5,040 orderings)
    active_puzzles = [2, 3, 4, 5, 6, 7, 8]
    n_schedules = math.factorial(len(active_puzzles))
    
    summary_ledger = {
        'experiment': 'Micro-Experiment 16: Out-of-Sample Transfer Benchmark',
        'provenance_hash': prov_hash,
        'manifest': PROVENANCE_16_MANIFEST,
        'instances_evaluated': {},
        'pooled_metrics': {},
        'hypotheses_verdict': {}
    }
    
    all_executed_workloads = []
    all_executed_times = []
    
    # Benchmark each instance in the panel
    for inst_id in panel_keys:
        inst = instances[inst_id]
        m = inst['m']
        obs_list = inst['observations']
        bs = inst['block_symbols']
        bps = max(1, (m - 1).bit_length())
        truth = tuple(inst['planted_permutation'])
        truth_digest = compute_digest([truth])
        
        print("\n" + "=" * 125)
        print(f"BENCHMARKING INSTANCE [{inst_id}]: {inst['description']}")
        print(f"Planted Permutation: {truth}")
        print(f"Target Solution Digest: {truth_digest}")
        print("=" * 125)
        
        obs_by_puz = {o['puzzle']: o for o in obs_list}
        
        # 1. External Baseline: Demand-Driven DFS (S1)
        print(f"\n[1] Running Demand-Driven DFS Baseline (S1) on [{inst_id}]...")
        t_dfs_start = time.perf_counter()
        s1_res = run_s1_demand_driven_dfs(m, obs_list, bs)
        t_dfs_wall = s1_res['wall_time_s']
        s1_digest = compute_digest(s1_res['survivors'])
        s1_match = (s1_digest == truth_digest)
        print(f"    DFS (S1) Finished: {t_dfs_wall:.2f}s | Nodes: {s1_res['nodes']:,} | Assign: {s1_res['assign']:,} | Digest Match: {s1_match}")
        
        # 2. Prospective 1,000-Candidate Probe Firewall
        print(f"\n[2] Setting up 1,000-Candidate Probe Firewall on [{inst_id}]...")
        np.random.seed(inst['truth_seed'])
        n_probes = 1000
        probe_indices = np.random.choice(N_0, size=n_probes, replace=False)
        S_probe = all_perms[probe_indices].copy()
        j_probe = np.zeros(n_probes, dtype=np.int8)
        
        max_probe_steps = max(obs_by_puz[p]['block_start'] + bs for p in active_puzzles)
        probe_stream = {}
        
        t_probe0 = time.perf_counter()
        for st in range(1, max_probe_steps + 1):
            i_s = st % m
            j_probe = (j_probe + S_probe[np.arange(n_probes), i_s]) % m
            j_p = j_probe
            tmp = S_probe[np.arange(n_probes), i_s].copy()
            S_probe[np.arange(n_probes), i_s] = S_probe[np.arange(n_probes), j_p]
            S_probe[np.arange(n_probes), j_p] = tmp
            k_s = (S_probe[np.arange(n_probes), i_s] + S_probe[np.arange(n_probes), j_p]) % m
            probe_stream[st] = S_probe[np.arange(n_probes), k_s]
            
        t_probe_ms = (time.perf_counter() - t_probe0) * 1000
        print(f"    Probe PRGA advanced 28 steps in {t_probe_ms:.2f} ms.")
        
        # Precompute boolean pass masks on probes
        obs_pass_masks = {}
        for puz in active_puzzles:
            obs = obs_by_puz[puz]
            val = np.zeros(n_probes, dtype=np.int64)
            for b_idx in range(1, bs):
                st_idx = obs['block_start'] + b_idx + 1
                val = (val << bps) | probe_stream[st_idx]
            rev_bits = obs['reveal_bits']
            mask = (1 << rev_bits) - 1
            res = obs['residue']
            obs_pass_masks[puz] = ((val & mask) == res)
            
        # 3. Dynamic Policy Derivations (pi_rho, pi_chi, pi_cost_myopic)
        sched_rho, sched_chi, sched_cost = derive_greedy_and_myopic_schedules(
            active_puzzles, obs_by_puz, bs, n_probes, obs_pass_masks, N_0
        )
        print(f"    Dynamic pi_rho Choice:         {sched_rho}")
        print(f"    Dynamic pi_chi Choice:         {sched_chi}")
        print(f"    Dynamic pi_cost (Myopic):      {sched_cost}")
        
        # 4. Prospective Scoring of All 5,040 Schedules
        print(f"\n[3] Prospectively Scoring all {n_schedules:,} Legal Schedules...")
        t_score0 = time.perf_counter()
        scored_schedules = []
        for perm_puz in itertools.permutations(active_puzzles):
            sched = list(perm_puz)
            w_pred, c_candstep, c_chi = evaluate_schedule_prospectively(
                sched, obs_by_puz, bs, n_probes, obs_pass_masks, N_0
            )
            scored_schedules.append({
                'schedule': sched,
                'w_pred': w_pred,
                'c_candstep_ms': c_candstep,
                'c_chi_ms': c_chi
            })
        t_score_ms = (time.perf_counter() - t_score0) * 1000
        print(f"    Scored all {n_schedules:,} schedules in {t_score_ms:.2f} ms ({t_score_ms / n_schedules * 1000:.2f} us/sched).")
        
        sorted_by_candstep = sorted(scored_schedules, key=lambda s: s['c_candstep_ms'])
        candstep_winner = sorted_by_candstep[0]
        chi_winner = min(scored_schedules, key=lambda s: s['c_chi_ms'])
        median_sched = sorted_by_candstep[len(sorted_by_candstep) // 2]
        worst_sched = sorted_by_candstep[-1]
        
        print(f"    Prospective Winner (pi_candstep):     {candstep_winner['schedule']} | Pred W: {candstep_winner['w_pred']/1e6:.2f}M | Pred Cost: {candstep_winner['c_candstep_ms']:.2f} ms")
        print(f"    Prospective Winner (pi_candstep+chi): {chi_winner['schedule']} | Pred W: {chi_winner['w_pred']/1e6:.2f}M | Pred Cost: {chi_winner['c_chi_ms']:.2f} ms")
        print(f"    Median Predicted Schedule:            {median_sched['schedule']} | Pred W: {median_sched['w_pred']/1e6:.2f}M | Pred Cost: {median_sched['c_candstep_ms']:.2f} ms")
        print(f"    Worst Predicted Schedule:             {worst_sched['schedule']} | Pred W: {worst_sched['w_pred']/1e6:.2f}M | Pred Cost: {worst_sched['c_candstep_ms']:.2f} ms")
        
        # 5. Tournament Execution Set (E_i)
        tourn_dict = {}
        tourn_dict['pi_candstep'] = candstep_winner['schedule']
        tourn_dict['pi_candstep_chi'] = chi_winner['schedule']
        tourn_dict['pi_static'] = [2, 3, 4, 5, 6, 7, 8]
        tourn_dict['pi_chi'] = sched_chi
        tourn_dict['pi_rho'] = sched_rho
        tourn_dict['pi_cost_myopic'] = sched_cost
        tourn_dict['top_2_pred'] = sorted_by_candstep[1]['schedule']
        tourn_dict['top_3_pred'] = sorted_by_candstep[2]['schedule']
        tourn_dict['median_pred'] = median_sched['schedule']
        tourn_dict['worst_pred'] = worst_sched['schedule']
        
        # Deduplicate while recording names
        sched_map = defaultdict(list)
        for pol_name, sched in tourn_dict.items():
            sched_map[tuple(sched)].append(pol_name)
            
        print(f"\n[4] Executing Tournament Set ({len(sched_map)} Unique Schedules)...")
        exec_results = []
        inst_workloads = []
        inst_times = []
        
        for sched_tup, pol_names in sched_map.items():
            sched = list(sched_tup)
            t_exec_start = time.perf_counter()
            res = execute_schedule(m, obs_list, bs, sched, all_perms)
            t_wall = res['wall_time_s']
            w_real = res['realized_workload']
            sol_digest = compute_digest(res['survivors'])
            d_match = (sol_digest == truth_digest)
            
            inst_workloads.append(w_real)
            inst_times.append(t_wall)
            all_executed_workloads.append(w_real)
            all_executed_times.append(t_wall)
            
            pols_str = ", ".join(pol_names)
            print(f"    [{pols_str:<28}] Sched: {sched} | W: {w_real/1e6:6.2f}M | Time: {t_wall:6.3f}s | Surv: {len(res['survivors'])} | Match: {d_match}")
            
            exec_results.append({
                'policies': pol_names,
                'schedule': sched,
                'w_realized': w_real,
                't_wall_s': t_wall,
                'digest_match': d_match
            })
            
        # 6. Instance Metrics & Analysis
        t_min_eval = min(r['t_wall_s'] for r in exec_results)
        fastest_eval_record = min(exec_results, key=lambda r: r['t_wall_s'])
        
        candstep_record = next(r for r in exec_results if 'pi_candstep' in r['policies'])
        myopic_record = next(r for r in exec_results if 'pi_cost_myopic' in r['policies'])
        static_record = next(r for r in exec_results if 'pi_static' in r['policies'])
        
        t_candstep = candstep_record['t_wall_s']
        t_myopic = myopic_record['t_wall_s']
        
        # Prospective Regret: R_pred = T_wall(pi_candstep) - min_{E} T_wall
        r_pred_ms = (t_candstep - t_min_eval) * 1000.0
        r_pred_pct = ((t_candstep - t_min_eval) / t_min_eval) * 100.0
        
        # Speedups
        speedup_over_dfs = t_dfs_wall / t_candstep
        speedup_over_myopic = t_myopic / t_candstep
        
        # Per-instance correlations
        r_inst = pearson_r(inst_workloads, inst_times)
        rho_inst = spearman_rho(inst_workloads, inst_times)
        
        print("\n" + "-" * 110)
        print(f"SCOREBOARD SUMMARY FOR [{inst_id}]:")
        print(f"  DFS (S1) Baseline:             {t_dfs_wall:6.3f} s")
        print(f"  Myopic Controller (pi_cost):   {t_myopic:6.3f} s  (Sched: {myopic_record['schedule']})")
        print(f"  Path Lookahead (pi_candstep):  {t_candstep:6.3f} s  (Sched: {candstep_record['schedule']})")
        print(f"  Fastest Evaluated Schedule:    {t_min_eval:6.3f} s  (Sched: {fastest_eval_record['schedule']})")
        print(f"  Regret R_pred:                 +{r_pred_ms:6.1f} ms (+{r_pred_pct:4.2f}%)")
        print(f"  Speedup vs DFS (S1):           {speedup_over_dfs:5.2f}x")
        print(f"  Speedup vs Myopic:             {speedup_over_myopic:5.2f}x")
        print(f"  Pearson r(W, T):               {r_inst:6.4f}")
        print(f"  Spearman rho(W, T):            {rho_inst:6.4f}")
        print("-" * 110)
        
        summary_ledger['instances_evaluated'][inst_id] = {
            'dfs_wall_s': t_dfs_wall,
            'dfs_nodes': s1_res['nodes'],
            'dfs_match': s1_match,
            'candstep_sched': candstep_record['schedule'],
            'candstep_wall_s': t_candstep,
            'candstep_workload': candstep_record['w_realized'],
            'myopic_sched': myopic_record['schedule'],
            'myopic_wall_s': t_myopic,
            'myopic_workload': myopic_record['w_realized'],
            'fastest_eval_sched': fastest_eval_record['schedule'],
            'fastest_eval_wall_s': t_min_eval,
            'regret_ms': r_pred_ms,
            'regret_pct': r_pred_pct,
            'speedup_vs_dfs': speedup_over_dfs,
            'speedup_vs_myopic': speedup_over_myopic,
            'pearson_r': r_inst,
            'spearman_rho': rho_inst,
            'all_executed': exec_results
        }
        
    # 7. Pooled Statistical Metrics
    pooled_r = pearson_r(all_executed_workloads, all_executed_times)
    pooled_rho = spearman_rho(all_executed_workloads, all_executed_times)
    
    fresh_ids = ["10-A", "10-B", "10-C"]
    gate_a_passed = all(
        summary_ledger['instances_evaluated'][fid]['candstep_wall_s'] < summary_ledger['instances_evaluated'][fid]['myopic_wall_s']
        for fid in fresh_ids
    )
    gate_b_passed = all(
        summary_ledger['instances_evaluated'][fid]['speedup_vs_dfs'] > 10.0
        for fid in fresh_ids
    )
    surrogate_passed = (pooled_r > 0.95)
    
    mean_speedup_dfs = np.mean([summary_ledger['instances_evaluated'][fid]['speedup_vs_dfs'] for fid in fresh_ids])
    mean_speedup_myopic = np.mean([summary_ledger['instances_evaluated'][fid]['speedup_vs_myopic'] for fid in fresh_ids])
    mean_regret_pct = np.mean([summary_ledger['instances_evaluated'][fid]['regret_pct'] for fid in fresh_ids])
    
    summary_ledger['pooled_metrics'] = {
        'pooled_pearson_r': pooled_r,
        'pooled_spearman_rho': pooled_rho,
        'mean_speedup_vs_dfs_fresh': mean_speedup_dfs,
        'mean_speedup_vs_myopic_fresh': mean_speedup_myopic,
        'mean_regret_pct_fresh': mean_regret_pct
    }
    
    summary_ledger['hypotheses_verdict'] = {
        'gate_a_path_beats_myopic_on_all_fresh': {
            'hypothesis': 'T_wall(pi_candstep) < T_wall(pi_cost) on 10-A, 10-B, 10-C',
            'passed': gate_a_passed
        },
        'gate_b_speedup_exceeds_10x_on_all_fresh': {
            'hypothesis': 'Speedup vs DFS > 10.0x on 10-A, 10-B, 10-C',
            'passed': gate_b_passed
        },
        'surrogate_pooled_pearson_exceeds_95': {
            'hypothesis': 'Pooled Pearson r(W, T) > 0.95',
            'passed': surrogate_passed,
            'realized_r': pooled_r
        }
    }
    
    print("\n" + "=" * 125)
    print("FINAL MULTI-INSTANCE VERDICT FOR MICRO-EXPERIMENT 16")
    print("=" * 125)
    print(f"Hypothesis 1 (Gate A Transfer - Path Beats Myopic on All Fresh): {'PASSED' if gate_a_passed else 'FAILED'}")
    print(f"Hypothesis 2 (Gate B Transfer - Speedup > 10x DFS on All Fresh):   {'PASSED' if gate_b_passed else 'FAILED'}")
    print(f"Hypothesis 3 (Surrogate Fidelity - Pooled Pearson r > 0.95):        {'PASSED' if surrogate_passed else 'FAILED'} (r = {pooled_r:.4f}, Spearman = {pooled_rho:.4f})")
    print(f"Mean Speedup over Demand-Driven DFS:                               {mean_speedup_dfs:.2f}x")
    print(f"Mean Speedup over Myopic Controller:                              {mean_speedup_myopic:.2f}x")
    print(f"Mean Regret vs Fastest Evaluated Schedule:                         +{mean_regret_pct:.2f}%")
    print("=" * 125)
    
    out_json = r"."
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(summary_ledger, f, indent=2)
    print(f"\nWrote structured summary JSON to {out_json}")

if __name__ == "__main__":
    run_exp16()
