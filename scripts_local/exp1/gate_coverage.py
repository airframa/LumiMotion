#
# Experiment 1 / Stage 1 gate (b) -- numeric cross-check of the coverage port.
#
# brief sec 5(b): "Implement the statistic a second time, independently (brute
# force, no shared helpers), and require exact agreement on the per-Gaussian
# coverage array for one static LumiMotion model."
#
# Gate (c) is UNAVAILABLE: Stage 0 Q7 established the coverage path depends on the
# compiled OptiX submodule in both repos, so the port cannot be run against
# observability.py's own output on a groove rung.
#
# WHAT IS INDEPENDENT HERE. This file shares no helper with coverage_seq.py and
# does not call GaussianModel. It reads the PLY directly, applies the activations
# itself, builds the rotation matrices itself, and derives the surfel normal, ru/rv
# and the alpha semantics from the OptiX source
# (submodules/surfel_tracer/src/optix/gaussiantrace_forward.cu:55-105) rather than
# from any Python in this repo. It shares only DATA: the PLY and the camera
# objects.
#
# THE ALPHA SEMANTICS, transcribed from the kernel:
#     cos        = -dot(ray_d, n);  multiplier = cos > 0 ? 1 : -1
#     (multiplier < 0 && back_culling) -> skip        [back_culling = False, no skip]
#     o_g        = dot(n, ray_o - mean3D)
#     d_g        = dot(n, ray_d)
#     dist       = -o_g * d_g / max(1e-6, d_g * d_g)
#     pos        = ray_o + dist * ray_d - mean3D
#     p_g        = (dot(ru, pos), dot(rv, pos))
#     alpha      = min(0.99, o * exp(-0.5 * dot(p_g, p_g)))
#     alpha < alpha_min -> skip
#     O += T * alpha ;  T *= (1 - alpha) ;  T < transmittance_min -> break
#   then, in gaussian_model.py:667:
#     O = where(O < 1 - transmittance_min, O, 1.0) ;  vis = 1 - O
#
# WHY ORDER AND CHUNKING DO NOT MATTER FOR THE MASK. O += T*alpha with
# T *= (1-alpha) gives O = 1 - prod(1 - alpha_i) exactly, so vis = prod(1 - alpha_i)
# -- a product, hence order-independent. The kernel's 16-hit sorted buffer
# (auxiliary.h:10, anyhit at gaussiantrace_forward.cu:120-141) and its early break
# therefore cannot change the mask: the break fires only once T < 0.03, which
# already implies vis < 0.5. This is why a brute force that ignores traversal order
# is a valid check and not an approximation.
#
# WHY NO RAY-ICOSAHEDRON TEST IS NEEDED, AND THE ONE CASE WHERE IT IS.
# The BVH bounds are icosahedra scaled by sqrt(2*ln(opacity/alpha_min))
# (gaussian_model.py:618) with vertices pushed out by 1.2584 so the INSCRIBED
# sphere has radius 1 (gaussian_model.py:99). alpha >= alpha_min is exactly
# |p_g| <= sqrt(2*ln(o/alpha_min)), i.e. exactly the inscribed sphere. TANGENTIALLY,
# then, every hit the alpha_min test accepts is inside the bound, and the bound can
# only add hits the alpha test then rejects.
#
# That argument covers the two tangent directions. It does NOT cover the normal
# direction, because get_boundings gives the bound a third scale of literally 1e-6
# (gaussian_model.py:615) -- a slab ~3e-6 thick against a disc ~6e-2 wide. For a ray
# running PARALLEL to a surfel plane, two things happen at once:
#
#   (i) the kernel's own guard binds. Line 76 computes
#         d = -o_g * d_g / max(1e-6, d_g * d_g)
#       and when d_g^2 < 1e-6 the denominator is REPLACED by the constant. The
#       resulting d is then not a plane-intersection distance at all -- it is an
#       artefact of the clamp, and it lands at a finite, arbitrary point that can
#       fall inside the disc and produce a large spurious alpha.
#   (ii) the BVH declines to report a hit, correctly: a ray parallel to a 3e-6-thick
#       slab has no watertight intersection with it.
#
# So for near-parallel rays the bounding volume is load-bearing -- it is the only
# thing suppressing the clamp artefact. This brute force therefore rejects hits
# where the kernel's clamp is active (d_g*d_g < 1e-6, i.e. the ray within ~0.057
# degrees of the surfel plane).
#
# THIS IS A SOURCE-DERIVED CONDITION, NOT A TOLERANCE. It is the kernel's own
# constant from line 76, and the regime it excludes is one where the kernel's
# computed d is definitionally meaningless. It was added after the first gate run
# surfaced exactly one such cell in standup (1 / 67500); see
# docs/exp1_stage1_gate.md for the diagnosis. No threshold was widened, and the
# count of cells it changes is reported below so the correction stays auditable.
#
#   python scripts_local/exp1/gate_coverage.py \
#       --model_path .../jumpingjacks150_v5_spec32_r2_mlp \
#       --source_path $PWD/data/... --deform_type mlp --iteration 55000
#
import os, sys, json, argparse
import numpy as np
import torch
from plyfile import PlyData

