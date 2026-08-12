#
# Test 2 -- render one configuration of the indirect-fraction ladder.
# Run inside Blender:
#   blender --background work/jj_work.blend --python render_config.py -- \
#           --config step1 --frames 10 40 70 100 130 --out out/step1 --samples 512
#
# READ-ONLY w.r.t. blend_files/: operates on a COPY. Never saves the .blend.
#
import bpy, sys, os, argparse, json
import numpy as np
from math import radians
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True)
ap.add_argument("--frames", type=int, nargs="+", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--samples", type=int, default=512)
ap.add_argument("--diffuse_bounces", type=int, default=1)
ap.add_argument("--max_bounces", type=int, default=None)
ap.add_argument("--envmap", default=None)
ap.add_argument("--view_transform", default="Raw")
a = ap.parse_args(argv)

scene = bpy.context.scene
os.makedirs(a.out, exist_ok=True)

# ---------------------------------------------------------------- render cfg
scene.render.engine = "CYCLES"
scene.cycles.device = "GPU"
scene.cycles.samples = a.samples
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False          # denoising mixes passes -> must be off
scene.cycles.diffuse_bounces = a.diffuse_bounces
if a.max_bounces is not None:
    scene.cycles.max_bounces = a.max_bounces
elif a.diffuse_bounces > scene.cycles.max_bounces:
    scene.cycles.max_bounces = max(a.diffuse_bounces, scene.cycles.max_bounces)
scene.render.resolution_x = scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.use_persistent_data = True

# EXR, linear, explicit colour management. View Transform is a GUI-only setting
# in the shipped files (docs/blend_files_survey.md) -- set explicitly here.
scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "32"
scene.render.image_settings.exr_codec = "ZIP"
scene.view_settings.view_transform = a.view_transform
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
try:
    scene.render.image_settings.color_management = "OVERRIDE"
    scene.render.image_settings.view_settings.view_transform = a.view_transform
    scene.render.image_settings.view_settings.look = "None"
except Exception as e:
    print("WARN colour-management override:", e)

# ---------------------------------------------------------------- passes
vl = scene.view_layers[0]
for p in ["use_pass_combined", "use_pass_diffuse_direct", "use_pass_diffuse_indirect",
          "use_pass_glossy_direct", "use_pass_glossy_indirect", "use_pass_diffuse_color",
          "use_pass_glossy_color", "use_pass_emit", "use_pass_environment",
          "use_pass_object_index", "use_pass_z"]:
    setattr(vl, p, True)
scene.use_nodes = False   # bypass the shipped compositor; write render result directly

# ---------------------------------------------------------------- object index
# pass_index = 1 on armature-driven meshes == exactly the "dynamic" definition
# the dataset's own dynamic_mask generator uses (docs/blend_files_survey.md 1c).
arm = bpy.data.objects.get("Armature")
n_char = 0
for o in bpy.data.objects:
    if o.type == "MESH":
        dyn = any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)
        o.pass_index = 1 if dyn else 0
        n_char += int(dyn)
print(f"[cfg] tagged {n_char} armature-driven mesh(es) with pass_index=1")

# ---------------------------------------------------------------- world / envmap
world = scene.world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
bg = nt.nodes.new("ShaderNodeBackground")
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.projection = "EQUIRECTANGULAR"
outw = nt.nodes.new("ShaderNodeOutputWorld")
mapn = nt.nodes.new("ShaderNodeMapping"); mapn.vector_type = "TEXTURE"
tc = nt.nodes.new("ShaderNodeTexCoord")
nt.links.new(tc.outputs["Generated"], mapn.inputs["Vector"])
nt.links.new(mapn.outputs["Vector"], env.inputs["Vector"])
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
nt.links.new(bg.outputs["Background"], outw.inputs["Surface"])
if a.envmap:
    img = bpy.data.images.load(a.envmap)
    # The shipped generator sets "Linear Rec.709" -- that is the Blender 4.x OCIO
    # name (these files were saved by 4.x). Blender 3.6's default config calls the
    # same space (linear, Rec.709 primaries) simply "Linear".
    for cs in ("Linear Rec.709", "Linear"):
        try:
            img.colorspace_settings.name = cs
            print(f"[cfg] envmap colorspace = {cs!r}")
            break
        except TypeError:
            continue
    else:
        raise RuntimeError("no linear Rec.709 colorspace available")
    env.image = img
mapn.inputs["Rotation"].default_value[2] = radians(0)

