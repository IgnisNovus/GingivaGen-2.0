"""
GingivaGen 2.0 — Visualization Module
=======================================
PyVista-based interactive 3-D viewers for inspecting scaffold geometry
at every pipeline phase.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("GingivaGen.Viz")

# Material visual properties  (material_id → (name, hex_colour, opacity))
MAT_VIS = {
    1: ("PCL+BAG Armor",   "#C8C8DC", 0.6),
    2: ("GelMA Core",      "#64C864", 0.4),
    3: ("GelMA Bio-Glue",  "#FFB432", 0.5),
    4: ("Pluronic Channels","#6496FF", 0.8),
}


def _require_pyvista():
    """Lazy import guard."""
    try:
        import pyvista as pv
        return pv
    except ImportError:
        raise ImportError(
            "PyVista is required for visualisation. "
            "Install with: pip install pyvista"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Phase-level viewers
# ═══════════════════════════════════════════════════════════════════════════

def view_segmentation(
    vertices: np.ndarray,
    defect_mask: np.ndarray,
    margin_points: np.ndarray,
    root_vertices: np.ndarray,
    screenshot: Optional[str] = None,
) -> None:
    """Visualise Phase 1 output: defect region + healthy margin."""
    pv = _require_pyvista()

    plotter = pv.Plotter(title="Phase 1 — Segmentation & Defect Extraction")

    # All vertices as point cloud
    cloud = pv.PolyData(vertices)
    colors = np.full((len(vertices), 3), 200, dtype=np.uint8)  # grey
    colors[defect_mask] = [255, 80, 80]  # red = defect
    cloud["colors"] = colors
    plotter.add_mesh(cloud, scalars="colors", rgb=True, point_size=3,
                     render_points_as_spheres=True, label="Scan Vertices")

    # Margin points
    margin_cloud = pv.PolyData(margin_points)
    plotter.add_mesh(margin_cloud, color="lime", point_size=6,
                     render_points_as_spheres=True, label="Healthy Margin")

    # Root surface
    root_cloud = pv.PolyData(root_vertices)
    plotter.add_mesh(root_cloud, color="blue", point_size=4,
                     render_points_as_spheres=True, label="Root Surface")

    plotter.add_legend()
    if screenshot:
        plotter.show(screenshot=screenshot)
    else:
        plotter.show()


def view_ideal_volume(
    voxel_grid: np.ndarray,
    grid_origin: np.ndarray,
    voxel_size: float,
    screenshot: Optional[str] = None,
) -> None:
    """Visualise Phase 2 output: the target scaffold volume."""
    pv = _require_pyvista()

    grid = pv.ImageData(
        dimensions=np.array(voxel_grid.shape) + 1,
        spacing=(voxel_size, voxel_size, voxel_size),
        origin=grid_origin,
    )
    grid.cell_data["scaffold"] = voxel_grid.ravel(order="F").astype(np.float32)

    plotter = pv.Plotter(title="Phase 2 — Ideal Scaffold Volume")
    plotter.add_mesh(grid.threshold(0.5), color="lightyellow",
                     opacity=0.3, show_edges=False, label="Target Volume")
    plotter.add_legend()
    if screenshot:
        plotter.show(screenshot=screenshot)
    else:
        plotter.show()


def view_material_grid(
    material_grid: np.ndarray,
    grid_origin: np.ndarray,
    voxel_size: float,
    title: str = "Multi-Material Scaffold",
    screenshot: Optional[str] = None,
) -> None:
    """Visualise any phase's material grid with per-material colouring."""
    pv = _require_pyvista()

    plotter = pv.Plotter(title=title)

    for mat_id, (name, color, opacity) in MAT_VIS.items():
        mask = material_grid == mat_id
        if not np.any(mask):
            continue

        grid = pv.ImageData(
            dimensions=np.array(material_grid.shape) + 1,
            spacing=(voxel_size, voxel_size, voxel_size),
            origin=grid_origin,
        )
        grid.cell_data["mat"] = mask.ravel(order="F").astype(np.float32)

        plotter.add_mesh(
            grid.threshold(0.5),
            color=color,
            opacity=opacity,
            show_edges=False,
            label=f"{name} ({int(mask.sum()):,} voxels)",
        )

    plotter.add_legend()
    plotter.add_axes()
    if screenshot:
        plotter.show(screenshot=screenshot)
    else:
        plotter.show()


def view_armor(material_grid, grid_origin, voxel_size, **kw):
    """Phase 3 shortcut."""
    view_material_grid(material_grid, grid_origin, voxel_size,
                       title="Phase 3 — PCL+BAG Armor Shell", **kw)


def view_core(material_grid, grid_origin, voxel_size, **kw):
    """Phase 4 shortcut."""
    view_material_grid(material_grid, grid_origin, voxel_size,
                       title="Phase 4 — Anisotropic Gyroid Core", **kw)


def view_channels(material_grid, grid_origin, voxel_size, **kw):
    """Phase 5 shortcut."""
    view_material_grid(material_grid, grid_origin, voxel_size,
                       title="Phase 5 — Vascular Channels", **kw)


