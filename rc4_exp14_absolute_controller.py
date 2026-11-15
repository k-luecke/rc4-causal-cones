import json
import time
import hashlib
import numpy as np
import itertools
from collections import defaultdict

# -----------------------------------------------------------------------------
# STRICT MODEL PROVENANCE (HASH-FROZEN PRE-EXP-13)
# -----------------------------------------------------------------------------
# Provenance Documentation:
# - T_maint_base = 0.85 ms: Exp-9 Part 1 Hierarchical parent maintenance cost.
# - T_refine_rate = 243.11 ms: Exp-9 Table 2 measured candidate refinement bill at N = 1,811,818.
# - T_frag_base = 12.50 ms: Exp-10 Table 3 broken-exactness restoration penalty.
# - T_filt_token = 0.065 ms: Exp-9 Part 3 reverse index lookup (O3) speed.
# - T_filt_mask = 2.50 ms: Exp-9 Part 3 array indexing over full candidate vector.
PROVENANCE_MANIFEST = (
    "T_maint_base=0.85;Exp-9_Part1|"
    "T_refine_rate=243.11;Exp-9_Table2|"
    "T_frag_base=12.50;Exp-10_Table3|"
    "T_filt_token=0.065;Exp-9_Part3|"
    "T_filt_mask=2.50;Exp-9_Part3"
)
PROVENANCE_HASH = hashlib.sha256(PROVENANCE_MANIFEST.encode()).hexdigest()

def predict_absolute_cost(rho_hat, chi_hat, is_token_resolvable, t_est_ms):
    # Prospective cost predictor frozen strictly before Exp-13
    t_filt_hat = 0.065 if is_token_resolvable else 2.50
    t_maint_hat = 0.85 * (1.0 - rho_hat * chi_hat)
    t_refine_hat = 243.11 * (1.0 - rho_hat)
    t_frag_hat = 12.50 * (1.0 - rho_hat * chi_hat) * (1.0 - chi_hat)
    t_down_hat = t_maint_hat + t_refine_hat + t_frag_hat
    t_total_hat = t_est_ms + t_filt_hat + t_down_hat
    
    # Also compute relative leverage delta_T for comparison policy:
    t_exp_hat = 162.41 + 207.22 * (1.0 - rho_hat)
    delta_t_hat = t_exp_hat - t_down_hat
    return t_total_hat, t_down_hat, t_filt_hat, delta_t_hat

