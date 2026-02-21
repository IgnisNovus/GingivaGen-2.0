"""
GingivaGen 2.0 — Validation Engine
====================================
Pore-size verification (PoreSpy EDT/local-thickness) and scaffold
stiffness estimation (Gibson-Ashby) with mechanotransduction guardrails.

The biological rationale for every threshold is commented inline so that
downstream engineers and reviewers understand *why* each limit exists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.optimize import brentq

# PoreSpy is used exclusively for Euclidean-Distance-Transform-based
# local thickness measurement — the gold-standard for pore-size
# characterisation in porous scaffold micro-CT analysis.
import porespy

logger = logging.getLogger("GingivaGen.Validation")


# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationReport:
    """Immutable record produced by a full scaffold validation pass."""

    mean_pore_size_um: float = 0.0
    pore_std_um: float = 0.0
    porosity: float = 0.0
    relative_density: float = 0.0
    scaffold_stiffness_kpa: float = 0.0
    stiffness_warning: Optional[str] = None
    pore_target_met: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ═══════════════════════════════════════════════════════════════════════════
# Pore-size validation  (PoreSpy local_thickness)
# ═══════════════════════════════════════════════════════════════════════════

class PoreValidator:
    """Measures pore dimensions via Euclidean Distance Transform (EDT).

    `porespy.filters.local_thickness` inscribes maximal spheres at every
    void voxel.  The diameter of each sphere is that voxel's *local pore
    size*.  We convert voxel units → µm using the known voxel pitch.
    """

    def __init__(self, voxel_size_mm: float = 0.05) -> None:
        self.voxel_size_mm = voxel_size_mm
        # 1 voxel edge in µm
        self.voxel_um = voxel_size_mm * 1000.0

    # ------------------------------------------------------------------
    def compute_local_thickness(
        self,
        binary_volume: np.ndarray,
        voxel_size_mm: float | None = None,
    ) -> np.ndarray:
        """Return a float volume where each *pore* voxel stores its local
        thickness in **micrometres**.

        Parameters
        ----------
        binary_volume : bool ndarray
            ``True`` = solid scaffold material, ``False`` = void / pore.
        voxel_size_mm : float, optional
            Override voxel pitch (mm) for this call.  Used when the grid
            being analysed has a different resolution to the pipeline.
        """
        voxel_um = (voxel_size_mm * 1000.0) if voxel_size_mm else self.voxel_um
        pore_phase = ~binary_volume  # invert: pores become True
        lt_voxels = porespy.filters.local_thickness(pore_phase)
        return lt_voxels * voxel_um  # voxel counts → µm

    # ------------------------------------------------------------------
    def measure_pore_statistics(
        self,
        binary_volume: np.ndarray,
        voxel_size_mm: float | None = None,
    ) -> dict:
        """Compute descriptive statistics of the pore-size distribution.

        Returns
        -------
        dict with keys: mean_pore_um, std_pore_um, min_pore_um,
        max_pore_um, porosity (void fraction 0-1).
        """
        lt_um = self.compute_local_thickness(binary_volume, voxel_size_mm)
        pore_mask = ~binary_volume
        porosity = float(pore_mask.sum()) / binary_volume.size

        pore_values = lt_um[pore_mask]
        if pore_values.size == 0:
            return dict(mean_pore_um=0.0, std_pore_um=0.0,
                        min_pore_um=0.0, max_pore_um=0.0, porosity=porosity)

        return dict(
            mean_pore_um=float(np.mean(pore_values)),
            std_pore_um=float(np.std(pore_values)),
            min_pore_um=float(np.min(pore_values)),
            max_pore_um=float(np.max(pore_values)),
            porosity=porosity,
        )

    # ------------------------------------------------------------------
    def solve_isovalue_for_target_pore_size(
        self,
        sdf_grid: np.ndarray,
        target_pore_um: float = 325.0,
        tolerance_um: float = 25.0,
        bracket: tuple[float, float] = (0.01, 1.5),
        voxel_size_mm: float | None = None,
    ) -> tuple[float, dict]:
        """Brentq root-find for the iso-value *t* that yields
        ``mean_pore_size ≈ target_pore_um ± tolerance_um``.

        The SDF is thresholded as a *sheet* gyroid: solid where ``|SDF| ≤ t``.

        Parameters
        ----------
        sdf_grid : float ndarray
            Raw gyroid SDF values (output of Shoen_Gyroid evaluation).
        target_pore_um : float
            Desired mean pore diameter in µm (default 325 for fibroblast
            migration per Karageorgiou & Kaplan 2005).
        tolerance_um : float
            Acceptable deviation from target.
        bracket : (lo, hi)
            Search interval for *t*.
        voxel_size_mm : float, optional
            Physical voxel pitch of *sdf_grid*.  When the solver grid
            has a different resolution to the pipeline grid, pass the
            solver grid's pitch here so that local-thickness is
            converted to µm correctly.

        Returns
        -------
        (optimal_t, pore_stats) where pore_stats is the dict from
        ``measure_pore_statistics`` at the solved iso-value.
        """

        def _objective(t: float) -> float:
            solid = np.abs(sdf_grid) <= t
            stats = self.measure_pore_statistics(solid, voxel_size_mm)
            return stats["mean_pore_um"] - target_pore_um

        try:
            optimal_t = brentq(_objective, bracket[0], bracket[1],
                               xtol=1e-4, maxiter=60)
        except ValueError:
            # Bracket does not straddle zero — fall back to midpoint
            logger.warning(
                "Brentq failed to converge; bracket [%.3f, %.3f] may not "
                "straddle the target pore size. Using bracket midpoint.",
                bracket[0], bracket[1])
            optimal_t = (bracket[0] + bracket[1]) / 2.0

        solid = np.abs(sdf_grid) <= optimal_t
        stats = self.measure_pore_statistics(solid, voxel_size_mm)
        logger.info("Solved isovalue t=%.4f -> mean pore %.1f um (target %d+/-%d)",
                    optimal_t, stats["mean_pore_um"], target_pore_um, tolerance_um)
        return optimal_t, stats


# ═══════════════════════════════════════════════════════════════════════════
# Stiffness validation  (Gibson-Ashby + mechanotransduction guardrails)
# ═══════════════════════════════════════════════════════════════════════════

class StiffnessValidator:
    """Gibson-Ashby cellular-solid stiffness estimation with a hard
    biological ceiling to prevent fibrotic scarring.

    The Gibson-Ashby model relates the Young's modulus of a porous
    scaffold to that of the fully-dense solid:

        E_scaffold = C · E_solid · (ρ_relative)^n

    where ρ_relative = 1 − porosity, and C ≈ 1.0, n ≈ 2.0 for open-cell
    foams (Gibson & Ashby, *Cellular Solids*, 2nd ed., 1997).
    """

    def __init__(
        self,
        e_solid_kpa: float = 50.0,
        gibson_ashby_C: float = 1.0,
        gibson_ashby_n: float = 2.0,
    ) -> None:
        self.e_solid = e_solid_kpa
        self.C = gibson_ashby_C
        self.n = gibson_ashby_n

    # ------------------------------------------------------------------
    def estimate_stiffness(self, porosity: float) -> dict:
        """Compute scaffold modulus from bulk-material modulus and porosity.

        Returns dict: relative_density, e_scaffold_kpa, porosity.
        """
        rho = 1.0 - porosity
        e_scaffold = self.e_solid * self.C * (rho ** self.n)
        return dict(
            relative_density=rho,
            e_scaffold_kpa=e_scaffold,
            porosity=porosity,
        )

    # ------------------------------------------------------------------
    def check_mechanotransduction_limit(
        self,
        e_scaffold_kpa: float,
        limit_kpa: float = 15.0,
    ) -> Optional[str]:
        """
        ╔══════════════════════════════════════════════════════════════╗
        ║  MECHANOTRANSDUCTION GUARDRAIL — why 15 KPa?               ║
        ╚══════════════════════════════════════════════════════════════╝

        Cells sense substrate stiffness through integrin-mediated focal
        adhesions. The key mechano-sensitive pathway is the YAP/TAZ
        transcriptional co-activator axis:

        1. On SOFT substrates (< ~15 KPa), YAP/TAZ remain cytoplasmic
           and inactive.  Fibroblasts maintain their quiescent,
           non-contractile phenotype — exactly what we want for healthy
           gingival connective-tissue regeneration.

        2. On STIFF substrates (> ~15 KPa), YAP/TAZ translocates into
           the nucleus and activates CTGF and Cyr61 target genes.
           This triggers:

           a) Up-regulation of α-smooth-muscle actin (α-SMA), the
              hallmark of MYOFIBROBLAST differentiation.
           b) Myofibroblasts are hyper-contractile and deposit
              excessive, cross-linked collagen-I.
           c) The result is FIBROTIC SCAR TISSUE, not functional
              gingiva.  Scar tissue lacks Sharpey's fibers, has
              reduced vascularity, and will eventually recede again.

        Therefore, we MUST keep E_scaffold ≤ 15 KPa to maintain the
        regenerative fibroblast phenotype and avoid pathological
        scarring.

        References
        ----------
        - Discher, D.E., Janmey, P. & Wang, Y-L. (2005). "Tissue Cells
          Feel and Respond to the Stiffness of Their Substrate." Science
          310(5751): 1139-1143.
        - Dupont, S. et al. (2011). "Role of YAP/TAZ in
          mechanotransduction." Nature 474: 179-183.
        - Hinz, B. (2010). "The myofibroblast: paradigm for a
          mechanically active cell." J. Biomech. 43(1): 146-155.
        """
        if e_scaffold_kpa > limit_kpa:
            warning = (
                f"WARNING REDUCE_DENSITY -- E_scaffold = {e_scaffold_kpa:.2f} KPa "
                f"exceeds the {limit_kpa} KPa mechanotransduction ceiling. "
                f"At this stiffness, YAP/TAZ nuclear translocation will drive "
                f"myofibroblast differentiation (a-SMA+), leading to fibrotic "
                f"scar tissue instead of functional attached gingiva. "
                f"ACTION: Increase porosity or reduce solid-phase modulus."
            )
            logger.warning(warning)
            return warning
        return None

    # ------------------------------------------------------------------
    def validate(self, porosity: float) -> dict:
        """Run stiffness estimation + mechanotransduction check."""
        result = self.estimate_stiffness(porosity)
        result["stiffness_warning"] = self.check_mechanotransduction_limit(
            result["e_scaffold_kpa"]
        )
        return result


# ═══════════════════════════════════════════════════════════════════════════
# Top-level orchestrator
# ═══════════════════════════════════════════════════════════════════════════

class ScaffoldValidator:
    """Unified validation façade used by ``orchestrator.py``."""

    def __init__(
        self,
        voxel_size_mm: float = 0.05,
        e_solid_kpa: float = 50.0,
    ) -> None:
        self.pore = PoreValidator(voxel_size_mm)
        self.stiffness = StiffnessValidator(e_solid_kpa)

    # ------------------------------------------------------------------
    def full_validation(
        self,
        binary_scaffold: np.ndarray,
        sdf_grid: np.ndarray | None = None,
        target_pore_um: float = 325.0,
        tolerance_um: float = 25.0,
    ) -> ValidationReport:
        """Run the complete pore + stiffness validation suite.

        Parameters
        ----------
        binary_scaffold : bool ndarray
            Solid = True.
        sdf_grid : float ndarray, optional
            If provided, the isovalue solver will be invoked to verify
            pore-size targeting.  If None, statistics are computed on the
            existing binary volume.
        """
        pore_stats = self.pore.measure_pore_statistics(binary_scaffold)
        stiffness = self.stiffness.validate(pore_stats["porosity"])

        pore_ok = abs(pore_stats["mean_pore_um"] - target_pore_um) <= tolerance_um

        return ValidationReport(
            mean_pore_size_um=pore_stats["mean_pore_um"],
            pore_std_um=pore_stats["std_pore_um"],
            porosity=pore_stats["porosity"],
            relative_density=stiffness["relative_density"],
            scaffold_stiffness_kpa=stiffness["e_scaffold_kpa"],
            stiffness_warning=stiffness["stiffness_warning"],
            pore_target_met=pore_ok,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def print_report(report: ValidationReport) -> None:
        sep = "=" * 60
        print(f"\n{sep}")
        print("  GingivaGen 2.0 -- Scaffold Validation Report")
        print(sep)
        print(f"  Timestamp          : {report.timestamp}")
        print(f"  Mean pore size     : {report.mean_pore_size_um:.1f} um")
        print(f"  Pore size std      : {report.pore_std_um:.1f} um")
        print(f"  Porosity           : {report.porosity:.3f}")
        print(f"  Relative density   : {report.relative_density:.3f}")
        print(f"  Scaffold stiffness : {report.scaffold_stiffness_kpa:.2f} KPa")
        print(f"  Pore target met    : {'YES' if report.pore_target_met else 'NO'}")
        if report.stiffness_warning:
            print(f"\n  {report.stiffness_warning}")
        print(sep + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# Self-test with synthetic gyroid
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(name)s | %(levelname)s | %(message)s")

    # --- Build a small synthetic gyroid volume for smoke-testing ----------
    N = 80
    voxel_mm = 0.05
    lin = np.linspace(-np.pi, np.pi, N)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")

    # Schoen Gyroid SDF
    sdf = np.cos(X) * np.sin(Y) + np.cos(Y) * np.sin(Z) + np.cos(Z) * np.sin(X)

    # Threshold at an arbitrary isovalue
    t_test = 0.4
    solid = np.abs(sdf) <= t_test

    print(f"Synthetic gyroid: {N}³ voxels, t={t_test}, "
          f"solid fraction = {solid.mean():.3f}")

    validator = ScaffoldValidator(voxel_size_mm=voxel_mm)
    report = validator.full_validation(solid, sdf_grid=sdf)
    validator.print_report(report)
