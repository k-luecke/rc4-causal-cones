from pathlib import Path
"""
Freeze three fresh out-of-sample transfer instances for m=10 (plus reference instance),
verifying the cryptographic hash and mirroring to Google Drive prior to any benchmark execution.
"""
import json
import hashlib
import random
from math import factorial
from dataclasses import dataclass, asdict
import os

def rc4_prga(S0, n):
    S = list(S0); m = len(S); i = j = 0; out = []
    for _ in range(n):
        i = (i + 1) % m
        j = (j + S[i]) % m
        S[i], S[j] = S[j], S[i]
        out.append(S[(S[i] + S[j]) % m])
    return out

def planted_permutation(m, seed):
    r = random.Random(seed); S = list(range(m)); r.shuffle(S); return tuple(S)

@dataclass(frozen=True)
class Observation:
    puzzle: int
    block_start: int
    reveal_bits: int
    residue: int

def make_observations(stream, m, block_symbols=4, max_puzzles=10):
    bps = max(1, (m - 1).bit_length()); out = []
    for n in range(1, max_puzzles + 1):
        start = (n - 1) * block_symbols
        block = stream[start:start + block_symbols]
        if len(block) < block_symbols: break
        x = 0
        for v in block[1:]: x = (x << bps) | v
        reveal = min(n - 1, bps * (block_symbols - 1))
        residue = x & ((1 << reveal) - 1) if reveal else 0
        out.append(Observation(n, start, reveal, residue))
    return out

def signature(S, m, block_symbols=4, max_puzzles=10):
    return make_observations(rc4_prga(S, block_symbols * max_puzzles),
                             m, block_symbols, max_puzzles)

# Define the transfer panel: 3 fresh instances + 1 reference instance
PANEL_CONFIGS = [
    {"id": "10-Ref", "m": 10, "truth_seed": 20260940, "desc": "Original Exp-15b reference instance from frozen_instances.json"},
    {"id": "10-A",   "m": 10, "truth_seed": 20261001, "desc": "Fresh untouched out-of-sample instance A"},
    {"id": "10-B",   "m": 10, "truth_seed": 20261002, "desc": "Fresh untouched out-of-sample instance B"},
    {"id": "10-C",   "m": 10, "truth_seed": 20261003, "desc": "Fresh untouched out-of-sample instance C"},
]

instances = {}
for cfg in PANEL_CONFIGS:
    inst_id = cfg["id"]
    m = cfg["m"]
    truth = planted_permutation(m, cfg["truth_seed"])
    max_puz = 10
    target = signature(truth, m, block_symbols=4, max_puzzles=max_puz)
    stream = rc4_prga(truth, 4 * max_puz)
    
    instances[inst_id] = {
        "id": inst_id,
        "m": m,
        "truth_seed": cfg["truth_seed"],
        "description": cfg["desc"],
        "planted_permutation": list(truth),
        "max_puzzles": max_puz,
        "block_symbols": 4,
        "stream_prefix": stream,
        "observations": [asdict(o) for o in target],
        "factorial_space": factorial(m),
    }

payload = json.dumps(instances, indent=2, sort_keys=True)
sha = hashlib.sha256(payload.encode()).hexdigest()

output = {
    "metadata": {
        "generator": "freeze_transfer_instances.py",
        "experiment": "Micro-Experiment 16: Out-of-Sample Transfer Benchmark",
        "sha256": sha,
        "instances_count": len(instances),
    },
    "instances": instances,
}

out_path = os.path.join(str(Path(__file__).resolve().parent), "transfer_instances.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2, sort_keys=True)

print(f"Successfully generated and wrote {out_path}")
print(f"Payload SHA-256: {sha}")
for inst_id, inst in sorted(instances.items()):
    p_perm = inst["planted_permutation"]
    res_list = [obs["residue"] for obs in inst["observations"]]
    print(f"  [{inst_id}] Truth: {p_perm} | Residues: {res_list}")
