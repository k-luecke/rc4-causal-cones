import itertools
import json
from collections import defaultdict

m = 9

def prga_step(state, i, j, m):
    S = list(state)
    i = (i + 1) % m
    j = (j + S[i]) % m
    S[i], S[j] = S[j], S[i]
    k = (S[i] + S[j]) % m
    z = S[k]
    return tuple(S), i, j, k, z

# Run PRGA up to step 9 for all permutations
all_perms = list(itertools.permutations(range(m)))
current_groups = defaultdict(list)
for p in all_perms:
    s = p
    i = j = 0
    prefix = []
    trace = []
    for step in range(1, 10):
        s, i, j, k, z = prga_step(s, i, j, m)
        prefix.append(z)
        trace.append((s, i, j, k, z))
    current_groups[tuple(prefix)].append((p, trace))

# Extract all colliding pairs at t=9
pairs = []
pair_id = 0
for prefix, group in sorted(current_groups.items()):
    if len(group) >= 2:
        for idx_a, idx_b in itertools.combinations(range(len(group)), 2):
            pair_id += 1
            perm_a, trace_a = group[idx_a]
            perm_b, trace_b = group[idx_b]
            
            # Step 10
            s9_a, i9_a, j9_a, _, _ = trace_a[-1]
            s9_b, i9_b, j9_b, _, _ = trace_b[-1]
            s10_a, i10_a, j10_a, k10_a, z10_a = prga_step(s9_a, i9_a, j9_a, m)
            s10_b, i10_b, j10_b, k10_b, z10_b = prga_step(s9_b, i9_b, j9_b, m)
            
            survives = int(z10_a == z10_b)
            pairs.append({
                "pair_id": pair_id,
                "prefix_9": list(prefix),
                "perm_a": list(perm_a),
                "perm_b": list(perm_b),
                "z10_a": z10_a,
                "z10_b": z10_b,
                "survives": survives
            })

print(f"Total pairs found: {len(pairs)}")
survivors = sum(p['survives'] for p in pairs)
print(f"Survivors: {survivors}, Separators: {len(pairs) - survivors}")
with open(r".", "w") as f:
    json.dump(pairs, f, indent=2)
print("Saved immutable pair population.")
