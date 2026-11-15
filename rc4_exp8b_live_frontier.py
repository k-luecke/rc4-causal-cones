import json
import time
import numpy as np
import itertools

def run_exp8b():
    print("=" * 110)
    print("RC4 MICRO-EXPERIMENT 8b: HORIZON-DEPENDENT FORGETTING & LIVE FRONTIER AUDIT (h = 1 .. 10)")
    print("=" * 110)
    
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
    
    # Track steps 1 to 18 (T0=8, horizons h=1..10)
    for step in range(1, 19):
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
    
    print("\n[Phase 2] Tracking Cumulative Exposure & Horizon Retained Support (h = 1 .. 10)...")
    labels = np.tile(np.arange(10, dtype=np.int8), (N_C8, 1))
    S_trace = S8_pool.copy()
    j_trace = j8_pool.copy()
    
    cum_touched_addrs = np.zeros((N_C8, 10), dtype=bool)
    origin_slots_read = np.zeros((N_C8, 10), dtype=bool)
    
    h_stats = []
    traj_sigs = {}
    
    ar_nc8 = np.arange(N_C8)
    
    for h in range(1, 11):
        step = 8 + h
        i_curr = step % 10
        
        # S_i read
        S_i = S_trace[:, i_curr].astype(np.int64)
        origin_slots_read[ar_nc8, labels[:, i_curr]] = True
        cum_touched_addrs[:, i_curr] = True
        
        j_trace = (j_trace.astype(np.int64) + S_i) % 10
        
        # S_j read
        S_j = S_trace[ar_nc8, j_trace].astype(np.int64)
        origin_slots_read[ar_nc8, labels[ar_nc8, j_trace]] = True
        cum_touched_addrs[ar_nc8, j_trace] = True
        
        # Swap in state and in labels:
        S_trace[ar_nc8, i_curr] = S_j.astype(np.int8)
        S_trace[ar_nc8, j_trace] = S_i.astype(np.int8)
        
        lbl_i = labels[:, i_curr].copy()
        lbl_j = labels[ar_nc8, j_trace].copy()
        labels[:, i_curr] = lbl_j
        labels[ar_nc8, j_trace] = lbl_i
        
        # k read
        k_curr = (S_j + S_i) % 10
        origin_slots_read[ar_nc8, labels[ar_nc8, k_curr]] = True
        cum_touched_addrs[ar_nc8, k_curr] = True
        
        # Cumulative addresses touched in the deck (0..9)
        mean_cum_addr = float(np.mean(np.sum(cum_touched_addrs, axis=1)))
        
        # Origin S8 slots required to reproduce transitions up to h:
        mean_origin_slots = float(np.mean(np.sum(origin_slots_read, axis=1)))
        pct_all_slots = float(np.mean(np.sum(origin_slots_read, axis=1) == 10) * 100)
        
        # Output symbol at step:
        z_curr = history[step]['z'][C8_indices]
        if h == 1:
            traj_sigs[h] = z_curr.astype(np.int64)
        else:
            traj_sigs[h] = (traj_sigs[h - 1] * 10 + z_curr.astype(np.int64))
            
        h_stats.append({
            'h': h,
            'step': step,
            'mean_cum_addrs': mean_cum_addr,
            'mean_origin_slots': mean_origin_slots,
            'pct_all_origin_slots': pct_all_slots
        })
        print(f"Horizon h={h:>2} (Step {step:>2}) -> Cumulative addrs touched: {mean_cum_addr:.2f} / 10 | Retained S8 slots required: {mean_origin_slots:.2f} / 10 ({pct_all_slots:.1f}% require all 10)")

    print("\n" + "=" * 110)
    print("[Phase 3] The Forgetting Intervention & Survival Curve")
    print("=" * 110)
    
    i9 = 9
    vi = S8_pool[:, i9].astype(np.int64)
    j9 = (j8_pool.astype(np.int64) + vi) % 10
    vj = S8_pool[ar_nc8, j9].astype(np.int64)
    k9 = (vj + vi) % 10
    vk = S8_pool[ar_nc8, k9].astype(np.int64)
    
    # Exact control token (with history):
    q_exact_control = (((sig3_8_pool * m + vi) * m + vj) * m + vk)
    
    # Intervention 1: FORGET HISTORY sig3_8!
    q_forgot_hist = ((j8_pool.astype(np.int64) * m + vi) * m + vj) * m + vk
    
    # Intervention 2: FORGET S8[k9]!
    q_forgot_k = (j8_pool.astype(np.int64) * m + vi) * m + vj
    
    # Intervention 3: FORGET S8[j9]!
    q_forgot_j = j8_pool.astype(np.int64) * m + vi
    
    interventions = [
        ('Control (Q_exact full with sig3_8)', q_exact_control),
        ('Intervention 1: Forget historical sig3_8 (Keep {j8, i9, j9, k9})', q_forgot_hist),
        ('Intervention 2: Forget S8[k9] (Keep {j8, i9, j9})', q_forgot_k),
        ('Intervention 3: Forget S8[j9] (Keep {j8, i9})', q_forgot_j)
    ]
    
    survival_results = {}
    
    for int_name, int_pool in interventions:
        print(f"\nEvaluating: {int_name}")
        unq_int, inv_int = np.unique(int_pool, return_inverse=True)
        K_int = len(unq_int)
        comp_int = N_C8 / K_int
        print(f"   Classes: {K_int} ({comp_int:.2f}x compression)")
        
        surv_by_h = {}
        for h in range(1, 11):
            target_h = traj_sigs[h]
            # Pack (inv_int, target_h) using np.unique
            # inv_int is in 0..K_int-1. target_h can be large for h=10.
            # Convert target_h to ranks/unique IDs first:
            _, inv_target = np.unique(target_h, return_inverse=True)
            # Now pair_code fits safely:
            pair_code = inv_int.astype(np.int64) * len(inv_target) + inv_target.astype(np.int64)
            unq_p = np.unique(pair_code)
            toks_p = unq_p // len(inv_target)
            r_per_tok = np.bincount(toks_p, minlength=K_int)
            closed_pct = float(np.mean(r_per_tok == 1) * 100)
            mean_r = float(np.mean(r_per_tok))
            surv_by_h[f'h_{h}'] = {
                'closed_pct': closed_pct,
                'mean_r': mean_r
            }
            if h in [1, 2, 3, 4, 6, 8, 10]:
                print(f"   h={h:>2} -> Trajectory deterministic classes: {closed_pct:>5.1f}% (mean r: {mean_r:.2f})")
                
        survival_results[int_name] = {
            'classes': K_int,
            'compression': comp_int,
            'survival_by_h': surv_by_h
        }
        
    save_data = {
        'horizon_stats': h_stats,
        'interventions': survival_results
    }
    
    with open('output/rc4_micro_exp8b_summary.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    print("\nSaved output to output/rc4_micro_exp8b_summary.json")

if __name__ == '__main__':
    run_exp8b()
