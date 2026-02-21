"""
GingivaGen 2.0 — Command-Line Interface
=========================================
Entry point for running the scaffold pipeline, batch processing,
dataset management, and visualization.

Usage::

    python cli.py run patient_scan.obj --output output/
    python cli.py batch --dataset D:/Teeth3DS+ --jaw lower --max 10
    python cli.py extract --dataset D:/Teeth3DS+
    python cli.py validate output/material_grid.npy
    python cli.py viz output/ --phase all
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import yaml


def _load_config(config_path: str | None) -> dict:
    """Load YAML config, falling back to defaults."""
    default = Path(__file__).parent / "config.yaml"
    path = Path(config_path) if config_path else default
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


# ═══════════════════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════════════════

def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline on a single scan."""
    from orchestrator import GingivaGenV2
    from mesh_exporter import export_all_materials, export_combined_obj

    cfg = _load_config(args.config)
    voxel_size = args.voxel_size or cfg.get("voxel_size_mm", 0.05)
    output_dir = args.output or cfg.get("output_dir", "output")

    pipeline = GingivaGenV2(output_dir=output_dir, voxel_size=voxel_size,
                            config=cfg)
    results = pipeline.run(args.input)

    # Export scaffold meshes
    mat = results.get("material_grid")
    vol = results.get("volume")
    if mat is not None and vol is not None:
        mesh_dir = Path(output_dir) / "meshes"
        fmt = cfg.get("export_format", "stl")
        export_all_materials(mat, voxel_size, vol["grid_origin"],
                             mesh_dir, fmt=fmt)
        if cfg.get("export_combined_obj", True):
            export_combined_obj(mat, voxel_size, vol["grid_origin"],
                                mesh_dir / "scaffold_combined.obj")

        # Save material grid for later validation / viz
        np.save(Path(output_dir) / "material_grid.npy", mat)

    # Auto-screenshots
    if cfg.get("visualization", {}).get("auto_screenshots", False):
        from visualization import generate_phase_screenshots
        ss_dir = cfg["visualization"].get("screenshot_dir",
                                           str(Path(output_dir) / "screenshots"))
        generate_phase_screenshots(results, ss_dir)

    print(f"\n[OK] Pipeline complete. Output -> {output_dir}")


def cmd_batch(args: argparse.Namespace) -> None:
    """Batch-process multiple scans from Teeth3DS+."""
    from orchestrator import GingivaGenV2
    from data_loader import Teeth3DSLoader

    cfg = _load_config(args.config)
    ds_root = args.dataset or cfg.get("dataset", {}).get("root", "D:/Teeth3DS+")
    voxel_size = args.voxel_size or cfg.get("voxel_size_mm", 0.05)

    loader = Teeth3DSLoader(dataset_root=ds_root)
    loader.extract_all()
    loader.build_catalogue()

    pipeline = GingivaGenV2(output_dir=args.output or "output/batch",
                            voxel_size=voxel_size, config=cfg)
    results = loader.batch_process(
        pipeline,
        jaw=args.jaw,
        max_scans=args.max,
        output_root=args.output or "output/batch",
    )

    succeeded = sum(1 for r in results if "error" not in r)
    print(f"\n[OK] Batch complete: {succeeded}/{len(results)} succeeded.")


def cmd_extract(args: argparse.Namespace) -> None:
    """Extract Teeth3DS+ dataset archives."""
    from data_loader import Teeth3DSLoader

    cfg = _load_config(args.config)
    ds_root = args.dataset or cfg.get("dataset", {}).get("root", "D:/Teeth3DS+")

    loader = Teeth3DSLoader(dataset_root=ds_root)

    if args.sample_only:
        loader.extract_sample()
        print("[OK] Sample extracted.")
    else:
        loader.extract_all(force=args.force)
        print("[OK] All archives extracted.")

    catalogue = loader.build_catalogue()
    print(f"  {len(catalogue)} scans catalogued.")


def cmd_validate(args: argparse.Namespace) -> None:
    """Run validation on a saved material grid."""
    from validation_engine import ScaffoldValidator

    cfg = _load_config(args.config)
    voxel_size = args.voxel_size or cfg.get("voxel_size_mm", 0.05)

    mat = np.load(args.input)
    core_mask = (mat == 2)  # MAT_GELMA_CORE

    if not core_mask.any():
        print("No GelMA core voxels found in the material grid.")
        sys.exit(1)

    validator = ScaffoldValidator(voxel_size_mm=voxel_size)
    report = validator.full_validation(core_mask)
    validator.print_report(report)


def cmd_viz(args: argparse.Namespace) -> None:
    """Launch interactive visualization."""
    from visualization import (view_material_grid, view_exported_meshes,
                               view_cross_section)

    cfg = _load_config(args.config)
    output_dir = Path(args.input)

    if args.meshes:
        mesh_dir = output_dir / "meshes"
        if mesh_dir.exists():
            view_exported_meshes(mesh_dir)
        else:
            print(f"No meshes directory found at {mesh_dir}")
        return

    grid_path = output_dir / "material_grid.npy"
    if not grid_path.exists():
        print(f"No material_grid.npy found at {grid_path}")
        sys.exit(1)

    mat = np.load(grid_path)
    voxel_size = args.voxel_size or cfg.get("voxel_size_mm", 0.05)
    origin = np.zeros(3)

    if args.cross_section:
        view_cross_section(mat, origin, voxel_size,
                           axis=args.cross_section, position=args.position)
    else:
        view_material_grid(mat, origin, voxel_size)


# ═══════════════════════════════════════════════════════════════════════════
# Argument parser
# ═══════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gingivagen",
        description="GingivaGen 2.0 — Multi-Material Gingival Scaffold Pipeline",
    )
    p.add_argument("--config", "-c", help="Path to config.yaml")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--voxel-size", type=float, default=None,
                   help="Override voxel size (mm)")

    sub = p.add_subparsers(dest="command", required=True)

    # run
    r = sub.add_parser("run", help="Process a single .obj scan")
    r.add_argument("input", help="Path to .obj or .stl file")
    r.add_argument("--output", "-o", default=None)

    # batch
    b = sub.add_parser("batch", help="Batch-process Teeth3DS+ dataset")
    b.add_argument("--dataset", "-d", default=None)
    b.add_argument("--output", "-o", default="output/batch")
    b.add_argument("--jaw", choices=["upper", "lower"], default=None)
    b.add_argument("--max", type=int, default=None)

    # extract
    e = sub.add_parser("extract", help="Extract Teeth3DS+ archives")
    e.add_argument("--dataset", "-d", default=None)
    e.add_argument("--sample-only", action="store_true")
    e.add_argument("--force", action="store_true")

    # validate
    v = sub.add_parser("validate", help="Validate a saved material grid")
    v.add_argument("input", help="Path to material_grid.npy")

    # viz
    z = sub.add_parser("viz", help="Visualize pipeline output")
    z.add_argument("input", help="Output directory")
    z.add_argument("--meshes", action="store_true",
                   help="View exported STL meshes")
    z.add_argument("--cross-section", choices=["x", "y", "z"], default=None)
    z.add_argument("--position", type=float, default=None,
                   help="Cross-section position (mm)")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(name)s | %(levelname)s | %(message)s",
    )

    commands = {
        "run": cmd_run,
        "batch": cmd_batch,
        "extract": cmd_extract,
        "validate": cmd_validate,
        "viz": cmd_viz,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
