#
# Test 2 -- reconstruct direct/indirect split from Cycles multilayer EXR passes
# and report the indirect fraction on the character.
#
import OpenEXR, Imath, numpy as np, os, glob, json, argparse
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)


def read_exr(path):
    f = OpenEXR.InputFile(path)
    dw = f.header()["dataWindow"]
    W = dw.max.x - dw.min.x + 1; H = dw.max.y - dw.min.y + 1
    names = set(f.header()["channels"].keys())

    def rgb(layer):
        out = []
        for c in "RGB":
            n = f"ViewLayer.{layer}.{c}"
            if n not in names:
                return None
            out.append(np.frombuffer(f.channel(n, FLOAT), dtype=np.float32).reshape(H, W))
        return np.stack(out, -1)

    d = {k: rgb(k) for k in ["Combined", "DiffDir", "DiffInd", "GlossDir", "GlossInd",
                             "DiffCol", "GlossCol", "Emit", "Env"]}
    idx = np.frombuffer(f.channel("ViewLayer.IndexOB.X", FLOAT), dtype=np.float32).reshape(H, W)
    d["IndexOB"] = idx
    return d


def stats(x):
    if x.size == 0:
        return {k: float("nan") for k in ["mean", "median", "p90", "p99", "max", "n"]}
    return {"mean": float(x.mean()), "median": float(np.median(x)),
            "p90": float(np.percentile(x, 90)), "p99": float(np.percentile(x, 99)),
            "max": float(x.max()), "n": int(x.size)}


def analyse_frame(path, eps=1e-8):
    d = read_exr(path)
    diff = d["DiffCol"] * (d["DiffDir"] + d["DiffInd"])
    gloss = d["GlossCol"] * (d["GlossDir"] + d["GlossInd"])
    total = diff + gloss + d["Emit"] + d["Env"]
    indirect = d["DiffCol"] * d["DiffInd"] + d["GlossCol"] * d["GlossInd"]

    mask = d["IndexOB"] > 0.5                      # character only
    # guard against near-black pixels making the ratio explode
    tot_s = total.mean(-1); ind_s = indirect.mean(-1)
    valid = mask & (tot_s > 1e-5)

    frac = np.zeros_like(tot_s)
    frac[valid] = ind_s[valid] / tot_s[valid]

    # Combined vs reconstruction sanity check, on the character
    comb_s = d["Combined"][..., :3].mean(-1)
    if valid.sum():
        num = np.abs(comb_s[valid] - tot_s[valid])
        rel = float(num.mean() / max(tot_s[valid].mean(), eps))
        rel_med = float(np.median(num / np.maximum(tot_s[valid], eps)))
    else:
        rel = rel_med = float("nan")

    # per-channel fractions (for the coloured-bounce step)
    per_ch = {}
    for i, c in enumerate("RGB"):
        t = total[..., i]; s = indirect[..., i]
        v = mask & (t > 1e-5)
        per_ch[c] = stats(s[v] / t[v]) if v.sum() else stats(np.array([]))

    return {"frac": frac, "valid": valid, "mask": mask, "total": tot_s, "indirect": ind_s,
            "stats": stats(frac[valid]), "per_channel": per_ch,
            "combined_vs_total_rel_mean": rel, "combined_vs_total_rel_median": rel_med,
            "n_char_px": int(mask.sum()), "n_valid_px": int(valid.sum())}


def analyse_config(out_dir, label, fig_dir=None):
    exrs = sorted(glob.glob(os.path.join(out_dir, "f*.exr")))
    assert exrs, f"no EXRs in {out_dir}"
    pooled, per_frame, sanity = [], [], []
    per_ch_pool = {c: [] for c in "RGB"}
    first = None
    for p in exrs:
        r = analyse_frame(p)
        if first is None:
            first = (p, r)
        pooled.append(r["frac"][r["valid"]])
        per_frame.append({"file": os.path.basename(p), **r["stats"],
                          "combined_vs_total_rel_mean": r["combined_vs_total_rel_mean"]})
        sanity.append(r["combined_vs_total_rel_mean"])
        for c in "RGB":
            per_ch_pool[c].append(r["per_channel"][c]["mean"])
    allf = np.concatenate(pooled)
    res = {"label": label, "dir": out_dir, "n_frames": len(exrs),
           "pooled": stats(allf),
           "per_channel_mean": {c: float(np.nanmean(per_ch_pool[c])) for c in "RGB"},
           "combined_vs_total_rel_mean": float(np.nanmean(sanity)),
           "combined_vs_total_rel_max": float(np.nanmax(sanity)),
           "per_frame": per_frame}

    if fig_dir:
        os.makedirs(fig_dir, exist_ok=True)
        p, r = first
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.8))
        shown = np.where(r["valid"], r["frac"], np.nan)
        vmax = max(np.nanpercentile(shown, 99), 1e-3)
        im = ax[0].imshow(shown, cmap="magma", vmin=0, vmax=vmax)
        ax[0].set_title(f"{label}\nindirect fraction (character)"); ax[0].axis("off")
        fig.colorbar(im, ax=ax[0], fraction=0.046)
        ax[1].hist(allf, bins=100, color="tab:purple", alpha=.85)
        for q, c in [(50, "orange"), (90, "red"), (99, "darkred")]:
            v = np.percentile(allf, q); ax[1].axvline(v, color=c, lw=1.2, label=f"p{q}={100*v:.1f}%")
        ax[1].set_xlabel("indirect fraction"); ax[1].set_ylabel("count"); ax[1].legend()
        ax[1].set_title(f"pooled over {len(exrs)} frames (n={allf.size})")
        fig.tight_layout(); fig.savefig(os.path.join(fig_dir, f"{label}.png"), dpi=140)
        plt.close(fig)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True, help="label=path pairs")
    ap.add_argument("--fig_dir", default=None)
    ap.add_argument("--json_out", default=None)
    a = ap.parse_args()
    out = []
    for spec in a.dirs:
        label, path = spec.split("=", 1)
        r = analyse_config(path, label, a.fig_dir)
        out.append(r)
        s = r["pooled"]
        print(f"{label:18s} n_fr={r['n_frames']:2d} n_px={s['n']:8d}  "
              f"mean {100*s['mean']:6.2f}%  median {100*s['median']:6.2f}%  "
              f"p90 {100*s['p90']:6.2f}%  p99 {100*s['p99']:6.2f}%  max {100*s['max']:6.2f}%   "
              f"|Comb-total|/total {100*r['combined_vs_total_rel_mean']:.3f}%")
    if a.json_out:
        json.dump(out, open(a.json_out, "w"), indent=2)
