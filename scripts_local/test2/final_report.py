#
# Test 2 -- final ladder table, threshold evaluation, implied render error.
#
import numpy as np, glob, sys, json, os
sys.path.insert(0, '.')
from analyse import read_exr
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

STEPS = [("step1", "1. as shipped, diffuse_bounces=1"),
         ("step2", "2. same scene, diffuse_bounces=8"),
         ("step3", "3. corner (2 grey walls)"),
         ("step4", "4. corner + red wall (albedo 0.8)"),
         ("step5", "5. draped cloth (folds)"),
         ("step6", "6. interior room (open one side)")]

# Test 1 rotation-dependent relative error in the frozen stored radiance
RELERR = {"jumpingjacks": {"median": .043, "p90": .088, "p99": .134},
          "standup":      {"median": .094, "p90": .243, "p99": .410}}
FLOOR_LO, FLOOR_HI = .024, .132     # Probe D reconstruction noise floor
THRESHOLD = .25


def stat(a):
    return dict(mean=float(a.mean()), median=float(np.median(a)),
                p90=float(np.percentile(a, 90)), p99=float(np.percentile(a, 99)),
                max=float(a.max()), n=int(a.size))


def measure(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, "f*.exr"))):
        e = read_exr(p)
        di = e["DiffCol"] * e["DiffInd"]; gi = e["GlossCol"] * e["GlossInd"]
        tot = e["DiffCol"] * (e["DiffDir"] + e["DiffInd"]) + \
              e["GlossCol"] * (e["GlossDir"] + e["GlossInd"]) + e["Emit"] + e["Env"]
        m = e["IndexOB"] > 0.5
        ts = tot.mean(-1); v = m & (ts > 1e-5)
        if v.sum() < 200:            # frame where the subject is essentially not visible
            continue
        comb = e["Combined"][..., :3].mean(-1)
        out.setdefault("all", []).append((di + gi).mean(-1)[v] / ts[v])
        out.setdefault("dif", []).append(di.mean(-1)[v] / ts[v])
        out.setdefault("san", []).append(float(np.abs(comb[v] - ts[v]).mean() / ts[v].mean()))
        out.setdefault("npx", []).append(int(v.sum()))
        for i, c in enumerate("RGB"):
            vv = m & (tot[..., i] > 1e-5)
            out.setdefault(f"ch{c}", []).append(float(((di + gi)[..., i][vv] / tot[..., i][vv]).mean()))
        out.setdefault("first", p)
    return out


rows = []
for key, label in STEPS:
    d = f"out/{key}"
    if not glob.glob(os.path.join(d, "f*.exr")):
        print(f"!! missing {d}"); continue
    m = measure(d)
    A = np.concatenate(m["all"]); D = np.concatenate(m["dif"])
    rows.append(dict(key=key, label=label, all=stat(A), dif=stat(D),
                     sanity=float(np.mean(m["san"])), sanity_max=float(np.max(m["san"])),
                     nframes=len(m["all"]), npx=int(np.mean(m["npx"])),
                     ch={c: float(np.mean(m[f"ch{c}"])) for c in "RGB"},
                     first=m["first"]))

json.dump(rows, open("out/final.json", "w"), indent=2)

W = 40
print("=" * 118)
print("LADDER  (Blender/Cycles ground truth; 'all' = diff+gloss indirect, 'diffuse-only' = LumiMotion-comparable)")
print("=" * 118)
print(f"{'configuration':{W}s} {'frames':>6s} {'mean':>8s} {'median':>8s} {'p90':>8s} {'p99':>8s} | {'dif mean':>8s} {'dif p90':>8s}")
print("-" * 118)
for r in rows:
    a, d = r["all"], r["dif"]
    print(f"{r['label']:{W}s} {r['nframes']:6d} {100*a['mean']:7.2f}% {100*a['median']:7.2f}% "
          f"{100*a['p90']:7.2f}% {100*a['p99']:7.2f}% | {100*d['mean']:7.2f}% {100*d['p90']:7.2f}%")
print("-" * 118)
print(f"{'sanity |Combined-total|/total:':{W}s}", " ".join(f"{r['key']}={100*r['sanity']:.3f}%" for r in rows))

