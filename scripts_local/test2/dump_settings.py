#
# Dump the RESOLVED state of a .blend immediately after load, in a
# version-agnostic way, so the same file read by two Blender versions can be
# diffed. Used to test whether Blender 3.6's "written by newer Blender binary
# (404.32), expect loss of data" warning actually drops anything that matters.
#
# Run:  blender --background FILE.blend --python dump_settings.py -- out.json
#
import bpy, sys, json
from collections import Counter

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/settings.json"


def g(obj, name, default=None):
    try:
        v = getattr(obj, name, default)
        return v if isinstance(v, (int, float, str, bool, type(None))) else str(v)
    except Exception as e:
        return f"<ERR {e}>"


sc = bpy.context.scene
r = sc.render
d = {}
d["blender_version"] = bpy.app.version_string
d["blender_version_tuple"] = list(bpy.app.version)
d["file"] = bpy.data.filepath
d["file_version"] = list(bpy.data.version) if hasattr(bpy.data, "version") else None

d["render"] = {k: g(r, k) for k in
               ["engine", "resolution_x", "resolution_y", "resolution_percentage",
                "film_transparent", "use_persistent_data", "fps", "use_compositing",
                "use_sequencer"]}
d["render"]["image_settings"] = {k: g(r.image_settings, k) for k in
                                 ["file_format", "color_mode", "color_depth", "exr_codec",
                                  "color_management"]}

d["cycles"] = {k: g(sc.cycles, k) for k in
               ["device", "samples", "preview_samples", "use_adaptive_sampling",
                "adaptive_threshold", "max_bounces", "diffuse_bounces", "glossy_bounces",
                "transmission_bounces", "volume_bounces", "transparent_max_bounces",
                "use_denoising", "denoiser", "caustics_reflective", "caustics_refractive",
                "sample_clamp_direct", "sample_clamp_indirect", "blur_glossy",
                "light_sampling_threshold", "use_light_tree"]} if hasattr(sc, "cycles") else None

d["color_management"] = {
    "view_transform": g(sc.view_settings, "view_transform"),
    "look": g(sc.view_settings, "look"),
    "exposure": g(sc.view_settings, "exposure"),
    "gamma": g(sc.view_settings, "gamma"),
    "use_curve_mapping": g(sc.view_settings, "use_curve_mapping"),
    "display_device": g(sc.display_settings, "display_device"),
    "sequencer_colorspace": g(sc.sequencer_colorspace_settings, "name"),
}

d["frame"] = {"start": sc.frame_start, "end": sc.frame_end, "current": sc.frame_current}

# view layer passes
vl = sc.view_layers[0]
d["view_layer_name"] = vl.name
d["passes"] = {k: g(vl, k) for k in sorted(dir(vl)) if k.startswith("use_pass_")}
d["n_view_layers"] = len(sc.view_layers)

# datablock counts
d["counts"] = {
    "objects": len(bpy.data.objects),
    "meshes": len(bpy.data.meshes),
    "materials": len(bpy.data.materials),
    "images": len(bpy.data.images),
    "armatures": len(bpy.data.armatures),
    "actions": len(bpy.data.actions),
    "worlds": len(bpy.data.worlds),
    "cameras": len(bpy.data.cameras),
    "lights": len(bpy.data.lights),
    "texts": len(bpy.data.texts),
    "node_groups": len(bpy.data.node_groups),
    "collections": len(bpy.data.collections),
    "scenes": len(bpy.data.scenes),
}
d["object_types"] = dict(Counter(o.type for o in bpy.data.objects))

# geometry totals (a real data-loss canary)
tot_v = tot_p = 0
for m in bpy.data.meshes:
    tot_v += len(m.vertices); tot_p += len(m.polygons)
d["geometry"] = {"total_vertices": tot_v, "total_polygons": tot_p}

# armature-driven meshes (the mask definition used by Test 2)
arm = bpy.data.objects.get("Armature")
d["armature_driven_meshes"] = sorted(
    o.name for o in bpy.data.objects
    if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))

# modifiers actually present
d["modifier_types"] = dict(Counter(m.type for o in bpy.data.objects for m in o.modifiers))

# images + colour spaces (as stored in the file)
d["images"] = {im.name: {"filepath": im.filepath,
                         "colorspace": g(im.colorspace_settings, "name"),
                         "size": list(im.size), "source": g(im, "source"),
                         "is_float": g(im, "is_float"),
                         "depth": g(im, "depth")}
               for im in bpy.data.images}

# world node graph
w = sc.world
if w:
    wd = {"name": w.name, "use_nodes": w.use_nodes}
    if w.use_nodes and w.node_tree:
        wd["nodes"] = []
        for n in w.node_tree.nodes:
            ni = {"name": n.name, "type": n.type}
            if n.type == "TEX_ENVIRONMENT":
                ni["image"] = n.image.name if n.image else None
                ni["image_colorspace"] = g(n.image.colorspace_settings, "name") if n.image else None
                ni["projection"] = g(n, "projection")
            if n.type == "BACKGROUND":
                try:
                    ni["strength"] = n.inputs["Strength"].default_value
                except Exception:
                    pass
            wd["nodes"].append(ni)
        wd["links"] = [f"{l.from_node.name}.{l.from_socket.name} -> {l.to_node.name}.{l.to_socket.name}"
                       for l in w.node_tree.links]
    d["world"] = wd

# materials: node counts + principled params (input names differ across versions)
mats = {}
for m in bpy.data.materials:
    mi = {"use_nodes": m.use_nodes,
          "n_nodes": len(m.node_tree.nodes) if (m.use_nodes and m.node_tree) else 0,
          "node_types": dict(Counter(n.type for n in m.node_tree.nodes)) if (m.use_nodes and m.node_tree) else {}}
    if m.use_nodes and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                inp = {}
                for sock in n.inputs:
                    if sock.is_linked:
                        inp[sock.name] = "LINKED"
                    else:
                        try:
                            v = sock.default_value
                            inp[sock.name] = list(v) if hasattr(v, "__len__") else float(v)
                        except Exception:
                            pass
                mi["principled_inputs"] = inp
                break
    mats[m.name] = mi
d["materials"] = mats

# camera
cam = bpy.data.objects.get("Camera")
if cam:
    d["camera"] = {"location": list(cam.location), "rotation_euler": list(cam.rotation_euler),
                   "parent": cam.parent.name if cam.parent else None,
                   "n_constraints": len(cam.constraints),
                   "constraint_types": dict(Counter(c.type for c in cam.constraints)),
                   "lens": g(cam.data, "lens"), "sensor_width": g(cam.data, "sensor_width"),
                   "angle_x": g(cam.data, "angle_x"), "type": g(cam.data, "type")}

with open(out, "w") as f:
    json.dump(d, f, indent=2, default=str, sort_keys=True)
print("WROTE", out)
