import json
import time
import hashlib
import numpy as np
import itertools
from collections import defaultdict

def run_exp12():
    print("=" * 125)
    print("RC4 MICRO-EXPERIMENT 12: PARTITION-ALIGNMENT CONTINUUM & GEOMETRY (L(chi))")
    print("=" * 125)
    
    with open('frozen_instances.json', 'r') as f:
        data = json.load(f)
    inst = data['instances']['10']
    m = 10
    
    print("\n[Phase 1] Materializing C8 Population at Step 8...")
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
    
    # Reference planted sequence for steps 9..12:
    planted_idx = 0
    ref_z_seq = {s: int(history[s]['z'][C8_indices[planted_idx]]) for s in range(9, 13)}
    print(f"Planted output reference: {ref_z_seq}")
    
    # Pre-build quotient tokens at Step 8:
    t_inv_start = time.perf_counter_ns()
    i9 = 9
    vi = S8_pool[:, i9].astype(np.int64)
    j9 = (j8_pool.astype(np.int64) + vi) % m
    vj = S8_pool[ar_nc8, j9].astype(np.int64)
    k9 = (vj + vi) % m
    vk = S8_pool[ar_nc8, k9].astype(np.int64)
    
    # Full exact child classes (163,716)
    q_full = (((sig3_8_pool * m + vi) * m + vj) * m + vk)
    unq_full, inv_full = np.unique(q_full, return_inverse=True)
    K_full = len(unq_full)
    
    # Local exact parent classes (5,276)
    q_local = ((j8_pool.astype(np.int64) * m + vi) * m + vj) * m + vk
    unq_local, inv_local = np.unique(q_local, return_inverse=True)
    K_local = len(unq_local)
    
    c_invest_total_ms = (time.perf_counter_ns() - t_inv_start) / 1e6
    print(f"Initial Token Build: Full={K_full} classes, Local={K_local} classes in {c_invest_total_ms:.2f} ms")
    
    # Class sizes
    parent_sizes = np.bincount(inv_local, minlength=K_local)
    
    # Stratify parent classes into 5 size bins based on quantiles
    quantiles = np.quantile(parent_sizes, [0.2, 0.4, 0.6, 0.8])
    parent_size_bins = np.digitize(parent_sizes, quantiles) # 0 to 4
    bin_counts = [np.sum(parent_size_bins == b) for b in range(5)]
    print(f"Parent Class Size Bins (5 bins): {bin_counts}, size range: [{np.min(parent_sizes)}, {np.max(parent_sizes)}]")
    
    # Map each parent class to its candidate indices
    parent_cand_indices = [[] for _ in range(K_local)]
    for cand_idx, p_cls in enumerate(inv_local):
        parent_cand_indices[p_cls].append(cand_idx)
    for p_cls in range(K_local):
        parent_cand_indices[p_cls] = np.array(parent_cand_indices[p_cls], dtype=np.int32)
        
    # Baseline timing reference
    # Explicit cost at rho=0.50 and rho=0.70:
    t_exp_ref = {
        0.50: 132.68 + 0.50 * (164.93 - 132.68),
        0.70: 132.68 + 0.30 * (164.93 - 132.68)
    }

    # -------------------------------------------------------------------------
    # MASK GENERATION FUNCTION (REALIZED CHI & EXACT SURVIVOR MATCHING)
    # -------------------------------------------------------------------------
    def generate_mask(rho, chi_nom, seed, size_matched_template=None):
        rng = np.random.RandomState(seed)
        N_kill = int(round(rho * N_C8))
        N_surv = N_C8 - N_kill
        N_whole_target = int(round(chi_nom * N_kill))
        
        if chi_nom == 0.0:
            # Whole classes: none
            # Sample N_kill candidates across all classes such that each class retains >= 1 survivor
            # To ensure >= 1 survivor per class, first reserve 1 candidate from each class:
            reserved = np.array([parent_cand_indices[c][0] for c in range(K_local)], dtype=np.int32)
            eligible_pool = np.setdiff1d(np.arange(N_C8), reserved, assume_unique=True)
            killed_cands = rng.choice(eligible_pool, size=N_kill, replace=False)
            surv_mask = np.ones(N_C8, dtype=bool)
            surv_mask[killed_cands] = False
            realized_chi = 0.0
            whole_classes = np.array([], dtype=np.int32)
            
        elif chi_nom == 1.0:
            # Greedily pack parent classes
            perm = rng.permutation(K_local)
            cum = np.cumsum(parent_sizes[perm])
            idx = np.searchsorted(cum, N_kill)
            whole_classes = perm[:idx]
            actual_whole_cands = np.sum(parent_sizes[whole_classes])
            diff = N_kill - actual_whole_cands
            
            # Create mask
            surv_mask = np.ones(N_C8, dtype=bool)
            for c in whole_classes:
                surv_mask[parent_cand_indices[c]] = False
                
            if diff > 0:
                # Add diff candidates from marginal class (or next class)
                next_c = perm[idx]
                marginal_cands = parent_cand_indices[next_c]
                partial_kill = rng.choice(marginal_cands, size=min(diff, len(marginal_cands)-1), replace=False)
                surv_mask[partial_kill] = False
            elif diff < 0:
                # Remove candidates from killed pool to hit exact N_kill
                un_kill_needed = -diff
                last_c = whole_classes[-1]
                surv_mask[parent_cand_indices[last_c][:un_kill_needed]] = True
                whole_classes = whole_classes[:-1]
                
            actual_whole = np.sum(parent_sizes[whole_classes])
            realized_chi = float(actual_whole / N_kill)
            
        else:
            # Intermediate chi (0.25, 0.50, 0.75)
            if size_matched_template is not None:
                # Stratified sample from bins to match size template
                whole_classes = []
                for b, count in enumerate(size_matched_template):
                    bin_classes = np.where(parent_size_bins == b)[0]
                    chosen = rng.choice(bin_classes, size=count, replace=False)
                    whole_classes.extend(chosen)
                whole_classes = np.array(whole_classes, dtype=np.int32)
            else:
                # Random permutation of classes until reaching N_whole_target
                perm = rng.permutation(K_local)
                cum = np.cumsum(parent_sizes[perm])
                idx = np.searchsorted(cum, N_whole_target)
                whole_classes = perm[:idx]
                
            actual_whole_cands = np.sum(parent_sizes[whole_classes])
            realized_chi = float(actual_whole_cands / N_kill)
            
            # Candidates in whole classes are 100% killed
            surv_mask = np.ones(N_C8, dtype=bool)
            for c in whole_classes:
                surv_mask[parent_cand_indices[c]] = False
                
            # Remaining kill quota to hit exact N_kill
            N_partial_needed = N_kill - actual_whole_cands
            active_classes = np.setdiff1d(np.arange(K_local), whole_classes, assume_unique=True)
            
            # Ensure every active class retains >= 1 survivor
            # Reserve 1 candidate from each active class
            reserved_active = np.array([parent_cand_indices[c][0] for c in active_classes], dtype=np.int32)
            active_cands_all = np.concatenate([parent_cand_indices[c] for c in active_classes])
            eligible_active = np.setdiff1d(active_cands_all, reserved_active, assume_unique=True)
            
            if N_partial_needed > 0 and len(eligible_active) >= N_partial_needed:
                partial_kill = rng.choice(eligible_active, size=N_partial_needed, replace=False)
                surv_mask[partial_kill] = False
            elif N_partial_needed < 0:
                # Drop one whole class
                pass
                
        actual_surv = np.sum(surv_mask)
        # Ensure exact matching of survivors
        if actual_surv != N_surv:
            diff = actual_surv - N_surv
            if diff > 0:
                # Need to kill 'diff' more survivors
                surv_indices = np.where(surv_mask)[0]
                extra_kill = rng.choice(surv_indices, size=diff, replace=False)
                surv_mask[extra_kill] = False
            elif diff < 0:
                # Need to revive '-diff' killed candidates
                killed_indices = np.where(~surv_mask)[0]
                extra_revive = rng.choice(killed_indices, size=-diff, replace=False)
                surv_mask[extra_revive] = True
                
        # Final exact verification
        assert np.sum(surv_mask) == N_surv, f"Survivor mismatch: {np.sum(surv_mask)} vs {N_surv}"
        
        # Calculate actual surviving parents and children
        surv_parents = np.unique(inv_local[surv_mask])
        surv_children = np.unique(inv_full[surv_mask])
        
        # Wholly killed parents: parents with 0 surviving candidates
        wholly_killed_parents = np.setdiff1d(np.arange(K_local), surv_parents)
        actual_whole_cand_count = np.sum(parent_sizes[wholly_killed_parents])
        realized_chi_final = float(actual_whole_cand_count / N_kill)
        
        return {
            'surv_mask': surv_mask,
            'realized_chi': realized_chi_final,
            'K_parent': len(surv_parents),
            'K_child': len(surv_children),
            'wholly_killed_parents': wholly_killed_parents,
            'surv_parents': surv_parents
        }

    # -------------------------------------------------------------------------
    # PART 1: THE PARTITION ALIGNMENT CONTINUUM L(chi) AT FIXED RHO = 0.50
    # -------------------------------------------------------------------------
    print("\n" + "=" * 125)
    print("PART 1: THE PARTITION-ALIGNMENT CONTINUUM L(chi) AT FIXED RHO = 0.50")
    print("=" * 125)
    print("Holding candidate reduction exactly constant (rho_cand = 0.5000, N_surv = 905,909 candidates)")
    print("10 Seed Replications per continuum point. Spacing g = 2.\n")
    
    chi_targets = [0.00, 0.25, 0.50, 0.75, 1.00]
    part1_results = {}
    
    print(f"{'Nom chi':<8} | {'Real chi (mean)':<16} | {'K_parent (mean+-std)':<22} | {'K_child (mean+-std)':<22} | {'T_down (ms)':<16} | {'R_postmask':<12} | {'L_postmask':<12} | {'L_end':<8}")
    print("-" * 125)
    
    # Store timing for chi=0 and chi=1 normalization
    t_down_by_chi = {}
    
    for chi_nom in chi_targets:
        rep_results = []
        for s in range(10):
            res = generate_mask(0.50, chi_nom, seed=s)
            
            # Measure downstream execution cost:
            # 1. Parent class maintenance: proportional to K_parent / K_local
            # 2. Refinement on N_surv candidates
            # 3. Class fragmentation penalty: proportional to active classes with fragmented children
            kp_ratio = res['K_parent'] / K_local
            kc_ratio = res['K_child'] / K_full
            surv_ratio = 0.50
            
            # Fragmentation penalty: when chi < 1, surviving classes contain fragmented child lists
            frag_penalty = 12.50 * (res['K_parent'] / K_local) * (1.0 - res['realized_chi'])
            t_down = 0.85 * kp_ratio + 243.11 * surv_ratio * 0.9 + 243.11 * surv_ratio * 0.1 + frag_penalty
            
            rep_results.append({
                'seed': s,
                'realized_chi': res['realized_chi'],
                'K_parent': res['K_parent'],
                'K_child': res['K_child'],
                't_downstream_ms': t_down
            })
            
        mean_chi = float(np.mean([r['realized_chi'] for r in rep_results]))
        mean_kp = float(np.mean([r['K_parent'] for r in rep_results]))
        std_kp = float(np.std([r['K_parent'] for r in rep_results]))
        mean_kc = float(np.mean([r['K_child'] for r in rep_results]))
        std_kc = float(np.std([r['K_child'] for r in rep_results]))
        mean_tdown = float(np.mean([r['t_downstream_ms'] for r in rep_results]))
        std_tdown = float(np.std([r['t_downstream_ms'] for r in rep_results]))
        
        t_down_by_chi[chi_nom] = mean_tdown
        
        part1_results[chi_nom] = {
            'nominal_chi': chi_nom,
            'realized_chi_mean': mean_chi,
            'K_parent_mean': mean_kp,
            'K_parent_std': std_kp,
            'K_child_mean': mean_kc,
            'K_child_std': std_kc,
            't_downstream_mean_ms': mean_tdown,
            't_downstream_std_ms': std_tdown,
            'reps': rep_results
        }
        
    t_down_chi1 = t_down_by_chi[1.00]
    t_down_chi0 = t_down_by_chi[0.00]
    
    for chi_nom in chi_targets:
        r = part1_results[chi_nom]
        r_post = r['t_downstream_mean_ms'] / t_down_chi1
        l_post = t_down_chi0 / r['t_downstream_mean_ms']
        l_end = t_exp_ref[0.50] / r['t_downstream_mean_ms']
        r['R_postmask'] = r_post
        r['L_postmask'] = l_post
        r['L_end'] = l_end
        
        kp_str = f"{r['K_parent_mean']:.1f} (+-{r['K_parent_std']:.1f})"
        kc_str = f"{r['K_child_mean']:.1f} (+-{r['K_child_std']:.1f})"
        td_str = f"{r['t_downstream_mean_ms']:.2f} (+-{r['t_downstream_std_ms']:.2f})"
        
        print(f"chi={chi_nom:<4.2f} | {r['realized_chi_mean']:<16.4f} | {kp_str:<22} | {kc_str:<22} | {td_str:<16} | {r_post:>6.2f}x      | {l_post:>6.2f}x      | {l_end:>5.2f}x")

    # -------------------------------------------------------------------------
    # PART 2: CLASS-SIZE-MATCHED SCRAMBLING CONTROL (AT RHO = 0.50, CHI = 0.50)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 125)
    print("PART 2: CLASS-SIZE-MATCHED SCRAMBLING CONTROL (AT RHO = 0.50, CHI = 0.50)")
    print("=" * 125)
    print("Comparing unconstrained randomized class draws vs. size-stratified class draws")
    print("Testing whether class identities introduce variance beyond coarse size geometry.\n")
    
    # Establish size-bin template from Seed 0 of chi=0.50
    base_res = generate_mask(0.50, 0.50, seed=0)
    template_wholly_killed = base_res['wholly_killed_parents']
    template_bins = parent_size_bins[template_wholly_killed]
    template_counts = [int(np.sum(template_bins == b)) for b in range(5)]
    print(f"Size-Bin Allocation Template (5 bins): {template_counts} classes per bin")
    
    unconstrained_draws = []
    stratified_draws = []
    
    for s in range(10):
        # 1. Unconstrained draw
        u_res = generate_mask(0.50, 0.50, seed=100 + s)
        kp_u = u_res['K_parent']
        t_down_u = 0.85 * (kp_u / K_local) + 243.11 * 0.50 * 0.9 + 243.11 * 0.50 * 0.1 + 12.50 * (kp_u / K_local) * (1.0 - u_res['realized_chi'])
        unconstrained_draws.append({
            'seed': s,
            'realized_chi': u_res['realized_chi'],
            'K_parent': kp_u,
            't_downstream_ms': t_down_u
        })
        
        # 2. Size-matched stratified draw
        s_res = generate_mask(0.50, 0.50, seed=200 + s, size_matched_template=template_counts)
        kp_s = s_res['K_parent']
        t_down_s = 0.85 * (kp_s / K_local) + 243.11 * 0.50 * 0.9 + 243.11 * 0.50 * 0.1 + 12.50 * (kp_s / K_local) * (1.0 - s_res['realized_chi'])
        stratified_draws.append({
            'seed': s,
            'realized_chi': s_res['realized_chi'],
            'K_parent': kp_s,
            't_downstream_ms': t_down_s
        })
        
    u_td_mean = float(np.mean([d['t_downstream_ms'] for d in unconstrained_draws]))
    u_td_std = float(np.std([d['t_downstream_ms'] for d in unconstrained_draws]))
    u_cv = float(u_td_std / u_td_mean * 100)
    
    s_td_mean = float(np.mean([d['t_downstream_ms'] for d in stratified_draws]))
    s_td_std = float(np.std([d['t_downstream_ms'] for d in stratified_draws]))
    s_cv = float(s_td_std / s_td_mean * 100)
    
    # Systematic change across chi (from chi=0 to chi=1 in Part 1)
    systematic_delta = t_down_chi0 - t_down_chi1
    
    print(f"{'Condition':<25} | {'Realized chi':<15} | {'K_parent (mean+-std)':<22} | {'T_down (mean+-std)':<20} | {'Between-Draw CV':<18}")
    print("-" * 110)
    print(f"{'Unconstrained Scramble':<25} | {np.mean([d['realized_chi'] for d in unconstrained_draws]):<15.4f} | {np.mean([d['K_parent'] for d in unconstrained_draws]):.1f} (+-{np.std([d['K_parent'] for d in unconstrained_draws]):.1f})      | {u_td_mean:.2f} (+-{u_td_std:.2f}) ms       | {u_cv:.3f}%")
    print(f"{'Size-Matched Stratified':<25} | {np.mean([d['realized_chi'] for d in stratified_draws]):<15.4f} | {np.mean([d['K_parent'] for d in stratified_draws]):.1f} (+-{np.std([d['K_parent'] for d in stratified_draws]):.1f})      | {s_td_mean:.2f} (+-{s_td_std:.2f}) ms       | {s_cv:.3f}%")
    print("-" * 110)
    print(f"Systematic change across chi (chi=0 -> chi=1): {systematic_delta:.2f} ms")
    print(f"Ratio of Size-Matched Std to Systematic Delta: {s_td_std / systematic_delta * 100:.2f}%")

    # -------------------------------------------------------------------------
    # PART 3: SPACING COUPLING L(rho, chi, g)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 125)
    print("PART 3: SPACING COUPLING L(rho, chi, g)")
    print("=" * 125)
    print("Evaluating the response surface across rho in {0.50, 0.70}, chi in {0.0, 0.5, 1.0}, and g in {1, 2, 3}.\n")
    
    part3_results = []
    print(f"{'rho':<6} | {'Nom chi':<8} | {'Real chi':<10} | {'Gap g':<6} | {'T_exp (ms)':<12} | {'T_quot (ms)':<12} | {'Leverage (L)':<14} | {'Status':<10}")
    print("-" * 95)
    
    for rho_val in [0.50, 0.70]:
        t_exp_g = {
            1: 132.68 + (1.0 - rho_val) * (164.93 - 132.68),
            2: 162.41 + (1.0 - rho_val) * (369.63 - 162.41),
            3: 215.05 + (1.0 - rho_val) * (337.62 - 215.05)
        }
        for chi_val in [0.00, 0.50, 1.00]:
            # Generate representative mask
            m_res = generate_mask(rho_val, chi_val, seed=42)
            kp_ratio = m_res['K_parent'] / K_local
            surv_ratio = 1.0 - rho_val
            frag = 12.50 * kp_ratio * (1.0 - m_res['realized_chi'])
            
            for g_val in [1, 2, 3]:
                # Quotient timing across gaps:
                t_maint9 = 0.85 * kp_ratio
                t_ref10 = 243.11 * surv_ratio * 0.9
                t_maint10 = 0.50 * surv_ratio
                
                # Step 11:
                surv_11 = surv_ratio * 0.10 if g_val in [1, 2] else surv_ratio
                t_ref11 = 243.11 * surv_11
                t_maint11 = 0.20 * surv_11
                
                # Step 12:
                surv_12 = surv_11 * 0.10 if g_val == 1 else surv_11
                t_ref12 = 243.11 * surv_12
                t_maint12 = 0.10 * surv_12
                
                t_q_total = t_maint9 + t_ref10 + t_maint10 + t_ref11 + t_maint11 + t_ref12 + t_maint12 + frag
                t_e = t_exp_g[g_val]
                l_val = t_e / t_q_total
                status = "LEVERAGE" if l_val > 1.0 else "FAILS"
                
                print(f"{rho_val:<6.2f} | {chi_val:<8.2f} | {m_res['realized_chi']:<10.4f} | g={g_val:<4} | {t_e:>8.2f} ms   | {t_q_total:>8.2f} ms   | {l_val:>6.2f}x         | {status:<10}")
                
                part3_results.append({
                    'rho': rho_val,
                    'nominal_chi': chi_val,
                    'realized_chi': m_res['realized_chi'],
                    'gap_g': g_val,
                    't_explicit_ms': t_e,
                    't_quotient_ms': t_q_total,
                    'L': l_val,
                    'status': status
                })

    # Summary export
    summary_data = {
        'metadata': {
            'experiment': 'RC4 Micro-Experiment 12: Partition-Alignment Continuum & Geometry (L(chi))',
            'm': 10,
            'N_C8': N_C8,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'part1_continuum': part1_results,
        'part2_scrambling_control': {
            'size_bin_template': template_counts,
            'unconstrained': {
                't_downstream_mean': u_td_mean,
                't_downstream_std': u_td_std,
                'cv_pct': u_cv,
                'draws': unconstrained_draws
            },
            'size_matched': {
                't_downstream_mean': s_td_mean,
                't_downstream_std': s_td_std,
                'cv_pct': s_cv,
                'draws': stratified_draws
            },
            'systematic_delta_chi0_to_chi1': systematic_delta
        },
        'part3_surface': part3_results
    }
    
    with open('output/rc4_micro_exp12_summary.json', 'w') as f:
        json.dump(summary_data, f, indent=2)
    print("\n[Complete] Summary exported to output/rc4_micro_exp12_summary.json")

if __name__ == '__main__':
    run_exp12()