print()
print("=" * 118)
print(f"THRESHOLD TEST  (pre-committed: {100*THRESHOLD:.0f}% indirect fraction)")
print("=" * 118)
print(f"{'configuration':{W}s} {'mean':>8s} {'vs 25%':>9s} {'p90':>8s} {'vs 25%':>9s}")
print("-" * 118)
for r in rows:
    a = r["all"]
    print(f"{r['label']:{W}s} {100*a['mean']:7.2f}% {'CLEARS' if a['mean']>=THRESHOLD else 'below':>9s} "
          f"{100*a['p90']:7.2f}% {'CLEARS' if a['p90']>=THRESHOLD else 'below':>9s}")

print()
print("=" * 118)
print("IMPLIED RENDER ERROR = indirect fraction x rotation-dependent relative error")
print(f"   (noise floor {100*FLOOR_LO:.1f}-{100*FLOOR_HI:.1f}%;  '*' = exceeds the LOW end, '**' = exceeds the HIGH end)")
print("=" * 118)
for scene in ["jumpingjacks", "standup"]:
    print(f"\n-- rotation error profile: {scene} "
          f"(median {100*RELERR[scene]['median']:.1f}%, p90 {100*RELERR[scene]['p90']:.1f}%, p99 {100*RELERR[scene]['p99']:.1f}%)")
    print(f"{'configuration':{W}s} {'mean x med':>11s} {'mean x p90':>11s} {'p90 x p90':>11s} {'p90 x p99':>11s}")
    for r in rows:
        a = r["all"]
        vals = [a["mean"] * RELERR[scene]["median"], a["mean"] * RELERR[scene]["p90"],
                a["p90"] * RELERR[scene]["p90"], a["p90"] * RELERR[scene]["p99"]]
        cells = []
        for v in vals:
            f = "**" if v >= FLOOR_HI else ("*" if v >= FLOOR_LO else "")
            cells.append(f"{100*v:8.2f}%{f:<2s}")
        print(f"{r['label']:{W}s} " + " ".join(cells))

print()
print("per-channel indirect fraction (mean), for the coloured-bounce step:")
print(f"{'configuration':{W}s} {'R':>8s} {'G':>8s} {'B':>8s}")
for r in rows:
    print(f"{r['label']:{W}s} " + " ".join(f"{100*r['ch'][c]:7.2f}%" for c in "RGB"))

# ---- figures ----
os.makedirs("figs", exist_ok=True)
fig, axes = plt.subplots(2, len(rows), figsize=(3.4 * len(rows), 7))
if len(rows) == 1: axes = axes.reshape(2, 1)
for j, r in enumerate(rows):
    e = read_exr(r["first"])
    di = e["DiffCol"] * e["DiffInd"]; gi = e["GlossCol"] * e["GlossInd"]
    tot = e["DiffCol"] * (e["DiffDir"] + e["DiffInd"]) + \
          e["GlossCol"] * (e["GlossDir"] + e["GlossInd"]) + e["Emit"] + e["Env"]
    m = e["IndexOB"] > 0.5; ts = tot.mean(-1); v = m & (ts > 1e-5)
    axes[0, j].imshow(np.clip(np.clip(e["Combined"][..., :3], 0, None) ** (1 / 2.2), 0, 1))
    axes[0, j].set_title(r["label"], fontsize=8); axes[0, j].axis("off")
    fr = np.where(v, (di + gi).mean(-1) / np.maximum(ts, 1e-9), np.nan)
    im = axes[1, j].imshow(fr, cmap="magma", vmin=0, vmax=1)
    axes[1, j].set_title(f"mean {100*r['all']['mean']:.1f}%  p90 {100*r['all']['p90']:.1f}%", fontsize=8)
    axes[1, j].axis("off")
fig.colorbar(im, ax=axes[1, :].tolist(), fraction=0.02, label="indirect fraction")
fig.suptitle("Test 2 ladder: beauty (top) and indirect fraction on the subject (bottom)")
fig.savefig("figs/ladder.png", dpi=130, bbox_inches="tight")
print("\nwrote figs/ladder.png and out/final.json")