# ---------------------------------------------------------------- scene geometry
def grey_mat(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = 0.0
    if "Specular" in b.inputs:
        b.inputs["Specular"].default_value = 0.5
    return m

def char_bounds():
    """World-space bbox of the armature-driven meshes at the current frame."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.pass_index == 1:
            oe = o.evaluated_get(dg)
            for c in oe.bound_box:
                pts.append(o.matrix_world @ Vector(c))
    if not pts:
        return Vector((0, 0, 0)), Vector((1, 1, 2))
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    lo = Vector((min(xs), min(ys), min(zs))); hi = Vector((max(xs), max(ys), max(zs)))
    return lo, hi

added = []
def add_plane(name, size, loc, rot, mat):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.data.materials.append(mat); o.pass_index = 0
    added.append(o); return o

cfg = a.config
if cfg in ("step3_corner", "step4_colour"):
    bpy.context.scene.frame_set(a.frames[0])
    lo, hi = char_bounds()
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    width = max(hi.x - lo.x, hi.y - lo.y)          # character width
    height = hi.z - lo.z
    d = 1.5 * width                                 # 1-2 character-widths away
    S = 4.0                                         # wall extent (room-scale, not a huge plane)
    grey = grey_mat("T2_Grey", (0.5, 0.5, 0.5))
    red = grey_mat("T2_Red", (0.8, 0.05, 0.05))
    # two vertical walls meeting at a corner on the -X/-Y side of the figure
    add_plane("T2_WallX", S, (cx - d, cy, lo.z + S / 2), (0, radians(90), 0),
              red if cfg == "step4_colour" else grey)
    add_plane("T2_WallY", S, (cx, cy - d, lo.z + S / 2), (radians(90), 0, 0), grey)
    print(f"[cfg] corner: char width {width:.3f} height {height:.3f}, wall dist {d:.3f} "
          f"({d/width:.2f} char-widths), wall extent {S:.3f}"
          f"{', X-wall RED albedo 0.8' if cfg == 'step4_colour' else ''}")

elif cfg == "step6_interior":
    bpy.context.scene.frame_set(a.frames[0])
    lo, hi = char_bounds()
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    height = hi.z - lo.z
    # Cornell-box style: floor, ceiling, and 3 walls, OPEN on the +Y side.
    # A fully sealed box admits no environment light at all and renders pure
    # black (verified) -- the open side is what lets the envmap in, and is the
    # standard configuration for this kind of enclosure test.
    R = 3.5                                         # room half-extent; camera sits inside
    CEIL = lo.z + 4.0
    grey = grey_mat("T2_Grey", (0.5, 0.5, 0.5))
    zc = (lo.z + CEIL) / 2
    add_plane("T2_WX0", 2 * R, (cx - R, cy, zc), (0, radians(90), 0), grey)
    add_plane("T2_WX1", 2 * R, (cx + R, cy, zc), (0, radians(90), 0), grey)
    add_plane("T2_WY0", 2 * R, (cx, cy - R, zc), (radians(90), 0, 0), grey)
    add_plane("T2_Ceil", 2 * R, (cx, cy, CEIL), (0, 0, 0), grey)
    add_plane("T2_Floor", 2 * R, (cx, cy, lo.z - 0.01), (0, 0, 0), grey)
    print(f"[cfg] interior room (open +Y): half-extent {R:.2f}, ceiling {CEIL:.2f}, "
          f"floor {lo.z:.2f} (figure height {height:.2f})")

elif cfg == "step5_cloth":
    # Character is FROZEN at one pose so the cloth sim is stable and
    # reproducible; the 30 "frames" then become 30 distinct camera angles on
    # one genuinely-folded configuration. This isolates the cloth variable.
    POSE = a.frames[0]
    bpy.context.scene.frame_set(POSE)
    lo, hi = char_bounds()
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    width = max(hi.x - lo.x, hi.y - lo.y)
    grey = grey_mat("T2_Cloth", (0.6, 0.6, 0.6))
    sz = 2.2 * max(width, 0.5)
    bpy.ops.mesh.primitive_plane_add(size=sz, location=(cx, cy, hi.z + 0.25))
    cloth = bpy.context.active_object; cloth.name = "T2_Cloth"
    cloth.data.materials.append(grey)
    cloth.pass_index = 1                      # cloth is part of the measured subject
    m = cloth.modifiers.new("Subsurf", "SUBSURF"); m.subdivision_type = "SIMPLE"
    m.levels = m.render_levels = 6            # 64x64 quads -> real folds
    bpy.ops.object.modifier_apply(modifier=m.name)
    cm = cloth.modifiers.new("Cloth", "CLOTH")
    cm.settings.quality = 10
    cm.settings.mass = 0.3
    cm.settings.tension_stiffness = 5
    cm.settings.compression_stiffness = 5
    cm.settings.bending_stiffness = 0.05      # low bending -> pronounced folds
    cm.collision_settings.distance_min = 0.005
    cm.collision_settings.collision_quality = 5
    cm.collision_settings.use_self_collision = True
    cm.collision_settings.self_distance_min = 0.005
    cm.point_cache.frame_start = POSE
    cm.point_cache.frame_end = POSE + 120
    for o in bpy.data.objects:                # character + floor collide
        if o.type == "MESH" and o is not cloth and not o.name.startswith("T2_"):
            if not any(mm.type == "COLLISION" for mm in o.modifiers):
                o.modifiers.new("Collision", "COLLISION")
    added.append(cloth)
    # step the sim forward so the cloth settles into folds
    SETTLE = 90
    for f in range(POSE, POSE + SETTLE + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
    CLOTH_SETTLED_FRAME = POSE + SETTLE
    print(f"[cfg] cloth: size {sz:.3f}, 64x64, self-collision on, settled {SETTLE} frames "
          f"over frozen pose {POSE} -> render frame {CLOTH_SETTLED_FRAME}")

print(f"[cfg] config={cfg} samples={a.samples} diffuse_bounces={scene.cycles.diffuse_bounces} "
      f"max_bounces={scene.cycles.max_bounces} denoise={scene.cycles.use_denoising} "
      f"view_transform={scene.view_settings.view_transform}")

# ---------------------------------------------------------------- camera (dataset trajectory)
cam = scene.objects["Camera"]
for c in list(cam.constraints):      # 61 accumulated TRACK_TO constraints in the shipped file
    cam.constraints.remove(c)
cam.parent = None
# Dataset camera sits at radius ~4.9 from the look-at point. For the enclosure
# configs that puts it OUTSIDE the walls (frames would show only wall), so it is
# pulled inside. 3.0 still frames a ~2m figure comfortably at 50mm / 39.6 deg FOV
# (needs >=2.8m). Documented in docs/test2_indirect_fraction_ladder.md.
if cfg in ("step3_corner", "step4_colour", "step6_interior"):
    CAM_LOC = (0, 3.0, 0.0)
else:
    CAM_LOC = (0, 4.0, 2.0)          # jumpingjacks' own script value
cam.location = CAM_LOC
emp = bpy.data.objects.new("T2_CamEmpty", None)
emp.location = (0.0, 0.0, 0.65)
scene.collection.objects.link(emp)
cam.parent = emp
con = cam.constraints.new(type="TRACK_TO")
con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"; con.target = emp
scene.camera = cam

CORNER_CFGS = ("step3_corner", "step4_colour")

def camera_rot_for(frame_id, views=150, seed=40422):
    """Replay the shipped generator's RNG stream to recover frame_id's camera.

    For the corner configs the walls occupy the -X/-Y side, so an unrestricted
    full-sphere azimuth puts the camera behind a wall for ~half the frames
    (verified: 16/30 frames had <5000 visible character px). Azimuth is
    therefore remapped into the OPEN quadrant; elevation sampling is unchanged.
    """
    rng = np.random.RandomState(seed)
    out = None
    for i in range(1, views + 1):
        u = rng.uniform(0, 1, size=3)
        rot = u * np.array([1, 0, 2 * np.pi])
        rot[0] = np.abs(np.arccos(1 - 2 * rot[0]) - np.pi / 2)
        if cfg in CORNER_CFGS:
            # Base camera offset is (0,+3,0). A +Z euler rotation by t maps
            # (0,3) -> (-3 sin t, 3 cos t), i.e. POSITIVE t swings toward -X --
            # straight behind the -X wall. The open (+X,+Y) quadrant is
            # therefore t in [-90, 0] deg, not [0, +90].
            rot[2] = -u[2] * (np.pi / 2)
            rot[0] = min(rot[0], np.pi / 3)      # keep off the poles
        elif cfg == "step6_interior":
            rot[2] = (u[2] - 0.5) * (np.pi / 2)  # azimuth -> +/-45 deg about the open +Y side
            rot[0] = min(rot[0], np.pi / 4)      # stay inside the room, off the ceiling
        if i == frame_id:
            out = rot
    return out

# ---------------------------------------------------------------- render
meta = {"config": cfg, "samples": a.samples, "diffuse_bounces": scene.cycles.diffuse_bounces,
        "max_bounces": scene.cycles.max_bounces, "glossy_bounces": scene.cycles.glossy_bounces,
        "denoising": scene.cycles.use_denoising, "view_transform": scene.view_settings.view_transform,
        "envmap": a.envmap, "camera_location": list(CAM_LOC), "frames": a.frames,
        "n_character_meshes": n_char, "added_objects": [o.name for o in added]}

for fid in a.frames:
    if cfg == "step5_cloth":
        # hold the settled cloth+pose; vary only the camera (see cfg block)
        scene.frame_set(CLOTH_SETTLED_FRAME)
    else:
        scene.frame_set(fid)
    emp.rotation_euler = camera_rot_for(fid)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(a.out, f"f{fid:04d}")
    bpy.ops.render.render(write_still=True)
    print(f"[render] frame {fid} -> {scene.render.filepath}.exr")

with open(os.path.join(a.out, "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
print("[done]", cfg)
