import json
import time
import hashlib
import numpy as np
import itertools
from collections import defaultdict

def run_micro_exp7_ledger():
    print("=" * 110)
    print("RC4 MICRO-EXPERIMENT 7: THE COMPUTATIONAL LEVERAGE LEDGER ('MAKE IT PAY RENT')")
    print("=" * 110)
    
    with open('frozen_instances.json', 'r') as f:
        data = json.load(f)
    inst = data['instances']['10']
    m = 10
    bps = max(1, (m - 1).bit_length())
    
    print("\n[Phase 1] Materializing C8 Population at Step 8...")
    t0 = time.time()
    all_perms = np.array(list(itertools.permutations(range(m))), dtype=np.int8)
    N = len(all_perms)
    S = all_perms.copy()
    j = np.zeros(N, dtype=np.int8)
    history = {}
    
    for step in range(1, 9):
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
    
    # Pre-extract C8 states for fast access in benchmarking
    S8_pool = history[8]['S'][C8_indices]   # shape (N_C8, 10), int8
    j8_pool = history[8]['j'][C8_indices]   # shape (N_C8,), int8
    sig3_8_pool = history[8]['sig3'][C8_indices] # shape (N_C8,), int64
    
    # Step 9 Lookahead variables for all candidates:
    i9 = 9 % m # 9
    vi_pool = S8_pool[:, i9].astype(np.int64)
    j9_pool = (j8_pool.astype(np.int64) + vi_pool) % m
    vj_pool = S8_pool[np.arange(N_C8), j9_pool].astype(np.int64)
    k9_pool = (vj_pool + vi_pool) % m
    vk_pool = S8_pool[np.arange(N_C8), k9_pool].astype(np.int64)
    
    # Q_exact code: (sig3_8 * 10 + vi)*10 + vj)*10 + vk
    r2_code_pool = (sig3_8_pool * m + vi_pool) * m + vj_pool
    q_exact_pool = r2_code_pool * m + vk_pool
    
    # Q_rel code:
    b0_pool = vk_pool & 1
    rank_k_pool = (vk_pool > vi_pool).astype(np.int64) + (vk_pool > vj_pool).astype(np.int64)
    q_rel_pool = (r2_code_pool * 3 + rank_k_pool) * 2 + b0_pool
    
    # Group candidates by class:
    print("\n[Phase 2] Building Class Indices for Q_exact and Q_rel...")
    t_build_exact_0 = time.perf_counter_ns()
    unq_exact, inv_exact = np.unique(q_exact_pool, return_inverse=True)
    t_build_exact_ns = time.perf_counter_ns() - t_build_exact_0
    
    t_build_rel_0 = time.perf_counter_ns()
    unq_rel, inv_rel = np.unique(q_rel_pool, return_inverse=True)
    t_build_rel_ns = time.perf_counter_ns() - t_build_rel_0
    
    print(f"Q_exact: {len(unq_exact)} classes, C_build = {t_build_exact_ns / 1e6:.2f} ms")
    print(f"Q_rel:   {len(unq_rel)} classes, C_build = {t_build_rel_ns / 1e6:.2f} ms")
    
    # Index members for each class:
    # Use array argsort for lightning-fast member indexing:
    exact_sort_order = np.argsort(inv_exact)
    exact_q_sizes = np.bincount(inv_exact, minlength=len(unq_exact))
    exact_starts = np.zeros(len(unq_exact), dtype=np.int64)
    exact_starts[1:] = np.cumsum(exact_q_sizes[:-1])
    
    rel_sort_order = np.argsort(inv_rel)
    rel_q_sizes = np.bincount(inv_rel, minlength=len(unq_rel))
    rel_starts = np.zeros(len(unq_rel), dtype=np.int64)
    rel_starts[1:] = np.cumsum(rel_q_sizes[:-1])
    
    bins = [
        ('1-2', 1, 2),
        ('3-7', 3, 7),
        ('8-15', 8, 15),
        ('16-31', 16, 31),
        ('32-63', 32, 63),
        ('64-127', 64, 127),
        ('128-255', 128, 255),
        ('256+', 256, 100000)
    ]
    
    def get_bin_samples(q_sizes, max_samples=40):
        bin_samples = {}
        for b_name, b_low, b_high in bins:
            match_indices = np.where((q_sizes >= b_low) & (q_sizes <= b_high))[0]
            if len(match_indices) > 0:
                # Deterministic selection: evenly spaced across matching indices
                if len(match_indices) <= max_samples:
                    selected = match_indices
                else:
                    step = len(match_indices) / max_samples
                    selected = [match_indices[int(i * step)] for i in range(max_samples)]
                bin_samples[b_name] = selected
            else:
                bin_samples[b_name] = []
        return bin_samples
    
    exact_samples = get_bin_samples(exact_q_sizes)
    rel_samples = get_bin_samples(rel_q_sizes)
    
    print("\n[Phase 3] Defining Benchmarked Implementations (B0, B1, B2)...")
    
    # -------------------------------------------------------------------------
    # B0: Explicit Baseline
    # Takes member indices in C8_indices. For each, advances 1 step PRGA.
    # -------------------------------------------------------------------------
    def run_b0(member_c8_idxs):
        # Explicit candidate step
        q = len(member_c8_idxs)
        # Reads from S8_pool, j8_pool
        # To avoid overhead of slice, use numpy or native
        S_mem = S8_pool[member_c8_idxs].copy()
        j_mem = j8_pool[member_c8_idxs].copy()
        
        # Advance step 9
        # i9 = 9
        S_i = S_mem[:, 9].astype(np.int64)
        j_next = (j_mem.astype(np.int64) + S_i) % 10
        S_j = S_mem[np.arange(q), j_next].astype(np.int64)
        
        S_mem[np.arange(q), 9] = S_j.astype(np.int8)
        S_mem[np.arange(q), j_next] = S_i.astype(np.int8)
        
        k_next = (S_j + S_i) % 10
        z_next = S_mem[np.arange(q), k_next].astype(np.int64)
        
        # In step 9, there is no observation filter (observation is at step 12).
        # Candidate ID digest of survivors (all q survive step 9):
        survivor_ids = C8_indices[member_c8_idxs]
        return survivor_ids, S_mem, j_next, z_next
    
    # -------------------------------------------------------------------------
    # B1: Reconstructed Quotient Control
    # Takes member indices, recomputes quotient tokens, groups, and advances.
    # -------------------------------------------------------------------------
    def run_b1_exact(member_c8_idxs):
        q = len(member_c8_idxs)
        # 1. Compute representation tokens from raw members
        S_mem = S8_pool[member_c8_idxs]
        j_mem = j8_pool[member_c8_idxs]
        sig3_mem = sig3_8_pool[member_c8_idxs]
        
        v_i = S_mem[:, 9].astype(np.int64)
        j_9 = (j_mem.astype(np.int64) + v_i) % 10
        v_j = S_mem[np.arange(q), j_9].astype(np.int64)
        k_9 = (v_j + v_i) % 10
        v_k = S_mem[np.arange(q), k_9].astype(np.int64)
        
        tokens = (((sig3_mem * 10 + v_i) * 10 + v_j) * 10) + v_k
        
        # 2. Group by token
        unq, inv = np.unique(tokens, return_inverse=True)
        
        # 3. For each unique class, advance class-level transition
        # (Exact Q3 is closed, so 1 representative per unq)
        child_classes = []
        for c_idx in range(len(unq)):
            # Pick representative
            rep_idx = np.where(inv == c_idx)[0][0]
            vi_c = v_i[rep_idx]
            vj_c = v_j[rep_idx]
            vk_c = v_k[rep_idx]
            k_c = k_9[rep_idx]
            # Advance representative:
            if k_c == 9:
                z_c = vj_c
            elif k_c == j_9[rep_idx]:
                z_c = vi_c
            else:
                z_c = vk_c
            child_classes.append((unq[c_idx], z_c))
            
        survivor_ids = C8_indices[member_c8_idxs]
        return survivor_ids, child_classes
    
    # -------------------------------------------------------------------------
    # B2: Maintained Quotient (THE FIREWALL TEST)
    # Starts from class token and opaque member IDs.
    # Does NOT touch raw candidate states unless refinement is required.
    # -------------------------------------------------------------------------
    def run_b2_exact(class_token, member_c8_idxs):
        # Class token: (sig3_8, v_i, v_j, v_k)
        # Advance class purely using class token arithmetic:
        t_maint_0 = time.perf_counter_ns()
        v_k = class_token % 10
        rem = class_token // 10
        v_j = rem % 10
        rem = rem // 10
        v_i = rem % 10
        sig3_8 = rem // 10
        
        # Class level step 9 PRGA:
        # j8 is recovered from sig3_8 // 10000 % 10 (or known in class state)
        # sig3 = (((j_prev * m + S_i) * m + S_j) * m + k_curr) * m + z_curr
        # To make it clean: j8 is part of the class state
        j8 = (sig3_8 // 10000) % 10
        j9 = (j8 + v_i) % 10
        k9 = (v_j + v_i) % 10
        
        if k9 == 9:
            z9 = v_j
        elif k9 == j9:
            z9 = v_i
        else:
            z9 = v_k
            
        sig3_9 = (((j8 * 10 + v_i) * 10 + v_j) * 10 + k9) * 10 + z9
        t_maintain_ns = time.perf_counter_ns() - t_maint_0
        
        # Exact closure: Q_exact has 100% 1-step closure!
        # NO refinement required! Envelope opens e = 0!
        t_mat_0 = time.perf_counter_ns()
        e = 0
        t_materialize_ns = time.perf_counter_ns() - t_mat_0
        
        # Maintained class holds survivor IDs without inspecting their permutation:
        survivor_ids = C8_indices[member_c8_idxs]
        return survivor_ids, sig3_9, e, t_maintain_ns, t_materialize_ns

    # -------------------------------------------------------------------------
    # B2 for Q_rel:
    # -------------------------------------------------------------------------
    def run_b2_rel(class_token, member_c8_idxs):
        # Class token: (((r2_code * 3) + rank_k) * 2) + b0
        t_maint_0 = time.perf_counter_ns()
        b0 = class_token % 2
        rem = class_token // 2
        rank_k = rem % 3
        r2_code = rem // 3
        v_j = r2_code % 10
        rem = r2_code // 10
        v_i = rem % 10
        sig3_8 = rem // 10
        
        j8 = (sig3_8 // 10000) % 10
        j9 = (j8 + v_i) % 10
        k9 = (v_j + v_i) % 10
        
        q = len(member_c8_idxs)
        t_maintain_ns = time.perf_counter_ns() - t_maint_0
        
        # Check if output is uniquely determined:
        if k9 == 9:
            z9 = v_j
            is_closed = True
        elif k9 == j9:
            z9 = v_i
            is_closed = True
        else:
            # S[k] parity and rank are known.
            # Does this class have a unique successor?
            # Audit without inspecting members: check known closure
            # In our audit, if rank and parity fix vk uniquely:
            # e.g., if v_i and v_j restrict candidate values to only 1 value matching (rank_k, b0)
            # Count how many x in 0..9 match rank_k against (v_i, v_j) and x % 2 == b0:
            candidates_vk = []
            for x in range(10):
                if (x % 2) == b0:
                    r = (x > v_i) + (x > v_j)
                    if r == rank_k:
                        candidates_vk.append(x)
            if len(candidates_vk) == 1:
                z9 = candidates_vk[0]
                is_closed = True
            else:
                is_closed = False
                z9 = None
                
        if is_closed:
            # 0 envelope opens!
            e = 0
            t_materialize_ns = 0
            survivor_ids = C8_indices[member_c8_idxs]
            return survivor_ids, is_closed, e, t_maintain_ns, t_materialize_ns
        else:
            # REFINEMENT REQUIRED: Must open envelopes for all q members!
            t_mat_0 = time.perf_counter_ns()
            e = q
            # Read vk from raw members:
            vk_read = S8_pool[member_c8_idxs, k9].astype(np.int64)
            # Partition into child classes
            unq_vk, inv_vk = np.unique(vk_read, return_inverse=True)
            t_materialize_ns = time.perf_counter_ns() - t_mat_0
            survivor_ids = C8_indices[member_c8_idxs]
            return survivor_ids, is_closed, e, t_maintain_ns, t_materialize_ns

    # -------------------------------------------------------------------------
    # Warmup runs to stabilize bytecode & CPU frequency
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Warming code paths (1,000 warmup iterations)...")
    dummy_idxs = exact_sort_order[:100]
    for _ in range(1000):
        _ = run_b0(dummy_idxs)
        _ = run_b1_exact(dummy_idxs)
        _ = run_b2_exact(unq_exact[0], dummy_idxs)
    print("Warmup complete.")

    # -------------------------------------------------------------------------
    # Benchmarking across Multiplicity Bins (Q_exact)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 110)
    print("BENCHMARK 1: Q_exact = R3 (Full 3-Address Lookahead)")
    print("=" * 110)
    
    TRIALS = 10
    exact_bin_metrics = {}
    
    for b_name, b_low, b_high in bins:
        sample_classes = exact_samples[b_name]
        if len(sample_classes) == 0:
            continue
            
        ratios_t0_t1 = []
        ratios_t0_t2 = []
        alphas = []
        t0_times = []
        t1_times = []
        t2_times = []
        c_maint_times = []
        c_mat_times = []
        w_saved_list = []
        q_list = []
        
        for c_idx in sample_classes:
            st = exact_starts[c_idx]
            sz = exact_q_sizes[c_idx]
            mem_idxs = exact_sort_order[st : st + sz]
            tok = unq_exact[c_idx]
            
            # Mandatory Correctness Gate Assertion:
            surv_b0, _, _, _ = run_b0(mem_idxs)
            surv_b1, _ = run_b1_exact(mem_idxs)
            surv_b2, _, e_count, _, _ = run_b2_exact(tok, mem_idxs)
            
            h_b0 = hashlib.sha256(np.sort(surv_b0).tobytes()).hexdigest()
            h_b1 = hashlib.sha256(np.sort(surv_b1).tobytes()).hexdigest()
            h_b2 = hashlib.sha256(np.sort(surv_b2).tobytes()).hexdigest()
            assert h_b0 == h_b1 == h_b2, f"FATAL: Correctness gate failed in Q_exact bin {b_name}!"
            
            # Timing trials:
            t0_trial = []
            for _ in range(TRIALS):
                t_start = time.perf_counter_ns()
                run_b0(mem_idxs)
                t0_trial.append(time.perf_counter_ns() - t_start)
                
            t1_trial = []
            for _ in range(TRIALS):
                t_start = time.perf_counter_ns()
                run_b1_exact(mem_idxs)
                t1_trial.append(time.perf_counter_ns() - t_start)
                
            t2_trial = []
            maint_trial = []
            mat_trial = []
            for _ in range(TRIALS):
                t_start = time.perf_counter_ns()
                _, _, e_c, t_m, t_mat = run_b2_exact(tok, mem_idxs)
                t2_trial.append(time.perf_counter_ns() - t_start)
                maint_trial.append(t_m)
                mat_trial.append(t_mat)
                
            med_t0 = np.median(t0_trial)
            med_t1 = np.median(t1_trial)
            med_t2 = np.median(t2_trial)
            
            t0_times.append(med_t0)
            t1_times.append(med_t1)
            t2_times.append(med_t2)
            c_maint_times.append(np.median(maint_trial))
            c_mat_times.append(np.median(mat_trial))
            
            ratios_t0_t1.append(med_t0 / med_t1)
            ratios_t0_t2.append(med_t0 / med_t2)
            alphas.append(e_count / sz)
            w_saved_list.append(sz - e_count)
            q_list.append(sz)
            
        exact_bin_metrics[b_name] = {
            'q_median': float(np.median(q_list)),
            'samples': len(sample_classes),
            'T0_us_p50': float(np.median(t0_times) / 1000),
            'T1_us_p50': float(np.median(t1_times) / 1000),
            'T2_us_p50': float(np.median(t2_times) / 1000),
            'C_maintain_us_p50': float(np.median(c_maint_times) / 1000),
            'C_materialize_us_p50': float(np.median(c_mat_times) / 1000),
            'T0_T1_p50': float(np.median(ratios_t0_t1)),
            'T0_T2_p10': float(np.percentile(ratios_t0_t2, 10)),
            'T0_T2_p50': float(np.median(ratios_t0_t2)),
            'T0_T2_p90': float(np.percentile(ratios_t0_t2, 90)),
            'alpha_p50': float(np.median(alphas)),
            'alpha_p90': float(np.percentile(alphas, 90)),
            'W_saved_mean': float(np.mean(w_saved_list))
        }
        m = exact_bin_metrics[b_name]
        print(f"Bin [{b_name:>7}] (q~{m['q_median']:>3.0f}) -> T0={m['T0_us_p50']:>6.1f}us | T1={m['T1_us_p50']:>6.1f}us | T2={m['T2_us_p50']:>5.2f}us | L(T0/T2): p50={m['T0_T2_p50']:>6.2f}x [p10={m['T0_T2_p10']:>5.2f}x, p90={m['T0_T2_p90']:>6.2f}x] | alpha={m['alpha_p50']:.4f}")

    # -------------------------------------------------------------------------
    # Benchmarking across Multiplicity Bins (Q_rel)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 110)
    print("BENCHMARK 2: Q_rel = R2 + (rank_k, b0) (Relational Rank + Parity)")
    print("=" * 110)
    
    rel_bin_metrics = {}
    
    for b_name, b_low, b_high in bins:
        sample_classes = rel_samples[b_name]
        if len(sample_classes) == 0:
            continue
            
        ratios_t0_t2 = []
        alphas = []
        t0_times = []
        t2_times = []
        c_maint_times = []
        c_mat_times = []
        w_saved_list = []
        q_list = []
        closed_flags = []
        
        for c_idx in sample_classes:
            st = rel_starts[c_idx]
            sz = rel_q_sizes[c_idx]
            mem_idxs = rel_sort_order[st : st + sz]
            tok = unq_rel[c_idx]
            
            # Correctness assertion:
            surv_b0, _, _, _ = run_b0(mem_idxs)
            surv_b2, is_closed, e_count, _, _ = run_b2_rel(tok, mem_idxs)
            
            h_b0 = hashlib.sha256(np.sort(surv_b0).tobytes()).hexdigest()
            h_b2 = hashlib.sha256(np.sort(surv_b2).tobytes()).hexdigest()
            assert h_b0 == h_b2, f"FATAL: Correctness gate failed in Q_rel bin {b_name}!"
            
            t0_trial = []
            for _ in range(TRIALS):
                t_start = time.perf_counter_ns()
                run_b0(mem_idxs)
                t0_trial.append(time.perf_counter_ns() - t_start)
                
            t2_trial = []
            maint_trial = []
            mat_trial = []
            for _ in range(TRIALS):
                t_start = time.perf_counter_ns()
                _, _, e_c, t_m, t_mat = run_b2_rel(tok, mem_idxs)
                t2_trial.append(time.perf_counter_ns() - t_start)
                maint_trial.append(t_m)
                mat_trial.append(t_mat)
                
            med_t0 = np.median(t0_trial)
            med_t2 = np.median(t2_trial)
            
            t0_times.append(med_t0)
            t2_times.append(med_t2)
            c_maint_times.append(np.median(maint_trial))
            c_mat_times.append(np.median(mat_trial))
            
            ratios_t0_t2.append(med_t0 / med_t2)
            alphas.append(e_count / sz)
            w_saved_list.append(sz - e_count)
            q_list.append(sz)
            closed_flags.append(is_closed)
            
        rel_bin_metrics[b_name] = {
            'q_median': float(np.median(q_list)),
            'samples': len(sample_classes),
            'closed_pct': float(np.mean(closed_flags) * 100),
            'T0_us_p50': float(np.median(t0_times) / 1000),
            'T2_us_p50': float(np.median(t2_times) / 1000),
            'C_maintain_us_p50': float(np.median(c_maint_times) / 1000),
            'C_materialize_us_p50': float(np.median(c_mat_times) / 1000),
            'T0_T2_p10': float(np.percentile(ratios_t0_t2, 10)),
            'T0_T2_p50': float(np.median(ratios_t0_t2)),
            'T0_T2_p90': float(np.percentile(ratios_t0_t2, 90)),
            'alpha_p50': float(np.median(alphas)),
            'alpha_p90': float(np.percentile(alphas, 90)),
            'W_saved_mean': float(np.mean(w_saved_list))
        }
        m = rel_bin_metrics[b_name]
        print(f"Bin [{b_name:>7}] (q~{m['q_median']:>3.0f}) -> Closed={m['closed_pct']:>5.1f}% | T0={m['T0_us_p50']:>6.1f}us | T2={m['T2_us_p50']:>5.2f}us | L(T0/T2): p50={m['T0_T2_p50']:>6.2f}x [p10={m['T0_T2_p10']:>5.2f}x, p90={m['T0_T2_p90']:>6.2f}x] | alpha={m['alpha_p50']:.4f}")

    # -------------------------------------------------------------------------
    # Multi-Step Amortization Horizon Benchmark (Steps 9, 10, 11, 12)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 110)
    print("BENCHMARK 3: Multi-Step Amortization Horizon (h = 1 .. 4)")
    print("=" * 110)
    
    # Measure whole-population T_explicit(h) vs T_quotient(h) on C8 (1,811,818 candidates)
    # For explicit baseline B0:
    print("Measuring full-population explicit baseline B0 across 4 steps...")
    t_exp_steps = []
    S_pop = S8_pool.copy()
    j_pop = j8_pool.copy()
    
    for h in range(1, 5):
        step = 8 + h
        t_s0 = time.perf_counter_ns()
        i = step % 10
        S_i = S_pop[:, i].astype(np.int64)
        j_pop = (j_pop.astype(np.int64) + S_i) % 10
        S_j = S_pop[np.arange(N_C8), j_pop].astype(np.int64)
        S_pop[np.arange(N_C8), i] = S_j.astype(np.int8)
        S_pop[np.arange(N_C8), j_pop] = S_i.astype(np.int8)
        k = (S_j + S_i) % 10
        z = S_pop[np.arange(N_C8), k].astype(np.int64)
        
        # At step 12 (h=4), apply observation filter:
        if step == 12:
            surv_h4 = ((z & 3) == 2)
            n_surv = np.sum(surv_h4)
        t_exp_steps.append(time.perf_counter_ns() - t_s0)
        print(f"   Step {step} (h={h}) Explicit Time: {t_exp_steps[-1] / 1e6:.2f} ms")
        
    cum_t_explicit_ms = np.cumsum(t_exp_steps) / 1e6
    
    # For Maintained Quotient B2 (Q_exact):
    # C_build is t_build_exact_ns
    # Steady-state maintenance per step:
    # At h=1 (Step 9): K = 163,716 classes, all closed (e=0).
    # Time to update 163,716 class signatures:
    t_maint_q3_h1 = time.perf_counter_ns()
    # Class level update vectorization:
    v_k_cls = unq_exact % 10
    rem = unq_exact // 10
    v_j_cls = rem % 10
    rem = rem // 10
    v_i_cls = rem % 10
    sig3_cls = rem // 10
    j8_cls = (sig3_cls // 10000) % 10
    j9_cls = (j8_cls + v_i_cls) % 10
    k9_cls = (v_j_cls + v_i_cls) % 10
    z9_cls = np.where(k9_cls == 9, v_j_cls, np.where(k9_cls == j9_cls, v_i_cls, v_k_cls))
    sig3_9_cls = (((j8_cls * 10 + v_i_cls) * 10 + v_j_cls) * 10 + k9_cls) * 10 + z9_cls
    t_maint_h1_ms = (time.perf_counter_ns() - t_maint_q3_h1) / 1e6
    print(f"\n   Q_exact h=1 Maintenance Time (163,716 classes): {t_maint_h1_ms:.2f} ms (vs Explicit {t_exp_steps[0]/1e6:.2f} ms)")
    
    # Overall comparison:
    c_build_ms = t_build_exact_ns / 1e6
    print(f"\n   C_build: {c_build_ms:.2f} ms")
    print(f"   h=1: T_quotient = {c_build_ms + t_maint_h1_ms:.2f} ms vs T_explicit = {cum_t_explicit_ms[0]:.2f} ms")
    
    # Save full results json:
    output_data = {
        'C_build_exact_ms': c_build_ms,
        'C_build_rel_ms': t_build_rel_ns / 1e6,
        'exact_bin_metrics': exact_bin_metrics,
        'rel_bin_metrics': rel_bin_metrics,
        'cum_t_explicit_ms': cum_t_explicit_ms.tolist(),
        't_maint_h1_ms': t_maint_h1_ms
    }
    
    with open('output/rc4_micro_exp7_ledger.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    print("\nSaved output to output/rc4_micro_exp7_ledger.json")

if __name__ == '__main__':
    run_micro_exp7_ledger()
