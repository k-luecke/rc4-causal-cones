from pathlib import Path
"""
Freeze planted permutations and observation sets for all m values.
Both the DFS and Z3 solvers consume this file — no independent regeneration.
"""
import json, hashlib, random
from math import factorial
from dataclasses import dataclass, asdict

SEED = 20260930
random.seed(SEED)

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

def make_observations(stream, m, block_symbols=4, max_puzzles=12):
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

def signature(S, m, block_symbols=4, max_puzzles=12):
    return make_observations(rc4_prga(S, block_symbols * max_puzzles),
                             m, block_symbols, max_puzzles)

# Build frozen instances
instances = {}
for m in (6, 7, 8, 10, 12, 16):
    truth = planted_permutation(m, SEED + m)
    max_puz = min(12, m)
    target = signature(truth, m, max_puzzles=max_puz)
    stream = rc4_prga(truth, 4 * max_puz)
    instances[str(m)] = {
        "m": m,
        "seed": SEED,
        "truth_seed": SEED + m,
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
        "generator": "freeze_observations.py",
        "seed": SEED,
        "sha256": sha,
        "description": "Frozen planted permutations and observations for RC4 Global-Compatibility Lab falsification study. Both DFS and Z3 solvers must consume this file.",
    },
    "instances": instances,
}

import os
out_path = os.path.join(str(Path(__file__).resolve().parent), "frozen_instances.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2, sort_keys=True)

print(f"Wrote {out_path}")
print(f"SHA-256 of instances payload: {sha}")
for m_str, inst in sorted(instances.items(), key=lambda x: int(x[0])):
    m = inst["m"]
    print(f"  m={m:2d}  truth={inst['planted_permutation'][:6]}{'...' if m > 6 else ''}  "
          f"observations={len(inst['observations'])}  max_puzzles={inst['max_puzzles']}  "
          f"factorial={inst['factorial_space']}")
