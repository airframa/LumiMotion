#
# Experiment 1 -- addendum 3 sec 3: gate (b) restricted to the adjudicating population.
#
# The addendum 2 sec B overflow clause fired. That clause is a PROXY for "could the
# tracer's anyhit-buffer defect bias coverage in the bottom decile?". This measures
# that directly instead, using the same brute force, unchanged, including the
# d_g^2 < 1e-6 clamp rejection.
#
# SAMPLE: 500 Gaussians, seed 0, from the bottom C_rigid decile of the DYNAMIC
# stratum, deciles taken over the C_rigid > 0 subset per exp1_stage2_plan.md sec 2.
#
# ARMS. Both are reproduced exactly as the Stage 2 run computed them:
#   rigid : d_xyz = d_rotation = d_scaling = 0, BVH built once, all 135 cameras.
#   seq   : DIAGONAL -- frame j uses the deformation at cams[j].fid AND camera j.
#           BVH built on frame 0 then update_bvh per frame, per train_stage2.py:155-159.
#   Getting this wrong (one fixed deformation across all cameras, as the earlier
#   single-frame gate did) would measure a configuration Stage 2 never evaluated.
#
# QUARANTINE (addendum 3 sec 0): this script never reads n_views_seq for any purpose
# other than an exact-equality consistency check against its own recomputation, and
# never forms C_seq/C_rigid. No P1/P2/P3 quantity is computed, printed or returned.
#
#   python scripts_local/exp1/gate_bottom_decile.py \
#       --model_path ... --source_path ... --deform_type mlp --iteration 55000 \
#       --npz docs/exp1_assets/coverage_<scene>.npz
#
import os, sys, json, argparse
import numpy as np
import torch

sys.path.insert(0, os.getcwd())
from scene import Scene, GaussianModel, DeformModel
from arguments import ModelParams, PipelineParams, get_combined_args
from utils.general_utils import safe_state
sys.path.insert(0, os.path.join(os.getcwd(), "scripts_local/exp1"))
from gate_coverage import read_ply_raw, quat_to_R, ALPHA_MIN, LIGHT_T_MIN, THR, \
                          TRANSMITTANCE_MIN, T_SCENE_MAX
from coverage_seq import coverage_frame, deformed_geometry

N_SAMPLE, SEED, CHUNK = 500, 0, 512
FRAG_DELTAS = (1e-3, 1e-2, 5e-2)