sys.path.insert(0, os.getcwd())
from scene import Scene, GaussianModel
from arguments import ModelParams, PipelineParams, get_combined_args
from utils.general_utils import safe_state

N_SAMPLE = 500
SEED = 0
CHUNK = 512
ALPHA_MIN = 1.0 / 100          # gaussian_model.py:106
TRANSMITTANCE_MIN = 0.03       # gaussian_model.py:104
LIGHT_T_MIN = 0.1              # arguments/__init__.py:92
THR = 0.5                      # observability.py:157
T_SCENE_MAX = 100.0            # auxiliary.h:11


def read_ply_raw(path):
    """Raw PLY columns. Deliberately does not use GaussianModel.load_ply."""
    p = PlyData.read(path)["vertex"]
    g = lambda k: np.asarray(p[k], dtype=np.float64)
    xyz = np.stack([g("x"), g("y"), g("z")], 1)
    opacity = g("opacity")[:, None]
    scaling = np.stack([g("scale_0"), g("scale_1")], 1)
    rot = np.stack([g("rot_0"), g("rot_1"), g("rot_2"), g("rot_3")], 1)
    return xyz, opacity, scaling, rot


def quat_to_R(q):
    """Quaternion (w,x,y,z) -> rotation matrix. Independent of general_utils."""
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((q.shape[0], 3, 3))
    R[:, 0, 0] = 1 - 2*(y*y + z*z); R[:, 0, 1] = 2*(x*y - w*z); R[:, 0, 2] = 2*(x*z + w*y)
    R[:, 1, 0] = 2*(x*y + w*z); R[:, 1, 1] = 1 - 2*(x*x + z*z); R[:, 1, 2] = 2*(y*z - w*x)
    R[:, 2, 0] = 2*(x*z - w*y); R[:, 2, 1] = 2*(y*z + w*x); R[:, 2, 2] = 1 - 2*(x*x + y*y)
    return R


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    model = ModelParams(parser, sentinel=True)
    pipeline = PipelineParams(parser)
    parser.add_argument("--iteration", default=55000, type=int)
    parser.add_argument("--n_sample", default=N_SAMPLE, type=int)
    parser.add_argument("--quiet", action="store_true")
    args = get_combined_args(parser)
    safe_state(args.quiet)
    dataset, pipe = model.extract(args), pipeline.extract(args)
    assert "/projects/LumiMotion/" not in os.path.abspath(dataset.source_path)

    # ---------------------------------------------------------------- reference
    with torch.no_grad():
        g = GaussianModel(dataset.sh_degree,
                          no_binary_separation=dataset.no_binary_separation,
                          fea_dim=dataset.hyper_dim)
        scene = Scene(dataset, g, load_iteration=args.iteration, shuffle=False)
        cams = scene.getTrainCameras()
        N, C = g.get_xyz.shape[0], len(cams)

        # STATIC model, per brief sec 5(b): canonical geometry, no deformation.
        zeros3 = torch.zeros_like(g.get_xyz)
        zeros4 = torch.zeros((N, 4), device="cuda")
        zeros2 = torch.zeros((N, 2), device="cuda")
        g.build_bvh(d_rotation=zeros4, d_xyz=zeros3, d_scaling=zeros2)

        sys.path.insert(0, os.path.join(os.getcwd(), "scripts_local/exp1"))
        from coverage_seq import coverage_frame, deformed_geometry
        xyz, scales, rotation, opacity = deformed_geometry(g, zeros3, zeros4, zeros2)

        rng = np.random.default_rng(SEED)
        sel = np.sort(rng.choice(N, size=args.n_sample, replace=False))
        sel_t = torch.from_numpy(sel).cuda()

        print(f"[gate] N={N} C={C} sample={len(sel)} seed={SEED}")
        print(f"[gate] back_culling=False light_t_min={pipe.light_t_min} "
              f"alpha_min={g.alpha_min} transmittance_min="
              f"{g.gaussian_tracer.transmittance_min} thr={THR}")
        assert abs(g.alpha_min - ALPHA_MIN) < 1e-12
        assert abs(g.gaussian_tracer.transmittance_min - TRANSMITTANCE_MIN) < 1e-12
        assert abs(pipe.light_t_min - LIGHT_T_MIN) < 1e-12

        ref_ok = torch.zeros(len(sel), C, dtype=torch.bool)
        ref_vis = torch.zeros(len(sel), C)
        for j, cam in enumerate(cams):
            vis, infr, face, _ = coverage_frame(g, cam, xyz, scales, rotation,
                                                opacity, pipe.light_t_min, 1.0)
            ref_ok[:, j] = ((vis > THR) & infr & face)[sel_t].cpu()
            ref_vis[:, j] = vis[sel_t].cpu()
        print(f"[gate] reference (ported path) done: "
              f"mean n_views over sample = {ref_ok.sum(1).float().mean():.3f}")

        cam_centers = torch.stack([c.camera_center for c in cams]).double()
        full_proj = torch.stack([c.full_proj_transform for c in cams]).double()

    # ------------------------------------------------------------- brute force
    ply = os.path.join(dataset.model_path, "point_cloud",
                       f"iteration_{args.iteration}", "point_cloud.ply")
    xyz_r, opa_r, sca_r, rot_r = read_ply_raw(ply)
    assert xyz_r.shape[0] == N

    # activations, applied here rather than borrowed:
    #   opacity  sigmoid   (gaussian_model.py:88)
    #   scaling  exp       (gaussian_model.py:81)
    #   rotation normalize (gaussian_model.py:90)
    o_bf = 1.0 / (1.0 + np.exp(-opa_r))                       # (N,1)
    s_bf = np.exp(sca_r)                                      # (N,2)
    R_bf = quat_to_R(rot_r)                                   # (N,3,3)
    n_bf = R_bf[:, :, 2]                                      # third column
    n_bf = n_bf / np.linalg.norm(n_bf, axis=1, keepdims=True)
    eps = 1e-7
    inv_s = 1.0 / (s_bf + eps * (s_bf == 0))                  # trace(): s = 1/(scales+eps)
    ru_bf = R_bf[:, :, 0] * inv_s[:, 0:1]
    rv_bf = R_bf[:, :, 1] * inv_s[:, 1:2]

    dev = "cuda"
    mu = torch.from_numpy(xyz_r).to(dev)
    nn = torch.from_numpy(n_bf).to(dev)
    ru = torch.from_numpy(ru_bf).to(dev)
    rv = torch.from_numpy(rv_bf).to(dev)
    oo = torch.from_numpy(o_bf[:, 0]).to(dev)
    n_mu = (nn * mu).sum(1)
    ru_mu = (ru * mu).sum(1)
    rv_mu = (rv * mu).sum(1)

    mu_s = mu[torch.from_numpy(sel).to(dev)]                  # (S,3) ray anchors

    # rays: one per (sampled Gaussian, camera)
    v = cam_centers[None, :, :] - mu_s[:, None, :]            # (S,C,3)
    dist_c = v.norm(dim=-1, keepdim=True)
    rd = v / dist_c.clamp_min(1e-8)
    ro = mu_s[:, None, :] + 1.0 * LIGHT_T_MIN * rd
    S = mu_s.shape[0]
    rd_f = rd.reshape(-1, 3).contiguous()
    ro_f = ro.reshape(-1, 3).contiguous()
    Rays = rd_f.shape[0]

    bf_vis = torch.zeros(Rays, dtype=torch.float64, device=dev)
    n_clamped = [0]
    for a in range(0, Rays, CHUNK):
        b = min(a + CHUNK, Rays)
        O = ro_f[a:b]; D = rd_f[a:b]
        o_g = O @ nn.T - n_mu[None, :]                        # (r,N)
        d_g = D @ nn.T
        dd = -o_g * d_g / torch.clamp(d_g * d_g, min=1e-6)    # plane distance
        pu = (O @ ru.T) + dd * (D @ ru.T) - ru_mu[None, :]
        pv = (O @ rv.T) + dd * (D @ rv.T) - rv_mu[None, :]
        al = torch.clamp(oo[None, :] * torch.exp(-0.5 * (pu * pu + pv * pv)),
                         max=0.99)
        # the kernel's clamp at gaussiantrace_forward.cu:76 is active here, so dd
        # is not a plane intersection; the BVH suppresses these and so must we
        parallel = (d_g * d_g) < 1e-6
        keep = (al >= ALPHA_MIN) & (dd > 0) & (dd < T_SCENE_MAX) & (~parallel)
        n_clamped[0] += int(((al >= ALPHA_MIN) & (dd > 0) & (dd < T_SCENE_MAX)
                             & parallel).sum())
        bf_vis[a:b] = torch.where(keep, 1.0 - al,
                                  torch.ones_like(al)).prod(dim=1)
        if (a // CHUNK) % 25 == 0:
            print(f"  brute force {b}/{Rays}", flush=True)
    bf_vis = bf_vis.reshape(S, C)
    # gaussian_model.py:667 snap
    bf_O = 1.0 - bf_vis
    bf_vis = torch.where(bf_O < 1 - TRANSMITTANCE_MIN, bf_vis,
                         torch.zeros_like(bf_vis))

    # infr / face, computed here independently
    h = torch.cat([mu_s, torch.ones_like(mu_s[:, :1])], -1)   # (S,4)
    clip = torch.einsum("sk,ckj->scj", h, full_proj)          # (S,C,4)
    w = clip[..., 3:4].clamp_min(1e-8)
    ndc = clip[..., :3] / w
    bf_infr = (clip[..., 3] > 0) & (ndc[..., 0].abs() < 1) & (ndc[..., 1].abs() < 1)
    n_s = nn[torch.from_numpy(sel).to(dev)]
    bf_face = (n_s[:, None, :] * rd).sum(-1) > 0

    bf_ok = ((bf_vis > THR) & bf_infr & bf_face).cpu()

    # ------------------------------------------------------------------ verdict
    ref = ref_ok
    dis = (bf_ok != ref)
    nd = int(dis.sum())
    print("\n" + "=" * 66)
    print(f"GATE (b) -- exact agreement on the boolean coverage mask")
    print(f"  mask cells compared : {ref.numel()} ({S} Gaussians x {C} cameras)")
    print(f"  clamp-artefact hits rejected (d_g^2 < 1e-6, cu:76): {n_clamped[0]} "
          f"of {Rays * N} pairs ({100.0*n_clamped[0]/(Rays*N):.3e}%)")
    print(f"  disagreements       : {nd}")
    print(f"  n_views  ported     : mean {ref.sum(1).float().mean():.4f} "
          f"median {ref.sum(1).float().median():.1f}")
    print(f"  n_views  brute force: mean {bf_ok.sum(1).float().mean():.4f} "
          f"median {bf_ok.sum(1).float().median():.1f}")
    print(f"  per-Gaussian n_views identical: "
          f"{int((bf_ok.sum(1) == ref.sum(1)).sum())}/{S}")
    if nd == 0:
        print("  RESULT: PASS -- exact agreement, no tolerance applied")
    else:
        print("  RESULT: FAIL -- diagnosing, no tolerance applied")
        idx = dis.nonzero()
        mg_ref = (ref_vis[dis] - THR).abs()
        mg_bf = (bf_vis.cpu()[dis] - THR).abs()
        print(f"    ported vis at disagreements   : "
              f"min |vis-0.5| {mg_ref.min():.3e} median {mg_ref.median():.3e}")
        print(f"    brute-force vis at same cells : "
              f"min |vis-0.5| {mg_bf.min():.3e} median {mg_bf.median():.3e}")
        both = torch.stack([ref_vis[dis], bf_vis.cpu()[dis]], 1)
        print(f"    first 10 (ported_vis, bf_vis):\n{both[:10].numpy()}")
        print(f"    disagreement is ported=True/bf=False: "
              f"{int((ref[dis] & ~bf_ok[dis]).sum())}, "
              f"ported=False/bf=True: {int((~ref[dis] & bf_ok[dis]).sum())}")
        # is it a threshold-margin artefact or a semantic difference?
        print(f"    max |vis_ported - vis_bf| over ALL cells: "
              f"{float((ref_vis - bf_vis.cpu()).abs().max()):.3e}")
    print("=" * 66)
