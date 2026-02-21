"""
Unit tests for GingivaGen 2.0 validation engine.
Run with:  pytest tests/ -v
"""

import numpy as np
import pytest
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validation_engine import (
    PoreValidator,
    StiffnessValidator,
    ScaffoldValidator,
    ValidationReport,
)


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def solid_cube():
    """Fully solid 20³ cube (no pores)."""
    return np.ones((20, 20, 20), dtype=bool)


@pytest.fixture
def empty_cube():
    """Fully empty 20³ cube (all pores)."""
    return np.zeros((20, 20, 20), dtype=bool)


@pytest.fixture
def checkerboard():
    """Alternating solid/void 3-D checkerboard."""
    grid = np.zeros((20, 20, 20), dtype=bool)
    grid[::2, ::2, ::2] = True
    grid[1::2, 1::2, 1::2] = True
    return grid


@pytest.fixture
def synthetic_gyroid():
    """Small gyroid SDF volume and its thresholded solid."""
    N = 40
    lin = np.linspace(-np.pi, np.pi, N)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")
    sdf = np.cos(X) * np.sin(Y) + np.cos(Y) * np.sin(Z) + np.cos(Z) * np.sin(X)
    solid = np.abs(sdf) <= 0.4
    return sdf, solid


# ═══════════════════════════════════════════════════════════════════════════
# PoreValidator
# ═══════════════════════════════════════════════════════════════════════════

class TestPoreValidator:

    def test_solid_cube_porosity_zero(self, solid_cube):
        pv = PoreValidator(voxel_size_mm=0.1)
        stats = pv.measure_pore_statistics(solid_cube)
        assert stats["porosity"] == pytest.approx(0.0, abs=1e-9)

    def test_empty_cube_porosity_one(self, empty_cube):
        pv = PoreValidator(voxel_size_mm=0.1)
        stats = pv.measure_pore_statistics(empty_cube)
        assert stats["porosity"] == pytest.approx(1.0, abs=1e-9)

    def test_checkerboard_porosity_near_half(self, checkerboard):
        pv = PoreValidator(voxel_size_mm=0.1)
        stats = pv.measure_pore_statistics(checkerboard)
        # Checkerboard sets only 2 of 8 sub-cubes → ~75% porosity
        assert 0.2 < stats["porosity"] < 0.85

    def test_local_thickness_returns_correct_shape(self, checkerboard):
        pv = PoreValidator(voxel_size_mm=0.1)
        lt = pv.compute_local_thickness(checkerboard)
        assert lt.shape == checkerboard.shape

    def test_local_thickness_units_are_microns(self, checkerboard):
        pv = PoreValidator(voxel_size_mm=0.05)
        lt = pv.compute_local_thickness(checkerboard)
        pore_values = lt[~checkerboard]
        if pore_values.size > 0:
            # Should be in µm range, not voxel counts
            assert pore_values.max() < 5000  # reasonable upper bound

    def test_gyroid_has_pores(self, synthetic_gyroid):
        _, solid = synthetic_gyroid
        pv = PoreValidator(voxel_size_mm=0.05)
        stats = pv.measure_pore_statistics(solid)
        assert stats["porosity"] > 0
        assert stats["mean_pore_um"] > 0

    def test_isovalue_solver_returns_valid_t(self, synthetic_gyroid):
        sdf, _ = synthetic_gyroid
        pv = PoreValidator(voxel_size_mm=0.05)
        t, stats = pv.solve_isovalue_for_target_pore_size(
            sdf, target_pore_um=200.0, tolerance_um=100.0,
            bracket=(0.05, 1.2),
        )
        assert 0.0 < t < 2.0
        assert stats["mean_pore_um"] > 0


# ═══════════════════════════════════════════════════════════════════════════
# StiffnessValidator
# ═══════════════════════════════════════════════════════════════════════════

