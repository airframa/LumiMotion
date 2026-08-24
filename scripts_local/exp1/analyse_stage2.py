#
# Experiment 1 -- Stage 2 adjudication + Stage 3 inputs.
#
# WRITTEN BEFORE THE COVERAGE ARRAYS EXISTED. The adjudication is therefore fixed
# pre-data, not chosen after seeing numbers.
#
# Order of operations is deliberate and enforced by the code:
#   1. addendum 2 sec B interpretation rule. If it trips, the script REFUSES to
#      print any P1/P2/P3 verdict and exits non-zero. "Do not adjudicate P1/P2 and
#      then caveat them."
#   2. addendum 1 sec B P1 ceiling, printed BEFORE the P1 verdict.
#   3. P1/P2/P3 against amendment 2 sec 4, thresholds untouched.
#   4. committed JSON of every adjudication input (addendum 1 sec D.1).
#
# DECILE READING, stated because it is an interpretive choice:
#   amendment 2 sec 4 defines deciles on C_rigid; sec 3 restricts P1/P2 to
#   C_rigid > 0 and P3 to C_rigid == 0. Deciles for P1/P2 are therefore taken over
#   the C_rigid > 0 subset of the stratum. Taking them over the whole stratum would
#   put every C_rigid == 0 Gaussian in the bottom decile and then remove them all
#   again, leaving it empty or unrepresentative. The alternative is computed and
#   reported as a sensitivity, and it adjudicates nothing.
#
#   python scripts_local/exp1/analyse_stage2.py \
#       --npz docs/exp1_assets/coverage_jumpingjacks150_v5_spec32_r2_mlp.npz \
#             docs/exp1_assets/coverage_standup150_v5_spec32_r2_mlp.npz \
#       --json docs/exp1_assets/exp1_adjudication.json
#
import os, sys, json, argparse
import numpy as np

P1_THRESHOLD = 1.5      # amendment 2 sec 4
P2_THRESHOLD = 1.3
P3_THRESHOLD = 2.0
P3_RESCUE_MIN = 3       # C_seq >= 3 counts as rescued
RULE_OVERFLOW_PP = 5.0  # addendum 2 sec B interpretation rule
RULE_FRAG_PCT = 1.0
CEILING_CAMS = 135      # addendum 1 sec B


def unpack(a, C):
    return np.unpackbits(a, axis=1)[:, :C].astype(bool)


def decile_index(v):
    """Decile membership 0..9 by C_rigid rank. Ties are frequent (integer counts),
    so boundaries are quantiles and bins are NOT equal-sized; counts are reported."""
    edges = np.percentile(v, np.arange(10, 100, 10))
    return np.digitize(v, edges, right=False), edges


def med(x):
    return float(np.median(x)) if len(x) else float("nan")


def exposure_block(xings, frag, gated, idx, C):
    """Exposure for a per-Gaussian index set: overflow + fragility."""
    x = xings[idx]                       # (n, C) crossing counts
    n_rays = x.size
    out = {
        "n_gaussians": int(len(idx)), "n_rays": int(n_rays),
        "overflow_frac_pct": float(100.0 * (x > 16).mean()) if n_rays else float("nan"),
        "xing_median": float(np.median(x)) if n_rays else float("nan"),
        "xing_p90": float(np.percentile(x, 90)) if n_rays else float("nan"),
        "xing_p99": float(np.percentile(x, 99)) if n_rays else float("nan"),
        "xing_max": int(x.max()) if n_rays else 0,
    }
    g = int(gated[idx].sum())
    out["gated_cells"] = g
    for k, dl in enumerate((1e-3, 1e-2, 5e-2)):
        f = int(frag[idx, k].sum())
        out[f"frag_lt_{dl:g}_count"] = f
        out[f"frag_lt_{dl:g}_pct_of_gated"] = float(100.0 * f / g) if g else float("nan")
    return out


