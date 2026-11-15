#!/usr/bin/env python3
"""
RC4 terminal-collision causal-cone perturbation experiment v1.

Purpose
-------
Falsify or support the strong interpretation of the frozen *pathwise* causal
cones from rc4_terminal_collision_causal_cone_freeze_v1.md.

This script:
  1. Exhaustively enumerates all initial permutations for m=6,7,8.
  2. Re-discovers the terminal collision pairs from complete output prefixes.
  3. Reconstructs each pair's realized separating-output dependency cone
     by exact provenance tracking (no hard-coded pair permutations).
  4. Holds the values at each member's cone positions fixed.
  5. Exhaustively permutes values among positions outside that cone.
  6. Re-runs the exact reduced-RC4 PRGA.
  7. Separately measures:
       - exact-path preservation
       - separating-step address preservation
       - original output-prefix preservation
       - separation-step preservation
       - same address-correspondence failure
  8. Writes CSV/JSON results and a SHA-256 manifest.

No entropy/information-theory quantities are computed.

Python: standard library only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import sys
import time
from collections import defaultdict
from pathlib import Path


TARGETS = {
    6: {"last_prefix": 6, "separating_step": 7, "expected_pairs": 5},
    7: {"last_prefix": 9, "separating_step": 10, "expected_pairs": 1},
    8: {"last_prefix": 11, "separating_step": 12, "expected_pairs": 1},
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prga_trace(initial, steps):
    """Exact semantics used by rc4_uncapped_m12.py."""
    m = len(initial)
    S = list(initial)
    i = j = 0
    trace = []

    for step in range(1, steps + 1):
        i = (i + 1) % m
        j = (j + S[i]) % m

        pre_i_val = S[i]
        pre_j_val = S[j]
        S[i], S[j] = S[j], S[i]

        k = (S[i] + S[j]) % m
        z = S[k]

        trace.append({
            "step": step,
            "i": i,
            "j": j,
            "pre_i_val": pre_i_val,
            "pre_j_val": pre_j_val,
            "k": k,
            "z": z,
            "state": tuple(S),
        })
    return trace


def prga_trace_with_provenance(initial, steps):
    """
    Pathwise provenance: each current cell carries the set of initial positions
    whose values were read to produce the realized execution leading to it.

    This deliberately tracks the *realized path*. It does NOT claim
    interventionally sufficient dependence; the perturbation experiment below
    tests that stronger claim.
    """
    m = len(initial)
    S = list(initial)
    prov = [{p} for p in range(m)]
    i = j = 0
    control = set()
    trace = []

    for step in range(1, steps + 1):
        i = (i + 1) % m

        # j' = j + S[i]; prior control determines the realized old j.
        read_i = set(prov[i])
        j_prov = set(control) | read_i
        j = (j + S[i]) % m

        # Reading S[j] depends on which j was selected plus the payload there.
        read_j = set(prov[j]) | j_prov

        # Swap payloads; selection of j is itself path-dependent.
        S[i], S[j] = S[j], S[i]
        prov[i], prov[j] = set(prov[j]) | j_prov, set(prov[i]) | j_prov

        # k = S[i] + S[j]
        address_prov = set(prov[i]) | set(prov[j]) | set(j_prov)
        k = (S[i] + S[j]) % m

        # z = S[k]: output includes address selection + payload at selected cell.
        output_prov = set(address_prov) | set(prov[k])
        z = S[k]

        control |= j_prov
        trace.append({
            "step": step,
            "i": i,
            "j": j,
            "k": k,
            "z": z,
            "state": tuple(S),
            "address_prov": tuple(sorted(address_prov)),
            "output_prov": tuple(sorted(output_prov)),
        })

    return trace


def prefix(initial, n):
    return tuple(x["z"] for x in prga_trace(initial, n))


def discover_terminal_pairs(m, last_prefix, separating_step):
    groups = defaultdict(list)
    for p in itertools.permutations(range(m)):
        groups[prefix(p, last_prefix)].append(p)

    colliding = [sorted(v) for v in groups.values() if len(v) > 1]
    colliding.sort(key=lambda xs: xs[0])

    pairs = []
    for group in colliding:
        if len(group) != 2:
            raise RuntimeError(
                f"m={m}: terminal collision class has size {len(group)}, expected 2"
            )
        a, b = group
        ta = prga_trace(a, separating_step)
        tb = prga_trace(b, separating_step)
        if tuple(x["z"] for x in ta[:last_prefix]) != tuple(
            x["z"] for x in tb[:last_prefix]
        ):
            raise AssertionError("collision rediscovery inconsistency")
        if ta[separating_step - 1]["z"] == tb[separating_step - 1]["z"]:
            raise AssertionError("pair does not separate at expected step")
        pairs.append((a, b))
    return pairs


def position_correspondence(state_a, state_b):
    pos_b = {value: pos for pos, value in enumerate(state_b)}
    return tuple(pos_b[value] for value in state_a)


def correspondence_failure_at(trace_a, trace_b, step):
    ea, eb = trace_a[step - 1], trace_b[step - 1]
    psi = position_correspondence(ea["state"], eb["state"])
    return psi[ea["k"]] != eb["k"]


def perturbations_preserving_positions(original, fixed_positions):
    """
    Preserve original values at fixed positions and exhaustively permute the
    remaining original values over remaining positions. Includes original.
    """
    m = len(original)
    fixed = set(fixed_positions)
    free_positions = [p for p in range(m) if p not in fixed]
    free_values = [original[p] for p in free_positions]

    for vals in itertools.permutations(free_values):
        q = list(original)
        for p, v in zip(free_positions, vals):
            q[p] = v
        yield tuple(q)


def path_signature(trace, through_step):
    return tuple(
        (e["i"], e["j"], e["k"], e["z"], e["state"])
        for e in trace[:through_step]
    )


def first_pair_separation(trace_a, trace_b):
    for ea, eb in zip(trace_a, trace_b):
        if ea["z"] != eb["z"]:
            return ea["step"]
    return None


def run_member_perturbations(
    m, pair_id, side, original, partner, cone, sep_step, writer, summary
):
    base = prga_trace(original, sep_step)
    partner_trace = prga_trace(partner, sep_step)
    base_prefix = tuple(e["z"] for e in base[: sep_step - 1])
    base_path = path_signature(base, sep_step)
    base_k = base[sep_step - 1]["k"]
    base_z = base[sep_step - 1]["z"]

    n = 0
    counts = defaultdict(int)

    for candidate in perturbations_preserving_positions(original, cone):
        n += 1
        tr = prga_trace(candidate, sep_step)
        exact_path = path_signature(tr, sep_step) == base_path
        address_preserved = tr[sep_step - 1]["k"] == base_k
        prefix_preserved = tuple(e["z"] for e in tr[: sep_step - 1]) == base_prefix
        sep_output_preserved = tr[sep_step - 1]["z"] == base_z

        counts["exact_path"] += exact_path
        counts["address"] += address_preserved
        counts["prefix"] += prefix_preserved
        counts["sep_output"] += sep_output_preserved

        writer.writerow({
            "m": m,
            "pair_id": pair_id,
            "side": side,
            "cone": " ".join(map(str, cone)),
            "candidate": " ".join(map(str, candidate)),
            "is_original": int(candidate == original),
            "exact_path_preserved": int(exact_path),
            "separating_address_preserved": int(address_preserved),
            "original_prefix_preserved": int(prefix_preserved),
            "separating_output_preserved": int(sep_output_preserved),
        })

    summary.append({
        "m": m,
        "pair_id": pair_id,
        "test": f"single_member_{side}",
        "cone": list(cone),
        "perturbations": n,
        "exact_path_preserved": counts["exact_path"],
        "separating_address_preserved": counts["address"],
        "original_prefix_preserved": counts["prefix"],
        "separating_output_preserved": counts["sep_output"],
    })


def run_joint_perturbations(
    m, pair_id, a, b, cone_a, cone_b, sep_step, writer, summary
):
    """
    Cross product of A/B cone-preserving perturbations. Small here because
    m<=8 and frozen cones leave at most 6 free positions.
    """
    pa = list(perturbations_preserving_positions(a, cone_a))
    pb = list(perturbations_preserving_positions(b, cone_b))
    base_a = prga_trace(a, sep_step)
    base_b = prga_trace(b, sep_step)
    original_prefix = tuple(e["z"] for e in base_a[: sep_step - 1])

    counts = defaultdict(int)
    n = 0

    for qa in pa:
        ta = prga_trace(qa, sep_step)
        for qb in pb:
            n += 1
            tb = prga_trace(qb, sep_step)

            common_original_prefix = (
                tuple(e["z"] for e in ta[: sep_step - 1]) == original_prefix
                and tuple(e["z"] for e in tb[: sep_step - 1]) == original_prefix
            )
            still_collide_to_sep_minus_1 = all(
                ta[s]["z"] == tb[s]["z"] for s in range(sep_step - 1)
            )
            separates_at_same_step = (
                still_collide_to_sep_minus_1
                and ta[sep_step - 1]["z"] != tb[sep_step - 1]["z"]
            )
            corr_fail = correspondence_failure_at(ta, tb, sep_step)
            first_sep = first_pair_separation(ta, tb)

            counts["common_original_prefix"] += common_original_prefix
            counts["collide_prefix"] += still_collide_to_sep_minus_1
            counts["same_step"] += separates_at_same_step
            counts["corr_fail"] += corr_fail
            counts["same_step_and_corr_fail"] += separates_at_same_step and corr_fail

            writer.writerow({
                "m": m,
                "pair_id": pair_id,
                "cone_a": " ".join(map(str, cone_a)),
                "cone_b": " ".join(map(str, cone_b)),
                "candidate_a": " ".join(map(str, qa)),
                "candidate_b": " ".join(map(str, qb)),
                "both_original": int(qa == a and qb == b),
                "both_preserve_original_prefix": int(common_original_prefix),
                "pair_collides_through_original_prefix": int(still_collide_to_sep_minus_1),
                "pair_separates_at_original_step": int(separates_at_same_step),
                "correspondence_fails_at_original_step": int(corr_fail),
                "same_step_and_correspondence_failure": int(
                    separates_at_same_step and corr_fail
                ),
                "first_separation_step": "" if first_sep is None else first_sep,
            })

    summary.append({
        "m": m,
        "pair_id": pair_id,
        "test": "joint_pair",
        "cone_a": list(cone_a),
        "cone_b": list(cone_b),
        "perturbation_pairs": n,
        "both_preserve_original_prefix": counts["common_original_prefix"],
        "pair_collides_through_original_prefix": counts["collide_prefix"],
        "pair_separates_at_original_step": counts["same_step"],
        "correspondence_fails_at_original_step": counts["corr_fail"],
        "same_step_and_correspondence_failure": counts["same_step_and_corr_fail"],
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--outdir",
        default="rc4_causal_cone_perturbation_v1_output",
        help="output directory",
    )
    ap.add_argument(
        "--skip-joint",
        action="store_true",
        help="skip cross-product A/B perturbations (single-member tests still run)",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    single_csv = outdir / "single_member_perturbations.csv"
    joint_csv = outdir / "joint_pair_perturbations.csv"
    summary_json = outdir / "summary.json"
    pairs_json = outdir / "rediscovered_terminal_pairs.json"
    manifest_json = outdir / "manifest.json"

    summary = []
    pair_records = []

    t0 = time.time()

    with single_csv.open("w", newline="", encoding="utf-8") as fs:
        single_fields = [
            "m", "pair_id", "side", "cone", "candidate", "is_original",
            "exact_path_preserved", "separating_address_preserved",
            "original_prefix_preserved", "separating_output_preserved",
        ]
        sw = csv.DictWriter(fs, fieldnames=single_fields)
        sw.writeheader()

        fj = None
        jw = None
        if not args.skip_joint:
            fj = joint_csv.open("w", newline="", encoding="utf-8")
            joint_fields = [
                "m", "pair_id", "cone_a", "cone_b", "candidate_a", "candidate_b",
                "both_original", "both_preserve_original_prefix",
                "pair_collides_through_original_prefix",
                "pair_separates_at_original_step",
                "correspondence_fails_at_original_step",
                "same_step_and_correspondence_failure",
                "first_separation_step",
            ]
            jw = csv.DictWriter(fj, fieldnames=joint_fields)
            jw.writeheader()

        try:
            for m, cfg in TARGETS.items():
                print(f"[m={m}] rediscovering terminal collision classes...")
                pairs = discover_terminal_pairs(
                    m, cfg["last_prefix"], cfg["separating_step"]
                )
                if len(pairs) != cfg["expected_pairs"]:
                    raise RuntimeError(
                        f"m={m}: found {len(pairs)} terminal pairs; "
                        f"expected {cfg['expected_pairs']}"
                    )

                for pair_id, (a, b) in enumerate(pairs, 1):
                    sep = cfg["separating_step"]

                    # Derive cones fresh from realized path; do not hard-code them.
                    pa = prga_trace_with_provenance(a, sep)
                    pb = prga_trace_with_provenance(b, sep)
                    cone_a = tuple(pa[sep - 1]["output_prov"])
                    cone_b = tuple(pb[sep - 1]["output_prov"])

                    ta = prga_trace(a, sep)
                    tb = prga_trace(b, sep)
                    pair_records.append({
                        "m": m,
                        "pair_id": pair_id,
                        "last_colliding_prefix": cfg["last_prefix"],
                        "separating_step": sep,
                        "a": list(a),
                        "b": list(b),
                        "cone_a_derived": list(cone_a),
                        "cone_b_derived": list(cone_b),
                        "address_cone_a_derived": list(pa[sep - 1]["address_prov"]),
                        "address_cone_b_derived": list(pb[sep - 1]["address_prov"]),
                        "output_prefix": [e["z"] for e in ta[:sep - 1]],
                        "separating_output_a": ta[sep - 1]["z"],
                        "separating_output_b": tb[sep - 1]["z"],
                        "separating_address_a": ta[sep - 1]["k"],
                        "separating_address_b": tb[sep - 1]["k"],
                    })

                    print(
                        f"  pair {pair_id}: cones A={cone_a}, B={cone_b}; "
                        "running perturbations..."
                    )

                    run_member_perturbations(
                        m, pair_id, "A", a, b, cone_a, sep, sw, summary
                    )
                    run_member_perturbations(
                        m, pair_id, "B", b, a, cone_b, sep, sw, summary
                    )

                    if jw is not None:
                        run_joint_perturbations(
                            m, pair_id, a, b, cone_a, cone_b, sep, jw, summary
                        )
        finally:
            if fj is not None:
                fj.close()

    pairs_json.write_text(json.dumps(pair_records, indent=2), encoding="utf-8")
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    elapsed = time.time() - t0
    manifest = {
        "experiment": "rc4_terminal_collision_causal_cone_perturbation_v1",
        "elapsed_seconds": elapsed,
        "python": sys.version,
        "targets": TARGETS,
        "joint_test_skipped": args.skip_joint,
        "files": {},
        "interpretation_boundary": (
            "This tests whether retrospective pathwise cones survive "
            "interventions outside the frozen positions. Failure is a valid "
            "falsification; do not silently enlarge/refit a failed cone."
        ),
    }

    for p in [single_csv, pairs_json, summary_json]:
        manifest["files"][p.name] = sha256_file(p)
    if joint_csv.exists():
        manifest["files"][joint_csv.name] = sha256_file(joint_csv)

    manifest_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nDone in {elapsed:.3f}s")
    print(f"Results: {outdir.resolve()}")
    print(f"Manifest: {manifest_json.resolve()}")


if __name__ == "__main__":
    main()
