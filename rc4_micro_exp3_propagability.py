import json
import numpy as np
import itertools
from collections import defaultdict

def run_experiment():
    with open('frozen_instances.json', 'r') as f:
        data = json.load(f)
    inst = data['instances']['8']
    m = 8
    bps = max(1, (m - 1).bit_length())
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
        
    z_8 = history[8]['z']
    c8_mask = ((z_8 & 1) == 0)
    C8_indices = np.where(c8_mask)[0]
    N_C8 = len(C8_indices)
    
    S_8 = history[8]['S'][C8_indices]
    j_8 = history[8]['j'][C8_indices]
    sig3_8 = history[8]['sig3'][C8_indices]
    
    i_9 = 1
    read_next_i = S_8[:, i_9].astype(np.int64)
    next_j = (j_8 + read_next_i) % m
    read_next_j = S_8[np.arange(N_C8), next_j].astype(np.int64)
    next_k = (read_next_j + read_next_i) % m
    read_next_k = S_8[np.arange(N_C8), next_k].astype(np.int64)
    
    reps = {
        'R0 (sig3 alone)': [tuple([s]) for s in sig3_8],
        'R1 (+ S_8[i_9])': [tuple([s, i_val]) for s, i_val in zip(sig3_8, read_next_i)],
        'R2 (+ S_8[i_9], S_8[j_9])': [tuple([s, i_val, j_val]) for s, i_val, j_val in zip(sig3_8, read_next_i, read_next_j)],
        'R3 (+ S_8[i_9], S_8[j_9], S_8[k_9])': [tuple([s, i_val, j_val, k_val]) for s, i_val, j_val, k_val in zip(sig3_8, read_next_i, read_next_j, read_next_k)],
        'R_full (full state)': [tuple([s] + list(s_row)) for s, s_row in zip(sig3_8, S_8)]
    }
    
    summary = {}
    for rep_name, rep_tokens in reps.items():
        cls_dict = defaultdict(list)
        for idx, tok in enumerate(rep_tokens):
            cls_dict[tok].append(idx)
        num_cls = len(cls_dict)
        comp = N_C8 / num_cls
        q_sizes = np.array([len(v) for v in cls_dict.values()])
        
        horizons = {}
        for h in [1, 2, 3, 4]:
            step_h = 8 + h
            sig3_h = history[step_h]['sig3'][C8_indices]
            r_list = []
            rho_list = []
            for tok, members in cls_dict.items():
                desc_sigs = set(sig3_h[m_idx] for m_idx in members)
                r = len(desc_sigs)
                r_list.append(r)
                rho_list.append(r / len(members))
            r_arr = np.array(r_list)
            rho_arr = np.array(rho_list)
            weighted_rho = float(np.sum(q_sizes * rho_arr) / np.sum(q_sizes))
            closed_pct = float(np.sum(r_arr == 1) / num_cls * 100)
            horizons[f'h_{h}'] = {
                'mean_r': float(np.mean(r_arr)),
                'median_r': float(np.median(r_arr)),
                'max_r': int(np.max(r_arr)),
                'weighted_rho': weighted_rho,
                'closed_pct': closed_pct
            }
        summary[rep_name] = {
            'num_classes': num_cls,
            'compression': float(comp),
            'mean_q': float(np.mean(q_sizes)),
            'max_q': int(np.max(q_sizes)),
            'horizons': horizons
        }
        
    with open('output/rc4_micro_exp3_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print("Saved output/rc4_micro_exp3_summary.json")

if __name__ == '__main__':
    run_experiment()