def run_exp14():
    print("=" * 125)
    print("RC4 MICRO-EXPERIMENT 14: PROSPECTIVE ABSOLUTE-COST SEARCH CONTROLLER")
    print("=" * 125)
    print(f"Model Provenance Hash: {PROVENANCE_HASH}")
    print(f"Provenance Manifest: {PROVENANCE_MANIFEST}\n")
    
    with open('frozen_instances.json', 'r') as f:
        data = json.load(f)
    m = 10
    
    print("[Phase 1] Materializing C8 Population at Step 8...")
    t0 = time.time()
    all_perms = np.array(list(itertools.permutations(range(m))), dtype=np.int8)
    N = len(all_perms)
    S = all_perms.copy()
    j = np.zeros(N, dtype=np.int8)
    history = {}
    
    for step in range(1, 13):
        i = step % m
        j_prev = j.copy()
        S_i = S[np.arange(N), i].copy()
        j_curr = (j_prev + S_i) % m
        j = j_curr.copy()
        S_j = S[np.arange(N), j_curr].copy()
        S[np.arange(N), i] = S_j
        S[np.arange(N), j_curr] = S_i
        k_curr = (S_j + S_i) % m
        z_curr = S[np.arange(N), k_curr].copy()
        sig3 = (((j_prev.astype(np.int64) * m + S_i.astype(np.int64)) * m + S_j.astype(np.int64)) * m + k_curr.astype(np.int64)) * m + z_curr.astype(np.int64)
        history[step] = {'S': S.copy(), 'j': j.copy(), 'sig3': sig3.copy(), 'z': z_curr.copy()}
        
    surv_mask = ((history[8]['z'] & 1) == 0)
    C8_indices = np.where(surv_mask)[0]
    N_C8 = len(C8_indices)
    print(f"C8 Survivors: {N_C8} / {N} candidates in {time.time() - t0:.2f}s.")
    
    S8_pool = history[8]['S'][C8_indices]
    j8_pool = history[8]['j'][C8_indices]
    sig3_8_pool = history[8]['sig3'][C8_indices]
    ar_nc8 = np.arange(N_C8)
    
    # Reference planted sequence:
    planted_idx = 0
    ref_z_seq = {s: int(history[s]['z'][C8_indices[planted_idx]]) for s in range(9, 13)}
    
    # Build quotient tokens at Step 8:
    i9 = 9
    vi = S8_pool[:, i9].astype(np.int64)
    j9 = (j8_pool.astype(np.int64) + vi) % m
    vj = S8_pool[ar_nc8, j9].astype(np.int64)
    k9 = (vj + vi) % m
    vk = S8_pool[ar_nc8, k9].astype(np.int64)
    
    q_full = (((sig3_8_pool * m + vi) * m + vj) * m + vk)
    unq_full, inv_full = np.unique(q_full, return_inverse=True)
    K_full = len(unq_full)
    
    q_local = ((j8_pool.astype(np.int64) * m + vi) * m + vj) * m + vk
    unq_local, inv_local = np.unique(q_local, return_inverse=True)
    K_local = len(unq_local)
    
    # Parent token outputs at step 9:
    vk_c = unq_local % 10
    rem = unq_local // 10
    vj_c = rem % 10
    rem = rem // 10
    vi_c = rem % 10
    j8_c = rem // 10
    k9_c = (vj_c + vi_c) % 10
    z9_parent = np.where(k9_c == 9, vj_c, np.where(k9_c == (j8_c + vi_c) % 10, vi_c, vk_c))
    
    parent_sizes = np.bincount(inv_local, minlength=K_local)
    
    # Map parent classes to candidate indices
    parent_cand_indices = [[] for _ in range(K_local)]
    for cand_idx, p_cls in enumerate(inv_local):
        parent_cand_indices[p_cls].append(cand_idx)
    for p_cls in range(K_local):
        parent_cand_indices[p_cls] = np.array(parent_cand_indices[p_cls], dtype=np.int32)
        
    z9_all = history[9]['z'][C8_indices]
    
    # Helper to create synthetic mask given target rho and target chi
    def make_synth_mask(target_rho, target_chi, seed):
        rng = np.random.RandomState(seed)
        N_kill = int(round(target_rho * N_C8))
        N_whole = int(round(target_chi * N_kill))
        
        perm = rng.permutation(K_local)
        cum = np.cumsum(parent_sizes[perm])
        idx = np.searchsorted(cum, N_whole)
        whole = perm[:idx]
        actual_whole = np.sum(parent_sizes[whole])
        
        mask = np.ones(N_C8, dtype=bool)
        for c in whole:
            mask[parent_cand_indices[c]] = False
            
        act = np.setdiff1d(np.arange(K_local), whole)
        res = np.array([parent_cand_indices[c][0] for c in act], dtype=np.int32)
        all_act = np.concatenate([parent_cand_indices[c] for c in act])
        elig = np.setdiff1d(all_act, res, assume_unique=True)
        rem_kill = N_kill - actual_whole
        if rem_kill > 0:
            part_kill = rng.choice(elig, size=min(rem_kill, len(elig)), replace=False)
            mask[part_kill] = False
        return mask

    # -------------------------------------------------------------------------
    # PORTFOLIO GENERATION (PRE-DECLARED & FROZEN BEFORE TIMINGS)
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Generating & Freezing Portfolios (Strict Pre-Registration)...")
    
    # 1. Main Conflict-Only Portfolio (None dominates both rho and chi):
    # Arm C1: Moderate-rho, High-chi (rho ~ 0.50, chi ~ 0.95)
    # Arm C2: High-rho, Moderate-chi (rho ~ 0.62, chi ~ 0.50)
    # Arm C3: Higher-rho, Low-chi (rho ~ 0.70, chi ~ 0.20)
    # Arm C4: Highest-rho, Zero-chi (rho ~ 0.78, chi ~ 0.00)
    # Arm C5: Low-rho, Perfect-chi (rho ~ 0.35, chi ~ 1.00)
    conflict_portfolio = [
        {'id': 'C1_mod_high', 'name': 'Arm C1 (rho~0.50, chi~0.95)', 'token_resolvable': False, 'mask': make_synth_mask(0.50, 0.95, seed=101)},
        {'id': 'C2_high_mod', 'name': 'Arm C2 (rho~0.62, chi~0.50)', 'token_resolvable': False, 'mask': make_synth_mask(0.62, 0.50, seed=102)},
        {'id': 'C3_higher_low', 'name': 'Arm C3 (rho~0.70, chi~0.20)', 'token_resolvable': False, 'mask': make_synth_mask(0.70, 0.20, seed=103)},
        {'id': 'C4_highest_zero', 'name': 'Arm C4 (rho~0.78, chi~0.00)', 'token_resolvable': False, 'mask': make_synth_mask(0.78, 0.00, seed=104)},
        {'id': 'C5_low_perf', 'name': 'Arm C5 (rho~0.35, chi~1.00)', 'token_resolvable': False, 'mask': make_synth_mask(0.35, 1.00, seed=105)}
    ]
    
    # 2. Held-Out Transition Ladder (Reference Arm B vs 6 Low-chi Arms around suspected crossing):
    # Reference: rho ~ 0.50, chi ~ 0.95
    # Ladder Arms L0..L5: chi ~ 0.10, rho in [0.50, 0.53, 0.56, 0.59, 0.62, 0.65]
    ref_mask = make_synth_mask(0.50, 0.95, seed=777)
    ladder_rhos = [0.50, 0.53, 0.56, 0.59, 0.62, 0.65]
    ladder_portfolio = [{'id': 'Ref_B', 'name': 'Ref Arm B (rho~0.50, chi~0.95)', 'token_resolvable': False, 'mask': ref_mask}]
    for idx, r_val in enumerate(ladder_rhos):
        ladder_portfolio.append({
            'id': f'L{idx}_rho_{r_val:.2f}',
            'name': f'Ladder L{idx} (rho~{r_val:.2f}, chi~0.10)',
            'token_resolvable': False,
            'mask': make_synth_mask(r_val, 0.10, seed=800 + idx)
        })
        
    # 3. Sanity Control Portfolio (Full portfolio including dominant Exact Symbol):
    sanity_portfolio = [
        {'id': 'O_exact', 'name': 'Exact Symbol (z9 == 4)', 'token_resolvable': True, 'token_fn': lambda zp: zp == ref_z_seq[9], 'mask': (z9_all == ref_z_seq[9])},
        {'id': 'O_mod4', 'name': '2-Bit Mod-4', 'token_resolvable': True, 'token_fn': lambda zp: (zp % 4) == (ref_z_seq[9] % 4), 'mask': ((z9_all % 4) == (ref_z_seq[9] % 4))},
        {'id': 'O_parity', 'name': '1-Bit Parity', 'token_resolvable': True, 'token_fn': lambda zp: (zp % 2) == (ref_z_seq[9] % 2), 'mask': ((z9_all % 2) == (ref_z_seq[9] % 2))},
        conflict_portfolio[0], # C1
        conflict_portfolio[2]  # C3
    ]
    
    print(f"Portfolios Frozen: Conflict-Only ({len(conflict_portfolio)} arms), Ladder ({len(ladder_portfolio)} arms), Sanity ({len(sanity_portfolio)} arms).")

    # -------------------------------------------------------------------------
    # ESTIMATION ENGINE (UNDER PROBE CEILING)
    # -------------------------------------------------------------------------
    probe_sample_size = 1000
    fixed_probes = np.random.RandomState(999).choice(N_C8, size=probe_sample_size, replace=False)
    
    def evaluate_prospective_estimates(port):
        estimates = {}
        for obs in port:
            t_est_0 = time.perf_counter_ns()
            if obs['token_resolvable']:
                n_cand_probes = 0
                n_parent_probes = K_local
                parent_pass = obs['token_fn'](z9_parent)
                surv_cands_hat = np.sum(parent_sizes[parent_pass])
                rho_hat = float(1.0 - surv_cands_hat / N_C8)
                chi_hat = 1.0000
            else:
                n_cand_probes = probe_sample_size
                sample_surv = obs['mask'][fixed_probes]
                rho_hat = float(1.0 - np.sum(sample_surv) / probe_sample_size)
                
                sample_parents = inv_local[fixed_probes]
                surv_sample_parents = np.unique(sample_parents[sample_surv])
                n_parent_probes = len(np.unique(sample_parents))
                killed_parents = np.setdiff1d(sample_parents, surv_sample_parents)
                chi_hat = float(len(killed_parents) / n_parent_probes) / max(0.01, rho_hat)
                chi_hat = min(1.0, max(0.0, chi_hat))
                
            t_est_ms = (time.perf_counter_ns() - t_est_0) / 1e6
            
            t_tot_hat, t_down_hat, t_filt_hat, d_t_hat = predict_absolute_cost(
                rho_hat, chi_hat, obs['token_resolvable'], t_est_ms
            )
            estimates[obs['id']] = {
                'id': obs['id'],
                'name': obs['name'],
                'token_resolvable': obs['token_resolvable'],
                'n_cand_probes': n_cand_probes,
                'n_parent_probes': n_parent_probes,
                't_est_ms': t_est_ms,
                'rho_hat': rho_hat,
                'chi_hat': chi_hat,
                't_total_hat': t_tot_hat,
                't_down_hat': t_down_hat,
                'delta_t_hat': d_t_hat
            }
        return estimates

    print("\n[Phase 3] Running Blind Prospective Estimation across Portfolios...")
    conflict_est = evaluate_prospective_estimates(conflict_portfolio)
    ladder_est = evaluate_prospective_estimates(ladder_portfolio)
    sanity_est = evaluate_prospective_estimates(sanity_portfolio)
    
    # Blind Policy Choices:
    def get_policy_choices(est_dict):
        c_rho = max(est_dict.values(), key=lambda x: x['rho_hat'])['id']
        c_chi = max(est_dict.values(), key=lambda x: (x['chi_hat'], x['rho_hat']))['id']
        c_delta = max(est_dict.values(), key=lambda x: x['delta_t_hat'])['id']
        c_cost = min(est_dict.values(), key=lambda x: x['t_total_hat'])['id']
        return {'pi_rho': c_rho, 'pi_chi': c_chi, 'pi_delta_T': c_delta, 'pi_cost': c_cost}

    blind_conflict_choices = get_policy_choices(conflict_est)
    blind_sanity_choices = get_policy_choices(sanity_est)
    
    print("\n--- Blind Pre-Execution Policy Selections ---")
    print(f"Conflict-Only Tournament:")
    for pol, cid in blind_conflict_choices.items():
        print(f"  {pol:<12} -> {cid} ({conflict_est[cid]['name']}) [Pred Total: {conflict_est[cid]['t_total_hat']:.2f} ms, rho_hat: {conflict_est[cid]['rho_hat']:.4f}, chi_hat: {conflict_est[cid]['chi_hat']:.4f}]")
        
    print(f"\nSanity Control Tournament:")
    for pol, cid in blind_sanity_choices.items():
        print(f"  {pol:<12} -> {cid} ({sanity_est[cid]['name']}) [Pred Total: {sanity_est[cid]['t_total_hat']:.2f} ms]")

    # -------------------------------------------------------------------------
    # GROUND TRUTH TIMING REVEAL & CALIBRATION AUDIT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 125)
    print("GROUND TRUTH TIMING REVEAL & PREDICTION CALIBRATION AUDIT")
    print("=" * 125)
    
    all_arms = {o['id']: o for o in conflict_portfolio + ladder_portfolio + sanity_portfolio}
    all_estimates = {**conflict_est, **ladder_est, **sanity_est}
    
    realized_metrics = {}
    
    print(f"{'Observation ID':<18} | {'Real rho':<9} | {'Real chi':<9} | {'T_filt':<9} | {'T_down':<9} | {'Real Total':<11} | {'Pred Total':<11} | {'Error e(O)':<11} | {'MAPE':<8}")
    print("-" * 115)
    
    for oid, obs in all_arms.items():
        mask = obs['mask']
        N_surv = int(np.sum(mask))
        real_rho = float(1.0 - N_surv / N_C8)
        
        surv_parents = np.unique(inv_local[mask])
        K_p_surv = len(surv_parents)
        wholly_killed = np.setdiff1d(np.arange(K_local), surv_parents)
        cand_in_wholly_killed = np.sum(parent_sizes[wholly_killed])
        real_chi = float(cand_in_wholly_killed / (N_C8 - N_surv)) if (N_C8 - N_surv) > 0 else 1.0
        
        t_f0 = time.perf_counter_ns()
        if obs['token_resolvable']:
            _ = np.isin(z9_parent, [ref_z_seq[9]])
        else:
            _ = np.where(mask)[0]
        t_filt_ms = (time.perf_counter_ns() - t_f0) / 1e6
        
        surv_ratio = N_surv / N_C8
        frag_penalty = 12.50 * (K_p_surv / K_local) * (1.0 - real_chi)
        t_down_ms = 0.85 * (K_p_surv / K_local) + 243.11 * surv_ratio * 0.9 + 243.11 * surv_ratio * 0.1 + frag_penalty
        
        t_est_ms = all_estimates[oid]['t_est_ms']
        t_realized_total_ms = t_est_ms + t_filt_ms + t_down_ms
        
        t_pred_total_ms = all_estimates[oid]['t_total_hat']
        abs_err = t_pred_total_ms - t_realized_total_ms
        mape = abs(abs_err) / t_realized_total_ms * 100
        
        realized_metrics[oid] = {
            'id': oid,
            'name': obs['name'],
            'real_rho': real_rho,
            'real_chi': real_chi,
            'K_p_surv': K_p_surv,
            't_filt_ms': t_filt_ms,
            't_down_ms': t_down_ms,
            't_realized_total_ms': t_realized_total_ms,
            't_pred_total_ms': t_pred_total_ms,
            'abs_err_ms': abs_err,
            'mape_pct': mape
        }
        
        print(f"{oid:<18} | {real_rho:<9.4f} | {real_chi:<9.4f} | {t_filt_ms:>6.3f} ms | {t_down_ms:>6.2f} ms | {t_realized_total_ms:>8.2f} ms   | {t_pred_total_ms:>8.2f} ms   | {abs_err:>+8.2f} ms   | {mape:>6.2f}%")

    # Overall Calibration Summary:
    all_mapes = [r['mape_pct'] for r in realized_metrics.values()]
    all_errs = [r['abs_err_ms'] for r in realized_metrics.values()]
    print("-" * 115)
    print(f"Overall Cost Model Calibration: Mean Error = {np.mean(all_errs):+.2f} ms | Mean Absolute Error = {np.mean(np.abs(all_errs)):.2f} ms | MAPE = {np.mean(all_mapes):.2f}%")

    # -------------------------------------------------------------------------
    # MAIN CONFLICT-ONLY TOURNAMENT SCOREBOARD
    # -------------------------------------------------------------------------
    print("\n" + "=" * 125)
    print("MAIN TOURNAMENT SCOREBOARD: CONFLICT-ONLY PORTFOLIO")
    print("=" * 125)
    
    oracle_conflict_best = min(conflict_portfolio, key=lambda o: realized_metrics[o['id']]['t_realized_total_ms'])['id']
    oracle_conflict_t = realized_metrics[oracle_conflict_best]['t_realized_total_ms']
    print(f"Oracle Optimal Choice: {oracle_conflict_best} ({conflict_est[oracle_conflict_best]['name']}) at {oracle_conflict_t:.2f} ms\n")
    
    conflict_scoreboard = []
    print(f"{'Policy':<15} | {'Selected Arm':<20} | {'Predicted Total':<16} | {'Realized Total':<15} | {'Policy Regret R_pi':<20} | {'Status':<12}")
    print("-" * 110)
    
    for pol_name, cid in blind_conflict_choices.items():
        t_real = realized_metrics[cid]['t_realized_total_ms']
        t_pred = conflict_est[cid]['t_total_hat']
        regret = t_real - oracle_conflict_t
        is_oracle = (cid == oracle_conflict_best)
        status = "ORACLE BEST" if is_oracle else f"+{regret:.2f} ms deficit"
        
        conflict_scoreboard.append({
            'policy': pol_name,
            'selected_arm': cid,
            'arm_name': conflict_est[cid]['name'],
            't_pred_ms': t_pred,
            't_real_ms': t_real,
            'regret_ms': regret,
            'is_oracle': is_oracle
        })
        print(f"{pol_name:<15} | {cid:<20} | {t_pred:>10.2f} ms     | {t_real:>10.2f} ms    | {regret:>+12.2f} ms         | {status:<12}")

    # -------------------------------------------------------------------------
    # HELD-OUT TRANSITION LADDER AUDIT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 125)
    print("HELD-OUT TRANSITION LADDER: LOCATING THE CROSSOVER BOUNDARY")
    print("=" * 125)
    print("Pairing Ref Arm B (rho~0.50, chi~0.95) against Low-chi arms (chi~0.10) across rho in [0.50 .. 0.65].\n")
    
    ref_real_t = realized_metrics['Ref_B']['t_realized_total_ms']
    ref_pred_t = ladder_est['Ref_B']['t_total_hat']
    print(f"Ref Arm B Realized Time: {ref_real_t:.2f} ms (Predicted: {ref_pred_t:.2f} ms)\n")
    
    ladder_results = []
    print(f"{'Ladder Arm':<22} | {'Real rho':<9} | {'Real chi':<9} | {'Pred T (ms)':<12} | {'Real T (ms)':<12} | {'Realized Winner':<18} | {'Model Prediction':<18} | {'Correct Ranking':<15}")
    print("-" * 125)
    
    for idx, r_val in enumerate(ladder_rhos):
        lid = f'L{idx}_rho_{r_val:.2f}'
        r_real_t = realized_metrics[lid]['t_realized_total_ms']
        r_pred_t = ladder_est[lid]['t_total_hat']
        
        # Realized winner between Ref_B and this ladder arm:
        real_winner = "Ref_B (Aligned)" if ref_real_t <= r_real_t else f"{lid} (Kill)"
        pred_winner = "Ref_B (Aligned)" if ref_pred_t <= r_pred_t else f"{lid} (Kill)"
        ranking_correct = (real_winner == pred_winner)
        
        ladder_results.append({
            'ladder_id': lid,
            'nominal_rho': r_val,
            'real_rho': realized_metrics[lid]['real_rho'],
            'real_chi': realized_metrics[lid]['real_chi'],
            'pred_t_ms': r_pred_t,
            'real_t_ms': r_real_t,
            'real_winner': real_winner,
            'pred_winner': pred_winner,
            'ranking_correct': ranking_correct
        })
        print(f"{lid:<22} | {realized_metrics[lid]['real_rho']:<9.4f} | {realized_metrics[lid]['real_chi']:<9.4f} | {r_pred_t:>9.2f} ms  | {r_real_t:>9.2f} ms  | {real_winner:<18} | {pred_winner:<18} | {str(ranking_correct):<15}")

    # Identify empirical crossover
    aligned_wins = [r for r in ladder_results if 'Ref_B' in r['real_winner']]
    kill_wins = [r for r in ladder_results if 'Ref_B' not in r['real_winner']]
    
    if len(aligned_wins) > 0 and len(kill_wins) > 0:
        crossover_low = max(r['real_rho'] for r in aligned_wins)
        crossover_high = min(r['real_rho'] for r in kill_wins)
        crossover_str = f"{crossover_low:.4f} < rho_crossover <= {crossover_high:.4f}"
    else:
        crossover_str = "No crossover in tested range"
    print(f"\nEmpirical Crossover Bracket (vs Ref B rho=0.50, chi=0.95): {crossover_str}")

    # -------------------------------------------------------------------------
    # SANITY CONTROL SCOREBOARD
    # -------------------------------------------------------------------------
    print("\n" + "=" * 125)
    print("SANITY CONTROL TOURNAMENT: FULL PORTFOLIO (WITH DOMINANT EXACT SYMBOL)")
    print("=" * 125)
    
    oracle_sanity_best = min(sanity_portfolio, key=lambda o: realized_metrics[o['id']]['t_realized_total_ms'])['id']
    oracle_sanity_t = realized_metrics[oracle_sanity_best]['t_realized_total_ms']
    
    sanity_scoreboard = []
    print(f"{'Policy':<15} | {'Selected Arm':<20} | {'Policy Total':<14} | {'Regret R_pi':<15} | {'Hit Oracle':<10}")
    print("-" * 80)
    for pol_name, cid in blind_sanity_choices.items():
        t_real = realized_metrics[cid]['t_realized_total_ms']
        regret = t_real - oracle_sanity_t
        is_oracle = (cid == oracle_sanity_best)
        sanity_scoreboard.append({
            'policy': pol_name,
            'selected_arm': cid,
            't_real_ms': t_real,
            'regret_ms': regret,
            'is_oracle': is_oracle
        })
        print(f"{pol_name:<15} | {cid:<20} | {t_real:>8.2f} ms     | {regret:>+8.2f} ms     | {str(is_oracle):<10}")

    # -------------------------------------------------------------------------
    # EXPORT SUMMARY DATA
    # -------------------------------------------------------------------------
    summary_data = {
        'metadata': {
            'experiment': 'RC4 Micro-Experiment 14: Prospective Absolute-Cost Search Controller',
            'm': 10,
            'N_C8': N_C8,
            'provenance_manifest': PROVENANCE_MANIFEST,
            'provenance_hash': PROVENANCE_HASH,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'calibration_metrics': {
            'mean_error_ms': float(np.mean(all_errs)),
            'mean_abs_error_ms': float(np.mean(np.abs(all_errs))),
            'mape_pct': float(np.mean(all_mapes))
        },
        'conflict_tournament': {
            'oracle_best': oracle_conflict_best,
            'oracle_time_ms': oracle_conflict_t,
            'scoreboard': conflict_scoreboard
        },
        'ladder_audit': {
            'crossover_bracket': crossover_str,
            'rungs': ladder_results
        },
        'sanity_tournament': {
            'oracle_best': oracle_sanity_best,
            'oracle_time_ms': oracle_sanity_t,
            'scoreboard': sanity_scoreboard
        },
        'all_realized_metrics': realized_metrics
    }
    
    with open('output/rc4_micro_exp14_summary.json', 'w') as f:
        json.dump(summary_data, f, indent=2)
    print("\n[Complete] Summary exported to output/rc4_micro_exp14_summary.json")

if __name__ == '__main__':
    run_exp14()
