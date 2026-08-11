# Survey of `blend_files/blendfiles_v5_specular32/` — read-only

No file under `blend_files/` was modified. All `.blend` files were opened
**headless** (`blender --background --python`) and inspected via a Python dump
script that reads scene/object/material/world/text data through `bpy` and writes
it to JSON; nothing was rendered, saved, or re-exported. The dump script and its
JSON outputs live outside the repo, under this session's scratch directory.

## Method note: the system `blender` cannot open these files

`/usr/bin/blender` (apt package `blender 3.0.1+dfsg-7`) is installed, but it
**crashes** (`CustomData_merge` segfault) trying to load these files — they were
saved by a newer Blender and the format has moved on too far for 3.0.1 to cope.
The crash log reports the source file as version `306.13` (3.6.13). A portable,
no-install Blender **3.6.13** binary (matching exactly) was downloaded from
`download.blender.org` and used for every dump in this survey; it opens all 15
files cleanly (aside from routine forward-compatibility warnings — see below).
**If GUI inspection is wanted, use Blender 3.6.13, not the system package** — 3.0.1
will not open these files without data loss or crashing.

One file (`hook150_v5_specular32.blend`) additionally warned "File written by a
newer Blender binary (404.32)" even under 3.6.13 — likely because some
appended/linked sub-asset inside it was itself last saved by a Blender 4.x
session. It loaded and dumped without error regardless; flagged in case it
matters for future GUI editing (Blender may prompt about this on save).

## File inventory

15 `.blend` files, one directory of source HDRIs, one extra zip of normal-map
example files:

| scene | base | `_dynamic_mask` | `_roughness` |
|---|---|---|---|
| hook150 | 41 MB | 41 MB | 41 MB |
| jumpingjacks | 96 MB | 96 MB | 96 MB |
| mouse | 75 MB | 75 MB | 75 MB |
| spheres_with_rotations | 12 MB | 11 MB | 11 MB |
| standup150 | 78 MB | 78 MB | 78 MB |

Plus `envmaps_32/` (the same 4 `.hdr` files used elsewhere in this repo) and
`blendfiles_for_normals_examples.zip` (4 more `.blend` files, ~230 MB
uncompressed: `hook150_v3_NORMALS.blend`, `jumpingjacks_NORMALS_EXAMPLE_
WATCH_COLORMANAGEMENTTAB.blend`, `mouse_NORMALS.blend`,
`standup150_v2_NORMALS.blend`). Only `hook150_v3_NORMALS.blend` (the smallest)
was extracted and inspected, since its filename directly names the exact thing
asked about (colour management) and confirmed the mechanism directly — see §6.

---

## (1) Embedded scripts

Every base/`_dynamic_mask` file has exactly one Text datablock, `360view.py`.
Every `_roughness` file has two: `360view.py` (camera/world boilerplate, mostly
unused) plus a second block named `Text` that does the actual roughness-pass
work. `spheres_with_rotations_v5_specular32.blend` is different — see §1e.

### (1a) `hook150_v5_specular32.blend` → `360view.py`, in full

