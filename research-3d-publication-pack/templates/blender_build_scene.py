#!/usr/bin/env python3
"""
T08-blender-scene: Reproducible Blender 4.5 scene builder for HHSA 3-D Spectral Landscape.
Generates:
  - phase2/blender/hhsa_scene.blend
  - site/assets/models/hhsa_axes.glb
  - site/assets/models/cube_synthetic.glb
  - site/assets/models/cube_cgm.glb
  - site/assets/models/cube_hrv_sessionA.glb
  - site/assets/models/cube_hrv_sessionB.glb
  - site/assets/img/hero.webp
  - site/assets/img/hero_turntable.webm
  - phase2/blender/blender_run.log
"""

import os
import sys
import json
import math
import time
import bpy
import bmesh
from mathutils import Vector, Euler, Matrix

LOG_LINES = []

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)

# Visual Spec Palette (§4.4) — sRGB to linear approx for Blender
def hex_to_linear(hex_str, alpha=1.0):
    h = hex_str.lstrip('#')
    sr, sg, sb = [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    def s2l(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (s2l(sr), s2l(sg), s2l(sb), alpha)

PALETTE = {
    "bg_primary": hex_to_linear("#0a0f1e"),
    "bg_card": hex_to_linear("#111d3c"),
    "teal": hex_to_linear("#4dd9cf"),
    "teal_light": hex_to_linear("#7ee8e2"),
    "purple": hex_to_linear("#8b5cf6"),
    "purple_light": hex_to_linear("#a78bfa"),
    "gold": hex_to_linear("#f4a261"),
    "red": hex_to_linear("#ef4444"),
    "green": hex_to_linear("#22c55e"),
    "text": hex_to_linear("#e8f4f8"),
    "text_sec": hex_to_linear("#8ba8c4"),
}

CUBE_SIZE = 10.0  # 3D space spans [0, 10] along X (f_c), Y (f_AM), Z (t)

def find_cube_path(filename):
    candidates = [
        os.path.join("phase2", "cube", filename),
        os.path.join("cube", filename),
        os.path.join(os.path.dirname(__file__), "..", "cube", filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    raise FileNotFoundError(f"Cube JSON not found: {filename}")

def make_emissive_material(name, color_rgba, strength=2.5, alpha=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    if alpha < 1.0:
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'BLENDED'
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color_rgba
        bsdf.inputs["Roughness"].default_value = 0.25
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color_rgba
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = strength
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
    return mat

def make_glass_slab_material(name, color_rgba, alpha=0.12):
    # Spec 4.4: band slabs as translucent glass (alpha <= 0.15)
    alpha = min(alpha, 0.15)
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    if hasattr(mat, "blend_method"):
        mat.blend_method = 'BLEND'
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'BLENDED'
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (color_rgba[0], color_rgba[1], color_rgba[2], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.12
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = 0.65
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color_rgba
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.35
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
    return mat

def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)

def create_cylinder_between(p1, p2, radius, name, mat, collection):
    v1 = Vector(p1)
    v2 = Vector(p2)
    dv = v2 - v1
    length = dv.length
    if length < 1e-6:
        return None
    mid = (v1 + v2) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=radius, depth=length, location=mid)
    obj = bpy.context.active_object
    obj.name = name
    # Align Z axis to dv
    z_axis = Vector((0, 0, 1))
    rot_quat = z_axis.rotation_difference(dv.normalized())
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot_quat
    obj.data.materials.append(mat)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj

def create_text_mesh(text, location, rotation_euler, size, name, mat, collection):
    bpy.ops.object.text_add(location=location, rotation=rotation_euler)
    txt_obj = bpy.context.active_object
    txt_obj.name = name + "_tmp"
    txt_obj.data.body = text
    txt_obj.data.size = size
    txt_obj.data.extrude = size * 0.06
    txt_obj.data.align_x = 'CENTER'
    txt_obj.data.align_y = 'CENTER'
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.active_object
    mesh_obj.name = name
    mesh_obj.data.materials.append(mat)
    for c in list(mesh_obj.users_collection):
        c.objects.unlink(mesh_obj)
    collection.objects.link(mesh_obj)
    return mesh_obj

def log_pos(val, vmin, vmax):
    val_c = max(min(val, vmax), vmin)
    return CUBE_SIZE * (math.log10(val_c) - math.log10(vmin)) / (math.log10(vmax) - math.log10(vmin))

def lin_pos(val, vmin, vmax):
    val_c = max(min(val, vmax), vmin)
    return CUBE_SIZE * (val_c - vmin) / max(vmax - vmin, 1e-9)

def build_admissibility_wireframe(name, mat_gold, mat_gold_fill, collection):
    objs = []
    n_grid = 10
    for i in range(n_grid + 1):
        u = (i / n_grid) * CUBE_SIZE
        r = 0.035 if i in (0, n_grid) else 0.016
        o1 = create_cylinder_between((u, u, 0), (u, u, CUBE_SIZE), r, f"{name}_z_{i}", mat_gold, collection)
        o2 = create_cylinder_between((0, 0, u), (CUBE_SIZE, CUBE_SIZE, u), r, f"{name}_xy_{i}", mat_gold, collection)
        if o1: objs.append(o1)
        if o2: objs.append(o2)

    mesh = bpy.data.meshes.new(f"{name}_surf_mesh")
    obj = bpy.data.objects.new(f"{name}_surf", mesh)
    collection.objects.link(obj)
    verts = [(0, 0, 0), (CUBE_SIZE, CUBE_SIZE, 0), (CUBE_SIZE, CUBE_SIZE, CUBE_SIZE), (0, 0, CUBE_SIZE)]
    faces = [(0, 1, 2, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.data.materials.append(mat_gold_fill)
    objs.append(obj)
    return objs

def build_axis_frame_collection(syn_meta, cgm_meta, hrv_meta, materials):
    col = bpy.data.collections.new("HHSA_Axes_Frame")
    bpy.context.scene.collection.children.link(col)

    mat_teal = materials["teal_emissive"]
    mat_teal_grid = materials["teal_grid"]
    mat_gold = materials["gold_emissive"]
    mat_gold_fill = materials["gold_glass"]
    mat_text = materials["text_emissive"]

    corners = [
        (0,0,0), (CUBE_SIZE,0,0), (CUBE_SIZE,CUBE_SIZE,0), (0,CUBE_SIZE,0),
        (0,0,CUBE_SIZE), (CUBE_SIZE,0,CUBE_SIZE), (CUBE_SIZE,CUBE_SIZE,CUBE_SIZE), (0,CUBE_SIZE,CUBE_SIZE)
    ]
    primary_edges = [
        (0, 1, "Axis_X_Carrier_fc"),
        (0, 3, "Axis_Y_AM_fam"),
        (0, 4, "Axis_Z_Time_t"),
    ]
    for i1, i2, ename in primary_edges:
        create_cylinder_between(corners[i1], corners[i2], 0.055, ename, mat_teal, col)

    secondary_edges = [
        (1,2), (2,3), (4,5), (5,6), (6,7), (7,4), (1,5), (2,6), (3,7)
    ]
    for idx, (i1, i2) in enumerate(secondary_edges):
        create_cylinder_between(corners[i1], corners[i2], 0.02, f"Frame_Edge_{idx}", mat_teal_grid, col)

    fc_min, fc_max = hrv_meta["axes"]["fc"][0], hrv_meta["axes"]["fc"][-1]
    hz_ticks = [0.004, 0.01, 0.04, 0.15, 0.40, 1.0, 2.0]
    for tk in hz_ticks:
        pos = log_pos(tk, fc_min, fc_max)
        create_cylinder_between((pos, -0.22, 0), (pos, 0.12, 0), 0.025, f"Tick_fc_{tk}Hz", mat_teal, col)
        create_cylinder_between((pos, 0, 0), (pos, CUBE_SIZE, 0), 0.01, f"Grid_fc_{tk}Hz", mat_teal_grid, col)
        create_text_mesh(f"{tk:g} Hz", (pos, -0.55, 0), (math.radians(90), 0, 0), 0.26, f"Label_fc_{tk}Hz", mat_text, col)

        create_cylinder_between((-0.22, pos, 0), (0.12, pos, 0), 0.025, f"Tick_fam_{tk}Hz", mat_teal, col)
        create_cylinder_between((0, pos, 0), (CUBE_SIZE, pos, 0), 0.01, f"Grid_fam_{tk}Hz", mat_teal_grid, col)
        create_text_mesh(f"{tk:g} Hz", (-0.65, pos, 0), (math.radians(90), 0, math.radians(90)), 0.26, f"Label_fam_{tk}Hz", mat_text, col)

    t_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    for frac in t_ticks:
        zpos = frac * CUBE_SIZE
        t_sec = int(round(frac * syn_meta["record"]["duration"]))
        t_hr = int(round(frac * cgm_meta["record"]["duration"]))
        create_cylinder_between((-0.22, 0, zpos), (0.12, 0, zpos), 0.025, f"Tick_t_{t_sec}s", mat_teal, col)
        create_text_mesh(f"{t_sec}s / {t_hr}h", (-0.75, 0, zpos), (math.radians(90), 0, math.radians(45)), 0.24, f"Label_t_{t_sec}s", mat_text, col)

    create_text_mesh("Carrier Frequency f_c (log Hz | c/h)", (CUBE_SIZE * 0.5, -1.25, 0), (math.radians(90), 0, 0), 0.36, "Title_Axis_X_fc", mat_teal, col)
    create_text_mesh("AM Frequency f_AM (log Hz | c/h)", (-1.45, CUBE_SIZE * 0.5, 0), (math.radians(90), 0, math.radians(90)), 0.36, "Title_Axis_Y_fam", mat_teal, col)
    create_text_mesh("Time t (s | h)", (-1.35, -0.4, CUBE_SIZE * 0.5), (math.radians(90), 0, math.radians(45)), 0.36, "Title_Axis_Z_t", mat_teal, col)
    create_text_mesh("Admissibility Plane (f_AM = f_c)", (CUBE_SIZE * 0.68, CUBE_SIZE * 0.68, CUBE_SIZE + 0.45), (math.radians(90), 0, math.radians(45)), 0.32, "Title_Admissibility", mat_gold, col)

    band_mats = [materials["slab_teal"], materials["slab_purple"], materials["slab_gold"], materials["slab_teal_alt"]]
    for b_idx, band in enumerate(hrv_meta["bands"]):
        bname = band["name"]
        x0 = log_pos(band["lo"], fc_min, fc_max)
        x1 = log_pos(band["hi"], fc_min, fc_max)
        cx = 0.5 * (x0 + x1)
        dx = max(x1 - x0, 0.1)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, CUBE_SIZE * 0.5, CUBE_SIZE * 0.5))
        slab = bpy.context.active_object
        slab.name = f"BandSlab_fc_{bname}"
        slab.scale = (dx * 0.98, CUBE_SIZE, CUBE_SIZE)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        slab.data.materials.append(band_mats[b_idx % len(band_mats)])
        for c in list(slab.users_collection):
            c.objects.unlink(slab)
        col.objects.link(slab)

    build_admissibility_wireframe("Admissibility_fAM_eq_fc", mat_gold, mat_gold_fill, col)

    root_empty = bpy.data.objects.new("HHSA_Axes_Metadata", None)
    col.objects.link(root_empty)
    root_empty["axes_log"] = True
    root_empty["hz_range"] = [fc_min, fc_max]
    root_empty["cph_range"] = [cgm_meta["axes"]["fc"][0], cgm_meta["axes"]["fc"][-1]]
    root_empty["hrv_bands_json"] = json.dumps(hrv_meta["bands"])
    root_empty["cgm_bands_json"] = json.dumps(cgm_meta["bands"])

    return col

def build_dataset_cube_collection(cube_meta, col_name, materials):
    col = bpy.data.collections.new(col_name)
    bpy.context.scene.collection.children.link(col)

    ds_name = cube_meta["dataset"]
    units_f = cube_meta["units"]["f"]
    units_t = cube_meta["units"]["t"]
    fc_arr = cube_meta["axes"]["fc"]
    fam_arr = cube_meta["axes"]["fam"]
    t_arr = cube_meta["axes"]["t"]
    bands = cube_meta["bands"]
    fc_min, fc_max = fc_arr[0], fc_arr[-1]
    fam_min, fam_max = fam_arr[0], fam_arr[-1]
    t_min, t_max = t_arr[0], t_arr[-1]

    mat_teal = materials["teal_emissive"]
    mat_purple = materials["purple_emissive"]
    mat_gold = materials["gold_emissive"]
    mat_text = materials["text_emissive"]

    create_cylinder_between((0,0,0), (CUBE_SIZE,0,0), 0.04, f"{ds_name}_Axis_fc", mat_teal, col)
    create_cylinder_between((0,0,0), (0,CUBE_SIZE,0), 0.04, f"{ds_name}_Axis_fam", mat_teal, col)
    create_cylinder_between((0,0,0), (0,0,CUBE_SIZE), 0.04, f"{ds_name}_Axis_t", mat_teal, col)

    band_mats = [materials["slab_teal"], materials["slab_purple"], materials["slab_gold"], materials["slab_teal_alt"]]
    for b_idx, b in enumerate(bands):
        bname = b["name"]
        x0 = log_pos(b["lo"], fc_min, fc_max)
        x1 = log_pos(b["hi"], fc_min, fc_max)
        cx = 0.5 * (x0 + x1)
        dx = max(x1 - x0, 0.08)

        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, CUBE_SIZE * 0.5, 0.06))
        slab = bpy.context.active_object
        slab.name = f"{ds_name}_BandSlab_{bname}"
        slab.scale = (dx * 0.96, CUBE_SIZE, 0.12)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        slab.data.materials.append(band_mats[b_idx % len(band_mats)])
        for c in list(slab.users_collection):
            c.objects.unlink(slab)
        col.objects.link(slab)

        if units_f == "cph":
            period_h = 1.0 / b["hi"]
            p_str = f"{period_h:.0f}h" if period_h >= 1.0 else f"{period_h*60:.0f}m"
            lbl = f"{b['hi']:g} c/h · {p_str}"
        else:
            lbl = f"{b['hi']:g} Hz ({bname})"
        create_cylinder_between((x1, -0.18, 0), (x1, 0.12, 0), 0.02, f"{ds_name}_Tick_{bname}", mat_teal, col)
        create_text_mesh(lbl, (cx, -0.48, 0), (math.radians(90), 0, 0), 0.21, f"{ds_name}_Label_{bname}", mat_text, col)

    band_cube = cube_meta.get("band_cube", [])
    n_bands = len(bands)
    if band_cube:
        if isinstance(band_cube[0][0], list):
            n_w = len(band_cube)
            mean_mat = [[0.0]*n_bands for _ in range(n_bands)]
            max_val = 1e-6
            for w in range(n_w):
                for i in range(min(n_bands, len(band_cube[w]))):
                    for j in range(min(n_bands, len(band_cube[w][i]))):
                        val = float(band_cube[w][i][j])
                        mean_mat[i][j] += val / n_w
                        if val > max_val:
                            max_val = val
        else:
            mean_mat = band_cube
            max_val = max(max(row) for row in mean_mat) if mean_mat else 1.0

        grid_n = 28
        mesh = bpy.data.meshes.new(f"{ds_name}_BandLandscape_Mesh")
        landscape_obj = bpy.data.objects.new(f"{ds_name}_BandLandscape", mesh)
        col.objects.link(landscape_obj)

        b_centers = []
        b_sigmas = []
        for b in bands:
            x0 = log_pos(b["lo"], fc_min, fc_max)
            x1 = log_pos(b["hi"], fc_min, fc_max)
            b_centers.append(0.5 * (x0 + x1))
            b_sigmas.append(max(0.45 * (x1 - x0), 0.45))

        verts = []
        faces = []
        for ix in range(grid_n + 1):
            u = (ix / grid_n) * CUBE_SIZE
            for iy in range(grid_n + 1):
                v = (iy / grid_n) * CUBE_SIZE
                h_val = 0.0
                for bi in range(n_bands):
                    for bj in range(n_bands):
                        w_ij = mean_mat[bi][bj] / max(max_val, 1e-6)
                        if w_ij > 0:
                            dx = (u - b_centers[bi]) / b_sigmas[bi]
                            dy = (v - b_centers[bj]) / b_sigmas[bj]
                            h_val += w_ij * math.exp(-0.5 * (dx*dx + dy*dy))
                z_height = 0.15 + min(h_val, 1.35) * 2.2
                verts.append((u, v, z_height))

        for ix in range(grid_n):
            for iy in range(grid_n):
                v0 = ix * (grid_n + 1) + iy
                v1 = v0 + 1
                v2 = (ix + 1) * (grid_n + 1) + iy + 1
                v3 = (ix + 1) * (grid_n + 1) + iy
                faces.append((v0, v3, v2, v1))

        mesh.from_pydata(verts, [], faces)
        for poly in mesh.polygons:
            poly.use_smooth = True
        mesh.update()
        landscape_obj.data.materials.append(materials["landscape_surface"])

    # Real cubes carry up to 10k sparse cells; one icosphere each would make a multi-MB GLB,
    # so the model keeps the strongest cells and the browser draws the full cloud itself.
    h_sparse = sorted(cube_meta.get("H_sparse", []), key=lambda pt: pt[3], reverse=True)[:400]
    if h_sparse:
        max_e = max(pt[3] for pt in h_sparse) if h_sparse else 1.0
        bm = bmesh.new()
        for pt in h_sparse:
            t_idx, fc_idx, fam_idx, energy = int(pt[0]), int(pt[1]), int(pt[2]), float(pt[3])
            t_val = t_arr[min(max(t_idx, 0), len(t_arr)-1)]
            fc_val = fc_arr[min(max(fc_idx, 0), len(fc_arr)-1)]
            fam_val = fam_arr[min(max(fam_idx, 0), len(fam_arr)-1)]

            x = log_pos(fc_val, fc_min, fc_max)
            y = log_pos(fam_val, fam_min, fam_max)
            z = lin_pos(t_val, t_min, t_max)
            norm_e = energy / max(max_e, 1e-6)
            radius = 0.10 + 0.24 * (norm_e ** 0.7)

            bmesh.ops.create_icosphere(
                bm,
                subdivisions=1,
                radius=radius,
                matrix=Matrix.Translation((x, y, z))
            )

        lobe_mesh = bpy.data.meshes.new(f"{ds_name}_EnergyLobes_Mesh")
        bm.to_mesh(lobe_mesh)
        bm.free()
        for poly in lobe_mesh.polygons:
            poly.use_smooth = True
        lobe_obj = bpy.data.objects.new(f"{ds_name}_EnergyLobes", lobe_mesh)
        col.objects.link(lobe_obj)
        lobe_obj.data.materials.append(mat_purple if not cube_meta.get("synthetic") else mat_teal)

    if "truth" in cube_meta and "fc_at_windows" in cube_meta["truth"]:
        fc_w = cube_meta["truth"]["fc_at_windows"]
        fam_w = cube_meta["truth"]["fam_at_windows"]
        pts = []
        for idx in range(min(len(t_arr), len(fc_w), len(fam_w))):
            px = log_pos(fc_w[idx], fc_min, fc_max)
            py = log_pos(fam_w[idx], fam_min, fam_max)
            pz = lin_pos(t_arr[idx], t_min, t_max)
            pts.append((px, py, pz))
        for k in range(len(pts) - 1):
            create_cylinder_between(pts[k], pts[k+1], 0.08, f"{ds_name}_TruthRidge_{k}", mat_gold, col)

    meta_obj = bpy.data.objects.new(f"{ds_name}_Metadata", None)
    col.objects.link(meta_obj)
    meta_obj["dataset"] = ds_name
    meta_obj["units_f"] = units_f
    meta_obj["units_t"] = units_t
    meta_obj["log_axes"] = bool(cube_meta["axes"].get("log", True))
    meta_obj["fc_range"] = [fc_min, fc_max]
    meta_obj["fam_range"] = [fam_min, fam_max]
    meta_obj["t_range"] = [t_min, t_max]
    meta_obj["bands_json"] = json.dumps(bands)

    return col

def export_collection_glb(col, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col.objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_yup=True,
        export_extras=True,
        export_materials='EXPORT'
    )
    size_kb = os.path.getsize(filepath) / 1024.0
    log(f"Exported {filepath} ({size_kb:.1f} KB, {len(col.objects)} objects)")

def setup_studio_and_render(axes_col, syn_col, cgm_col, hero_webp_path, turntable_webm_path):
    log("Entering setup_studio_and_render...")
    scene = bpy.context.scene

    if scene.world is None:
        world = bpy.data.worlds.new("HHSA_Dark_Studio")
        scene.world = world
    else:
        world = scene.world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = PALETTE["bg_primary"]
        bg_node.inputs["Strength"].default_value = 1.0
    log("World configured.")

    for o in bpy.data.objects:
        o.hide_render = True
    for c in (axes_col, syn_col):
        for o in c.objects:
            o.hide_render = False
    for o in cgm_col.objects:
        if "EnergyLobes" in o.name or "BandLandscape" in o.name:
            o.hide_render = False
    log("Visibility configured.")

    light_data1 = bpy.data.lights.new(name="KeyLight_Teal", type='AREA')
    light_data1.energy = 800.0
    light_data1.color = PALETTE["teal_light"][:3]
    light_data1.size = 12.0
    light1 = bpy.data.objects.new(name="KeyLight_Teal", object_data=light_data1)
    light1.location = (16.0, -14.0, 15.0)
    light1.rotation_euler = (math.radians(50), 0, math.radians(40))
    scene.collection.objects.link(light1)

    light_data2 = bpy.data.lights.new(name="FillLight_Purple", type='AREA')
    light_data2.energy = 600.0
    light_data2.color = PALETTE["purple_light"][:3]
    light_data2.size = 12.0
    light2 = bpy.data.objects.new(name="FillLight_Purple", object_data=light_data2)
    light2.location = (-12.0, 16.0, 12.0)
    light2.rotation_euler = (math.radians(55), 0, math.radians(-135))
    scene.collection.objects.link(light2)

    light_data3 = bpy.data.lights.new(name="RimLight_Gold", type='POINT')
    light_data3.energy = 450.0
    light_data3.color = PALETTE["gold"][:3]
    light3 = bpy.data.objects.new(name="RimLight_Gold", object_data=light_data3)
    light3.location = (5.0, 5.0, 16.0)
    scene.collection.objects.link(light3)
    log("Lights configured.")

    pivot = bpy.data.objects.new("Camera_Pivot", None)
    pivot.location = (5.0, 5.0, 4.6)
    scene.collection.objects.link(pivot)

    cam_data = bpy.data.cameras.new("Hero_Camera")
    cam_data.lens = 36.0
    cam_obj = bpy.data.objects.new("Hero_Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    cam_obj.parent = pivot
    cam_obj.location = (14.5, -14.5, 8.2)

    direction = Vector((0.0, 0.0, 0.0)) - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = rot_quat.to_euler()

    scene.camera = cam_obj
    log("Camera configured.")

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.use_adaptive_sampling = True
    if hasattr(scene.cycles, "adaptive_threshold"):
        scene.cycles.adaptive_threshold = 0.05
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 3
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 1
    scene.cycles.transmission_bounces = 2
    scene.cycles.volume_bounces = 0
    scene.cycles.transparent_max_bounces = 4
    log("Cycles CPU configured.")

    scene.render.fps = 12
    scene.frame_start = 1
    scene.frame_end = 24
    pivot.rotation_mode = 'XYZ'
    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert(data_path="rotation_euler", frame=1)
    pivot.rotation_euler = (0, 0, math.radians(360))
    pivot.keyframe_insert(data_path="rotation_euler", frame=25)
    log("Keyframes inserted.")

    blend_path = os.path.abspath("phase2/blender/hhsa_scene.blend")
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    log(f"Saving .blend to {blend_path}...")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    log(f"Saved Blender scene to {blend_path} ({os.path.getsize(blend_path)/1024:.1f} KB)")

    os.makedirs(os.path.dirname(hero_webp_path), exist_ok=True)
    scene.frame_set(4)
    scene.cycles.samples = 16
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'WEBP'
    scene.render.image_settings.quality = 92
    scene.render.filepath = hero_webp_path

    log(f"Rendering 1920x1080 hero image to {hero_webp_path} using {scene.render.engine} (CPU)...")
    bpy.ops.render.render(write_still=True)
    log(f"Hero render complete ({os.path.getsize(hero_webp_path)/1024:.1f} KB)")

    os.makedirs(os.path.dirname(turntable_webm_path), exist_ok=True)
    scene.cycles.samples = 8
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'WEBM'
    scene.render.ffmpeg.codec = 'WEBM'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.filepath = turntable_webm_path

    log(f"Rendering turntable animation (24 frames @ 12 fps) to {turntable_webm_path}...")
    bpy.ops.render.render(animation=True)
    if not os.path.exists(turntable_webm_path):
        parent_dir = os.path.dirname(turntable_webm_path)
        for fn in os.listdir(parent_dir):
            if fn.startswith("hero_turntable") and fn.endswith(".webm"):
                src = os.path.join(parent_dir, fn)
                if os.path.abspath(src) != os.path.abspath(turntable_webm_path):
                    os.replace(src, turntable_webm_path)
                break
    log(f"Turntable animation complete ({os.path.getsize(turntable_webm_path)/1024:.1f} KB)")

def main():
    t0 = time.time()
    log("Starting T08 Blender 4.5 scene generation...")
    clear_scene()

    syn_meta = json.load(open(find_cube_path("synthetic_cube.json"), "r", encoding="utf-8"))
    cgm_meta = json.load(open(find_cube_path("cgm_cube.json"), "r", encoding="utf-8"))
    hrvA_meta = json.load(open(find_cube_path("hrv_sessionA_cube.json"), "r", encoding="utf-8"))
    hrvB_meta = json.load(open(find_cube_path("hrv_sessionB_cube.json"), "r", encoding="utf-8"))
    log("Loaded all 4 cube JSON metadata files.")

    materials = {
        "teal_emissive": make_emissive_material("Mat_Teal_Emissive", PALETTE["teal"], strength=3.2),
        "teal_grid": make_emissive_material("Mat_Teal_Grid", PALETTE["teal"], strength=1.1, alpha=0.45),
        "purple_emissive": make_emissive_material("Mat_Purple_Emissive", PALETTE["purple"], strength=2.8),
        "gold_emissive": make_emissive_material("Mat_Gold_Emissive", PALETTE["gold"], strength=3.5),
        "text_emissive": make_emissive_material("Mat_Text_Emissive", PALETTE["text"], strength=2.2),
        "slab_teal": make_glass_slab_material("Mat_Slab_Teal", PALETTE["teal"], alpha=0.10),
        "slab_purple": make_glass_slab_material("Mat_Slab_Purple", PALETTE["purple"], alpha=0.11),
        "slab_gold": make_glass_slab_material("Mat_Slab_Gold", PALETTE["gold"], alpha=0.10),
        "slab_teal_alt": make_glass_slab_material("Mat_Slab_TealAlt", PALETTE["teal_light"], alpha=0.09),
        "gold_glass": make_glass_slab_material("Mat_Admissibility_Glass", PALETTE["gold"], alpha=0.08),
        "landscape_surface": make_glass_slab_material("Mat_Landscape_Surface", PALETTE["purple_light"], alpha=0.15),
    }

    axes_col = build_axis_frame_collection(syn_meta, cgm_meta, hrvA_meta, materials)
    export_collection_glb(axes_col, os.path.abspath("site/assets/models/hhsa_axes.glb"))

    syn_col = build_dataset_cube_collection(syn_meta, "Cube_Synthetic", materials)
    export_collection_glb(syn_col, os.path.abspath("site/assets/models/cube_synthetic.glb"))

    cgm_col = build_dataset_cube_collection(cgm_meta, "Cube_CGM", materials)
    export_collection_glb(cgm_col, os.path.abspath("site/assets/models/cube_cgm.glb"))

    hrvA_col = build_dataset_cube_collection(hrvA_meta, "Cube_HRV_SessionA", materials)
    export_collection_glb(hrvA_col, os.path.abspath("site/assets/models/cube_hrv_sessionA.glb"))

    hrvB_col = build_dataset_cube_collection(hrvB_meta, "Cube_HRV_SessionB", materials)
    export_collection_glb(hrvB_col, os.path.abspath("site/assets/models/cube_hrv_sessionB.glb"))

    hero_webp = os.path.abspath("site/assets/img/hero.webp")
    turntable_webm = os.path.abspath("site/assets/img/hero_turntable.webm")
    setup_studio_and_render(axes_col, syn_col, cgm_col, hero_webp, turntable_webm)

    elapsed = time.time() - t0
    log(f"All T08 outputs built successfully in {elapsed:.1f}s.")

    log_path = os.path.abspath("phase2/blender/blender_run.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(LOG_LINES) + "\n")

if __name__ == "__main__":
    main()