def brute_vis(mu_np, opa_raw, sca_raw, rot_raw, d_xyz, d_rot, d_sca, sel, cam):
    """Independent visibility for `sel` Gaussians against one camera.

    Same brute force as gate_coverage.py: activations applied here, rotation
    matrices built here, alpha semantics transcribed from
    gaussiantrace_forward.cu:55-105, and the clamp rejection (d_g^2 < 1e-6) kept.
    """
    xyz = mu_np + d_xyz
    o = 1.0 / (1.0 + np.exp(-opa_raw))
    s = np.exp(sca_raw) + d_sca
    R = quat_to_R(rot_raw + d_rot)
    n = R[:, :, 2]; n = n / np.linalg.norm(n, axis=1, keepdims=True)
    eps = 1e-7
    inv = 1.0 / (s + eps * (s == 0))
    ru = R[:, :, 0] * inv[:, 0:1]
    rv = R[:, :, 1] * inv[:, 1:2]

    dev = "cuda"
    mu = torch.from_numpy(xyz).to(dev); nn = torch.from_numpy(n).to(dev)
    ruT = torch.from_numpy(ru).to(dev); rvT = torch.from_numpy(rv).to(dev)
    oo = torch.from_numpy(o[:, 0]).to(dev)
    n_mu = (nn * mu).sum(1); ru_mu = (ruT * mu).sum(1); rv_mu = (rvT * mu).sum(1)

    mu_s = mu[torch.from_numpy(sel).to(dev)]
    v = cam.camera_center.double() - mu_s
    D = v / v.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    O = mu_s + LIGHT_T_MIN * D

    out = torch.zeros(O.shape[0], dtype=torch.float64, device=dev)
    for a in range(0, O.shape[0], CHUNK):
        b = min(a + CHUNK, O.shape[0])
        Oc, Dc = O[a:b], D[a:b]
        o_g = Oc @ nn.T - n_mu[None, :]
        d_g = Dc @ nn.T
        dd = -o_g * d_g / torch.clamp(d_g * d_g, min=1e-6)
        pu = (Oc @ ruT.T) + dd * (Dc @ ruT.T) - ru_mu[None, :]
        pv = (Oc @ rvT.T) + dd * (Dc @ rvT.T) - rv_mu[None, :]
        al = torch.clamp(oo[None, :] * torch.exp(-0.5 * (pu * pu + pv * pv)), max=0.99)
        keep = (al >= ALPHA_MIN) & (dd > 0) & (dd < T_SCENE_MAX) & ((d_g * d_g) >= 1e-6)
        out[a:b] = torch.where(keep, 1.0 - al, torch.ones_like(al)).prod(dim=1)
    out = torch.where((1.0 - out) < 1 - TRANSMITTANCE_MIN, out, torch.zeros_like(out))

    # infr / face for the same cells, computed here
    h = torch.cat([mu_s, torch.ones_like(mu_s[:, :1])], -1)
    clip = h @ cam.full_proj_transform.double()
    w = clip[:, 3:4].clamp_min(1e-8); ndc = clip[:, :3] / w
    infr = (clip[:, 3] > 0) & (ndc[:, 0].abs() < 1) & (ndc[:, 1].abs() < 1)
    face = (nn[torch.from_numpy(sel).to(dev)] * D).sum(-1) > 0
    return (out > THR) & infr & face


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    model = ModelParams(ap, sentinel=True); pipeline = PipelineParams(ap)
    ap.add_argument("--iteration", default=55000, type=int)
    ap.add_argument("--npz", required=True)
    ap.add_argument("--out_json", default="")
    ap.add_argument("--quiet", action="store_true")
    args = get_combined_args(ap); safe_state(False)
    dataset, pipe = model.extract(args), pipeline.extract(args)
    assert "/projects/LumiMotion/" not in os.path.abspath(dataset.source_path)

    d = np.load(args.npz)
    cr = d["n_views_rigid"].astype(np.int64)
    dyn = d["dynamic"].astype(bool)
    C = int(d["n_cams"])

    # ---- bottom C_rigid decile of the dynamic stratum, C_rigid > 0
    pool = np.flatnonzero(dyn & (cr > 0))
    edges = np.percentile(cr[pool], np.arange(10, 100, 10))
    dec = np.digitize(cr[pool], edges, right=False)
    bottom = pool[dec == 0]
    med_cr = float(np.median(cr[bottom]))
    rng = np.random.default_rng(SEED)
    sel = np.sort(rng.choice(bottom, size=min(N_SAMPLE, len(bottom)), replace=False))

    print(f"[{os.path.basename(dataset.model_path)}]")
    print(f"  dynamic & C_rigid>0 : {len(pool)}   bottom decile : {len(bottom)}")
    print(f"  bottom-decile C_rigid: boundary {edges[0]:.1f}, "
          f"min {cr[bottom].min()}, median {med_cr:.1f}, max {cr[bottom].max()}")
    print(f"  sample: {len(sel)} Gaussians, seed {SEED}")

    with torch.no_grad():
        g = GaussianModel(dataset.sh_degree,
                          no_binary_separation=dataset.no_binary_separation,
                          fea_dim=dataset.hyper_dim)
        scene = Scene(dataset, g, load_iteration=args.iteration, shuffle=False)
        cams = scene.getTrainCameras(); N = g.get_xyz.shape[0]
        assert len(cams) == C and N == len(cr)
        deform = DeformModel(deform_type=dataset.deform_type,
                             is_blender=dataset.is_blender,
                             hyper_dim=dataset.hyper_dim, pred_color=dataset.pred_color)
        assert deform.load_weights(dataset.model_path, iteration=args.iteration)
        bfeat = g.get_binary_feature()
        z3 = torch.zeros_like(g.get_xyz)
        z4 = torch.zeros((N, 4), device="cuda"); z2 = torch.zeros((N, 2), device="cuda")

    ply = os.path.join(dataset.model_path, "point_cloud",
                       f"iteration_{args.iteration}", "point_cloud.ply")
    xyz_r, opa_r, sca_r, rot_r = read_ply_raw(ply)
    sel_t = torch.from_numpy(sel).cuda()
    Z3 = np.zeros_like(xyz_r); Z4 = np.zeros((N, 4)); Z2 = np.zeros((N, 2))

    results = {}
    for arm in ("rigid", "seq"):
        port = torch.zeros(len(sel), C, dtype=torch.bool)
        brut = torch.zeros(len(sel), C, dtype=torch.bool)
        built = False
        with torch.no_grad():
            for j, cam in enumerate(cams):
                if arm == "rigid":
                    dx, dr_, ds_ = z3, z4, z2
                    nx, nr, ns = Z3, Z4, Z2
                else:
                    t = cam.fid.to("cuda").view(1, 1).expand(N, 1).contiguous()
                    dv = deform.step(g.get_xyz.detach(), t, feature=bfeat)
                    dx, dr_, ds_ = dv["d_xyz"], dv["d_rotation"], dv["d_scaling"]
                    nx = dx.double().cpu().numpy()
                    nr = dr_.double().cpu().numpy()
                    ns = ds_.double().cpu().numpy()
                if not built:
                    g.build_bvh(d_rotation=dr_, d_xyz=dx, d_scaling=ds_); built = True
                else:
                    g.update_bvh(d_rotation=dr_, d_xyz=dx, d_scaling=ds_)
                xyz, scales, rotation, opacity = deformed_geometry(g, dx, dr_, ds_)
                vis, infr, face, _ = coverage_frame(g, cam, xyz, scales, rotation,
                                                    opacity, pipe.light_t_min, 1.0)
                port[:, j] = ((vis > THR) & infr & face)[sel_t].cpu()
                brut[:, j] = brute_vis(xyz_r, opa_r, sca_r, rot_r, nx, nr, ns,
                                       sel, cam).cpu()
                if arm == "rigid" and built and j == 0:
                    pass
            # the rigid arm has constant geometry; rebuild once is equivalent, but
            # update_bvh per frame is what Stage 2 did, so it is what is reproduced
        nv_port = port.sum(1).numpy().astype(np.int64)
        nv_brut = brut.sum(1).numpy().astype(np.int64)
        dis = int((port != brut).sum())
        b = float((nv_port - nv_brut).mean())
        results[arm] = dict(nv_port=nv_port, nv_brut=nv_brut, dis=dis, b=b,
                            cells=int(port.numel()))
        # consistency: the recomputed port must equal what Stage 2 stored
        stored = d[f"n_views_{arm}"][sel].astype(np.int64)
        results[arm]["reproduces_stage2"] = int((stored == nv_port).sum())
        print(f"  [{arm}] reproduces Stage 2 n_views: "
              f"{results[arm]['reproduces_stage2']}/{len(sel)}")

    # ---- exposure for the SAME population, read from the Stage 2 full-population dump
    expo = {}
    for arm in ("rigid", "seq"):
        x_dec = d[f"xings_{arm}"][bottom]; x_sam = d[f"xings_{arm}"][sel]
        fr = d[f"frag_{arm}"]; ga = d[f"gated_{arm}"]
        e = dict(
            overflow_pct_decile=float(100.0 * (x_dec > 16).mean()),
            overflow_pct_sample=float(100.0 * (x_sam > 16).mean()),
            xing_median=float(np.median(x_dec)), xing_p90=float(np.percentile(x_dec, 90)),
            xing_p99=float(np.percentile(x_dec, 99)), xing_max=int(x_dec.max()),
        )
        gsum = int(ga[bottom].sum())
        e["gated_cells_decile"] = gsum
        for k, dl in enumerate(FRAG_DELTAS):
            e[f"frag_{dl:g}_pct"] = float(100.0 * fr[bottom, k].sum() / gsum) if gsum else float("nan")
        expo[arm] = e

    db = results["seq"]["b"] - results["rigid"]["b"]
    ratio = abs(db) / med_cr if med_cr > 0 else float("inf")
    proceed = ratio < 0.02
    sat = (expo["rigid"]["overflow_pct_decile"] > 90.0 and
           expo["seq"]["overflow_pct_decile"] > 90.0)

    print(f"\n  --- addendum 3 sec 3 quantities, bottom decile of the dynamic stratum ---")
    print(f"  (1) mask disagreement rate")
    for arm in ("rigid", "seq"):
        r = results[arm]
        print(f"        {arm:6s}: {r['dis']} / {r['cells']} cells "
              f"({100.0*r['dis']/r['cells']:.5f} %)")
    print(f"  (2) mean per-Gaussian coverage bias b = mean(n_views_port - n_views_brute), cameras")
    for arm in ("rigid", "seq"):
        print(f"        b_{arm:6s} = {results[arm]['b']:+.6f}")
    print(f"  (3) delta_b = b_seq - b_rigid = {db:+.6f} cameras")
    print(f"        median(C_rigid | bottom decile) = {med_cr:.1f}")
    print(f"        |delta_b| / median = {ratio:.6f}")
    print(f"  (4) overflow LEVELS (upper bound; circumscribed radius)")
    for arm in ("rigid", "seq"):
        e = expo[arm]
        print(f"        {arm:6s}: decile {e['overflow_pct_decile']:.3f} %  "
              f"(sample {e['overflow_pct_sample']:.3f} %)   crossings median "
              f"{e['xing_median']:.0f} p90 {e['xing_p90']:.0f} p99 {e['xing_p99']:.0f} "
              f"max {e['xing_max']}")
    print(f"        between-arm difference = "
          f"{expo['seq']['overflow_pct_decile'] - expo['rigid']['overflow_pct_decile']:+.3f} pp")
    print(f"        saturated (both arms > 90 %)? {sat}")
    print(f"  (5) fragility, fraction of gated cells in the bottom decile")
    for arm in ("rigid", "seq"):
        e = expo[arm]
        print(f"        {arm:6s}: <1e-3 {e['frag_0.001_pct']:.4f} %   "
              f"<1e-2 {e['frag_0.01_pct']:.4f} %   <5e-2 {e['frag_0.05_pct']:.4f} %")
    print(f"\n  DECISION RULE (addendum 3 sec 3): |delta_b| / median(C_rigid) < 0.02")
    print(f"    {ratio:.6f} {'<' if proceed else '>='} 0.02  ->  "
          f"{'PROCEED' if proceed else 'STOP'}")

    if args.out_json:
        out = dict(scene=os.path.basename(dataset.model_path),
                   n_dynamic_pos=int(len(pool)), n_bottom_decile=int(len(bottom)),
                   bottom_decile_boundary=float(edges[0]),
                   bottom_decile_C_rigid_median=med_cr,
                   bottom_decile_C_rigid_min=int(cr[bottom].min()),
                   bottom_decile_C_rigid_max=int(cr[bottom].max()),
                   n_sample=int(len(sel)), seed=SEED,
                   disagreements={a: results[a]["dis"] for a in results},
                   cells={a: results[a]["cells"] for a in results},
                   reproduces_stage2={a: results[a]["reproduces_stage2"] for a in results},
                   b={a: results[a]["b"] for a in results},
                   delta_b=db, ratio=ratio, proceed=bool(proceed),
                   overflow_saturated=bool(sat), exposure=expo)
        os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
        with open(args.out_json, "w") as f:
            json.dump(out, f, indent=2, sort_keys=True)
        print(f"  wrote {args.out_json}")