# ═══════════════════════════════════════════════════════════════════════════
# Cross-section viewer
# ═══════════════════════════════════════════════════════════════════════════

def view_cross_section(
    material_grid: np.ndarray,
    grid_origin: np.ndarray,
    voxel_size: float,
    axis: str = "z",
    position: Optional[float] = None,
    screenshot: Optional[str] = None,
) -> None:
    """Show a 2-D cross-section of the material grid at a given plane.

    Parameters
    ----------
    axis : 'x', 'y', or 'z'
    position : float, optional
        World-coordinate position along the axis. Defaults to midpoint.
    """
    pv = _require_pyvista()

    grid = pv.ImageData(
        dimensions=np.array(material_grid.shape) + 1,
        spacing=(voxel_size, voxel_size, voxel_size),
        origin=grid_origin,
    )
    grid.cell_data["material"] = material_grid.ravel(order="F").astype(np.float32)

    if position is None:
        ax_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]
        position = grid_origin[ax_idx] + material_grid.shape[ax_idx] * voxel_size / 2

    normal_map = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
    normal = normal_map[axis.lower()]
    origin_pt = [0.0, 0.0, 0.0]
    origin_pt[{"x": 0, "y": 1, "z": 2}[axis.lower()]] = position

    sliced = grid.slice(normal=normal, origin=origin_pt)

    plotter = pv.Plotter(title=f"Cross-Section — {axis.upper()}={position:.2f} mm")
    plotter.add_mesh(sliced, scalars="material", cmap="Set1",
                     show_edges=False, clim=[0, 4])
    plotter.view_xy() if axis.lower() == "z" else None
    plotter.add_axes()
    if screenshot:
        plotter.show(screenshot=screenshot)
    else:
        plotter.show()


# ═══════════════════════════════════════════════════════════════════════════
# STL mesh viewer
# ═══════════════════════════════════════════════════════════════════════════

def view_exported_meshes(
    mesh_dir: str | Path,
    screenshot: Optional[str] = None,
) -> None:
    """Load and display all STL/OBJ files from the export directory."""
    pv = _require_pyvista()

    mesh_dir = Path(mesh_dir)
    plotter = pv.Plotter(title="Exported Scaffold Meshes")

    mat_color_by_stem = {
        "PCL_BAG_armor": ("#C8C8DC", 0.6),
        "GelMA_core": ("#64C864", 0.4),
        "GelMA_bioglue": ("#FFB432", 0.5),
        "Pluronic_sacrificial": ("#6496FF", 0.8),
    }

    for fpath in sorted(mesh_dir.glob("*.stl")) + sorted(mesh_dir.glob("*.obj")):
        mesh = pv.read(str(fpath))
        color, opacity = mat_color_by_stem.get(fpath.stem, ("#AAAAAA", 0.5))
        plotter.add_mesh(mesh, color=color, opacity=opacity,
                         label=fpath.stem)

    plotter.add_legend()
    plotter.add_axes()
    if screenshot:
        plotter.show(screenshot=screenshot)
    else:
        plotter.show()


# ═══════════════════════════════════════════════════════════════════════════
# Batch screenshot generator
# ═══════════════════════════════════════════════════════════════════════════

def generate_phase_screenshots(
    results: dict,
    output_dir: str | Path,
) -> list[Path]:
    """Render and save screenshots of every pipeline phase (headless).

    Requires PyVista's off-screen rendering (``pyvista.OFF_SCREEN = True``).
    """
    pv = _require_pyvista()
    pv.OFF_SCREEN = True

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    seg = results.get("segmentation")
    vol = results.get("volume")
    mat = results.get("material_grid")

    if seg:
        path = str(output_dir / "phase1_segmentation.png")
        try:
            view_segmentation(
                seg["vertices"], seg["defect_mask"],
                seg["margin_points"], seg["root_surface_vertices"],
                screenshot=path,
            )
            saved.append(Path(path))
        except Exception as e:
            logger.warning("Phase 1 screenshot failed: %s", e)

    if vol:
        path = str(output_dir / "phase2_volume.png")
        try:
            view_ideal_volume(
                vol["voxel_grid"], vol["grid_origin"], vol["grid_spacing"],
                screenshot=path,
            )
            saved.append(Path(path))
        except Exception as e:
            logger.warning("Phase 2 screenshot failed: %s", e)

    if mat is not None and vol:
        for phase, title in [(3, "armor"), (4, "core"), (5, "channels")]:
            path = str(output_dir / f"phase{phase}_{title}.png")
            try:
                view_material_grid(
                    mat, vol["grid_origin"], vol["grid_spacing"],
                    title=f"Phase {phase}", screenshot=path,
                )
                saved.append(Path(path))
            except Exception as e:
                logger.warning("Phase %d screenshot failed: %s", phase, e)

    logger.info("Saved %d screenshots -> %s", len(saved), output_dir)
    return saved
