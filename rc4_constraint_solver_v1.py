from pathlib import Path
import json
import hashlib
import time
import itertools
import pandas as pd
import z3
import tracemalloc
import os

z3.set_param('timeout', 300000)

def verify_sha256(filepath, expected_hash):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_hash

def z3_lookup(arr, idx, m):
    result = arr[m - 1]
    for k in range(m - 2, -1, -1):
        result = z3.If(idx == k, arr[k], result)
    return result

def build_rc4_model(m, observations, block_symbols=4):
    solver = z3.Solver()
    S_0 = [z3.Int(f'S_0_{k}') for k in range(m)]
    
    for k in range(m):
        solver.add(S_0[k] >= 0, S_0[k] < m)
    solver.add(z3.Distinct(S_0))
    
    max_puz = max([o['puzzle'] for o in observations]) if observations else 0
    T = block_symbols * max_puz
    
    S_t_prev = S_0
    j_t_prev = 0
    r_vars = []
    
    all_vars_dict = {'S_0': S_0}
    
    for t in range(1, T + 1):
        i_t = t % m
        j_t = z3.Int(f'j_{t}')
        j_sum = j_t_prev + S_t_prev[i_t]
        solver.add(j_t == z3.If(j_sum >= m, j_sum - m, j_sum))
        
        S_t = [z3.Int(f'S_{t}_{k}') for k in range(m)]
        for k in range(m):
            if k == i_t:
                solver.add(S_t[k] == z3_lookup(S_t_prev, j_t, m))
            else:
                solver.add(S_t[k] == z3.If(j_t == k, S_t_prev[i_t], S_t_prev[k]))
        
        s_i = S_t[i_t]
        s_j = z3_lookup(S_t, j_t, m)
        sum_ij = s_i + s_j
        out_idx = z3.If(sum_ij >= m, sum_ij - m, sum_ij)
        
        r_t = z3.Int(f'r_{t}')
        solver.add(r_t == z3_lookup(S_t, out_idx, m))
        
        r_vars.append(r_t)
        S_t_prev = S_t
        j_t_prev = j_t

        all_vars_dict[f'S_{t}'] = S_t
        all_vars_dict[f'r_{t}'] = r_t
        all_vars_dict[f'j_{t}'] = j_t
        
    bps = max(1, (m - 1).bit_length())
    
    for o in observations:
        block_start = o['block_start']
        reveal_bits = o['reveal_bits']
        residue = o['residue']
        
        block = [r_vars[block_start + idx] for idx in range(block_symbols)]
        
        x = 0
        for v in block[1:]:
            x = (x * (2**bps)) + v
            
        if reveal_bits > 0:
            solver.add((x % (2**reveal_bits)) == residue)
            
    return solver, S_0, all_vars_dict

def get_stats(solver):
    stats = solver.statistics()
    res = {}
    for k, v in stats:
        res[k] = v
    return res

def solve_and_enumerate(m, observations, max_solutions=100, block_symbols=4):
    start_time = time.time()
    solver, S_0, _ = build_rc4_model(m, observations, block_symbols)
    
    solutions = []
    time_to_first = None
    time_to_unique = None
    sat_result = None
    
    stats_first = {}
    
    while len(solutions) < max_solutions:
        res = solver.check()
        if res == z3.sat:
            if time_to_first is None:
                time_to_first = time.time() - start_time
                stats_first = get_stats(solver)
                sat_result = "SAT"
            
            model = solver.model()
            sol = tuple(model.evaluate(S_0[k]).as_long() for k in range(m))
            solutions.append(sol)
            print(f"  Found solution {len(solutions)}: {sol}")
            if len(solutions) % 10 == 0:
                print(f"  Found {len(solutions)} solutions...")
            
            block = []
            for k in range(m):
                block.append(S_0[k] != sol[k])
            solver.add(z3.Or(block))
        elif res == z3.unsat:
            if time_to_first is None:
                sat_result = "UNSAT"
                stats_first = get_stats(solver)
            elif time_to_unique is None and len(solutions) == 1:
                time_to_unique = time.time() - start_time
            break
        else:
            if time_to_first is None:
                sat_result = "UNKNOWN"
            break
            
    total_time = time.time() - start_time
    return {
        'solutions': solutions,
        'sat_result': sat_result,
        'time_to_first_solution': time_to_first,
        'time_to_prove_uniqueness': time_to_unique,
        'total_time': total_time,
        'solver_stats': stats_first,
        'num_solutions': len(solutions)
    }

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

def run_exhaustive(m, observations, block_symbols=4):
    survivors = []
    for S in itertools.permutations(range(m)):
        if compatible(S, observations, m, block_symbols):
            survivors.append(S)
    return set(survivors)