def analyse(path):
    d = np.load(path)
    C = int(d["n_cams"])
    params = json.loads(str(d["params"]))
    scene = os.path.basename(path).replace("coverage_", "").replace(".npz", "")
    cr = d["n_views_rigid"].astype(np.int64)
    cs = d["n_views_seq"].astype(np.int64)
    bf = d["binary_feature"]
    dyn = d["dynamic"].astype(bool)
    R = {"scene": scene, "params": params, "N": int(len(cr)), "n_cams": C}

    # ---------------------------------------------------------------- exposure
    xr, xs = d["xings_rigid"], d["xings_seq"]
    fr, fs = d["frag_rigid"], d["frag_seq"]
    gr, gs = d["gated_rigid"], d["gated_seq"]

    strata = {"dynamic": dyn, "static": ~dyn, "pooled": np.ones_like(dyn)}
    R["exposure"] = {}
    R["deciles"] = {}
    R["counts"] = {}

    for sname, smask in strata.items():
        pos = smask & (cr > 0)
        zero = smask & (cr == 0)
        R["counts"][sname] = {"n": int(smask.sum()),
                              "n_C_rigid_gt0": int(pos.sum()),
                              "n_C_rigid_eq0": int(zero.sum())}
        if pos.sum() < 10:
            continue
        dec, edges = decile_index(cr[pos])
        pos_idx = np.flatnonzero(pos)
        R["deciles"][sname] = {"edges": [float(e) for e in edges], "bins": []}
        R["exposure"][sname] = []
        for k in range(10):
            sel = pos_idx[dec == k]
            ratio = cs[sel] / cr[sel]
            R["deciles"][sname]["bins"].append({
                "decile": k, "count": int(len(sel)),
                "C_rigid_min": int(cr[sel].min()) if len(sel) else None,
                "C_rigid_max": int(cr[sel].max()) if len(sel) else None,
                "C_rigid_median": med(cr[sel]),
                "C_seq_median": med(cs[sel]),
                "ratio_median": med(ratio),
            })
            er = exposure_block(xr, fr, gr, sel, C)
            es = exposure_block(xs, fs, gs, sel, C)
            R["exposure"][sname].append({
                "decile": k,
                "rigid": er, "seq": es,
                "overflow_diff_pp": float(es["overflow_frac_pct"] - er["overflow_frac_pct"]),
                "frag_lt_1e-2_pct_max": float(max(er["frag_lt_0.01_pct_of_gated"],
                                                  es["frag_lt_0.01_pct_of_gated"])),
            })

    # --------------------------------- addendum 2 sec B interpretation rule
    b = R["exposure"]["dynamic"][0]
    R["interpretation_rule"] = {
        "stratum": "dynamic", "decile": 0,
        "overflow_diff_pp": b["overflow_diff_pp"],
        "overflow_diff_bound_pp": RULE_OVERFLOW_PP,
        "frag_lt_1e-2_pct": b["frag_lt_1e-2_pct_max"],
        "frag_bound_pct": RULE_FRAG_PCT,
        "passes": bool(abs(b["overflow_diff_pp"]) < RULE_OVERFLOW_PP
                       and b["frag_lt_1e-2_pct_max"] < RULE_FRAG_PCT),
    }

    # ------------------------------------- addendum 1 sec B: the P1 ceiling
    R["p1_ceiling"] = {}
    for sname in ("dynamic", "pooled"):
        if sname not in R["deciles"]:
            continue
        bot = R["deciles"][sname]["bins"][0]
        m = bot["C_rigid_median"]
        ceil = CEILING_CAMS / m if m and m > 0 else float("inf")
        R["p1_ceiling"][sname] = {
            "bottom_decile_boundary": R["deciles"][sname]["edges"][0],
            "bottom_decile_C_rigid_median": m,
            "implied_ceiling": ceil,
            "ceiling_below_P1_threshold": bool(ceil < P1_THRESHOLD),
        }

    # ------------------------------------------------------- P1, P2, P3
    R["predictions"] = {}
    for sname in ("dynamic", "pooled"):
        if sname not in R["deciles"]:
            continue
        bins = R["deciles"][sname]["bins"]
        p1 = bins[0]["ratio_median"]
        gain_bot, gain_top = bins[0]["ratio_median"], bins[9]["ratio_median"]
        p2 = gain_bot / gain_top if gain_top else float("nan")
        R["predictions"][sname] = {
            "P1_median_ratio_bottom_decile": p1,
            "P1_threshold": P1_THRESHOLD,
            "P1_pass": bool(p1 > P1_THRESHOLD),
            "P2_bottom_over_top": p2,
            "P2_threshold": P2_THRESHOLD,
            "P2_pass": bool(p2 >= P2_THRESHOLD),
            "gain_bottom": gain_bot, "gain_top": gain_top,
        }

    # P3: rescue rate among C_rigid == 0
    def rescue(mask):
        z = mask & (cr == 0)
        n = int(z.sum())
        r = int((cs[z] >= P3_RESCUE_MIN).sum())
        return {"n_C_rigid_eq0": n, "n_rescued": r,
                "rate": float(r / n) if n else float("nan")}

    p3 = {}
    for cname, cmask in (("primary_lt0.5", bf < 0.5), ("secondary_lt0.01", bf < 0.01)):
        dd, ss = rescue(dyn), rescue(cmask)
        ratio = dd["rate"] / ss["rate"] if ss["rate"] and ss["rate"] > 0 else float("inf")
        p3[cname] = {"dynamic": dd, "static_control": ss, "rate_ratio": ratio,
                     "threshold": P3_THRESHOLD, "pass": bool(ratio >= P3_THRESHOLD)}
    R["predictions"]["P3"] = p3

    # sensitivity: deciles over the whole stratum, adjudicates nothing
    sens = {}
    for sname, smask in (("dynamic", dyn), ("pooled", np.ones_like(dyn))):
        idx = np.flatnonzero(smask)
        dec, edges = decile_index(cr[idx])
        sel = idx[dec == 0]
        keep = sel[cr[sel] > 0]
        sens[sname] = {"bottom_decile_n": int(len(sel)),
                       "bottom_decile_n_C_rigid_gt0": int(len(keep)),
                       "ratio_median": med(cs[keep] / cr[keep]) if len(keep) else None}
    R["sensitivity_deciles_over_full_stratum"] = sens
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", nargs="+", required=True)
    ap.add_argument("--json", default="docs/exp1_assets/exp1_adjudication.json")
    a = ap.parse_args()

    out = {}
    stop = False
    for p in a.npz:
        R = analyse(p)
        out[R["scene"]] = R
        s = R["scene"]
        ir = R["interpretation_rule"]
        print(f"\n{'='*72}\n{s}\n{'='*72}")
        print(f"N={R['N']}  cameras={R['n_cams']}")
        print(f"\n-- addendum 2 sec B interpretation rule (dynamic stratum, bottom decile) --")
        print(f"   between-arm overflow difference : {ir['overflow_diff_pp']:+.3f} pp "
              f"(bound {RULE_OVERFLOW_PP} pp)")
        print(f"   |vis-0.5| < 1e-2, worst arm     : {ir['frag_lt_1e-2_pct']:.4f} % of gated "
              f"(bound {RULE_FRAG_PCT} %)")
        print(f"   -> {'PASS, verdict stands as measured' if ir['passes'] else 'EXCEEDED -- STOP'}")
        if not ir["passes"]:
            stop = True
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(f"\nwrote {a.json}")

    if stop:
        print("\n*** addendum 2 sec B interpretation rule EXCEEDED. "
              "No verdict printed. Stop and report. ***")
        sys.exit(2)

    for s, R in out.items():
        print(f"\n{'='*72}\n{s} -- verdicts\n{'='*72}")
        for sname in ("dynamic", "pooled"):
            if sname not in R["predictions"]:
                continue
            c = R["p1_ceiling"][sname]; P = R["predictions"][sname]
            tag = "PRIMARY" if sname == "dynamic" else "secondary (no thresholds)"
            print(f"\n[{sname}] {tag}")
            print(f"  C_rigid = 0 excluded from P1/P2 : "
                  f"{R['counts'][sname]['n_C_rigid_eq0']} of {R['counts'][sname]['n']}")
            print(f"  -- P1 ceiling (addendum 1 sec B), BEFORE the verdict --")
            print(f"     bottom-decile boundary {c['bottom_decile_boundary']:.1f}, "
                  f"median C_rigid {c['bottom_decile_C_rigid_median']:.1f}")
            print(f"     implied ceiling 135/median = {c['implied_ceiling']:.3f}x; "
                  f"below 1.5x? {c['ceiling_below_P1_threshold']}")
            print(f"  P1  median C_seq/C_rigid bottom decile = "
                  f"{P['P1_median_ratio_bottom_decile']:.4f}  (> 1.5) -> "
                  f"{'PASS' if P['P1_pass'] else 'FAIL'}")
            print(f"  P2  bottom/top gain = {P['P2_bottom_over_top']:.4f}  (>= 1.3) -> "
                  f"{'PASS' if P['P2_pass'] else 'FAIL'}")
        for cname, v in R["predictions"]["P3"].items():
            print(f"  P3 [{cname}] dynamic {v['dynamic']['n_rescued']}/"
                  f"{v['dynamic']['n_C_rigid_eq0']} = {v['dynamic']['rate']:.5f}, "
                  f"static {v['static_control']['n_rescued']}/"
                  f"{v['static_control']['n_C_rigid_eq0']} = {v['static_control']['rate']:.5f}, "
                  f"ratio {v['rate_ratio']:.3f} (>= 2) -> "
                  f"{'PASS' if v['pass'] else 'FAIL'}"
                  + ("   [adjudicating]" if cname.startswith("primary") else "   [declared secondary]"))
