#!/usr/bin/env python3
"""Render 3D screenshots of the Murphy bed model via trimesh + pyglet.

Loads the component STLs (which already have baked world-coordinate positions),
assembles them by view, and renders PNGs from multiple angles.
"""

import json
import math
import os
import sys
from pathlib import Path

import trimesh

os.environ["PYGLET_HEADLESS"] = "1"

REPO = Path("/home/kboran/Nextcloud/development/murphy bed")
STL_DIR = REPO / "design" / "3d" / "stl"
MANIFEST_PATH = REPO / "design" / "3d" / "manifest.json"
OUT_DIR = REPO / "design" / "3d" / "screenshots"
OFF = 800  # group separation for exploded view (matches viewer.html)


def load_manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def load_mesh(stl_rel_path, color_hex):
    """Load a single STL and return a trimesh.Trimesh with its color metadata."""
    path = STL_DIR / stl_rel_path.replace("stl/", "")
    mesh = trimesh.load(str(path))
    # Parse hex → (0-255, 0-255, 0-255)
    h = color_hex.lstrip("#")
    rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    rgba = rgb + (255,)
    if not hasattr(mesh.visual, "face_colors") or mesh.visual.face_colors is None:
        mesh.visual = trimesh.visual.ColorVisuals(mesh, face_colors=rgba)
    else:
        mesh.visual.face_colors[:, :4] = rgba
    return mesh


def build_scene(entry_filter, explode_groups=False):
    """Build a trimesh.Scene with colored meshes.

    entry_filter:   callable(manifest_entry) → bool, selects which parts to include
    explode_groups: if True, offset each group so they're separated (exploded view)
    """
    manifest = load_manifest()
    geoms = []

    for entry in manifest:
        if not entry_filter(entry):
            continue
        mesh = load_mesh(entry["stl"], entry["color"])

        # Apply group offset for exploded view
        if explode_groups:
            group_offsets = {
                "room": (-OFF * 1.5, 0, 0),
                "cabinet": (-OFF / 2, 0, 0),
                "bed": (OFF / 2, 0, 0),
                "mechanism": (OFF * 1.5, 0, 0),
            }
            off = group_offsets.get(entry["group"], (0, 0, 0))
            mesh = mesh.copy().apply_translation(off)

        geoms.append(mesh)

    scene = trimesh.Scene(geoms)
    return scene


def camera_look_at(scene, azimuth, elevation, dist_mult=1.0, focus_center=None, focus_size=None):
    """Position the scene camera to look at the scene center from a given angle.

    azimuth:   radians — 0 = default view, PI/2 = right (+X), PI = behind
    elevation: radians — 0 = horizon, PI/2 = top-down
    focus_center: (3,) override auto center
    focus_size:   (3,) override auto size (for tighter crop)
    """
    from trimesh.transformations import rotation_matrix

    if focus_center is not None and focus_size is not None:
        center = focus_center
        max_dim = max(focus_size)
    else:
        bounds = scene.bounds
        center = (bounds[0] + bounds[1]) / 2
        size = bounds[1] - bounds[0]
        max_dim = max(size)
    dist = max_dim * 2.0 * dist_mult

    # Extend far clip plane so entire scene is visible
    scene.camera.z_far = dist + max_dim * 3.0
    scene.camera.z_near = 1.0

    mat_az = rotation_matrix(azimuth, [0, 1, 0])
    mat_el = rotation_matrix(-elevation, [1, 0, 0])
    rot = mat_az @ mat_el

    scene.camera_transform = trimesh.scene.cameras.look_at(
        np.array([center]),
        fov=(45, 45),
        rotation=rot,
        distance=dist,
        center=center,
    )


# Need numpy
import numpy as np


def render(view_name, entry_filter, shots, explode=False, focus_filter=None):
    print(f"\n{'='*60}")
    print(f"View: {view_name}")
    print(f"{'='*60}")

    scene = build_scene(entry_filter, explode_groups=explode)

    # Compute focus from a subset of objects (exclude room by default)
    focus_center = focus_size = None
    if focus_filter is not None:
        manifest = load_manifest()
        sel = [e for e in manifest if focus_filter(e)]
        if sel:
            # Compute bounds from just these entries
            scene2 = build_scene(focus_filter, explode_groups=explode)
            focus_center = (scene2.bounds[0] + scene2.bounds[1]) / 2
            focus_size = scene2.bounds[1] - scene2.bounds[0]
            del scene2

    for name, az, el, dm in shots:
        camera_look_at(scene, az, el, dist_mult=dm,
                       focus_center=focus_center, focus_size=focus_size)
        out_path = OUT_DIR / f"{view_name}-{name}.png"
        print(f"  {name:25s}  az={az:.2f} el={el:.2f} dm={dm:.1f}  → {out_path.name}")
        png = scene.save_image(resolution=(1920, 1080))
        with open(out_path, "wb") as f:
            f.write(png)

    del scene


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Shot presets
    # (name, azimuth, elevation, distance_multiplier)
    front = ("front", 0.0, 0.4, 1.0)
    angle = ("angle", 0.6, 0.35, 1.0)
    side = ("side", 1.5, 0.25, 1.0)
    low = ("low", 0.35, 0.15, 0.9)
    top = ("top", 0.0, 1.3, 1.0)
    far = ("overview", 0.3, 0.3, 1.6)
    topwide = ("topwide", 0.0, 1.2, 1.4)
    rear = ("rear", -1.2, 0.3, 1.0)

    def open_only(e):
        return e["name"].startswith("open_")
    def stored_only(e):
        return e["name"].startswith("stored_")
    def cab_or_room_open(e):
        return e["name"].startswith("open_") and e["group"] in ("room", "cabinet")
    def cab_open(e):
        return e["name"].startswith("open_") and e["group"] == "cabinet"
    stored_cab = lambda e: e["name"].startswith("stored_") and e["group"] in ("room", "cabinet")
    stored_cab_only = lambda e: e["name"].startswith("stored_") and e["group"] == "cabinet"

    # ── With room context (focus on non-room objects) ──
    no_room = lambda e: e["group"] != "room"
    render("open",     open_only,        [front, angle, side, low, top, rear],
           focus_filter=no_room)
    render("stored",   stored_only,      [front, angle, side],
           focus_filter=no_room)
    render("cabinet",  cab_or_room_open, [front, angle],
           focus_filter=lambda e: e["group"] == "cabinet")

    # ── Without room (tight crop on relevant parts) ──
    render("open-close",   open_only,    [front, angle, side, low, top],
           focus_filter=no_room)
    render("stored-close", stored_only,  [front, angle, side],
           focus_filter=no_room)
    render("cabinet-close", cab_open,    [front, angle],
           focus_filter=lambda e: e["group"] == "cabinet")

    # Exploded
    render("exploded", open_only, [far, topwide], explode=True,
           focus_filter=no_room)

    print(f"\nDone — all screenshots saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