```python
import os
import glob
import json
import bpy
import numpy as np
import shutil
import logging
from math import radians

# Logging setup
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
logfile_path = bpy.path.abspath("//logs_hook100_v2.log")
file_handler = logging.FileHandler(logfile_path)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Configuration
VIEWS = 150
RESOLUTION = 800
RESULTS_PATH = "/Users/jandubinski/Dynamic3GS/datasets/hook150_v5_spec32_statictimestep1"  # change as needed
COLOR_DEPTH = 8
FORMAT = "PNG"
ENV_TEXTURE_PATH = "/Users/jandubinski/Dynamic3GS/envmaps_32"

stepsize = 360.0 / VIEWS

# Setup environment texture
world_nodes = bpy.context.scene.world.node_tree.nodes
world_links = bpy.context.scene.world.node_tree.links
world_nodes.clear()

bg_node = world_nodes.new(type="ShaderNodeBackground")
env_texture_node = world_nodes.new(type="ShaderNodeTexEnvironment")
env_texture_node.projection = "EQUIRECTANGULAR"
output_node = world_nodes.new(type="ShaderNodeOutputWorld")

mapping_node = world_nodes.new(type="ShaderNodeMapping")
tex_coord_node = world_nodes.new(type="ShaderNodeTexCoord")
mapping_node.vector_type = 'TEXTURE'

world_links.new(tex_coord_node.outputs["Generated"], mapping_node.inputs["Vector"])
world_links.new(mapping_node.outputs["Vector"], env_texture_node.inputs["Vector"])
world_links.new(env_texture_node.outputs["Color"], bg_node.inputs["Color"])
world_links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])

# Render settings
scene = bpy.context.scene
scene.render.use_persistent_data = True
scene.render.resolution_x = RESOLUTION
scene.render.resolution_y = RESOLUTION
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = FORMAT
scene.render.image_settings.color_depth = str(COLOR_DEPTH)
scene.render.film_transparent = True

# Camera setup
cam = scene.objects["Camera"]
cam.location = (0, 3.0, 3.0)
cam_constraint = cam.constraints.new(type="TRACK_TO")
cam_constraint.track_axis = "TRACK_NEGATIVE_Z"
cam_constraint.up_axis = "UP_Y"

# Empties for movement
b_empty = bpy.data.objects.new("Empty", None)
b_empty.location = (0.0, 0.0, 0.65)
scene.collection.objects.link(b_empty)
cam.parent = b_empty
cam_constraint.target = b_empty

# Compositor setup
scene.use_nodes = True
tree = scene.node_tree
links = tree.links
tree.nodes.clear()
render_layers = tree.nodes.new("CompositorNodeRLayers")

depth_output = tree.nodes.new(type="CompositorNodeOutputFile")
depth_output.format.file_format = FORMAT

albedo_output = tree.nodes.new(type="CompositorNodeOutputFile")
albedo_output.format.file_format = FORMAT

map_node = tree.nodes.new(type="CompositorNodeMapValue")
map_node.offset = [-0.7]
map_node.size = [1.4]
map_node.use_min = True
map_node.min = [0]

links.new(render_layers.outputs["DiffCol"], albedo_output.inputs[0])
links.new(render_layers.outputs["Depth"], map_node.inputs[0])
links.new(map_node.outputs[0], depth_output.inputs[0])

# Camera setup
cam = scene.objects["Camera"]
out_data_train = {"camera_angle_x": cam.data.angle_x, "frames": []}
out_data_test = {"camera_angle_x": cam.data.angle_x, "frames": []}

hdr_files = sorted(glob.glob(os.path.join(ENV_TEXTURE_PATH, "*.hdr")))

for id_hdr, hdr_path in enumerate(hdr_files[:]):
    envmap_name = os.path.splitext(os.path.basename(hdr_path))[0]
    envmap_output_dir = bpy.path.abspath(f"//{RESULTS_PATH}")
    os.makedirs(envmap_output_dir, exist_ok=True)
    shutil.copy(hdr_path, os.path.join(envmap_output_dir, os.path.basename(hdr_path)))

    logger.info(f"Processing environment: {envmap_name}")

    if env_texture_node.image:
        bpy.data.images.remove(env_texture_node.image)
    env_texture_node.image = bpy.data.images.load(hdr_path)
    env_texture_node.image.colorspace_settings.name = "Linear Rec.709"

    depth_output.base_path = envmap_output_dir
    albedo_output.base_path = envmap_output_dir

    np.random.seed(40422)
    for frame_id in range(1, VIEWS + 1, 1):
        rot = np.random.uniform(0, 1, size=3) * (1, 0, 2 * np.pi)
        rot[0] = np.abs(np.arccos(1 - 2 * rot[0]) - np.pi / 2)

        b_empty.rotation_euler = rot
        bpy.context.scene.frame_current = 1  # frame_id

        render_base = os.path.join(envmap_output_dir, envmap_name, f"r_{frame_id:04d}")
        scene.render.filepath = render_base
        depth_output.file_slots[0].path = os.path.join("depth", f"r_{frame_id:04d}")
        albedo_output.file_slots[0].path = os.path.join("albedo", f"r_{frame_id:04d}")

        mapping_node.inputs["Rotation"].default_value[2] = radians(0)
        bpy.ops.render.render(write_still=True)

        if id_hdr == 0:
            frame_data = {
                "file_path": f"r_{frame_id:04d}",
                "rotation": radians(stepsize),
                "transform_matrix": [list(row) for row in cam.matrix_world],
                "time": frame_id / VIEWS,
            }
            if frame_id % 10 == 0:
                out_data_test["frames"].append(frame_data)
            else:
                out_data_train["frames"].append(frame_data)

    if id_hdr == 0:
        with open(os.path.join(envmap_output_dir, "transforms_train.json"), "w") as f_train:
            json.dump(out_data_train, f_train, indent=4)
        with open(os.path.join(envmap_output_dir, "transforms_test.json"), "w") as f_test:
            json.dump(out_data_test, f_test, indent=4)

        config_dict = {
            "train_light": "chapel_day_4k_32x16_rot0",
            "test_light": "golden_bay_4k_32x16_rot330",
        }
        with open(os.path.join(envmap_output_dir, "config.json"), "w") as config_file:
            json.dump(config_dict, config_file, indent=4)
```

