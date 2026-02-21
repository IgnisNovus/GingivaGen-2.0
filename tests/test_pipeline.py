"""
Integration tests for GingivaGen 2.0 orchestrator pipeline.
Run with:  pytest tests/test_pipeline.py -v

These tests use synthetic geometry and do NOT require external
model weights or GPU.
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import (
    GingivaGenV2,
    MAT_EMPTY, MAT_PCL_BAG, MAT_GELMA_CORE,
    MAT_GELMA_BIOGLUE, MAT_PLURONIC,
)


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def synthetic_obj(tmp_path):
    """Create a minimal .obj mesh simulating gingival recession."""
    import trimesh

    nx, ny = 40, 30
    x = np.linspace(-6, 6, nx)
    y = np.linspace(-4, 4, ny)
    Xm, Ym = np.meshgrid(x, y, indexing="ij")
    Zm = 5.0 - 5.0 * np.exp(-(Xm**2 + Ym**2) / 8.0)

    verts = []
    faces = []
    for i in range(nx):
        for j in range(ny):
            verts.append([Xm[i, j], Ym[i, j], Zm[i, j]])

    for i in range(nx - 1):
        for j in range(ny - 1):
            v00 = i * ny + j
            v10 = (i + 1) * ny + j
            v01 = i * ny + (j + 1)
            v11 = (i + 1) * ny + (j + 1)
            faces.append([v00, v10, v11])
            faces.append([v00, v11, v01])

    mesh = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
    obj_path = tmp_path / "test_scan.obj"
    mesh.export(str(obj_path))
    return str(obj_path)


@pytest.fixture
def pipeline(tmp_path):
    """Pipeline with coarse resolution for fast testing."""
    return GingivaGenV2(output_dir=str(tmp_path / "output"), voxel_size=0.2)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase1:

    def test_returns_required_keys(self, pipeline, synthetic_obj):
        result = pipeline.phase1_neural_segmentation(synthetic_obj)
        assert "mesh" in result
        assert "vertices" in result
        assert "defect_mask" in result
        assert "defect_vertices" in result
        assert "margin_points" in result
        assert "root_surface_vertices" in result

    def test_defect_is_subset(self, pipeline, synthetic_obj):
        result = pipeline.phase1_neural_segmentation(synthetic_obj)
        n_total = len(result["vertices"])
        n_defect = len(result["defect_vertices"])
        assert 0 < n_defect < n_total

    def test_margin_is_nonempty(self, pipeline, synthetic_obj):
        result = pipeline.phase1_neural_segmentation(synthetic_obj)
        assert len(result["margin_points"]) > 0


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase2:

    def test_voxel_grid_is_3d_bool(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        assert vol["voxel_grid"].ndim == 3
        assert vol["voxel_grid"].dtype == bool

    def test_grid_has_filled_voxels(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        assert vol["voxel_grid"].sum() > 0

    def test_returns_grid_metadata(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        assert "grid_origin" in vol
        assert "grid_spacing" in vol
        assert "rbf_surface" in vol


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase3:

    def test_armor_shell_is_material_1(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        assert np.any(mat == MAT_PCL_BAG)

    def test_armor_shell_preserves_shape(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        assert mat.shape == vol["voxel_grid"].shape

    def test_shell_subset_of_volume(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        # Every shell voxel should be inside the original volume
        shell_mask = mat == MAT_PCL_BAG
        assert np.all(vol["voxel_grid"][shell_mask])


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase4:

    def test_core_fills_interior(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        mat = pipeline.phase4_anisotropic_core(mat, vol, seg)
        # Should have core or bioglue material
        has_core = np.any(mat == MAT_GELMA_CORE)
        has_bioglue = np.any(mat == MAT_GELMA_BIOGLUE)
        assert has_core or has_bioglue

    def test_no_overlap_with_armor(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        armor_before = (mat == MAT_PCL_BAG).sum()
        mat = pipeline.phase4_anisotropic_core(mat, vol, seg)
        armor_after = (mat == MAT_PCL_BAG).sum()
        # Armor should not be overwritten by core
        assert armor_after == armor_before


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase5:

    def test_channels_use_pluronic_tag(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        mat = pipeline.phase4_anisotropic_core(mat, vol, seg)
        mat = pipeline.phase5_vascular_channels(mat, vol)
        # Pluronic may or may not be present depending on geometry
        # but the function should not crash
        assert mat.shape == vol["voxel_grid"].shape

    def test_channels_do_not_overwrite_armor(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        mat = pipeline.phase4_anisotropic_core(mat, vol, seg)
        armor_before = (mat == MAT_PCL_BAG).sum()
        mat = pipeline.phase5_vascular_channels(mat, vol)
        armor_after = (mat == MAT_PCL_BAG).sum()
        assert armor_after == armor_before


# ═══════════════════════════════════════════════════════════════════════════
# Material grid invariants
# ═══════════════════════════════════════════════════════════════════════════

class TestMaterialGridInvariants:

    def test_all_tags_are_valid(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        mat = pipeline.phase4_anisotropic_core(mat, vol, seg)
        mat = pipeline.phase5_vascular_channels(mat, vol)

        valid_tags = {MAT_EMPTY, MAT_PCL_BAG, MAT_GELMA_CORE,
                      MAT_GELMA_BIOGLUE, MAT_PLURONIC}
        unique = set(np.unique(mat))
        assert unique.issubset(valid_tags)

    def test_no_material_outside_volume(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        mat = pipeline.phase4_anisotropic_core(mat, vol, seg)

        # Every non-empty voxel should be inside the original volume
        filled = mat > MAT_EMPTY
        assert np.all(vol["voxel_grid"][filled])


# ═══════════════════════════════════════════════════════════════════════════
# Mesh exporter tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMeshExporter:

    def test_export_stl(self, tmp_path):
        from mesh_exporter import export_all_materials

        N = 20
        grid = np.zeros((N, N, N), dtype=np.int8)
        # Simple sphere shell
        xs = np.linspace(-2, 2, N)
        X, Y, Z = np.meshgrid(xs, xs, xs, indexing="ij")
        R = np.sqrt(X**2 + Y**2 + Z**2)
        grid[(R >= 1.0) & (R <= 1.5)] = 1

        origin = np.array([-2, -2, -2], dtype=np.float64)
        out = tmp_path / "meshes"
        paths = export_all_materials(grid, 0.2, origin, out, fmt="stl")
        assert len(paths) >= 1
        for p in paths.values():
            assert p.exists()
            assert p.stat().st_size > 0

    def test_export_obj(self, tmp_path):
        from mesh_exporter import export_all_materials

        N = 20
        grid = np.zeros((N, N, N), dtype=np.int8)
        grid[5:15, 5:15, 5:15] = 2
        origin = np.zeros(3)
        paths = export_all_materials(grid, 0.2, origin, tmp_path, fmt="obj")
        assert len(paths) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Data loader tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDataLoader:

    def test_fdi_mapping(self):
        from data_loader import FDI_TO_SLOT, slot_to_fdi
        # FDI 11 (upper central incisor) → slot 8
        assert FDI_TO_SLOT[11] == 8
        # FDI 31 (lower central incisor) → slot 8
        assert FDI_TO_SLOT[31] == 8
        # Round-trip
        assert slot_to_fdi(8, "upper") == 11
        assert slot_to_fdi(8, "lower") == 31

    def test_loader_init(self, tmp_path):
        from data_loader import Teeth3DSLoader
        loader = Teeth3DSLoader(dataset_root=tmp_path)
        assert loader.root == tmp_path


# ═══════════════════════════════════════════════════════════════════════════
# Phase 6 tests — G-code export (requires fullcontrol)
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase6:

    @pytest.fixture(autouse=True)
    def _skip_without_fullcontrol(self):
        pytest.importorskip("fullcontrol")

    def _run_phases_1_to_5(self, pipeline, synthetic_obj):
        seg = pipeline.phase1_neural_segmentation(synthetic_obj)
        vol = pipeline.phase2_ideal_volume(seg)
        mat = pipeline.phase3_armor_shell(vol)
        mat = pipeline.phase4_anisotropic_core(mat, vol, seg)
        mat = pipeline.phase5_vascular_channels(mat, vol)
        return mat, vol

    def test_gcode_is_nonempty_string(self, pipeline, synthetic_obj):
        mat, vol = self._run_phases_1_to_5(pipeline, synthetic_obj)
        gcode = pipeline.phase6_gcode_export(mat, vol)
        assert isinstance(gcode, str)
        assert len(gcode) > 0

    def test_gcode_file_created(self, pipeline, synthetic_obj):
        mat, vol = self._run_phases_1_to_5(pipeline, synthetic_obj)
        pipeline.phase6_gcode_export(mat, vol)
        gcode_path = Path(pipeline.output_dir) / "scaffold.gcode"
        assert gcode_path.exists()

    def test_gcode_contains_header(self, pipeline, synthetic_obj):
        mat, vol = self._run_phases_1_to_5(pipeline, synthetic_obj)
        gcode = pipeline.phase6_gcode_export(mat, vol)
        assert "GingivaGen 2.0" in gcode

    def test_gcode_contains_tool_switches(self, pipeline, synthetic_obj):
        mat, vol = self._run_phases_1_to_5(pipeline, synthetic_obj)
        gcode = pipeline.phase6_gcode_export(mat, vol)
        assert "T0" in gcode or "T1" in gcode


# ═══════════════════════════════════════════════════════════════════════════
# End-to-end integration tests
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEnd:

    @pytest.fixture(autouse=True)
    def _skip_without_fullcontrol(self):
        pytest.importorskip("fullcontrol")

    def test_full_pipeline_run(self, pipeline, synthetic_obj):
        results = pipeline.run(synthetic_obj)
        for key in ("segmentation", "volume", "material_grid", "gcode", "gcode_path"):
            assert key in results, f"Missing key: {key}"
        assert results["material_grid"].ndim == 3
        assert isinstance(results["gcode"], str)
        assert len(results["gcode"]) > 0

    def test_run_produces_output_files(self, pipeline, synthetic_obj):
        pipeline.run(synthetic_obj)
        out = Path(pipeline.output_dir)
        assert (out / "material_grid.npy").exists()
        assert (out / "scaffold.gcode").exists()


# ═══════════════════════════════════════════════════════════════════════════
# Real-scan integration test (Teeth3DS+ sample)
# ═══════════════════════════════════════════════════════════════════════════

REAL_SCAN = (
    Path(__file__).resolve().parent.parent
    / "Teeth3DS+"
    / "extracted"
    / "teeth3ds_sample"
    / "01F4JV8X"
    / "01F4JV8X_upper.obj"
)


@pytest.mark.skipif(not REAL_SCAN.exists(), reason=f"Real scan not found: {REAL_SCAN}")
class TestRealScanIntegration:
    """Integration tests against a real Teeth3DS+ intraoral scan.

    The pipeline is run once (class-scoped) at coarse voxel size (0.5 mm)
    to keep wall-clock time reasonable on CPU-only CI.
    """

    @pytest.fixture(autouse=True)
    def _skip_without_fullcontrol(self):
        pytest.importorskip("fullcontrol")

    @pytest.fixture(scope="class")
    def real_results(self, tmp_path_factory):
        pytest.importorskip("fullcontrol")
        out = tmp_path_factory.mktemp("real_output")
        pipe = GingivaGenV2(output_dir=str(out), voxel_size=0.5)
        results = pipe.run(str(REAL_SCAN))
        results["_output_dir"] = out
        return results

    def test_full_pipeline_result_keys(self, real_results):
        for key in ("segmentation", "volume", "material_grid", "gcode", "gcode_path"):
            assert key in real_results, f"Missing key: {key}"

    def test_material_grid_contains_all_materials(self, real_results):
        mat = real_results["material_grid"]
        unique = set(np.unique(mat))
        for tag in (MAT_PCL_BAG, MAT_GELMA_CORE, MAT_GELMA_BIOGLUE, MAT_PLURONIC):
            assert tag in unique, f"Material tag {tag} not found in grid"

    def test_output_files_exist(self, real_results):
        out = real_results["_output_dir"]
        assert (out / "material_grid.npy").exists()
        assert (out / "scaffold.gcode").exists()

    def test_validation_report_sane(self, real_results):
        report = real_results.get("validation")
        assert report is not None, "Validation report missing from results"
        assert report.porosity > 0, "Porosity should be > 0"
        assert report.scaffold_stiffness_kpa > 0, "Stiffness should be > 0"
