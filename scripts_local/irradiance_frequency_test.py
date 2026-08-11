#
# Standalone numerical experiment -- NOT part of the LumiMotion pipeline. No
# LumiMotion code, models, or checkpoints are touched. Only reads the
# existing 32x16 benchmark envmaps (to discover the rotation convention
# baked into their filenames) and downloads the original 4K source HDRIs.
#
# Question: Probes B/C/D (docs/test1_probe_{b,c,d}*.md) found no measurable
# error from freezing a surfel's outgoing radiance under deformation -- but
# every envmap in the benchmark is 32x16, a very low-frequency light probe.
# Is that null result a property of the lighting resolution, or does it
# hold generally? This script measures how much diffuse irradiance E(n)
# changes when a normal n rotates by angle theta, as a function of envmap
# resolution, with and without a self-shadowing occluder.
#
# Method: direct hemispherical integration over envmap texels with
# solid-angle weighting (equirectangular texel solid angle = sin(theta) *
# dtheta * dphi) -- deliberately NOT an SH projection, since SH truncation
# is itself a low-pass filter and would bias the result toward "resolution
# doesn't matter" regardless of what's actually in the data.
#
# Rotation convention: the benchmark's 32x16 files are the same Poly Haven
# 4K source, downsized and then rolled horizontally by an angle encoded in
# the filename (rot0/90/270/330 -> a circular shift of round(deg/360*W)
# pixels along the horizontal axis) -- confirmed empirically (MSE ~3e-4
# against the actual 32x16 file for the claimed rotation, an order of
# magnitude below any other candidate shift). Every resolution in this
# script's ladder is built from the SAME rotated 4K source, so a 32x16 rung
# built here reproduces the shipped benchmark file almost exactly -- the
# methodology check for this experiment.
#
# Occlusion model: a spherical cap centered at the query normal itself,
# half-angle alpha = arccos(1 - f), blocking exactly a solid-angle fraction
# f of that normal's own hemisphere (a closed form, since a cap of
# half-angle <=90 deg centered at n is entirely inside n's hemisphere -- no
# per-normal numerical root-finding needed). This is a real simplification
# (a physical fold more plausibly occludes near grazing/horizon directions
# on one side, not a disk centered on the normal) -- documented, not hidden.
# What matters for the frequency-content question under test is that
# occlusion multiplies the integrand by a hard-edged binary mask, which is
# the actual mechanism regardless of exactly where the mask is centered.
# The occluder is rigidly attached to the local normal: centered at n when
# evaluating E(n), centered at n' when evaluating E(n') -- i.e. it rotates
# WITH the surface, matching a fold whose geometry is fixed relative to the
# surface rather than to world space.
#
# Run from the repo root:
#   python -m scripts_local.irradiance_frequency_test --out_dir docs/irradiance_frequency_test_assets
#
import argparse
import json
import os
import re
import urllib.request

import cv2
import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/lumimotion_irradiance_test/hdri_4k")
DEFAULT_DATA_DIR = "data/d-nerf-relight-spec32"
ENVMAP_NAMES = ["chapel_day", "dam_wall", "golden_bay", "small_harbour_sunset"]
FALLBACK_ROTATIONS = {"chapel_day": 0, "dam_wall": 90, "golden_bay": 330, "small_harbour_sunset": 270}
RESOLUTION_LADDER = [(16, 32), (32, 64), (64, 128), (128, 256), (256, 512)]  # (H,W), doubling from 32x16
MEASURED_ANGLES = {"median": 8.7, "p90": 49.6, "p99": 91.2}  # docs/test1_probe_c.md, dynamic-Gaussian rotation


def discover_rotations(data_dir):
    """Read the rotation baked into the shipped 32x16 filenames
    (..._4k_32x16_rotXXX.hdr) rather than hardcoding it, so this script
    stays correct if the benchmark ever ships different rotations. Falls
    back to the known values if the data directory isn't available (this
    script is meant to also work as a fully standalone experiment)."""
    rotations = {}
    if os.path.isdir(data_dir):
        for root, _, files in os.walk(data_dir):
            for f in files:
                m = re.match(r"([a-z_]+)_4k_32x16_rot(\d+)\.hdr$", f)
                if m and m.group(1) in ENVMAP_NAMES:
                    rotations[m.group(1)] = int(m.group(2))
            if len(rotations) == len(ENVMAP_NAMES):
                break
    for name in ENVMAP_NAMES:
        rotations.setdefault(name, FALLBACK_ROTATIONS[name])
    return rotations