**This is the STATIC-timestep-1 variant**, not the dynamic training-set
generator — note `bpy.context.scene.frame_current = 1  # frame_id` (the real
frame index is commented out) and `RESULTS_PATH` ending in
`hook150_v5_spec32_statictimestep1`. It renders all 150 random camera views
against the animation frozen at frame 1. This confirms, from the source
generation script itself, what `docs/lumimotion_repro.md`/`docs/lumimotion_eval.md`
inferred from the dataset side: the `_statictimestepN` datasets really are the
same character mesh at one fixed pose, viewed from 150 different random cameras.

### (1b) jumpingjacks / mouse / standup150 → `360view.py`

Structurally identical to (1a) — same logging setup, same world-node
construction, same compositor (depth + albedo File Output branches), same
random-camera-rotation loop with `np.random.seed(40422)` (**the same seed
across every scene** — see §5). The only differences are `RESULTS_PATH` and
the frame-index line:

| file | `RESULTS_PATH` suffix | frame-index line |
|---|---|---|
| `jumpingjacks_v5_specular32.blend` | `jumpingjacks150_v5_spec32` (no suffix) | `bpy.context.scene.frame_current = frame_id` — **live**, `# scene.frame_set(frame_id)` commented out |
| `mouse_v5_specular32.blend` | two full copies concatenated in one Text block — see below | first copy: `statictimestep1`, `frame_current = 1`; second copy: no suffix, `frame_current = frame_id` |
| `standup150_v5_specular32.blend` | two full copies concatenated — see below | first copy: `statictimestep75`, `frame_current = 75`; second copy: no suffix, `frame_current = frame_id` |

**`mouse_v5_specular32.blend` and `standup150_v5_specular32.blend`'s
`360view.py` text block is not one script — it is two complete copies of the
whole script (imports, logging setup, everything) pasted one after the other in
the same buffer**, with no comment marker separating them. Running the whole
buffer top-to-bottom would execute both in sequence: first the static-timestep
variant (writing to `..._statictimestepN/`), then the dynamic variant (writing
to the plain scene folder) — i.e. one "Run Script" click in these two files
would regenerate both the static baseline and the dynamic training set for that
scene, back to back. `hook150_v5_specular32.blend` and
`jumpingjacks_v5_specular32.blend` each contain only one copy (static-only and
dynamic-only respectively) — so for hook the dynamic generator was evidently
either run from a file not included in this drop, or the buffer was
overwritten/not re-saved after that run. Not something knowable from the file
alone; flagged as an inconsistency in what's included in this archive, not a
red flag about the data itself (the dataset actually shipped in this repo's
`data/d-nerf-relight-spec32/` demonstrably includes the dynamic hook150 set).

### (1c) `*_dynamic_mask.blend` → `360view.py`, in full (hook150; jumpingjacks
identical apart from `OUTPUT_DIR`)

