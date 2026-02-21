"""
GingivaGen 2.0 — Multi-Material Mesh Exporter
===============================================
Marching-cubes extraction of per-material isosurfaces from the voxel
grid, with STL/OBJ export for FEA simulation and print-preview.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from skimage.measure import marching_cubes

logger = logging.getLogger("GingivaGen.Exporter")

# Material tag → human-readable name (must match orchestrator constants)
MAT_NAMES = {
    1: "PCL_BAG_armor",
    2: "GelMA_core",
    3: "GelMA_bioglue",
    4: "Pluronic_sacrificial",
}

# Colours for per-material visualisation (RGBA 0-255)
MAT_COLORS = {
    1: (200, 200, 220, 255),   # Silver — PCL armor
    2: (100, 200, 100, 200),   # Green  — GelMA core
    3: (255, 180,  50, 230),   # Orange — bio-glue
    4: (100, 150, 255, 150),   # Blue   — Pluronic channels
}


def extract_material_mesh(
    material_grid: np.ndarray,
    mat_id: int,
    voxel_size: float,
    grid_origin: np.ndarray,
) -> Optional[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Run marching cubes on a single material's binary mask.

    Returns (vertices, faces, normals) in world coordinates,
    or None if the material has too few voxels for a surface.
    """
    binary = (material_grid == mat_id).astype(np.float32)

    if binary.sum() < 8:
        logger.warning("Material %d has < 8 voxels — skipping mesh extraction.",
                       mat_id)
        return None

    # Pad with one layer of zeros so marching cubes can close the surface
    padded = np.pad(binary, pad_width=1, mode="constant", constant_values=0)

    try:
        verts, faces, normals, _ = marching_cubes(
            padded, level=0.5, spacing=(voxel_size, voxel_size, voxel_size)
        )
    except (RuntimeError, ValueError) as exc:
        logger.error("Marching cubes failed for material %d: %s", mat_id, exc)
        return None

    # Shift vertices: undo padding offset + apply world origin
    verts -= voxel_size  # one-voxel pad
    verts += grid_origin

    return verts, faces, normals


def export_stl(
    verts: np.ndarray,
    faces: np.ndarray,
    normals: np.ndarray,
    filepath: str | Path,
) -> Path:
    """Write an ASCII STL file from vertices and faces."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="ascii") as f:
        name = filepath.stem
        f.write(f"solid {name}\n")
        for tri in faces:
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            # Compute face normal from cross product
            e1 = v1 - v0
            e2 = v2 - v0
            n = np.cross(e1, e2)
            norm = np.linalg.norm(n)
            if norm > 0:
                n /= norm
            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write("    outer loop\n")
            for v in (v0, v1, v2):
                f.write(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {name}\n")

    logger.info("  STL saved: %s  (%d triangles)", filepath, len(faces))
    return filepath


def export_obj(
    verts: np.ndarray,
    faces: np.ndarray,
    filepath: str | Path,
) -> Path:
    """Write a Wavefront OBJ file from vertices and faces."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# GingivaGen 2.0 — {filepath.stem}\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for tri in faces:
            # OBJ uses 1-indexed faces
            f.write(f"f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n")

    logger.info("  OBJ saved: %s  (%d verts, %d faces)",
                filepath, len(verts), len(faces))
    return filepath


def export_all_materials(
    material_grid: np.ndarray,
    voxel_size: float,
    grid_origin: np.ndarray,
    output_dir: str | Path,
    fmt: str = "stl",
) -> dict[int, Path]:
    """Extract and export meshes for every material in the grid.

    Parameters
    ----------
    material_grid : int ndarray
        Voxel grid with material tags (0 = empty).
    voxel_size : float
        Isotropic voxel edge length in mm.
    grid_origin : array-like
        XYZ of the grid's (0,0,0) corner in world coords.
    output_dir : path
        Directory for output files.
    fmt : 'stl' or 'obj'
        Export format.

    Returns
    -------
    dict mapping material_id → Path of the exported file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    grid_origin = np.asarray(grid_origin, dtype=np.float64)

    unique_mats = np.unique(material_grid)
    unique_mats = unique_mats[unique_mats > 0]  # skip empty

    logger.info("Exporting %d material(s) as %s -> %s",
                len(unique_mats), fmt.upper(), output_dir)

    exported: dict[int, Path] = {}
    for mat_id in unique_mats:
        mat_id = int(mat_id)
        result = extract_material_mesh(material_grid, mat_id,
                                       voxel_size, grid_origin)
        if result is None:
            continue

        verts, faces, normals = result
        name = MAT_NAMES.get(mat_id, f"material_{mat_id}")

        if fmt.lower() == "obj":
            path = export_obj(verts, faces, output_dir / f"{name}.obj")
        else:
            path = export_stl(verts, faces, normals, output_dir / f"{name}.stl")
        exported[mat_id] = path

    return exported


def export_combined_obj(
    material_grid: np.ndarray,
    voxel_size: float,
    grid_origin: np.ndarray,
    filepath: str | Path,
) -> Path:
    """Export a single OBJ with material groups for multi-material viewers.

    Each material becomes a named group (``g material_name``) so that
    slicers and mesh viewers can colour/handle them independently.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    grid_origin = np.asarray(grid_origin, dtype=np.float64)

    unique_mats = sorted(m for m in np.unique(material_grid) if m > 0)

    vertex_offset = 0
    lines: list[str] = ["# GingivaGen 2.0 — Combined Multi-Material Scaffold\n"]

    for mat_id in unique_mats:
        result = extract_material_mesh(material_grid, int(mat_id),
                                       voxel_size, grid_origin)
        if result is None:
            continue

        verts, faces, _ = result
        name = MAT_NAMES.get(int(mat_id), f"material_{mat_id}")
        lines.append(f"\ng {name}\n")

        for v in verts:
            lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for tri in faces:
            f0 = tri[0] + 1 + vertex_offset
            f1 = tri[1] + 1 + vertex_offset
            f2 = tri[2] + 1 + vertex_offset
            lines.append(f"f {f0} {f1} {f2}\n")
        vertex_offset += len(verts)

    filepath.write_text("".join(lines), encoding="utf-8")
    logger.info("Combined OBJ saved: %s", filepath)
    return filepath


# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(name)s | %(levelname)s | %(message)s")

    # Quick smoke test with a synthetic sphere shell
    N = 50
    xs = np.linspace(-5, 5, N)
    X, Y, Z = np.meshgrid(xs, xs, xs, indexing="ij")
    R = np.sqrt(X**2 + Y**2 + Z**2)

    grid = np.zeros((N, N, N), dtype=np.int8)
    grid[(R >= 3.0) & (R <= 4.0)] = 1   # shell
    grid[(R >= 1.0) & (R < 3.0)] = 2    # core

    origin = np.array([-5, -5, -5], dtype=np.float64)
    paths = export_all_materials(grid, voxel_size=0.2, grid_origin=origin,
                                 output_dir="output/meshes", fmt="stl")
    print(f"Exported: {paths}")
