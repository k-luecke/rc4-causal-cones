import json
import numpy as np
import itertools
from collections import defaultdict

def run_micro_exp4():
    with open('frozen_instances.json', 'r') as f:
        data = json.load(f)
        
    results = {}
    
    for m_target in [8, 10]:
        inst = data['instances'][str(m_target)]
        m = m_target
        bps = max(1, (m - 1).bit_length())
        T_0 = 8
        
        all_perms = np.array(list(itertools.permutations(range(m))), dtype=np.int8)
        N = len(all_perms)
        S = all_perms.copy()
        j = np.zeros(N, dtype=np.int8)
        
        # Advance to T_0 = 8
        for step in range(1, T_0 + 1):
            i = step % m
            j_prev = j.copy()
            S_i = S[np.arange(N), i].copy()
            j = (j_prev + S_i) % m
            S_j = S[np.arange(N), j].copy()
            S[np.arange(N), i] = S_j
            S[np.arange(N), j] = S_i
            k = (S_j + S_i) % m
            z = S[np.arange(N), k].copy()
            
        # Filter survivors at step 8
        surv_mask = ((z & 1) == 0)
        C_indices = np.where(surv_mask)[0]
        N_C = len(C_indices)
        
        # Build R3 at step 8
        # S_8 for active
        S_8 = S[C_indices].copy()
        j_8 = j[C_indices].copy()
        
        # Next step read frontier at step 8:
        i_next = 9 % m
        S_i_next = S_8[:, i_next].astype(np.int64)
        j_next = (j_8 + S_i_next) % m
        S_j_next = S_8[np.arange(N_C), j_next].astype(np.int64)
        k_next = (S_j_next + S_i_next) % m
        S_k_next = S_8[np.arange(N_C), k_next].astype(np.int64)
        
        # R3 token for each candidate
        # Pack into tuple
        r3_tokens = list(zip(j_8, S_i_next, S_j_next, S_k_next))
        r3_classes = defaultdict(list)
        for c_idx, tok in enumerate(r3_tokens):
            r3_classes[tok].append(c_idx)
            
        num_classes = len(r3_classes)
        print(f"=== m={m}: |C_8| = {N_C} candidates in {num_classes} R3 classes ===")
        
        # Now track frontier F_h for h = 1 .. m
        # We also want to measure:
        # 1. Candidate-level F_h
        # 2. Class-level frontier coherence: fraction of R3 classes where ALL members access identical (i_t, j_t, k_t) at horizon h
        
        exposed = np.zeros((N_C, m), dtype=bool)
        
        # S_sim and j_sim for active candidates
        S_sim = S_8.copy()
        j_sim = j_8.copy()
        
        frontier_stats = []
        class_coherence = []
        
        class_active_members = {tok: list(mems) for tok, mems in r3_classes.items()}
        class_is_coherent = {tok: True for tok in r3_classes}
        
        prev_mean_F = 0.0
        
        for h in range(1, m + 1):
            step = T_0 + h
            i = step % m
            j_prev_h = j_sim.copy()
            S_i_h = S_sim[np.arange(N_C), i].copy()
            j_curr_h = (j_prev_h + S_i_h) % m
            j_sim = j_curr_h.copy()
            S_j_h = S_sim[np.arange(N_C), j_curr_h].copy()
            
            S_sim[np.arange(N_C), i] = S_j_h
            S_sim[np.arange(N_C), j_curr_h] = S_i_h
            
            k_curr_h = (S_j_h + S_i_h) % m
            z_curr_h = S_sim[np.arange(N_C), k_curr_h].copy()
            
            # Update exposed
            exposed[np.arange(N_C), i] = True
            exposed[np.arange(N_C), j_curr_h] = True
            exposed[np.arange(N_C), k_curr_h] = True
            
            F_h = np.sum(exposed, axis=1)
            mean_F = float(np.mean(F_h))
            delta_F = mean_F - prev_mean_F
            prev_mean_F = mean_F
            reuse_rate = float(1.0 - (delta_F / 3.0)) if h > 0 else 0.0
            
            sat_pct = float(np.sum(F_h == m) / N_C * 100)
            
            # Check class-level coherence at horizon h:
            # Does every class member have identical (i, j_curr_h, k_curr_h)?
            coherent_cls_count = 0
            cand_in_coherent = 0
            for tok, mems in class_active_members.items():
                if class_is_coherent[tok]:
                    # check if all members have same j_curr_h and k_curr_h
                    j_sub = j_curr_h[mems]
                    k_sub = k_curr_h[mems]
                    if np.all(j_sub == j_sub[0]) and np.all(k_sub == k_sub[0]):
                        coherent_cls_count += 1
                        cand_in_coherent += len(mems)
                    else:
                        class_is_coherent[tok] = False
                        
            frontier_stats.append({
                'h': h,
                'step': step,
                'mean_F': mean_F,
                'delta_F': delta_F,
                'reuse_rate': reuse_rate,
                'median_F': float(np.median(F_h)),
                'min_F': int(np.min(F_h)),
                'max_F': int(np.max(F_h)),
                'saturated_pct': sat_pct,
                'coherent_classes': coherent_cls_count,
                'coherent_cls_pct': float(coherent_cls_count / num_classes * 100),
                'cand_in_coherent_pct': float(cand_in_coherent / N_C * 100)
            })
            
        results[f'm_{m}'] = {
            'm': m,
            'T_0': T_0,
            'population': N_C,
            'num_R3_classes': num_classes,
            'compression': float(N_C / num_classes),
            'horizons': frontier_stats
        }
        
    with open('output/rc4_micro_exp4_summary.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Saved output/rc4_micro_exp4_summary.json")
    return results

if __name__ == '__main__':
    run_micro_exp4()
