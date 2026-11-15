from pathlib import Path
import json
import hashlib
import pickle
import time
import signal
import sys
import os
import csv
from itertools import permutations

def verify_frozen_instances(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    expected_hash = "ae7a8bf22f0444cfdff32f4194a71890f8b79a834a984632f330b9bdf852cce7"
    if data.get("metadata", {}).get("sha256") != expected_hash:
        raise ValueError(f"Hash mismatch! Expected {expected_hash}, got {data.get('metadata', {}).get('sha256')}")
    return data

def get_next_demand(state, m, observations, block_symbols, bps, obs_by_end_step, max_steps):
    i = 0
    j = 0
    S = list(state)
    stream = []
    
    for step in range(1, max_steps + 1):
        i = (i + 1) % m
        if S[i] is None: return True, i
        j = (j + S[i]) % m
        if S[j] is None: return True, j
        
        S[i], S[j] = S[j], S[i]
        
        out_idx = (S[i] + S[j]) % m
        if S[out_idx] is None: return True, out_idx
        
        stream.append(S[out_idx])
        
        if step in obs_by_end_step:
            for obs in obs_by_end_step[step]:
                start = obs["block_start"]
                val = 0
                for k in range(block_symbols):
                    val = (val << bps) | stream[start + k]
                reveal_bits = obs["reveal_bits"]
                mask = (1 << reveal_bits) - 1
                if (val & mask) != obs["residue"]:
                    return False, None
                    
    return True, None

def run_dfs():
    base_dir = str(Path(__file__).resolve().parent)
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    frozen_path = os.path.join(base_dir, "frozen_instances.json")
    checkpoint_path = os.path.join(base_dir, "rc4_m12_checkpoint.pkl")
    progress_csv = os.path.join(output_dir, "rc4_m12_progress.csv")
    stats_csv = os.path.join(output_dir, "rc4_m12_depth_stats.csv")
    
    data = verify_frozen_instances(frozen_path)
    inst = data["instances"]["12"]
    
    m = inst["m"]
    observations = inst["observations"]
    block_symbols = inst["block_symbols"]
    bps = max(1, (m - 1).bit_length())
    
    max_steps = max(obs["block_start"] + block_symbols for obs in observations) if observations else 0
    obs_by_end_step = {}
    for obs in observations:
        end_step = obs["block_start"] + block_symbols
        if end_step not in obs_by_end_step:
            obs_by_end_step[end_step] = []
        obs_by_end_step[end_step].append(obs)
        
    # State variables
    stack = []
    nodes = 0
    nodes_by_depth = {}
    survivors = []
    observations_checked = 0
    observations_rejected = 0
    rejection_depth_histogram = {}
    elapsed_seconds = 0.0
    
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'rb') as f:
            cp = pickle.load(f)
        stack = cp['stack']
        nodes = cp['nodes']
        nodes_by_depth = cp['nodes_by_depth']
        survivors = cp['survivors']
        observations_checked = cp['observations_checked']
        observations_rejected = cp['observations_rejected']
        rejection_depth_histogram = cp['rejection_depth_histogram']
        elapsed_seconds = cp['elapsed_seconds']
        print(f"Resuming from checkpoint at {nodes} nodes")
    else:
        initial_state = [None] * m
        initial_used = set()
        is_valid, need_idx = get_next_demand(initial_state, m, observations, block_symbols, bps, obs_by_end_step, max_steps)
        if is_valid and need_idx is not None:
            candidates = [v for v in range(m) if v not in initial_used]
            stack.append((initial_state, initial_used, need_idx, candidates))
            
    # Write CSV headers if new
    if not os.path.exists(progress_csv):
        with open(progress_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'elapsed_seconds', 'nodes', 'nodes_per_sec', 'current_max_depth', 'survivors_found'])
            
    # Setup signal handling
    shutdown_requested = False
    def signal_handler(sig, frame):
        nonlocal shutdown_requested
        print(f"\\nReceived signal {sig}, initiating graceful shutdown...")
        shutdown_requested = True
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    last_checkpoint_time = time.time()
    last_progress_nodes = nodes
    last_progress_time = time.time()
    start_time = time.time()
    
    def save_checkpoint():
        cp = {
            'stack': stack,
            'nodes': nodes,
            'nodes_by_depth': nodes_by_depth,
            'survivors': survivors,
            'observations_checked': observations_checked,
            'observations_rejected': observations_rejected,
            'rejection_depth_histogram': rejection_depth_histogram,
            'elapsed_seconds': elapsed_seconds + (time.time() - start_time)
        }
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(cp, f)
            
        with open(stats_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['depth', 'nodes', 'rejections'])
            for d in range(1, m + 1):
                writer.writerow([d, nodes_by_depth.get(d, 0), rejection_depth_histogram.get(d, 0)])
    
    try:
        while stack and not shutdown_requested:
            state, used, need_idx, candidates = stack[-1]
            
            if not candidates:
                stack.pop()
                continue
                
            val = candidates.pop()
            
            new_state = list(state)
            new_state[need_idx] = val
            new_used = used.copy()
            new_used.add(val)
            
            nodes += 1
            depth = len(new_used)
            nodes_by_depth[depth] = nodes_by_depth.get(depth, 0) + 1
            
            observations_checked += 1
            is_valid, next_need = get_next_demand(new_state, m, observations, block_symbols, bps, obs_by_end_step, max_steps)
            
            if not is_valid:
                observations_rejected += 1
                rejection_depth_histogram[depth] = rejection_depth_histogram.get(depth, 0) + 1
            else:
                if next_need is None:
                    remaining_indices = [idx for idx, v in enumerate(new_state) if v is None]
                    remaining_values = [v for v in range(m) if v not in new_used]
                    for perm in permutations(remaining_values):
                        survivor = list(new_state)
                        for idx, v in zip(remaining_indices, perm):
                            survivor[idx] = v
                        survivors.append(survivor)
                else:
                    new_candidates = [v for v in range(m) if v not in new_used]
                    stack.append((new_state, new_used, next_need, new_candidates))
                    
            # Progress reporting
            if nodes - last_progress_nodes >= 1000000:
                now = time.time()
                dt = now - last_progress_time
                nps = (nodes - last_progress_nodes) / dt if dt > 0 else 0
                current_max_depth = max(nodes_by_depth.keys()) if nodes_by_depth else 0
                
                with open(progress_csv, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                        elapsed_seconds + (now - start_time),
                        nodes,
                        f"{nps:.2f}",
                        current_max_depth,
                        len(survivors)
                    ])
                    
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Nodes: {nodes}, NPS: {nps:.2f}, Survivors: {len(survivors)}")
                last_progress_nodes = nodes
                last_progress_time = now
                
            # Checkpointing
            if time.time() - last_checkpoint_time >= 60:
                save_checkpoint()
                last_checkpoint_time = time.time()
                
    except KeyboardInterrupt:
        print("\\nCaught KeyboardInterrupt")
        shutdown_requested = True

    elapsed_seconds += (time.time() - start_time)
    
    if shutdown_requested:
        print("Saving checkpoint before shutdown...")
        save_checkpoint()
        print("Shutdown complete.")
        sys.exit(0)
        
    print(f"\\nSearch complete in {elapsed_seconds:.2f} seconds!")
    print(f"Total nodes: {nodes}")
    print(f"Survivors found: {len(survivors)}")
    
    with open(os.path.join(output_dir, "rc4_m12_survivors.json"), "w") as f:
        json.dump(survivors, f)
        
    # Final stats update
    save_checkpoint()
    
if __name__ == '__main__':
    run_dfs()