```python
import bpy
import numpy as np
import os
import json
import math

# === CONFIG ===
VIEWS = 150
RESOLUTION = 800
OUTPUT_DIR = "/Users/joannakaleta/Documents/Sano_Preludium_projekty_doktorat/dynamic_relightable/dynamic_relightning_blender_sets/dataset/hook150_v5_spec32_mask"  # Change as needed
SEED = 40422
CAMERA = bpy.data.objects["Camera"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === RENDER SETTINGS ===
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = RESOLUTION
scene.render.resolution_y = RESOLUTION
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
view_layer = scene.view_layers[0]
view_layer.use_pass_combined = True

# === SETUP CAMERA ===
CAMERA.location = (0, 3.0, 3.0)
cam_constraint = CAMERA.constraints.new(type="TRACK_TO")
cam_constraint.target = bpy.data.objects.new("Empty", None)
cam_constraint.target.location = (0.0, 0.0, 0.65)
cam_constraint.track_axis = "TRACK_NEGATIVE_Z"
cam_constraint.up_axis = "UP_Y"
scene.collection.objects.link(cam_constraint.target)
CAMERA.parent = cam_constraint.target

# === CREATE MATERIALS ===
def create_emission_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = 1.0
    mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat

white_mat = create_emission_material("White_Mask", (1, 1, 1, 1))
black_mat = create_emission_material("Black_Background", (0, 0, 0, 1))

# === ASSIGN MASK MATERIALS (only for Armature named "Armature") ===
target_armature = bpy.data.objects.get("Armature")

for obj in bpy.data.objects:
    if obj.type == "MESH":
        influenced_by_target = any(
            mod.type == 'ARMATURE' and mod.object == target_armature
            for mod in obj.modifiers
        )
        obj.data.materials.clear()
        obj.data.materials.append(white_mat if influenced_by_target else black_mat)

# === RENDER LOOP ===
np.random.seed(SEED)
stepsize = 360.0 / VIEWS
out_data = {"camera_angle_x": CAMERA.data.angle_x, "frames": []}

for frame_id in range(1, VIEWS + 1):
    rot = np.random.uniform(0, 1, size=3) * (1, 0, 2 * np.pi)
    rot[0] = np.abs(np.arccos(1 - 2 * rot[0]) - np.pi / 2)
    cam_constraint.target.rotation_euler = rot

    scene.frame_current = frame_id  # 1  # Keep static frame
    render_path = os.path.join(OUTPUT_DIR, f"mask_{frame_id:04d}.png")
    scene.render.filepath = render_path
    bpy.ops.render.render(write_still=True)

    out_data["frames"].append({
        "file_path": f"mask_{frame_id:04d}.png",
        "rotation": math.radians(stepsize),
        "transform_matrix": [list(row) for row in CAMERA.matrix_world],
        "time": frame_id / VIEWS,
    })

with open(os.path.join(OUTPUT_DIR, "transforms_masks.json"), "w") as f:
    json.dump(out_data, f, indent=4)
```

**This is the ground-truth generator for `data/*/dynamic_mask/mask_XXXX.png`,
and it changes the correct interpretation of that data established earlier in
this investigation — see §7, "significant finding," below.** In short: every
mesh gets replaced with a flat white or flat black emission material
(white iff a modifier on it is an Armature modifier targeting the object named
`"Armature"` — i.e. iff the mesh is skinned to the character rig), the world/
lighting is untouched by this script (irrelevant to an emission-only render),
and the same `SEED = 40422` random camera path is reused. Same `VIEWS=150`,
same random-camera scheme as every other pass — but note `film_transparent =
True` and **no world/lighting setup at all** in this script (it never touches
`scene.world`), so whatever envmap happened to be wired into the World node
tree when the file was saved is present for this render too, though
irrelevant to an emission-shaded output.

### (1d) `*_roughness.blend` → second Text block (`Text`), key excerpt

The `360view.py` companion in these files is boilerplate (camera + world setup)
left over from a template and is largely superseded by the second block. The
real roughness-pass logic:

```python
scene.render.engine = 'BLENDER_EEVEE_NEXT'   # or 'CYCLES'
...
# MATERIAL -> EMISSION(ROUGHNESS)
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        nodes = nt.nodes
        links = nt.links
        output = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
        if not output:
            continue
        shader = next((n for n in nodes if "Roughness" in n.inputs), None)
        if not shader:
            continue
        rough_input = shader.inputs["Roughness"]

        if "Emission_Roughness" in nodes:
            emission = nodes["Emission_Roughness"]
        else:
            emission = nodes.new("ShaderNodeEmission")
            emission.name = "Emission_Roughness"
            ...

        if rough_input.is_linked:
            source_socket = rough_input.links[0].from_socket
            if not any(l.to_node == emission and l.to_socket == emission.inputs["Color"] for l in links):
                links.new(source_socket, emission.inputs["Color"])
        else:
            # In Blender there are two different "roughness" concepts.
            # THIS IF sets specular roughness to 1.0 for diffuse BSDF (some other roughness for diffusebsdf was 0)
            rough_val = rough_input.default_value
            if rough_val == 0:
                rough_val = 1.0
            ...  # wire a Value node -> Emission.Color instead

        # Mix Shader, Fac forced to 1.0 -> pure emission, original shading discarded
        ...
        mix_shader.inputs["Fac"].default_value = 1.0
```

