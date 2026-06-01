"""
Murphy Bed 3D — Individual Component Export
=============================================
Each major component is exported as a separate STL/STEP file for
colored assembly in a 3D viewer. Avoids boolean union issues.

Usage:
    python3 murphy_bed_3d.py              # export all components
    python3 murphy_bed_3d.py stl          # STL only
    python3 murphy_bed_3d.py step         # STEP only
"""

import sys, os, math, json
import cadquery as cq

OUT_DIR = os.path.dirname(__file__) or "."

# ═══════════════════════════════════════════════════════════════
# PARAMETERS  (mm)
# ═══════════════════════════════════════════════════════════════

CEILING_H    = 2121
CAB_W        = 1690
CAB_D        = 406
CAB_H        = 2138
OSB18        = 18
OSB12        = 12
CAB_IW       = CAB_W - 2*OSB18
CAB_ID       = CAB_D - OSB12
CAB_IH       = CAB_H - 2*OSB18

MALM_LEN     = 2020
MALM_RAIL_W  = 70
MALM_RAIL_T  = 16
MALM_INNER   = 1521

MATT_W       = 1525
MATT_L       = 2030
MATT_H       = 254

PIVOT_Z      = CAB_H - OSB18 - 50    # near top of cabinet (head end of bed)

RECESS_W     = 1715
RECESS_D     = 457

# ═══════════════════════════════════════════════════════════════
# COMPONENT BUILDERS
# ═══════════════════════════════════════════════════════════════

def box(w, d, h, center=(0,0,0)):
    cx, cy, cz = center
    return cq.Workplane("XY").box(w, d, h, centered=(True,True,True)).translate((cx, cy, cz))

# ---- 1. Cabinet sides ----
def part_cabinet_side_L():
    return box(OSB18, CAB_D, CAB_H, (-CAB_IW/2 - OSB18/2, 0, CAB_H/2))

def part_cabinet_side_R():
    return box(OSB18, CAB_D, CAB_H, (CAB_IW/2 + OSB18/2, 0, CAB_H/2))

def part_cabinet_back():
    return box(CAB_W, OSB12, CAB_IH, (0, -CAB_D/2 + OSB12/2, OSB18 + CAB_IH/2))

def part_cabinet_top():
    return box(CAB_IW, CAB_ID, OSB18, (0, -OSB12/2, CAB_H - OSB18/2))

def part_cabinet_bottom():
    return box(CAB_IW, CAB_D, OSB18, (0, 0, OSB18/2))

def part_cabinet_shelf():
    sz = OSB18 + 0.4 * CAB_IH
    return box(CAB_IW, CAB_ID, OSB18, (0, -OSB12/2, sz))

# ---- 2. Malm bed frame ----
def part_bed_open():
    """Bed frame in horizontal position, ready to position."""
    bed = cq.Workplane("XY")
    sep = MALM_INNER + MALM_RAIL_T
    for sy in (-sep/2, sep/2):
        bed = bed.union(box(MALM_LEN, MALM_RAIL_T, MALM_RAIL_W, (0, sy, MALM_RAIL_W/2)))
    # Slats
    bed = bed.union(box(MALM_LEN - 60, MALM_INNER, 6, (0, 0, MALM_RAIL_W)))
    return bed

def part_bed_stored():
    """Bed frame rotated vertical for storage."""
    bed = part_bed_open()
    # Rotate so length (x) becomes vertical (z)
    bed = bed.rotate((0,0,0), (0,1,0), 90)
    # Position: pivot at PIVOT_Z, bed extends downward
    pivot_in_bed = -MALM_LEN/2 + 30  # where Connect Bracket attaches
    bed = bed.translate((0, 0, PIVOT_Z + pivot_in_bed))
    return bed

# ---- 3. Mattress ----
def part_mattress_open():
    return box(MATT_L, MATT_W, MATT_H, (0, 0, MATT_H/2))