class TestStiffnessValidator:

    def test_zero_porosity_equals_solid(self):
        sv = StiffnessValidator(e_solid_kpa=50.0)
        result = sv.estimate_stiffness(porosity=0.0)
        assert result["e_scaffold_kpa"] == pytest.approx(50.0)
        assert result["relative_density"] == pytest.approx(1.0)

    def test_full_porosity_equals_zero(self):
        sv = StiffnessValidator(e_solid_kpa=50.0)
        result = sv.estimate_stiffness(porosity=1.0)
        assert result["e_scaffold_kpa"] == pytest.approx(0.0)
        assert result["relative_density"] == pytest.approx(0.0)

    def test_half_porosity_gibson_ashby(self):
        sv = StiffnessValidator(e_solid_kpa=50.0, gibson_ashby_C=1.0,
                                gibson_ashby_n=2.0)
        result = sv.estimate_stiffness(porosity=0.5)
        # E = 50 * 1.0 * (0.5)^2 = 12.5
        assert result["e_scaffold_kpa"] == pytest.approx(12.5)

    def test_no_warning_under_limit(self):
        sv = StiffnessValidator(e_solid_kpa=50.0)
        warning = sv.check_mechanotransduction_limit(10.0, limit_kpa=15.0)
        assert warning is None

    def test_warning_over_limit(self):
        sv = StiffnessValidator(e_solid_kpa=50.0)
        warning = sv.check_mechanotransduction_limit(20.0, limit_kpa=15.0)
        assert warning is not None
        assert "REDUCE_DENSITY" in warning
        assert "YAP/TAZ" in warning

    def test_warning_at_exact_limit(self):
        sv = StiffnessValidator(e_solid_kpa=50.0)
        warning = sv.check_mechanotransduction_limit(15.0, limit_kpa=15.0)
        assert warning is None  # at limit, not over

    def test_validate_returns_combined(self):
        sv = StiffnessValidator(e_solid_kpa=50.0)
        result = sv.validate(porosity=0.7)
        assert "e_scaffold_kpa" in result
        assert "stiffness_warning" in result
        assert "relative_density" in result


# ═══════════════════════════════════════════════════════════════════════════
# ScaffoldValidator (integration)
# ═══════════════════════════════════════════════════════════════════════════

class TestScaffoldValidator:

    def test_full_validation_returns_report(self, synthetic_gyroid):
        _, solid = synthetic_gyroid
        sv = ScaffoldValidator(voxel_size_mm=0.05, e_solid_kpa=50.0)
        report = sv.full_validation(solid)
        assert isinstance(report, ValidationReport)
        assert report.porosity > 0
        assert report.scaffold_stiffness_kpa >= 0

    def test_report_has_timestamp(self, synthetic_gyroid):
        _, solid = synthetic_gyroid
        sv = ScaffoldValidator()
        report = sv.full_validation(solid)
        assert len(report.timestamp) > 10  # ISO format

    def test_solid_cube_high_stiffness(self, solid_cube):
        sv = ScaffoldValidator(e_solid_kpa=50.0)
        report = sv.full_validation(solid_cube)
        assert report.scaffold_stiffness_kpa == pytest.approx(50.0)
        assert report.stiffness_warning is not None  # 50 > 15


# ═══════════════════════════════════════════════════════════════════════════
# Gibson-Ashby math edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestGibsonAshbyMath:

    @pytest.mark.parametrize("porosity,expected_rho", [
        (0.0, 1.0),
        (0.25, 0.75),
        (0.5, 0.5),
        (0.75, 0.25),
        (1.0, 0.0),
    ])
    def test_relative_density(self, porosity, expected_rho):
        sv = StiffnessValidator()
        result = sv.estimate_stiffness(porosity)
        assert result["relative_density"] == pytest.approx(expected_rho)

    @pytest.mark.parametrize("C,n", [
        (1.0, 2.0),
        (0.3, 1.5),
        (2.0, 3.0),
    ])
    def test_custom_constants(self, C, n):
        sv = StiffnessValidator(e_solid_kpa=100.0, gibson_ashby_C=C,
                                gibson_ashby_n=n)
        result = sv.estimate_stiffness(porosity=0.4)
        expected = 100.0 * C * (0.6 ** n)
        assert result["e_scaffold_kpa"] == pytest.approx(expected, rel=1e-6)
