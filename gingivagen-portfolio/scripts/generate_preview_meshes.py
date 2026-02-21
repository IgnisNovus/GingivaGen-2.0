"""
Generate polished scaffold preview meshes for the portfolio.

Creates a dome-shaped gingival scaffold with:
  - PCL+BAG armor shell (outer 0.5 mm)
  - Schoen Gyroid GelMA core (325 um pores)
  - Pluronic F-127 sacrificial channels (400 um diameter)

Run from project root:  python gingivagen-portfolio/scripts/generate_preview_meshes.py
"""

import struct
import numpy as np
from pathlib import Path
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes

OUT_DIR = Path("gingivagen-portfolio/public/models/scaffold_preview")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Scaffold dimensions (mm) ───────────────────────────────────────────
DOME_RX = 5.0          # half-width X
DOME_RY = 4.0          # half-width Y
DOME_HEIGHT = 3.0      # max height Z
ARMOR_THICK = 0.5      # shell thickness
VOXEL = 0.06           # mm per voxel (resolution)
GYROID_CELL = 2.0      # mm period
GYROID_T = 0.35        # isovalue threshold
CHANNEL_DIA = 0.4      # mm
CHANNEL_SPACING = 2.0  # mm centre-to-centre
SMOOTH_SIGMA = 0.8     # Gaussian sigma in voxels


def export_stl(verts, faces, path):
    """Write compact binary STL."""
    with open(path, 'wb') as f:
        f.write(b'\0' * 80)
        f.write(struct.pack('<I', len(faces)))
        for tri in faces:
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            n = np.cross(v1 - v0, v2 - v0)
            nl = np.linalg.norm(n)
            if nl > 0:
                n /= nl
            f.write(struct.pack('<fff', *n))
            f.write(struct.pack('<fff', *v0))
            f.write(struct.pack('<fff', *v1))
            f.write(struct.pack('<fff', *v2))
            f.write(struct.pack('<H', 0))
    kb = path.stat().st_size / 1024
    print(f"  {path.name}: {len(verts):,} verts, {len(faces):,} faces, {kb:.0f} KB")


def mc_extract(volume, voxel_size, sigma=SMOOTH_SIGMA):
    """Gaussian-smooth a binary volume and run marching cubes."""
    smoothed = gaussian_filter(volume.astype(np.float32), sigma=sigma)
    padded = np.pad(smoothed, 1, mode='constant', constant_values=0)
    spacing = (voxel_size, voxel_size, voxel_size)
    verts, faces, _, _ = marching_cubes(padded, level=0.5, spacing=spacing)
    verts -= voxel_size  # undo padding offset
    return verts, faces


def main():
    # ── Build coordinate grids ──────────────────────────────────────────
    nx = int(2 * DOME_RX / VOXEL) + 2
    ny = int(2 * DOME_RY / VOXEL) + 2
    nz = int(DOME_HEIGHT / VOXEL) + 2
    print(f"Grid: {nx} x {ny} x {nz} = {nx*ny*nz:,} voxels  (voxel {VOXEL} mm)")

    xs = np.linspace(-DOME_RX - VOXEL, DOME_RX + VOXEL, nx)
    ys = np.linspace(-DOME_RY - VOXEL, DOME_RY + VOXEL, ny)
    zs = np.linspace(-VOXEL, DOME_HEIGHT + VOXEL, nz)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')

    # ── Dome shape: elliptic paraboloid ─────────────────────────────────
    # z_max(x,y) = DOME_HEIGHT * (1 - (x/rx)^2 - (y/ry)^2)  clamped >= 0
    r2 = (X / DOME_RX) ** 2 + (Y / DOME_RY) ** 2
    z_ceil = DOME_HEIGHT * np.clip(1.0 - r2, 0, 1)
    dome = (Z >= 0) & (Z <= z_ceil) & (r2 <= 1.0)
    print(f"Dome voxels: {dome.sum():,}")

    # ── Armor shell: outer ARMOR_THICK mm of the dome ───────────────────
    # Erode the dome inward
    from scipy.ndimage import binary_erosion
    erode_r = max(1, int(round(ARMOR_THICK / VOXEL)))
    struct_el = np.ones((2*erode_r+1,) * 3, dtype=bool)
    inner = binary_erosion(dome, structure=struct_el)
    armor = dome & ~inner
    print(f"Armor voxels: {armor.sum():,}  (erosion radius {erode_r})")

    # ── Gyroid core inside the inner volume ──────────────────────────────
    freq = 2 * np.pi / GYROID_CELL
    sdf = (np.cos(freq * X) * np.sin(freq * Y) +
           np.cos(freq * Y) * np.sin(freq * Z) +
           np.cos(freq * Z) * np.sin(freq * X))
    gyroid_solid = np.abs(sdf) <= GYROID_T
    core = inner & gyroid_solid
    print(f"Core voxels: {core.sum():,}")

    # ── Pluronic channels: vertical cylinders through the core ──────────
    channel_r = CHANNEL_DIA / 2.0
    channels = np.zeros_like(dome, dtype=bool)
    cx_range = np.arange(-DOME_RX + 1.0, DOME_RX, CHANNEL_SPACING)
    cy_range = np.arange(-DOME_RY + 1.0, DOME_RY, CHANNEL_SPACING)
    n_ch = 0
    for cx in cx_range:
        for cy in cy_range:
            dist_xy = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
            cyl = (dist_xy <= channel_r) & inner
            if cyl.any():
                channels |= cyl
                n_ch += 1
    # Channels replace core material
    core[channels] = False
    print(f"Channel voxels: {channels.sum():,}  ({n_ch} channels)")

    # ── Marching cubes + export ─────────────────────────────────────────
    print("\nExtracting surfaces ...")
    for name, vol in [("PCL_BAG_armor", armor),
                      ("GelMA_core", core),
                      ("Pluronic_channels", channels)]:
        if vol.sum() < 10:
            print(f"  {name}: too few voxels, skipping")
            continue
        verts, faces = mc_extract(vol, VOXEL)
        # Centre the mesh at origin
        centre = (verts.max(axis=0) + verts.min(axis=0)) / 2
        verts -= centre
        export_stl(verts, faces, OUT_DIR / f"{name}.stl")

    print("\nDone!")


if __name__ == "__main__":
    main()