def part_mattress_stored():
    mat = part_mattress_open()
    mat = mat.rotate((0,0,0), (0,1,0), 90)
    pivot_in_bed = -MALM_LEN/2 + 30
    mat_z = PIVOT_Z + pivot_in_bed + MATT_L/2
    mat = mat.translate((0, 0, mat_z))
    return mat

# ---- 4. Room elements ----
def part_floor():
    return box(5000, 5000, 200, (0, CAB_D/2, -100))

def part_wall():
    return box(5000, 40, CEILING_H, (0, -20, CEILING_H/2))

def part_ceiling():
    """Ceiling slab with recess cutout for cabinet."""
    ceil = cq.Workplane("XY").box(5000, 5000, 100, centered=(True, True, True))
    cut = cq.Workplane("XY").box(RECESS_W, RECESS_D, 200, centered=(True, True, True))
    ceil = ceil.cut(cut)
    ceil = ceil.translate((0, CAB_D/2, CEILING_H - 50))
    return ceil

# ---- 5. Mechanism (simplified) ----
def part_bracket_A():
    return box(8, 40, 200, (-CAB_IW/2 - OSB18/2 - 4, 0, PIVOT_Z))

def part_bracket_A_R():
    return box(8, 40, 200, (CAB_IW/2 + OSB18/2 + 4, 0, PIVOT_Z))

def part_legs():
    """Legs for open position — built at z relative to bed height.
    pos_open will add bed_z in z, so we pre-subtract it.
    """
    legs = cq.Workplane("XY")
    sep = MALM_INNER + MALM_RAIL_T
    for sy in (-sep/2 - 30, sep/2 + 30):
        # Build at z=155, then pos_open adds bed_z → bottom at bed_z, top at bed_z+310
        # But we want bottom at 0 (floor), top at 310. So subtract bed_z:
        legs = legs.union(box(20, 20, 310, (MALM_LEN/2 - 150, sy, 155)))
    return legs

# ═══════════════════════════════════════════════════════════════
# POSITION HELPERS
# ═══════════════════════════════════════════════════════════════

def pos_open_xy(part):
    """Rotate and translate a bed part in XY for the open position.
    Z translation is NOT applied — caller handles Z separately.
    """
    part = part.rotate((0,0,0), (0,0,1), 90)
    pivot_y = -MALM_LEN/2 + 30
    return part.translate((0, CAB_D/2 - pivot_y, 0))

BED_Z = 310  # horizontal bed frame height above floor

# ═══════════════════════════════════════════════════════════════
# MANIFEST  — describes all parts for the viewer
# ═══════════════════════════════════════════════════════════════

