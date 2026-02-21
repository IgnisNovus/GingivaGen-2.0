"""
GingivaGen 2.0 — Master Orchestrator
======================================
Autonomous pipeline converting intraoral .obj/.stl scans into
multi-material, implantable hybrid gingival scaffolds.

Triple-Threat Biological Strategy
----------------------------------
1. **Mechanical Defense** — 0.5 mm PCL + 10 % Bioactive Glass (BAG) shell
   prevents suture tearing and mastication collapse.
2. **Bio-Grafting** — Anisotropic Schoen Gyroid GelMA core (325 µm pores)
   guides fibroblast migration and Sharpey's fiber alignment.
3. **Vascular / Immune Support** — Sacrificial Pluronic F-127 channels for
   angiogenesis; BAG doping promotes M2 macrophage polarization and
   suppresses bacterial colonisation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
from scipy import ndimage
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree

logger = logging.getLogger("GingivaGen")

# ── Optional library availability flags ───────────────────────────────────
_HAS_MESHLIB = False
try:
    import meshlib.mrmeshpy as mrmeshpy
    _HAS_MESHLIB = True
except ImportError:
    pass

_HAS_LISBON_TPMS = False
try:
    from LisbonTPMStool.TPMS import TPMS as LisbonTPMS, TPMS_domain
    from LisbonTPMStool.Surfaces import Shoen_Gyroid
    _HAS_LISBON_TPMS = True
except ImportError:
    pass

# ═══════════════════════════════════════════════════════════════════════════
# Material tags for the multi-material voxel grid
# ═══════════════════════════════════════════════════════════════════════════
MAT_EMPTY = 0
MAT_PCL_BAG = 1          # Armor: PCL + 10 % Bioactive Glass (45S5)
MAT_GELMA_CORE = 2       # Anisotropic gyroid GelMA
MAT_GELMA_BIOGLUE = 3    # High-density GelMA bio-glue (root interface)
MAT_PLURONIC = 4          # Sacrificial Pluronic F-127

# ═══════════════════════════════════════════════════════════════════════════
# Dimensional / biological constraints
# ═══════════════════════════════════════════════════════════════════════════
ARMOR_THICKNESS_MM = 0.5        # Required for suture retention (Schmitt 2020)
BIOGLUE_THICKNESS_MM = 0.1      # 100 µm high-density adhesion layer
VOXEL_SIZE_MM = 0.05            # 50 µm isotropic resolution
TARGET_PORE_UM = 325.0          # Optimal for fibroblast migration
PORE_TOLERANCE_UM = 25.0        # ±25 µm acceptance window
VASCULAR_CHANNEL_DIA_MM = 0.4   # 400 µm sacrificial channel diameter
VASCULAR_SPACING_MM = 2.0       # Centre-to-centre channel spacing
PDL_ANISOTROPY_K = 3.0          # Z-stretch factor at root surface
PDL_DECAY_LENGTH = 2.0          # mm — exponential decay length

# Bioprinting head parameters  (tool_id → config)
HEAD_CONFIG = {
    0: dict(name="PCL+BAG",    pressure_kpa=300, speed_mm_s=3, nozzle_mm=0.41),
    1: dict(name="GelMA",      pressure_kpa=45,  speed_mm_s=5, nozzle_mm=0.25),
    2: dict(name="Pluronic",   pressure_kpa=60,  speed_mm_s=8, nozzle_mm=0.41),
}

# Map material tag → tool id
MAT_TO_TOOL = {
    MAT_PCL_BAG: 0,
    MAT_GELMA_CORE: 1,
    MAT_GELMA_BIOGLUE: 1,  # Same head as core, lower isovalue
    MAT_PLURONIC: 2,
}


def _mm_s_to_mm_min(v: float) -> float:
    """FullControl expects mm/min for feedrate."""
    return v * 60.0


# ═══════════════════════════════════════════════════════════════════════════
# GingivaGenV2  — main pipeline class
# ═══════════════════════════════════════════════════════════════════════════

class GingivaGenV2:
    """End-to-end scaffold generator.

    Typical usage::

        pipeline = GingivaGenV2(output_dir="output")
        results  = pipeline.run("patient_scan.obj")
    """

    def __init__(
        self,
        output_dir: str = "output",
        voxel_size: float = VOXEL_SIZE_MM,
        config: dict | None = None,
    ) -> None:
        self.voxel_size = voxel_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}

        # Lazy import so module can be loaded even when porespy is missing
        from validation_engine import ScaffoldValidator
        e_solid = self._cfg("core", "e_solid_gelma_kpa", 50.0)
        self.validator = ScaffoldValidator(voxel_size_mm=voxel_size,
                                          e_solid_kpa=e_solid)
        logger.info("GingivaGen 2.0 initialised -- voxel %.3f mm, output -> %s",
                     voxel_size, self.output_dir)

    def _cfg(self, section: str, key: str, default: Any = None) -> Any:
        """Read a value from the nested config dict with a fallback."""
        return self.config.get(section, {}).get(key, default)

    # ───────────────────────────────────────────────────────────────────
    # PHASE 1 — Neural Segmentation & Defect Extraction
    # ───────────────────────────────────────────────────────────────────
    def phase1_neural_segmentation(self, obj_path: str) -> dict:
        """Segment the intraoral scan into teeth + gingiva and isolate
        the recession defect region.

        When 3DTeethSAM weights are available, the full inference
        pipeline is invoked.  Otherwise a geometric heuristic extracts
        the defect from vertex height distribution.
        """
        import trimesh

        logger.info("PHASE 1 — Loading mesh: %s", obj_path)
        mesh = trimesh.load(obj_path, process=True)
        verts = np.array(mesh.vertices)

        # ----------------------------------------------------------
        # 3DTeethSAM neural segmentation (when checkpoint available)
        # ----------------------------------------------------------
        seg_model = self._cfg("segmentation", "model", "geometric")
        labels = None

        if seg_model == "3dteethsam":
            checkpoint = self._cfg("segmentation", "checkpoint", "ckpts/best.pth")
            device = self._cfg("segmentation", "device", "cuda:0")
            num_views = self._cfg("segmentation", "num_views", 7)
            try:
                from start_inference import InferencePipeline
                pipe = InferencePipeline(
                    checkpoint=checkpoint,
                    device=device,
                    num_views=num_views,
                )
                pipe.load_model()
                labels = pipe.run_single(obj_path)
                logger.info("  3DTeethSAM segmentation succeeded (%d labels)",
                            len(np.unique(labels)))
            except Exception as exc:
                logger.warning("  3DTeethSAM failed (%s); falling back to geometric",
                               exc)

        if labels is not None:
            # Neural segmentation path: use predicted labels
            gingiva_mask = labels == 0
            tooth_mask = labels > 0
            z = verts[:, 2]
            z_median = np.median(z)
            # Defect = gingiva vertices below the median tooth height
            tooth_z_median = np.median(z[tooth_mask]) if tooth_mask.any() else z_median
            defect_mask = gingiva_mask & (z < tooth_z_median)
            defect_verts = verts[defect_mask]
            root_mask = gingiva_mask & (z < np.percentile(z[gingiva_mask], 20))
            root_verts = verts[root_mask]
            margin_mask = gingiva_mask & (z >= tooth_z_median) & (z < np.percentile(z, 75))
            margin_pts = verts[margin_mask]
        else:
            # Geometric fallback — use z-height percentile to approximate
            # the cemento-enamel junction (CEJ).
            z = verts[:, 2]
            z_median = np.median(z)
            z_q25 = np.percentile(z, 25)

            # Vertices below 25th-percentile height → exposed root / defect
            defect_mask = z < z_q25
            defect_verts = verts[defect_mask]

            # "Root surface" — the lowest region
            root_mask = z < np.percentile(z, 15)
            root_verts = verts[root_mask]

            # Healthy margin — band just above the defect boundary
            margin_mask = (z >= z_q25) & (z < z_median)
            margin_pts = verts[margin_mask]

        logger.info("  Defect vertices : %d / %d", defect_verts.shape[0], len(verts))
        logger.info("  Margin points   : %d", margin_pts.shape[0])

        return dict(
            mesh=mesh,
            vertices=verts,
            defect_mask=defect_mask,
            defect_vertices=defect_verts,
            margin_points=margin_pts,
            root_surface_vertices=root_verts,
            obj_path=obj_path,
        )

    # ───────────────────────────────────────────────────────────────────
    # PHASE 2 — Gap Closing & The "Ideal Volume"
    # ───────────────────────────────────────────────────────────────────
    def phase2_ideal_volume(self, seg: dict) -> dict:
        """Interpolate the healthy gingival contour across the recession
        gap to define the *target scaffold volume*.

        An RBF (thin-plate-spline) through the healthy margin points
        yields the "ideal" tissue surface.  The scaffold occupies the
        boolean difference between that surface and the exposed root.
        """
        logger.info("PHASE 2 — Computing ideal volume via RBF interpolation")

        margin = seg["margin_points"]
        root = seg["root_surface_vertices"]

        # Read RBF config
        rbf_kernel = self._cfg("ideal_volume", "rbf_kernel", "thin_plate_spline")
        rbf_smoothing = self._cfg("ideal_volume", "rbf_smoothing", 1.0)
        padding_mm = self._cfg("ideal_volume", "padding_mm", 0.5)

        # Subsample margin if too large (RBF scales as O(N^2) in memory)
        MAX_RBF_POINTS = 500
        if len(margin) > MAX_RBF_POINTS:
            logger.info("  Subsampling margin: %d -> %d points",
                        len(margin), MAX_RBF_POINTS)
            idx = np.random.default_rng(42).choice(
                len(margin), MAX_RBF_POINTS, replace=False)
            margin = margin[idx]

        # RBF: f(x,y) -> z  fitted to healthy margin
        rbf = RBFInterpolator(
            margin[:, :2],        # XY positions
            margin[:, 2],         # Z (height) values
            kernel=rbf_kernel,
            smoothing=rbf_smoothing,
        )

        # Bounding box of the defect + margin with padding
        all_pts = np.vstack([margin, root])
        bb_min = all_pts.min(axis=0) - padding_mm
        bb_max = all_pts.max(axis=0) + padding_mm

        # Cap grid dimensions to prevent memory blowup
        MAX_VOXELS_PER_AXIS = 200
        spans = bb_max - bb_min
        eff_voxel = max(self.voxel_size, float(spans.max() / MAX_VOXELS_PER_AXIS))
        if eff_voxel > self.voxel_size:
            logger.info("  Capping voxel size to %.3f mm (grid would exceed %d^3)",
                        eff_voxel, MAX_VOXELS_PER_AXIS)

        # 3-D voxel grid at target resolution
        xs = np.arange(bb_min[0], bb_max[0], eff_voxel)
        ys = np.arange(bb_min[1], bb_max[1], eff_voxel)
        zs = np.arange(bb_min[2], bb_max[2], eff_voxel)
        Xg, Yg, Zg = np.meshgrid(xs, ys, zs, indexing="ij")
        logger.info("  Grid shape: %s (voxel %.3f mm)", Xg.shape, eff_voxel)

        # Evaluate ideal surface height at every XY column
        xy_flat = np.column_stack([Xg[:, :, 0].ravel(), Yg[:, :, 0].ravel()])
        z_ideal_flat = rbf(xy_flat)
        z_ideal = z_ideal_flat.reshape(Xg.shape[:2])

        # Build KDTree of root surface for distance queries
        root_tree = cKDTree(root)

        # Target volume: between root surface and ideal surface
        # A voxel is "inside" if:
        #   - its z is ABOVE the nearest root-surface height, AND
        #   - its z is BELOW the ideal (interpolated) surface.
        #
        # Approximate "above root" via distance to root cloud.
        voxel_centres = np.column_stack([Xg.ravel(), Yg.ravel(), Zg.ravel()])
        dist_to_root, _ = root_tree.query(voxel_centres)
        dist_vol = dist_to_root.reshape(Xg.shape)

        # The ideal surface acts as a ceiling per XY column
        z_ceil = z_ideal[:, :, np.newaxis]   # broadcast over Z axis
        above_root = dist_vol > (self.voxel_size * 2)  # not inside root itself
        below_ideal = Zg <= z_ceil
        # Keep voxels above the root surface floor (per-column, not hard cutoff)
        root_z_min = np.min(root[:, 2]) if len(root) > 0 else bb_min[2]
        above_bottom = Zg >= root_z_min

        voxel_grid = above_root & below_ideal & above_bottom

        logger.info("  Grid shape       : %s", voxel_grid.shape)
        logger.info("  Filled voxels    : %d (%.1f %%)",
                     voxel_grid.sum(),
                     100.0 * voxel_grid.sum() / voxel_grid.size)

        return dict(
            voxel_grid=voxel_grid,
            grid_origin=bb_min,
            grid_spacing=self.voxel_size,
            xs=xs, ys=ys, zs=zs,
            Xg=Xg, Yg=Yg, Zg=Zg,
            rbf_surface=rbf,
            root_tree=root_tree,
            root_verts=root,
            mesh_path=seg.get("obj_path"),
        )

    # ───────────────────────────────────────────────────────────────────
    # PHASE 3 — The "Antibacterial Armor" (PCL + BAG Shell)
    # ───────────────────────────────────────────────────────────────────
    def phase3_armor_shell(self, volume: dict) -> np.ndarray:
        """Create a dense 0.5 mm PCL shell by binary erosion.

        Bioactive Glass (45S5) Doping at 10 wt %
        -----------------------------------------
        The BAG component releases Si⁴⁺ and Ca²⁺ ions that:
        • Elevate local pH → direct bactericidal effect.
        • Promote M2 (anti-inflammatory) macrophage polarization,
          suppressing chronic inflammation at the implant site.
        • Enhance osteoblast activity at the bone-crest interface.

        Manufacturing note: BAG increases melt viscosity ~15 %; the
        slicer must raise extrusion pressure accordingly for Tool 0.
        """
        thickness_mm = self._cfg("armor", "thickness_mm", ARMOR_THICKNESS_MM)
        erosion_conn = self._cfg("armor", "erosion_connectivity", 1)
        use_meshlib = self._cfg("armor", "use_meshlib", True)

        logger.info("PHASE 3 — Generating PCL+BAG armor shell (%.1f mm)",
                     thickness_mm)

        voxel_grid = volume["voxel_grid"]
        n_erode = max(1, int(round(thickness_mm / self.voxel_size)))

        # ── Scipy binary erosion (reliable for all geometries) ────────
        struct = ndimage.generate_binary_structure(3, erosion_conn)
        eroded = ndimage.binary_erosion(voxel_grid, structure=struct,
                                        iterations=n_erode)

        # If erosion consumed everything (thin regions), reduce
        # iterations until at least some interior remains.
        actual_n = n_erode
        while not eroded.any() and actual_n > 1:
            actual_n -= 1
            eroded = ndimage.binary_erosion(voxel_grid, structure=struct,
                                            iterations=actual_n)
        if actual_n != n_erode:
            logger.info("  Reduced erosion %d -> %d iters (thin geometry)",
                        n_erode, actual_n)

        shell_mask = voxel_grid & ~eroded

        # Initialise the material grid
        material_grid = np.zeros(voxel_grid.shape, dtype=np.int8)
        material_grid[shell_mask] = MAT_PCL_BAG

        n_shell = int(shell_mask.sum())
        logger.info("  Shell voxels     : %d  (erosion iter=%d)", n_shell, n_erode)
        return material_grid

    # ───────────────────────────────────────────────────────────────────
    # PHASE 4 — Anisotropic Core (Bio-Glue + PDL-guided Gyroid)
    # ───────────────────────────────────────────────────────────────────
    def phase4_anisotropic_core(
        self,
        material_grid: np.ndarray,
        volume: dict,
        seg: dict,
    ) -> np.ndarray:
        """Fill the interior with an anisotropic Schoen Gyroid lattice.

        Two sub-zones
        -------------
        1. **Bio-Glue** (100 µm adjacent to root): high-density GelMA
           (low isovalue → thick walls) for maximum cell attachment to
           the denuded root surface.
        2. **Main Core**: standard gyroid whose pore direction is
           *stretched* along the root-normal axis to create elongated
           channels for Sharpey's fiber ingrowth and PDL regeneration.

        PDL Anisotropy Transform
        ~~~~~~~~~~~~~~~~~~~~~~~~
        z' = z × (1 + (k − 1) · exp(−d / λ))

        where k=3 stretches pores 3× at the root surface and decays
        exponentially with distance d (λ=2 mm).  This mimics the
        natural 45–90° fibre insertion angle of Sharpey's fibres.
        """
        # Read core config
        target_pore = self._cfg("core", "target_pore_um", TARGET_PORE_UM)
        pore_tol = self._cfg("core", "pore_tolerance_um", PORE_TOLERANCE_UM)
        bioglue_mm = self._cfg("core", "bioglue_thickness_mm", BIOGLUE_THICKNESS_MM)
        pdl_k = self._cfg("core", "pdl_anisotropy_k", PDL_ANISOTROPY_K)
        pdl_decay = self._cfg("core", "pdl_decay_length_mm", PDL_DECAY_LENGTH)
        cell_size = self._cfg("core", "cell_size_mm", 2.0)
        iso_bracket = tuple(self._cfg("core", "isovalue_bracket", [0.01, 1.5]))
        stiffness_limit = self._cfg("core", "stiffness_limit_kpa", 15.0)

        logger.info("PHASE 4 — Building anisotropic GelMA gyroid core")

        voxel_grid = volume["voxel_grid"]
        Xg, Yg, Zg = volume["Xg"], volume["Yg"], volume["Zg"]
        root_tree: cKDTree = volume["root_tree"]

        # Interior = inside the original volume but NOT part of armor
        interior_mask = voxel_grid & (material_grid == MAT_EMPTY)

        # --- Distance from every voxel to root surface ----------------
        interior_coords = np.column_stack([
            Xg[interior_mask], Yg[interior_mask], Zg[interior_mask]
        ])
        dist_to_root, _ = root_tree.query(interior_coords)

        # --- Sub-zone 1: Bio-Glue layer ------
        bioglue_local = dist_to_root <= bioglue_mm
        bioglue_indices = np.where(interior_mask)
        for i, is_bg in enumerate(bioglue_local):
            if is_bg:
                material_grid[
                    bioglue_indices[0][i],
                    bioglue_indices[1][i],
                    bioglue_indices[2][i],
                ] = MAT_GELMA_BIOGLUE

        n_bioglue = int(bioglue_local.sum())
        logger.info("  Bio-glue voxels  : %d", n_bioglue)

        # --- Sub-zone 2: Gyroid core with PDL anisotropy --------------
        core_mask = interior_mask & (material_grid == MAT_EMPTY)
        if core_mask.sum() == 0:
            logger.warning("  No interior voxels remain for gyroid core.")
            return material_grid

        Xc = Xg[core_mask]
        Yc = Yg[core_mask]
        Zc = Zg[core_mask]

        # Distance to root for core voxels
        core_coords = np.column_stack([Xc, Yc, Zc])
        d_root, _ = root_tree.query(core_coords)

        # PDL anisotropy: stretch Z near root
        aniso_factor = 1.0 + (pdl_k - 1.0) * np.exp(
            -d_root / pdl_decay
        )
        Zc_prime = Zc * aniso_factor

        # ── SDF evaluation ────────────────────────────────────────────
        # Scale coordinates so the gyroid repeats every cell_size mm.
        # 2π in trig space = one unit cell = cell_size in physical space.
        freq = 2.0 * np.pi / cell_size
        Xn = Xc * freq
        Yn = Yc * freq
        Zn = Zc_prime * freq

        if _HAS_LISBON_TPMS:
            logger.info("  LisbonTPMS available (used for isovalue solver below)")
        sdf_vals = (
            np.cos(Xn) * np.sin(Yn) +
            np.cos(Yn) * np.sin(Zn) +
            np.cos(Zn) * np.sin(Xn)
        )

        # --- Solve isovalue for 325 µm mean pore size ----------------
        # Build a small dense SDF volume for the solver (subsample)
        N_sub = min(60, int(round(core_mask.sum() ** (1/3))))
        if N_sub >= 10:
            if _HAS_LISBON_TPMS:
                # Use LisbonTPMS TPMS class for the solver volume
                logger.info("  Using LisbonTPMS TPMS class for isovalue solver")
                bbox = np.ptp(core_coords, axis=0)
                dim_mm = float(max(bbox.max(), 1.0))
                tpms = LisbonTPMS(name='gyroid', dimensions=dim_mm,
                                  voxel_size=dim_mm / N_sub)
                tpms.cell_size_config(cell_size=cell_size)
                sdf_sub = tpms.grid
                sub_voxel_mm = dim_mm / N_sub
            else:
                lin = np.linspace(-np.pi, np.pi, N_sub)
                Xs, Ys, Zs = np.meshgrid(lin, lin, lin, indexing="ij")
                sdf_sub = (
                    np.cos(Xs) * np.sin(Ys) +
                    np.cos(Ys) * np.sin(Zs) +
                    np.cos(Zs) * np.sin(Xs)
                )
                sub_voxel_mm = cell_size / N_sub
            try:
                optimal_t, pore_stats = self.validator.pore \
                    .solve_isovalue_for_target_pore_size(
                        sdf_sub,
                        target_pore_um=target_pore,
                        tolerance_um=pore_tol,
                        bracket=iso_bracket,
                        voxel_size_mm=sub_voxel_mm,
                    )
            except Exception as exc:
                logger.warning("Isovalue solver failed (%s); using t=0.35", exc)
                optimal_t = 0.35
        else:
            optimal_t = 0.35

        # Threshold the per-voxel SDF
        solid_core = np.abs(sdf_vals) <= optimal_t

        core_indices = np.where(core_mask)
        for i, is_solid in enumerate(solid_core):
            if is_solid:
                material_grid[
                    core_indices[0][i],
                    core_indices[1][i],
                    core_indices[2][i],
                ] = MAT_GELMA_CORE

        n_core = int(solid_core.sum())
        logger.info("  Core voxels      : %d  (t=%.4f)", n_core, optimal_t)

        # --- Stiffness check ------------------------------------------
        porosity = 1.0 - solid_core.mean()
        warning = self.validator.stiffness.check_mechanotransduction_limit(
            self.validator.stiffness.estimate_stiffness(porosity)["e_scaffold_kpa"],
            limit_kpa=stiffness_limit,
        )
        stiff = self.validator.stiffness.estimate_stiffness(porosity)
        stiff["stiffness_warning"] = warning
        logger.info("  Porosity=%.3f  E_scaffold=%.2f KPa",
                     porosity, stiff["e_scaffold_kpa"])
        if warning:
            logger.warning("  %s", warning)

        return material_grid

    # ───────────────────────────────────────────────────────────────────
    # PHASE 5 — Sacrificial Vascular Blueprint
    # ───────────────────────────────────────────────────────────────────
    def phase5_vascular_channels(
        self,
        material_grid: np.ndarray,
        volume: dict,
    ) -> np.ndarray:
        """Boolean-OR a sparse grid of 400 µm Pluronic F-127 cylinders
        into the core region for post-fabrication channel perfusion.

        After scaffold maturation the Pluronic is dissolved at 4 °C,
        leaving open lumens that support capillary sprouting from the
        host vascular bed (pre-vascularisation strategy, Miller 2012).
        """
        channel_dia = self._cfg("vascular", "channel_diameter_mm", VASCULAR_CHANNEL_DIA_MM)
        channel_spacing = self._cfg("vascular", "channel_spacing_mm", VASCULAR_SPACING_MM)

        logger.info("PHASE 5 — Inserting sacrificial vascular channels")

        Xg, Yg = volume["Xg"], volume["Yg"]
        radius_mm = channel_dia / 2.0

        # Grid of cylinder centres in XY
        x_range = np.arange(Xg.min() + 1.0, Xg.max() - 1.0, channel_spacing)
        y_range = np.arange(Yg.min() + 1.0, Yg.max() - 1.0, channel_spacing)

        n_channels = 0
        for cx in x_range:
            for cy in y_range:
                # Distance from each voxel's XY to cylinder axis
                dist_xy = np.sqrt((Xg - cx) ** 2 + (Yg - cy) ** 2)
                inside_cyl = dist_xy <= radius_mm

                # Only overwrite core material (preserve armor)
                overwrite = inside_cyl & np.isin(
                    material_grid, [MAT_GELMA_CORE, MAT_GELMA_BIOGLUE]
                )
                material_grid[overwrite] = MAT_PLURONIC
                n_channels += 1

        logger.info("  Channels placed  : %d  (Ø %.0f µm, spacing %.1f mm)",
                     n_channels,
                     channel_dia * 1000,
                     channel_spacing)
        return material_grid

    # ───────────────────────────────────────────────────────────────────
    # PHASE 6 — Multi-Material G-code Export (FullControl)
    # ───────────────────────────────────────────────────────────────────
    def phase6_gcode_export(
        self,
        material_grid: np.ndarray,
        volume: dict,
    ) -> str:
        """Slice the multi-material voxel grid into 3-head bioprinter
        G-code using the FullControl library.

        Print order per layer (CRITICAL):
            Tool 0  →  PCL+BAG Armor   (retaining wall — prints first)
            Tool 1  →  GelMA Core
            Tool 2  →  Pluronic Channels

        The armor MUST print first so that its rigid walls contain the
        soft GelMA hydrogel during extrusion.
        """
        import fullcontrol as fc

        logger.info("PHASE 6 — Generating multi-material G-code")

        # Read gcode config (override HEAD_CONFIG if provided)
        gcode_cfg = self.config.get("gcode", {})
        travel_speed = gcode_cfg.get("travel_speed_mm_min", 3000)
        cfg_heads = gcode_cfg.get("heads", None)
        if cfg_heads:
            head_config = {}
            for h in cfg_heads:
                head_config[h["tool_id"]] = dict(
                    name=h["name"],
                    pressure_kpa=h["pressure_kpa"],
                    speed_mm_s=h["speed_mm_s"],
                    nozzle_mm=h["nozzle_mm"],
                )
        else:
            head_config = HEAD_CONFIG

        xs, ys, zs = volume["xs"], volume["ys"], volume["zs"]
        layer_height = self.voxel_size  # one voxel per layer

        default_nozzle = head_config.get(0, HEAD_CONFIG[0])["nozzle_mm"]
        default_speed = head_config.get(0, HEAD_CONFIG[0])["speed_mm_s"]

        # --- G-code controls ------------------------------------------
        controls = fc.GcodeControls(
            printer_name="custom",
            initialization_data={
                "print_speed": _mm_s_to_mm_min(default_speed),
                "travel_speed": travel_speed,
                "extrusion_width": default_nozzle,
                "extrusion_height": layer_height,
            },
            save_as=str(self.output_dir / "scaffold_gcode"),
        )

        steps: list = []

        # --- Preamble -------------------------------------------------
        steps.append(fc.ManualGcode(text="; === GingivaGen 2.0 Multi-Material Scaffold ==="))
        steps.append(fc.ManualGcode(text="G28 ; home"))
        steps.append(fc.ManualGcode(text="G90 ; absolute positioning"))
        steps.append(fc.ManualGcode(text="M83 ; relative extrusion"))

        # --- Layer-by-layer slicing -----------------------------------
        # Print order per material, per layer
        mat_print_order = [MAT_PCL_BAG, MAT_GELMA_CORE,
                           MAT_GELMA_BIOGLUE, MAT_PLURONIC]
        n_layers = material_grid.shape[2]

        for lz in range(n_layers):
            layer_slice = material_grid[:, :, lz]
            if not np.any(layer_slice > MAT_EMPTY):
                continue

            z_mm = zs[lz] if lz < len(zs) else zs[-1]
            steps.append(fc.ManualGcode(
                text=f"; --- Layer {lz}  z={z_mm:.3f} mm ---"))

            for mat in mat_print_order:
                mat_mask = layer_slice == mat
                if not np.any(mat_mask):
                    continue

                tool_id = MAT_TO_TOOL.get(mat, 1)
                self._switch_tool(steps, tool_id, head_config, travel_speed)

                # Serpentine raster of the material voxels
                ixs, iys = np.where(mat_mask)
                if len(ixs) == 0:
                    continue

                # Sort into raster rows
                row_order = np.lexsort((iys, ixs))
                prev_row = -1
                reverse = False
                for idx in row_order:
                    ix, iy = ixs[idx], iys[idx]
                    if ix != prev_row:
                        reverse = not reverse
                        prev_row = ix
                    x_mm = xs[ix] if ix < len(xs) else xs[-1]
                    y_mm = ys[iy] if iy < len(ys) else ys[-1]
                    steps.append(fc.Point(x=float(x_mm),
                                         y=float(y_mm),
                                         z=float(z_mm)))

        # --- End procedure --------------------------------------------
        steps.append(fc.Extruder(on=False))
        steps.append(fc.ManualGcode(text="G91"))
        steps.append(fc.ManualGcode(text="G0 Z10 F3000 ; lift"))
        steps.append(fc.ManualGcode(text="G90"))
        steps.append(fc.ManualGcode(text="M0 ; end"))

        gcode = fc.transform(steps, "gcode", controls)

        gcode_path = self.output_dir / "scaffold.gcode"
        gcode_path.write_text(gcode, encoding="utf-8")
        logger.info("  G-code saved     : %s  (%d lines)",
                     gcode_path, gcode.count("\n"))
        return gcode

    # ------------------------------------------------------------------
    @staticmethod
    def _switch_tool(
        steps: list,
        tool_id: int,
        head_config: dict | None = None,
        travel_speed: float = 3000,
    ) -> None:
        """Insert G-code commands to activate a bioprint head."""
        import fullcontrol as fc

        heads = head_config or HEAD_CONFIG
        cfg = heads[tool_id]
        steps.append(fc.Extruder(on=False))
        steps.append(fc.ManualGcode(text=f"; Switch to {cfg['name']} (T{tool_id})"))
        steps.append(fc.ManualGcode(text=f"T{tool_id}"))
        steps.append(fc.ManualGcode(
            text=f"M42 S{cfg['pressure_kpa']} ; pressure {cfg['pressure_kpa']} kPa"))
        steps.append(fc.Printer(
            print_speed=_mm_s_to_mm_min(cfg["speed_mm_s"]),
            travel_speed=travel_speed,
        ))
        steps.append(fc.ExtrusionGeometry(
            area_model="circle", diameter=cfg["nozzle_mm"]))
        steps.append(fc.Extruder(on=True))

    # ───────────────────────────────────────────────────────────────────
    # RUN — full pipeline orchestration
    # ───────────────────────────────────────────────────────────────────
    def run(self, obj_path: str) -> dict:
        """Execute all six phases and return results dict."""
        results: dict[str, Any] = {}
        t0 = time.perf_counter()

        # Phase 1
        t1 = time.perf_counter()
        seg = self.phase1_neural_segmentation(obj_path)
        results["segmentation"] = seg
        logger.info("  Phase 1 done in %.2f s", time.perf_counter() - t1)

        # Phase 2
        t1 = time.perf_counter()
        vol = self.phase2_ideal_volume(seg)
        results["volume"] = vol
        logger.info("  Phase 2 done in %.2f s", time.perf_counter() - t1)

        # Phase 3
        t1 = time.perf_counter()
        mat = self.phase3_armor_shell(vol)
        logger.info("  Phase 3 done in %.2f s", time.perf_counter() - t1)

        # Phase 4
        t1 = time.perf_counter()
        mat = self.phase4_anisotropic_core(mat, vol, seg)
        logger.info("  Phase 4 done in %.2f s", time.perf_counter() - t1)

        # Phase 5
        t1 = time.perf_counter()
        mat = self.phase5_vascular_channels(mat, vol)
        results["material_grid"] = mat
        logger.info("  Phase 5 done in %.2f s", time.perf_counter() - t1)

        # Phase 6
        t1 = time.perf_counter()
        gcode = self.phase6_gcode_export(mat, vol)
        results["gcode"] = gcode
        results["gcode_path"] = str(self.output_dir / "scaffold.gcode")
        logger.info("  Phase 6 done in %.2f s", time.perf_counter() - t1)

        total = time.perf_counter() - t0
        logger.info("== Pipeline complete in %.2f s ==", total)

        # Final validation report
        # Binary volume: solid = any material OR exterior.
        # Only interior empty voxels count as pores — excludes the
        # vast exterior empty space that would inflate measurements.
        has_core = np.any(mat == MAT_GELMA_CORE)
        if has_core:
            validation_binary = (mat > MAT_EMPTY) | ~vol["voxel_grid"]
            report = self.validator.full_validation(validation_binary)
            self.validator.print_report(report)
            results["validation"] = report

        # ── Mesh export (marching cubes → STL/OBJ per material) ──────
        try:
            from mesh_exporter import export_all_materials, export_combined_obj
            mesh_dir = self.output_dir / "meshes"
            exported = export_all_materials(
                mat, self.voxel_size, vol["grid_origin"], mesh_dir, fmt="stl")
            results["exported_meshes"] = exported

            combined = export_combined_obj(
                mat, self.voxel_size, vol["grid_origin"],
                mesh_dir / "scaffold_combined.obj")
            results["combined_mesh"] = str(combined)
            logger.info("  Exported %d material meshes + combined OBJ", len(exported))
        except Exception as exc:
            logger.warning("Mesh export skipped: %s", exc)

        # ── Save material grid for offline validation / viz ───────────
        np.save(self.output_dir / "material_grid.npy", mat)

        return results


# ═══════════════════════════════════════════════════════════════════════════
# Self-test — synthetic gingival recession mesh
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s | %(levelname)s | %(message)s",
    )

    import trimesh

    # --- Build a single-surface synthetic mesh mimicking recession ------
    # Real intraoral scans are single surfaces.  We create a surface
    # with a raised rim (healthy gingiva) and a deep central dip
    # (exposed root / recession defect).  The z-range spread of ~6 mm
    # gives phase 2 enough height to generate a thick scaffold volume.
    nx, ny = 80, 60
    x = np.linspace(-6, 6, nx)
    y = np.linspace(-4, 4, ny)
    Xm, Ym = np.meshgrid(x, y, indexing="ij")

    # Healthy margin = raised outer ring at z ≈ 5
    # Recession defect = central Gaussian dip down to z ≈ 0
    Zm = 5.0 - 5.0 * np.exp(-(Xm ** 2 + Ym ** 2) / 8.0)

    verts_list = []
    faces_list = []
    for i in range(nx):
        for j in range(ny):
            verts_list.append([Xm[i, j], Ym[i, j], Zm[i, j]])
    verts_arr = np.array(verts_list)

    for i in range(nx - 1):
        for j in range(ny - 1):
            v00 = i * ny + j
            v10 = (i + 1) * ny + j
            v01 = i * ny + (j + 1)
            v11 = (i + 1) * ny + (j + 1)
            faces_list.append([v00, v10, v11])
            faces_list.append([v00, v11, v01])
    faces_arr = np.array(faces_list)

    test_mesh = trimesh.Trimesh(vertices=verts_arr, faces=faces_arr)
    test_path = "output/test_recession.obj"
    Path("output").mkdir(exist_ok=True)
    test_mesh.export(test_path)
    logger.info("Synthetic test mesh saved: %s (%d verts)", test_path, len(verts_arr))

    # --- Run the full pipeline ----------------------------------------
    # Use 0.15 mm voxel for the self-test; production uses 0.05 mm
    pipeline = GingivaGenV2(output_dir="output", voxel_size=0.15)
    results = pipeline.run(test_path)

    # --- Summary ------------------------------------------------------
    mat = results.get("material_grid")
    if mat is not None:
        for tag, name in [(1, "PCL+BAG armor"), (2, "GelMA core"),
                          (3, "Bio-glue"), (4, "Pluronic")]:
            count = int((mat == tag).sum())
            if count > 0:
                print(f"  {name}: {count:,} voxels")

    print("\nGingivaGen 2.0 pipeline completed successfully.")