def download_4k(name, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{name}_4k.hdr")
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return path
    api_url = f"https://api.polyhaven.com/files/{name}"
    with urllib.request.urlopen(api_url, timeout=30) as resp:
        meta = json.load(resp)
    hdr_url = meta["hdri"]["4k"]["hdr"]["url"]
    print(f"Downloading {name} 4K HDRI from {hdr_url}")
    urllib.request.urlretrieve(hdr_url, path)
    return path


def load_rotated_source(name, rotations, cache_dir):
    path = download_4k(name, cache_dir)
    img = imageio.imread(path).astype(np.float32)  # (H,W,3)
    H, W = img.shape[:2]
    shift_px = int(round(rotations[name] / 360.0 * W))
    return np.roll(img, shift_px, axis=1)


def build_resolution_ladder(img_full):
    """img_full: (H,W,3) float32, already rotation-matched. Returns dict
    {label: (H,W,3) array} for every rung, downsized from the SAME rotated
    source via area-averaging (matches how the shipped 32x16 files were
    themselves produced -- confirmed by the module-docstring MSE check)."""
    H, W = img_full.shape[:2]
    out = {}
    for h, w in RESOLUTION_LADDER:
        resized = cv2.resize(img_full, (w, h), interpolation=cv2.INTER_AREA)
        out[f"{w}x{h}"] = resized
    out[f"{W}x{H} (full)"] = img_full
    return out


def build_texel_grid(H, W, device):
    """Equirectangular convention: theta (colatitude) in [0,pi] over rows,
    phi (azimuth) in [0,2pi) over columns; z is the pole axis. Texel solid
    angle = sin(theta) * (pi/H) * (2*pi/W)."""
    i = torch.arange(H, device=device, dtype=torch.float64)
    j = torch.arange(W, device=device, dtype=torch.float64)
    theta = (i + 0.5) / H * np.pi
    phi = (j + 0.5) / W * 2 * np.pi
    theta_grid, phi_grid = torch.meshgrid(theta, phi, indexing='ij')
    sin_t = torch.sin(theta_grid)
    x = sin_t * torch.cos(phi_grid)
    y = sin_t * torch.sin(phi_grid)
    z = torch.cos(theta_grid)
    directions = torch.stack([x, y, z], dim=-1).reshape(-1, 3).float()
    solid_angle = (sin_t * (np.pi / H) * (2 * np.pi / W)).reshape(-1).float()
    return directions.to(device), solid_angle.to(device)


def integrate_irradiance(directions, weighted_L, query_normals, occlusion_frac=0.0, texel_chunk=20000):
    """directions: (Nt,3) unit vectors; weighted_L: (Nt,) = radiance*solid_angle;
    query_normals: (Nq,3) unit vectors. Returns (Nq,) irradiance. Occlusion:
    a cap of half-angle arccos(1-f) centered at the query normal itself
    blocks that fraction of ITS OWN hemisphere -- visible iff 0 < dot < 1-f."""
    Nq = query_normals.shape[0]
    E = torch.zeros(Nq, device=query_normals.device, dtype=torch.float32)
    upper = 1.0 - occlusion_frac
    Nt = directions.shape[0]
    for start in range(0, Nt, texel_chunk):
        end = min(start + texel_chunk, Nt)
        d_chunk = directions[start:end]
        w_chunk = weighted_L[start:end]
        dots = query_normals @ d_chunk.T  # (Nq, Tc)
        mask = (dots > 0) & (dots < upper)
        contrib = torch.where(mask, dots, torch.zeros_like(dots)) * w_chunk[None, :]
        E += contrib.sum(dim=1)
    return E


def fibonacci_sphere(n, device):
    i = torch.arange(n, device=device, dtype=torch.float64)
    golden = (1 + 5 ** 0.5) / 2
    z = 1 - 2 * (i + 0.5) / n
    r = torch.sqrt((1 - z * z).clamp_min(0))
    theta = 2 * np.pi * i / golden
    x = r * torch.cos(theta)
    y = r * torch.sin(theta)
    return torch.stack([x, y, z], dim=-1).float()


def perpendicular_basis(n):
    """(Nn,3) unit normals -> two (Nn,3) unit vectors u,v spanning the
    tangent plane at each n."""
    ref = torch.tensor([0.0, 0.0, 1.0], device=n.device).expand_as(n)
    alt = torch.tensor([1.0, 0.0, 0.0], device=n.device).expand_as(n)
    ref = torch.where(n[:, 2:3].abs() > 0.9, alt, ref)
    u = torch.nn.functional.normalize(torch.cross(ref, n, dim=-1), dim=-1)
    v = torch.cross(n, u, dim=-1)
    return u, v


def rotate_by_angle(n, u, v, theta_deg, phi):
    """Move each n by exactly theta_deg of angular distance, toward a
    direction in the tangent plane parameterised by phi (the 'random
    rotation axis' -- equivalently, the free azimuthal choice of which way
    to move n by the fixed angle theta). n' = cos(theta) n + sin(theta) w,
    w = cos(phi) u + sin(phi) v."""
    theta = np.deg2rad(theta_deg)
    w = torch.cos(phi)[:, None] * u + torch.sin(phi)[:, None] * v
    return np.cos(theta) * n + np.sin(theta) * w


def run(out_dir, cache_dir, data_dir, n_normals, k_axes, thetas, occlusion_fracs, texel_chunk, seed):
    os.makedirs(out_dir, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)

    rotations = discover_rotations(data_dir)
    print("Rotation convention (deg):", rotations)

    base_normals = fibonacci_sphere(n_normals, device)
    u, v = perpendicular_basis(base_normals)
    rng = torch.Generator(device=device).manual_seed(seed)

    results = {}  # envmap -> resolution_label -> occlusion -> {"base_E":..., "theta": {deg: {mean,median,p90}}}

    for name in ENVMAP_NAMES:
        img_full = load_rotated_source(name, rotations, cache_dir)
        ladder = build_resolution_ladder(img_full)
        results[name] = {}

        for res_label, img in ladder.items():
            H, W = img.shape[:2]
            directions, solid_angle = build_texel_grid(H, W, device)
            L = torch.from_numpy(img.mean(axis=-1)).float().to(device).reshape(-1)  # (H*W,) greyscale radiance
            weighted_L = L * solid_angle
            results[name][res_label] = {}

            for f in occlusion_fracs:
                E_base = integrate_irradiance(directions, weighted_L, base_normals, occlusion_frac=f,
                                              texel_chunk=texel_chunk)
                theta_results = {}
                for theta_deg in thetas:
                    phi = torch.rand(n_normals * k_axes, generator=rng, device=device) * 2 * np.pi
                    n_rep = base_normals.repeat_interleave(k_axes, dim=0)
                    u_rep = u.repeat_interleave(k_axes, dim=0)
                    v_rep = v.repeat_interleave(k_axes, dim=0)
                    n_rot = rotate_by_angle(n_rep, u_rep, v_rep, theta_deg, phi)
                    n_rot = torch.nn.functional.normalize(n_rot, dim=-1)

                    E_rot = integrate_irradiance(directions, weighted_L, n_rot, occlusion_frac=f,
                                                 texel_chunk=texel_chunk)
                    E_base_rep = E_base.repeat_interleave(k_axes, dim=0)
                    valid = E_base_rep.abs() > 1e-8
                    rel = (E_rot - E_base_rep).abs() / E_base_rep.clamp_min(1e-8)
                    rel = rel[valid].cpu().numpy()
                    theta_results[theta_deg] = {
                        "mean": float(rel.mean()), "median": float(np.median(rel)),
                        "p90": float(np.percentile(rel, 90)), "n": int(rel.shape[0]),
                    }
                results[name][res_label][f] = {
                    "mean_E_base": float(E_base.mean().item()), "theta": theta_results,
                }
                print(f"  {name} {res_label} occ={f}: "
                     f"{[round(theta_results[t]['mean'],4) for t in thetas]}")

    with open(os.path.join(out_dir, "results.json"), "w") as fh:
        json.dump({"rotations": rotations, "resolutions": list(next(iter(results.values())).keys()),
                  "thetas": thetas, "occlusion_fracs": occlusion_fracs,
                  "measured_angles": MEASURED_ANGLES, "n_normals": n_normals, "k_axes": k_axes,
                  "results": results}, fh, indent=2)
    print(f"Wrote {out_dir}/results.json")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diffuse irradiance vs. envmap resolution and normal rotation")
    parser.add_argument("--out_dir", type=str, default="docs/irradiance_frequency_test_assets")
    parser.add_argument("--cache_dir", type=str, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--data_dir", type=str, default=DEFAULT_DATA_DIR)
    parser.add_argument("--n_normals", type=int, default=3000)
    parser.add_argument("--k_axes", type=int, default=6, help="random rotation-axis samples per normal per angle")
    parser.add_argument("--theta_step", type=float, default=15.0)
    parser.add_argument("--occlusion_fracs", type=float, nargs="+", default=[0.0, 0.25, 0.5, 0.75])
    parser.add_argument("--texel_chunk", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    thetas = sorted(set(list(np.arange(0, 181, args.theta_step)) + list(MEASURED_ANGLES.values())))
    thetas = [round(t, 1) for t in thetas]

    run(args.out_dir, args.cache_dir, args.data_dir, args.n_normals, args.k_axes, thetas,
       args.occlusion_fracs, args.texel_chunk, args.seed)
