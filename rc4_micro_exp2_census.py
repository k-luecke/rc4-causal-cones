import json
import time
import numpy as np
import itertools
from collections import defaultdict

def run_census_all(m_target):
    with open('frozen_instances.json', 'r') as f:
        data = json.load(f)
    inst = data['instances'][str(m_target)]
    m = m_target
    bps = max(1, (m - 1).bit_length())
    observations = inst['observations']
    obs_by_end_step = {o['block_start'] + 4: o for o in observations}
    max_steps = max(obs_by_end_step.keys())
    
    t_start = time.time()
    print(f"Generating permutations for m={m}...")
    all_perms = np.array(list(itertools.permutations(range(m))), dtype=np.int8)
    N = len(all_perms)
    print(f"Total permutations for m={m}: {N} (generated in {time.time() - t_start:.2f}s)")
    
    S = all_perms.copy()
    j = np.zeros(N, dtype=np.int8)
    active_indices = np.arange(N)
    
    stream = np.zeros((N, max_steps), dtype=np.int8)
    results_by_step = []
    
    for step in range(1, max_steps + 1):
        step_t0 = time.time()
        i = step % m
        N_curr = len(active_indices)
        if N_curr == 0:
            break
            
        j_prev = j[active_indices].copy()
        S_i = S[active_indices, i].copy()
        
        j_curr = (j_prev + S_i) % m
        j[active_indices] = j_curr
        
        S_j = S[active_indices, j_curr].copy()
        
        # Swap
        S[active_indices, i] = S_j
        S[active_indices, j_curr] = S_i
        
        k_curr = (S_j + S_i) % m
        z_curr = S[active_indices, k_curr].copy()
        stream[active_indices, step - 1] = z_curr
        
        if step in obs_by_end_step:
            obs = obs_by_end_step[step]
            start = obs['block_start']
            reveal = obs['reveal_bits']
            expected = obs['residue']
            
            v1 = stream[active_indices, start + 1].astype(np.int32)
            v2 = stream[active_indices, start + 2].astype(np.int32)
            v3 = stream[active_indices, start + 3].astype(np.int32)
            x = (v1 << (2 * bps)) | (v2 << bps) | v3
            residue = x & ((1 << reveal) - 1) if reveal > 0 else np.zeros_like(x)
            survives = (residue == expected)
        else:
            survives = np.ones(N_curr, dtype=bool)
            
        n_surv_total = int(np.sum(survives))
        n_rej_total = int(N_curr - n_surv_total)
        
        # Pack signatures using integer encoding for speed on large N
        # sigma0: z_curr (0..m-1)
        # sigma1: j_curr * m + z_curr
        # sigma2: j_prev * m*m + S_i * m + S_j
        # sigma3: j_prev * m^4 + S_i * m^3 + S_j * m^2 + k_curr * m + z_curr
        sig_0 = z_curr.astype(np.int64)
        sig_1 = j_curr.astype(np.int64) * m + z_curr.astype(np.int64)
        sig_2 = (j_prev.astype(np.int64) * m + S_i.astype(np.int64)) * m + S_j.astype(np.int64)
        sig_3 = (((j_prev.astype(np.int64) * m + S_i.astype(np.int64)) * m + S_j.astype(np.int64)) * m + k_curr.astype(np.int64)) * m + z_curr.astype(np.int64)
        
        sig_data = {}
        for sig_name, sig_vals in [('sigma0', sig_0), ('sigma1', sig_1), ('sigma2', sig_2), ('sigma3', sig_3)]:
            # Fast grouping via numpy bincount / unique
            unq_sigs, inv_indices = np.unique(sig_vals, return_inverse=True)
            num_classes = len(unq_sigs)
            
            q_counts = np.bincount(inv_indices, minlength=num_classes)
            s_counts = np.bincount(inv_indices, weights=survives.astype(np.int64), minlength=num_classes).astype(np.int64)
            r_counts = q_counts - s_counts
            
            homo_rej_mask = (s_counts == 0)
            homo_surv_mask = (r_counts == 0)
            mixed_mask = (s_counts > 0) & (r_counts > 0)
            
            n_homo_rej_classes = int(np.sum(homo_rej_mask))
            cand_in_homo_rej = int(np.sum(q_counts[homo_rej_mask]))
            Q_reject = float(cand_in_homo_rej / n_homo_rej_classes) if n_homo_rej_classes > 0 else 0.0
            A_potential = int(np.sum(q_counts[homo_rej_mask] - 1))
            
            cov_ge2 = float(np.sum(q_counts[q_counts >= 2]) / N_curr)
            cov_ge5 = float(np.sum(q_counts[q_counts >= 5]) / N_curr)
            cov_ge10 = float(np.sum(q_counts[q_counts >= 10]) / N_curr)
            
            sig_data[sig_name] = {
                'num_classes': int(num_classes),
                'mean_q': float(np.mean(q_counts)),
                'median_q': float(np.median(q_counts)),
                'max_q': int(np.max(q_counts)),
                'cov_ge2': cov_ge2,
                'cov_ge5': cov_ge5,
                'cov_ge10': cov_ge10,
                'n_homo_rej_classes': n_homo_rej_classes,
                'cand_in_homo_rej': cand_in_homo_rej,
                'Q_reject': Q_reject,
                'A_potential': A_potential,
                'num_mixed_classes': int(np.sum(mixed_mask)),
                'cand_in_mixed': int(np.sum(q_counts[mixed_mask])),
                'num_homo_surv_classes': int(np.sum(homo_surv_mask)),
                'cand_in_homo_surv': int(np.sum(q_counts[homo_surv_mask]))
            }
            
        results_by_step.append({
            'step': step,
            'is_obs_step': step in obs_by_end_step,
            'reveal_bits': obs_by_end_step[step]['reveal_bits'] if step in obs_by_end_step else None,
            'C_prev': int(N_curr),
            'C_next': n_surv_total,
            'rejected': n_rej_total,
            'dt_sec': float(time.time() - step_t0),
            'signatures': sig_data
        })
        
        active_indices = active_indices[survives]
        
    return results_by_step

if __name__ == '__main__':
    print("=== Running m=8 Census ===")
    res_8 = run_census_all(8)
    print("\n=== Running m=10 Census ===")
    t0 = time.time()
    res_10 = run_census_all(10)
    print(f"m=10 Census completed in {time.time() - t0:.2f}s")
    
    # Save results to JSON
    with open('output/rc4_micro_exp2_census.json', 'w') as f:
        json.dump({'m8': res_8, 'm10': res_10}, f, indent=2)
    print("Saved output/rc4_micro_exp2_census.json")