For every mesh material it locates whichever BSDF node exposes a `Roughness`
input, reads either the linked source (if the artist textured roughness) or the
scalar default, and drives a pure `Emission` node with that value — with an
explicit, commented special case: a `Roughness == 0` default is remapped to
`1.0` before use, because for a Diffuse BSDF a roughness of exactly `0` in
Blender's data model is not a meaningful "smooth" value the way it is for a
glossy/specular BSDF (the comment: *"In Blender there are two different
'roughness' concepts... THIS IF sets specular roughness to 1.0 for diffuse BSDF
(some other roughness for diffuse BSDF was 0)"*). The original material's
Surface output is rerouted through a `Mix Shader` with `Fac=1.0`, so the
emission fully replaces the original shading rather than blending with it.
World/HDRI setup is rebuilt identically to (1a)/(1b) further down in the same
script (same node graph, same links) but is irrelevant to the emission output.

### (1e) `spheres_with_rotations_v5_specular32.blend` — five Text blocks, mostly unrelated leftovers

This file (uniquely) carries five scripts: `arch_balls_rotate_point_light`,
`bouncingballs_360view_dataset.py`, `bouncingballs_one_cam_visualisation.py`,
`hotdog_360_view.py`, and an unnamed `Text`. Despite the names, only
**`bouncingballs_360view_dataset.py`** is the live generator for this repo's
`spheres_v5_spec32` scene — it is the only one of the five referencing
`envmaps_32` and a `spec32` output path. Its config differs from every other
scene: `VIEWS = 100` (not 150) and an explicit `TIMESTEPS = VIEWS` variable.
The other four (`arch_balls_rotate_point_light`, a single-camera
"visualisation" variant, and a `hotdog_360_view.py` clearly descended from the
original NeRF-synthetic `hotdog` dataset's Blender script, `RESULTS_PATH =
'results/'`) are dev/legacy scripts from earlier, unrelated experiments,
reused in this file as scratch space — not part of this benchmark's generation
path. Not dumped in full here since they're out of scope; available in the
saved JSON dumps if wanted.

---

## (2) Render settings

Consistent across every base/`_dynamic_mask` file checked (hook150,
jumpingjacks, mouse, standup150; spheres uses the same values via its own
script):

| setting | value |
|---|---|
| engine | **Cycles** (base/main dataset); **EEVEE Next** (`_dynamic_mask`, `_roughness` — set at runtime by their scripts, see §1c/1d) |
| resolution | 800×800, 100% |
| samples | **128** |
| max bounces | 4 total; **diffuse bounces: 1**; glossy bounces: 2; transmission: 4; volume: 0 |
| caustics | reflective + refractive both **on** |
| device | GPU |
| denoising | **on** (`use_denoising = True`) |
| film | transparent |
| image format | PNG, 8-bit, RGBA |
| view transform | **Standard** (not Filmic/AgX) |
| display device | sRGB |
| exposure / gamma | 0.0 / 1.0 (neutral) |
| look | None |

`diffuse_bounces = 1` is worth flagging explicitly for this investigation: it
means the reference (ground-truth) renders themselves only account for
**one bounce** of diffuse light transport, matching LumiMotion's own
one-bounce indirect model in spirit — the GT was never simulating more bounces
than the reconstruction pipeline attempts to learn.

`use_denoising = True` is a further, separate caveat on top of everything
established in `docs/indirect_fraction.md` and friends: the shipped GT PNGs are
**not raw path-traced samples** — the OptiX/OpenImageDenoise denoiser has run
over them. Any noise-floor argument comparing render error to GT should keep in
mind the GT itself already has denoiser-introduced smoothing, which a
comparison to a non-denoised reconstruction render would not share.

The **compositor is only used for the separate depth/albedo File Output
branches** (see §1a) — the main beauty PNG is written directly via
`scene.render.filepath` / `bpy.ops.render.render(write_still=True)`, not routed
through any compositor node. So the main color image path is: Cycles render →
Standard view transform → sRGB encode → PNG, with nothing else in between.

---

## (3) Render passes / AOVs

Current View Layer pass flags (`hook150_v5_specular32.blend`, and identical in
every base file checked):

```
use_pass_combined      = True   (the beauty image)
use_pass_diffuse_color = True   (feeds the compositor's Albedo output branch)
use_pass_z             = True   (feeds the compositor's Depth output branch)
use_pass_cryptomatte_accurate = True
```

Everything else is **off**, including, notably:

```
use_pass_diffuse_direct   = False
use_pass_diffuse_indirect = False
use_pass_glossy_color     = False
use_pass_glossy_direct    = False
use_pass_glossy_indirect  = False
use_pass_ambient_occlusion = False
use_pass_normal           = False
use_pass_shadow           = False
use_pass_environment      = False
```

**To enable the indirect diffuse and glossy passes**: in the View Layer
Properties tab (Passes → Diffuse / Glossy), tick "Indirect" (and "Direct" if
the direct-only component is also wanted) for both Diffuse and Glossy — in
Python, on the relevant `view_layer`:

```python
view_layer.use_pass_diffuse_indirect = True
view_layer.use_pass_diffuse_direct   = True   # optional, if direct-only is also wanted
view_layer.use_pass_glossy_indirect  = True
view_layer.use_pass_glossy_direct    = True   # optional
```

then wire a matching `CompositorNodeRLayers` output socket (`"DiffInd"` /
`"GlossInd"`, alongside the existing `"DiffCol"` used for the albedo branch) to
a new `CompositorNodeOutputFile` the same way `depth_output`/`albedo_output`
are wired in §1a — no other part of the pipeline needs to change. This would
give a Cycles-native, ground-truth indirect-only image per frame, a direct
alternative/cross-check to this repo's own `dump_light_indirect`
hook-and-differencing approach (`docs/indirect_fraction.md`) — the Cycles pass
separates **all** bounced light (not just the one-bounce diffuse term
LumiMotion models), so it would over-count relative to LumiMotion's own
indirect definition, but at `diffuse_bounces=1` (see §2) the two should be very
close.

---

## (4) Scene structure

**Objects** (hook150; jumpingjacks/mouse/standup150 structurally identical,
spheres_with_rotations obviously not — a procedural sphere-grid scene, not
inspected in the same depth):

- 1 `CAMERA` ("Camera"), 1 `ARMATURE` ("Armature"), 8 `MESH`, 55 `EMPTY`.
- **No `LIGHT` objects anywhere in the scene** — illumination is exclusively
  from the World environment texture. Confirms the "distant lighting only"
  assumption used throughout this investigation is exactly what the reference
  data was rendered with, not an approximation.
- The character mesh (`vanguard_Mesh`, `vanguard_visor`) carries an
  **Armature modifier** targeting the "Armature" object — a rigged mesh, not
  shape-key or per-vertex animation.
- The Armature's action is named **`Armature|mixamo.com|Layer0.007`** — a
  standard Mixamo export naming pattern. The body motion is a baked Mixamo
  animation clip, `frame_start=1`/`frame_end=150` (matching `VIEWS`).
- The 55 `EMPTY` objects have no animation data and no clear purpose visible
  from object-level data alone (likely leftover bone-visualisation or
  IK-target empties from the Mixamo rig import) — not investigated further,
  out of scope for this survey.

**Materials** (hook150; 4 total):
- `Vanguard_VisorMat.001` / `VanguardBodyMat` — Principled BSDF, **Metallic =
  0**, **Roughness = 0.553 fixed constant** (not textured — every point on the
  character shares one roughness value; matches `docs/lumimotion_eval.md`'s
  note that LumiMotion's own `_roughness` parameter starts from a single
  `init_roughness_value` too), Base Color driven by an **sRGB** image texture,
  a tangent-space Normal Map fed by a **Non-Color** image texture, and
  Specular driven by a third, also **Non-Color**, image texture.
- `Material cone` / `Material.001` — simple Diffuse BSDF; `Material.001` (the
  floor) uses a **procedural Checker Texture** node, not an image — this is
  the checkerboard floor pattern visible throughout every render in this
  investigation, confirmed procedural rather than a texture asset.

**Environment texture wiring** (World node tree, every base file — this is
exactly what `env_texture_node.colorspace_settings.name = "Linear Rec.709"`
targets):

```
Texture Coordinate (Generated) -> Mapping (Vector, TEXTURE type) -> Environment Texture
   (EQUIRECTANGULAR projection, colorspace "Linear Rec.709")
   -> Background (Color; Strength = 1.0) -> World Output (Surface)
```

The `.hdr` file loaded into the Environment Texture node is swapped at
runtime, once per element of `sorted(glob(envmaps_32/*.hdr))` — the file's
saved-on-disk state simply reflects whichever `.hdr` was loaded **last** in the
most recent run (e.g. `hook150_v5_specular32.blend` was left pointing at
`small_harbour_sunset_4k_32x16_rot270.hdr`, alphabetically last of the four).
The `Mapping` node's rotation is reset to `radians(0)` every frame in code —
**the per-file rotation baked into `data/*/​*_4k_32x16_rot{0,90,270,330}.hdr`
filenames is not applied via this Mapping node at all**; those rotated 32×16
files are a separate, pre-baked asset (confirmed empirically in this session's
`docs/irradiance_frequency_test.md`: the 32×16 files are the 4K source rolled
horizontally by the filename's angle, then downsampled) — the Blender scene
always renders with the *unrotated* mapping, using whichever already-rotated
`.hdr` file it's handed.

---

## (5) Camera trajectory generation

**Not an orbit — a fixed-seed random walk**, identical in structure across
every scene (only `VIEWS`/`RESOLUTION` differ, spheres uses `VIEWS=100`):

```python
cam.location = (0, 3.0, 3.0)
# TRACK_TO constraint, tracking a child Empty at (0, 0, 0.65) — camera always looks at that point
np.random.seed(40422)
for frame_id in range(1, VIEWS + 1):
    rot = np.random.uniform(0, 1, size=3) * (1, 0, 2*np.pi)   # y-component always 0
    rot[0] = np.abs(np.arccos(1 - 2*rot[0]) - np.pi/2)         # remap x for uniform-on-sphere polar angle
    b_empty.rotation_euler = rot
```

The camera itself never moves; it is parented to an `Empty` at `(0,0,0.65)`
(roughly character hip height) with a `TRACK_TO` constraint, and the *empty's*
rotation is randomized per view. `rot[0]` (Euler X) is remapped through
`arccos(1 - 2u) - π/2` — the standard trick for sampling a polar angle
uniformly **on a sphere** (not uniformly in angle, which would over-sample the
poles) from a uniform `u ∈ [0,1]`; `rot[2]` (Euler Z, azimuth) is left as a
plain uniform draw over `[0, 2π)`; `rot[1]` (Euler Y, roll) is always exactly
`0`. So: camera distance from the look-at point is fixed (implicitly, by the
empty's parent-to-camera offset), azimuth is uniform, and polar angle is
sphere-uniform — a **uniformly-random point on a sphere shell** around the
character, re-sampled independently every frame, not a smooth path. **The same
`np.random.seed(40422)` is used in every scene's script**, including the
`_dynamic_mask` variant — meaning the *sequence* of 150 random camera poses is
identical across hook, jumpingjacks, mouse, standup150, and each scene's own
mask pass (spheres differs only because it draws 100 samples from the same
seeded stream, not 150, so its poses 1-100 match everyone else's poses 1-100 but
its stream doesn't continue to 150). This isn't in principle required to make
the datasets comparable to each other, but it is a specific, verifiable
property of the released assets, if it matters for future work.

Frame-to-camera pairing is exactly what `docs/lumimotion_eval.md`/Probe D's
render scripts assumed: for the **dynamic** variant, `scene.frame_current =
frame_id` is set immediately before each camera pose is applied and rendered
— camera pose `i` and animation frame `i` are rendered together, in lock-step,
for `i = 1..VIEWS`. For the **static** variant, `frame_current` is pinned to a
single fixed frame (`1` for `hook150`/`mouse`/`jumpingjacks`-static,
`75` for `standup150`-static — chosen once per scene, not necessarily frame 1)
while the 150 random camera draws still run through their full sequence.
`transforms_train.json`/`transforms_test.json` are only written on the first
environment-map iteration (`id_hdr == 0`, i.e. `chapel_day`, alphabetically
first) — every other lighting condition reuses those same camera transforms
(consistent with all four `.hdr`s under `envmaps_32/` sharing one camera
trajectory, which is exactly what `docs/test1_probe_d_relight.md` assumed when
reusing `render_trajectory.py`'s per-frame camera list for the golden_bay
relight pass). The train/test split is `frame_id % 10 == 0 → test`, i.e. every
10th frame (10 of 150 → the 15 test cameras Probes B/C/D found and worked
around throughout this investigation).

---

## Significant finding: `dynamic_mask` RGB and Alpha channels are not the same mask

Earlier work in this investigation (`docs/test1_probe_d_relight.md` §Method,
and the `analyse_probe_d.py`/`load_dynamic_mask` function it introduced)
inferred the semantics of `dynamic_mask/mask_XXXX.png` empirically from pixel
statistics — RGB channels identical to each other (a soft grayscale coverage
map) and a numerically different Alpha channel — and used the **Alpha**
channel, thresholded, as "the silhouette of the dynamic-only Gaussian subset."

**Reading the actual generation script (§1c above) shows this is backwards.**
The script assigns a pure-white **RGB** emission material to meshes influenced
by the Armature modifier (the moving character) and pure-black to everything
else (the static floor), with `film_transparent = True`. That means:

- **RGB** (all three channels, identical — matches the "soft grayscale
  coverage" observation) is the actual dynamic/static segmentation: white
  (high) wherever a dynamic (armature-influenced) surface is visible, black
  (near-zero) everywhere else, including the floor.
- **Alpha** is the ordinary render-alpha of *any* opaque object in frame
  (character **and** floor both being opaque, non-transparent emission
  materials) — i.e. essentially the same foreground silhouette as the main
  beauty render's own alpha channel, not a dynamic-only signal at all.

This means `analyse_probe_d.py`'s `--dynamic_mask_dir` restriction, as
implemented, thresholded the **wrong channel** — it intersected the eroded
beauty-render alpha with what is effectively a second copy of the same
whole-scene silhouette, rather than with the intended dynamic-only region. The
qualitative effect this had on `docs/test1_probe_d_relight.md`'s findings (in
particular, whether the background floor pattern was actually excluded from
the "dynamic-only" qualitative panels, or excluded for an unrelated reason) was
**not re-verified here** — this was a read-only survey of the `.blend` files,
not a re-run of the probe pipeline. Flagging this precisely so it can be
checked and, if needed, corrected: the fix is to threshold the mask's **RGB**
channel (e.g. channel-mean > some threshold) instead of Alpha in
`load_dynamic_mask()`.

## Significant finding: View Transform ("Raw" vs. "Standard") is a manual, per-file GUI setting — never scripted

`hook150_v3_NORMALS.blend` (from `blendfiles_for_normals_examples.zip`, whose
sibling file is literally named
`..._NORMALS_EXAMPLE_WATCH_COLORMANAGEMENTTAB.blend`) has **Color Management →
View Transform = "Raw"**, versus **"Standard"** in every main dataset file
(§2). Checked every `360view.py`/`Text` script in every file for any line
touching `view_settings`, `view_transform`, or colorspace: the **only**
colour-management line any of them ever sets, anywhere, is the environment
texture's own input colorspace
(`env_texture_node.image.colorspace_settings.name = "Linear Rec.709"`).
**View Transform is never set by code in any script surveyed — it is a saved
scene property the author sets by hand in the GUI, per file, per purpose.**
This is exactly the mechanism behind the author's warning: reusing one of
these files for a new kind of pass (e.g. duplicating a beauty-render file to
set up a normal-map render) silently keeps whichever View Transform the
duplicated file happened to have, and getting it wrong — "Standard" applied to
what's meant to be raw linear normal-vector data, or vice versa — corrupts the
output with no error or warning. **Anyone adapting these files for a new
render pass must check Color Management → View Transform by hand**; it cannot
be inferred from, or fixed by, the Python script alone.

---

## What could not be determined from code/data alone

- **The purpose of the 55 `Empty` objects** in each character scene — no
  animation data, no obvious naming, not referenced by any script surveyed.
  Likely Mixamo-rig leftovers; would need GUI inspection (outliner + parenting
  hierarchy) to confirm.
- **Whether `hook150_v5_specular32.blend`'s dynamic (non-static) dataset was
  ever generated from this exact file** — its `360view.py` only contains the
  static-timestep-1 variant (§1b). The dynamic hook150 set clearly exists in
  this repo's `data/`, so it was generated somehow, just apparently not
  captured in this saved buffer.
- **Exact cause of the "File written by a newer Blender binary (404.32)"
  warning** specific to `hook150_v5_specular32.blend` — plausibly an appended
  asset saved from a Blender 4.x session, not confirmed.
- **GUI-only view-layer/compositor state not captured by this survey's dump
  script** (e.g. Compositor "backdrop" or viewer-node settings, N-panel
  per-object display toggles) — the dump script reads `bpy.data`/`bpy.context`
  programmatically and would report any of these that affect render output,
  but was not cross-checked against a live GUI session (headless-only, per the
  task).