def main():
    os.makedirs(str(Path(__file__).resolve().parent / "output"), exist_ok=True)
    
    print("=== Section 1: Load and verify ===")
    filepath = str(Path(__file__).resolve().parent / "frozen_instances.json")
    with open(filepath, "r") as f:
        frozen = json.load(f)
        
    expected_hash = frozen['metadata']['sha256']
    is_valid = verify_sha256(filepath, expected_hash)
    print(f"SHA256 Match: {is_valid}")
    print(f"Instances loaded: {list(frozen['instances'].keys())}")
    
    print("\n=== Section 3: Validation (m=6,7,8) ===")
    for m_str in ['6', '7', '8']:
        m = int(m_str)
        if m_str not in frozen['instances']: continue
        inst = frozen['instances'][m_str]
        obs = inst['observations']
        bs = inst['block_symbols']
        planted = tuple(inst['planted_permutation'])
        
        print(f"Testing m={m}...")
        z3_res = solve_and_enumerate(m, obs, max_solutions=100000, block_symbols=bs)
        z3_set = set(z3_res['solutions'])
        
        start = time.time()
        ex_set = run_exhaustive(m, obs, block_symbols=bs)
        ex_time = time.time() - start
        
        print(f"  Z3 count: {len(z3_set)}, Exhaustive count: {len(ex_set)}")
        print(f"  Sets equal: {z3_set == ex_set}")
        print(f"  Planted in Z3: {planted in z3_set}")
        print(f"  Planted in Ex: {planted in ex_set}")
        
        bad_obs = [dict(o) for o in obs]
        for i, o in enumerate(bad_obs):
            if o['reveal_bits'] > 0:
                bad_obs[i]['residue'] ^= 1
                break
        
        unsat_res = solve_and_enumerate(m, bad_obs, max_solutions=1, block_symbols=bs)
        unsat_pass = (unsat_res['sat_result'] == 'UNSAT')
        print(f"  UNSAT test pass: {unsat_pass}")
        
        if z3_set == ex_set and (planted in z3_set) and unsat_pass:
            print(f"  Result: PASS")
        else:
            print(f"  Result: FAIL")

    print("\n=== Section 4: Scale runs (m=8,10,12,16) ===")
    scale_results = []
    for m_str in ['8', '10', '12', '16']:
        m = int(m_str)
        if m_str not in frozen['instances']: continue
        inst = frozen['instances'][m_str]
        obs = inst['observations']
        bs = inst['block_symbols']
        print(f"Running m={m}...")
        
        res = solve_and_enumerate(m, obs, max_solutions=100, block_symbols=bs)
        stats = res['solver_stats']
        scale_results.append({
            'm': m,
            'sat_result': res['sat_result'],
            'num_solutions': res['num_solutions'],
            'total_time': res['total_time'],
            'time_to_first': res['time_to_first_solution'],
            'time_to_unique': res['time_to_prove_uniqueness'],
            'decisions': stats.get('decisions', 0),
            'conflicts': stats.get('conflicts', 0),
            'propagations': stats.get('propagations', 0)
        })
    pd.DataFrame(scale_results).to_csv(str(Path(__file__).resolve().parent / "output" / "rc4_constraint_results_v1.csv"), index=False)
    
    print("\n=== Section 5: Progressive observation experiments ===")
    prog_results = []
    for m_str in ['8', '10', '12', '16']:
        m = int(m_str)
        if m_str not in frozen['instances']: continue
        inst = frozen['instances'][m_str]
        obs = inst['observations']
        bs = inst['block_symbols']
        
        print(f"Progressive m={m}...")
        for k in range(1, len(obs) + 1):
            sub_obs = obs[:k]
            res = solve_and_enumerate(m, sub_obs, max_solutions=100, block_symbols=bs)
            stats = res['solver_stats']
            total_reveal = sum(o['reveal_bits'] for o in sub_obs)
            prog_results.append({
                'm': m,
                'k': k,
                'num_observations_used': k,
                'total_reveal_bits': total_reveal,
                'sat_result': res['sat_result'],
                'num_solutions': res['num_solutions'],
                'wall_time': res['total_time'],
                'time_to_first': res['time_to_first_solution'],
                'time_to_unique': res['time_to_prove_uniqueness'],
                'decisions': stats.get('decisions', 0),
                'conflicts': stats.get('conflicts', 0),
                'propagations': stats.get('propagations', 0)
            })
    pd.DataFrame(prog_results).to_csv(str(Path(__file__).resolve().parent / "output" / "rc4_progressive_observations_v1.csv"), index=False)

    print("\n=== Section 6: Leave-one-out ablation ===")
    loo_results = []
    for m_str in ['8', '10']:
        m = int(m_str)
        if m_str not in frozen['instances']: continue
        inst = frozen['instances'][m_str]
        obs = inst['observations']
        bs = inst['block_symbols']
        
        print(f"LOO m={m}...")
        for i in range(len(obs)):
            sub_obs = obs[:i] + obs[i+1:]
            res = solve_and_enumerate(m, sub_obs, max_solutions=100, block_symbols=bs)
            stats = res['solver_stats']
            loo_results.append({
                'm': m,
                'left_out_index': i,
                'left_out_puzzle': obs[i]['puzzle'],
                'num_solutions': res['num_solutions'],
                'wall_time': res['total_time'],
                'decisions': stats.get('decisions', 0),
                'conflicts': stats.get('conflicts', 0)
            })
    pd.DataFrame(loo_results).to_csv(r".", index=False)

    print("\n=== Section 7: Corrupted observation tests ===")
    corr_results = []
    for m_str in ['8', '10']:
        m = int(m_str)
        if m_str not in frozen['instances']: continue
        inst = frozen['instances'][m_str]
        obs = inst['observations']
        bs = inst['block_symbols']
        
        print(f"Corrupted m={m}...")
        for i in range(len(obs)):
            if obs[i]['reveal_bits'] == 0: continue
            bad_obs = [dict(o) for o in obs]
            bad_obs[i]['residue'] ^= 1
            res = solve_and_enumerate(m, bad_obs, max_solutions=1, block_symbols=bs)
            corr_results.append({
                'm': m,
                'corrupted_index': i,
                'sat_result': res['sat_result'],
                'wall_time': res['total_time']
            })
    pd.DataFrame(corr_results).to_csv(r".", index=False)
    
    print("\n=== DONE ===")

if __name__ == '__main__':
    main()