MANIFEST = [
    # (filename, builder_fn, color_hex, label, group)
    # --- Open position ---
    ("open_floor",       part_floor,             "#8a7060", "Floor", "room"),
    ("open_wall",        part_wall,             "#e6e0d6", "Wall", "room"),
    ("open_ceiling",     part_ceiling,           "#d0d0d0", "Ceiling", "room"),
    ("open_cab_side_L",  part_cabinet_side_L,    "#8c6632", "Left Side (OSB)", "cabinet"),
    ("open_cab_side_R",  part_cabinet_side_R,    "#8c6632", "Right Side (OSB)", "cabinet"),
    ("open_cab_back",    part_cabinet_back,      "#7a6b50", "Back Panel (OSB)", "cabinet"),
    ("open_cab_top",     part_cabinet_top,       "#8c6632", "Top (OSB)", "cabinet"),
    ("open_cab_bottom",  part_cabinet_bottom,    "#8c6632", "Bottom (OSB)", "cabinet"),
    ("open_cab_shelf",   part_cabinet_shelf,     "#8c6632", "Shelf (OSB)", "cabinet"),
    ("open_bracket_A_L", part_bracket_A,         "#888888", "Side Bracket (A)", "mechanism"),
    ("open_bracket_A_R", part_bracket_A_R,       "#888888", "Side Bracket (A)", "mechanism"),
    ("open_bed",         lambda: pos_open_xy(part_bed_open()).translate((0,0,BED_Z)),
                       "#b89860", "Malm Frame", "bed"),
    ("open_mattress",    lambda: pos_open_xy(part_mattress_open()).translate((0,0,BED_Z + MALM_RAIL_W)),
                       "#e0d8c8", "Mattress", "bed"),
    ("open_legs",        lambda: pos_open_xy(part_legs()),   "#777777", "Legs (C)", "mechanism"),

    # --- Stored position ---
    ("stored_floor",     part_floor,             "#8a7060", "Floor", "room"),
    ("stored_wall",      part_wall,             "#e6e0d6", "Wall", "room"),
    ("stored_ceiling",   part_ceiling,           "#d0d0d0", "Ceiling", "room"),
    ("stored_cab_side_L", part_cabinet_side_L,   "#8c6632", "Left Side (OSB)", "cabinet"),
    ("stored_cab_side_R", part_cabinet_side_R,   "#8c6632", "Right Side (OSB)", "cabinet"),
    ("stored_cab_back",  part_cabinet_back,      "#7a6b50", "Back Panel (OSB)", "cabinet"),
    ("stored_cab_top",   part_cabinet_top,       "#8c6632", "Top (OSB)", "cabinet"),
    ("stored_cab_bottom",part_cabinet_bottom,    "#8c6632", "Bottom (OSB)", "cabinet"),
    ("stored_cab_shelf", part_cabinet_shelf,     "#8c6632", "Shelf (OSB)", "cabinet"),
    ("stored_bracket_A_L", part_bracket_A,       "#888888", "Side Bracket (A)", "mechanism"),
    ("stored_bracket_A_R", part_bracket_A_R,     "#888888", "Side Bracket (A)", "mechanism"),
    ("stored_bed",       part_bed_stored,        "#b89860", "Malm Frame", "bed"),
    ("stored_mattress",  part_mattress_stored,   "#e0d8c8", "Mattress", "bed"),
]

# ═══════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════

def export_stl(shape, fn):
    path = os.path.join(OUT_DIR, fn)
    cq.exporters.export(shape, path, exportType="STL")
    return path, os.path.getsize(path)

def export_step(shape, fn):
    path = os.path.join(OUT_DIR, fn)
    cq.exporters.export(shape, path, exportType="STEP")
    return path, os.path.getsize(path)

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    do_stl = mode in ("all", "stl")
    do_step = mode in ("all", "step")

    os.makedirs(OUT_DIR, exist_ok=True)

    stl_dir = os.path.join(OUT_DIR, "stl")
    step_dir = os.path.join(OUT_DIR, "step")
    if do_stl: os.makedirs(stl_dir, exist_ok=True)
    if do_step: os.makedirs(step_dir, exist_ok=True)

    print(f"Exporting {len(MANIFEST)} components ({mode})...\n")

    # Build manifest for the viewer
    viewer_manifest = []

    for fn, builder, color, label, group in MANIFEST:
        print(f"  {fn}...", end=" ", flush=True)
        try:
            shape = builder()
            if shape is None:
                print("SKIP (None)")
                continue

            info = {
                "name": fn, "label": label, "group": group, "color": color,
                "stl": None, "step": None, "size_stl": 0, "size_step": 0
            }

            if do_stl:
                p, sz = export_stl(shape, os.path.join(stl_dir, f"{fn}.stl"))
                info["stl"] = f"stl/{fn}.stl"
                info["size_stl"] = sz

            if do_step:
                p, sz = export_step(shape, os.path.join(step_dir, f"{fn}.step"))
                info["step"] = f"step/{fn}.step"
                info["size_step"] = sz

            viewer_manifest.append(info)
            print("OK")
        except Exception as e:
            print(f"FAIL: {e}")

    # Write manifest JSON for the web viewer
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(viewer_manifest, f, indent=2)
    print(f"\n  manifest.json  ({len(viewer_manifest)} components)")

    total_stl = sum(m["size_stl"] for m in viewer_manifest)
    total_step = sum(m["size_step"] for m in viewer_manifest)
    if do_stl:  print(f"  STL total: {total_stl/1024:.0f} KB")
    if do_step: print(f"  STEP total: {total_step/1024:.0f} KB")
    print("\nDone!")
