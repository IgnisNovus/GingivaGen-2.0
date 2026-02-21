"""
GingivaGen 2.0 — Teeth3DS+ Dataset Loader
===========================================
Extract, catalogue, and batch-process the MICCAI 2022 Teeth3DS+ dataset
(1,800 intraoral scans with FDI vertex labels).

Expected archive layout (D:/Teeth3DS+/):
    data_part_1.zip … data_part_7.zip   — mesh .obj files
    3DTeethLand_landmarks_train.zip     — training landmark JSONs
    3DTeethLand_landmarks_test.zip      — test landmark JSONs
    teeth3ds_sample.zip                 — small sample subset
"""

from __future__ import annotations

import json
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger("GingivaGen.DataLoader")

DEFAULT_DATASET_ROOT = Path("D:/Teeth3DS+")
DEFAULT_EXTRACT_DIR = Path("D:/Teeth3DS+/extracted")


@dataclass
class ScanRecord:
    """Metadata for a single intraoral scan."""
    case_id: str
    jaw: str                          # "upper" or "lower"
    obj_path: Path                    # path to .obj file
    label_path: Optional[Path] = None  # per-vertex label .json / .txt
    landmark_path: Optional[Path] = None
    fdi_labels: dict = field(default_factory=dict)


class Teeth3DSLoader:
    """Discover, extract, and iterate over Teeth3DS+ scans."""

    DATA_ZIPS = [f"data_part_{i}.zip" for i in range(1, 8)]
    LANDMARK_ZIPS = [
        "3DTeethLand_landmarks_train.zip",
        "3DTeethLand_landmarks_test.zip",
    ]
    SAMPLE_ZIP = "teeth3ds_sample.zip"

    def __init__(
        self,
        dataset_root: str | Path = DEFAULT_DATASET_ROOT,
        extract_dir: str | Path | None = None,
    ) -> None:
        self.root = Path(dataset_root)
        self.extract_dir = Path(extract_dir) if extract_dir else self.root / "extracted"
        self._catalogue: list[ScanRecord] = []

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------
    def extract_all(self, force: bool = False) -> Path:
        """Unzip all data archives into ``self.extract_dir``.

        Skips already-extracted archives unless ``force=True``.
        """
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        all_zips = self.DATA_ZIPS + self.LANDMARK_ZIPS + [self.SAMPLE_ZIP]
        for zname in all_zips:
            zpath = self.root / zname
            if not zpath.exists():
                logger.debug("Archive not found, skipping: %s", zpath)
                continue

            marker = self.extract_dir / f".{zname}.extracted"
            if marker.exists() and not force:
                logger.debug("Already extracted: %s", zname)
                continue

            logger.info("Extracting %s -> %s", zpath, self.extract_dir)
            with zipfile.ZipFile(zpath, "r") as zf:
                zf.extractall(self.extract_dir)
            marker.touch()

        return self.extract_dir

    def extract_sample(self) -> Path:
        """Extract only the small sample archive for quick testing."""
        self.extract_dir.mkdir(parents=True, exist_ok=True)
        zpath = self.root / self.SAMPLE_ZIP
        if not zpath.exists():
            raise FileNotFoundError(f"Sample archive not found: {zpath}")

        logger.info("Extracting sample -> %s", self.extract_dir)
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(self.extract_dir)
        return self.extract_dir

    # ------------------------------------------------------------------
    # Cataloguing
    # ------------------------------------------------------------------
    def build_catalogue(self) -> list[ScanRecord]:
        """Walk the extracted directory tree and build a list of ScanRecords.

        Expected structure per case:
            <jaw>/<CASE_ID>/<CASE_ID>_<jaw>.obj
            <jaw>/<CASE_ID>/<CASE_ID>_<jaw>.json   (optional labels)
        """
        self._catalogue.clear()

        if not self.extract_dir.exists():
            logger.warning("Extract dir does not exist: %s — run extract_all() first.",
                           self.extract_dir)
            return self._catalogue

        # Recursively find all .obj files
        obj_files = sorted(self.extract_dir.rglob("*.obj"))
        logger.info("Found %d .obj files in %s", len(obj_files), self.extract_dir)

        for obj_path in obj_files:
            stem = obj_path.stem  # e.g. "00OMSZGW_lower"
            parts = stem.rsplit("_", 1)
            if len(parts) == 2:
                case_id, jaw = parts
            else:
                case_id, jaw = stem, "unknown"

            record = ScanRecord(
                case_id=case_id,
                jaw=jaw.lower(),
                obj_path=obj_path,
            )

            # Look for label file (JSON or TXT) alongside the OBJ
            for ext in (".json", ".txt"):
                label_candidate = obj_path.with_suffix(ext)
                if label_candidate.exists():
                    record.label_path = label_candidate
                    break

            # Look for landmark file
            lm_candidate = obj_path.parent / f"{stem}_landmarks.json"
            if lm_candidate.exists():
                record.landmark_path = lm_candidate

            self._catalogue.append(record)

        logger.info("Catalogued %d scans (%d upper, %d lower)",
                     len(self._catalogue),
                     sum(1 for r in self._catalogue if r.jaw == "upper"),
                     sum(1 for r in self._catalogue if r.jaw == "lower"))
        return self._catalogue

    @property
    def catalogue(self) -> list[ScanRecord]:
        if not self._catalogue:
            self.build_catalogue()
        return self._catalogue

    # ------------------------------------------------------------------
    # Iteration & filtering
    # ------------------------------------------------------------------
    def iter_scans(
        self,
        jaw: Optional[str] = None,
        max_scans: Optional[int] = None,
    ) -> Iterator[ScanRecord]:
        """Yield ScanRecords, optionally filtered by jaw type."""
        count = 0
        for record in self.catalogue:
            if jaw and record.jaw != jaw.lower():
                continue
            yield record
            count += 1
            if max_scans and count >= max_scans:
                return

    def get_scan(self, case_id: str, jaw: str = "lower") -> Optional[ScanRecord]:
        """Retrieve a specific scan by case ID and jaw type."""
        for record in self.catalogue:
            if record.case_id == case_id and record.jaw == jaw.lower():
                return record
        return None

    # ------------------------------------------------------------------
    # Label loading
    # ------------------------------------------------------------------
    @staticmethod
    def load_labels(record: ScanRecord) -> Optional[dict]:
        """Load per-vertex FDI labels from a scan's label file.

        Supports both JSON format (Teeth3DS+ ground truth) and
        plain-text format (3DTeethSAM inference output).
        """
        if record.label_path is None:
            return None

        path = record.label_path
        if path.suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Teeth3DS+ JSON: {"labels": [fdi_int, ...]} or {"instances": [...]}
            return data

        if path.suffix == ".txt":
            # One integer per line, matching vertex order
            labels = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        labels.append(int(line))
            return {"labels": labels}

        return None

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------
    def batch_process(
        self,
        pipeline,
        jaw: Optional[str] = None,
        max_scans: Optional[int] = None,
        output_root: str | Path = "output/batch",
    ) -> list[dict]:
        """Run a GingivaGenV2 pipeline on multiple scans.

        Parameters
        ----------
        pipeline : GingivaGenV2
            An initialised pipeline instance.
        jaw : str, optional
            Filter to "upper" or "lower" jaw only.
        max_scans : int, optional
            Cap on number of scans to process.
        output_root : path
            Root directory; each scan gets a sub-folder.

        Returns
        -------
        List of result dicts from ``pipeline.run()``.
        """
        output_root = Path(output_root)
        results = []

        for record in self.iter_scans(jaw=jaw, max_scans=max_scans):
            scan_dir = output_root / f"{record.case_id}_{record.jaw}"
            scan_dir.mkdir(parents=True, exist_ok=True)

            logger.info("═ Batch: %s (%s) ═", record.case_id, record.jaw)
            pipeline.output_dir = scan_dir

            try:
                result = pipeline.run(str(record.obj_path))
                result["case_id"] = record.case_id
                result["jaw"] = record.jaw
                results.append(result)
            except Exception as exc:
                logger.error("Failed on %s: %s", record.case_id, exc)
                results.append({"case_id": record.case_id, "error": str(exc)})

        logger.info("Batch complete: %d/%d succeeded",
                     sum(1 for r in results if "error" not in r), len(results))
        return results


# ─────────────────────────────────────────────────────────────────────────
# FDI label utilities
# ─────────────────────────────────────────────────────────────────────────

UPPER_TEETH_FDI = [18, 17, 16, 15, 14, 13, 12, 11,
                   21, 22, 23, 24, 25, 26, 27, 28]
LOWER_TEETH_FDI = [38, 37, 36, 35, 34, 33, 32, 31,
                   41, 42, 43, 44, 45, 46, 47, 48]

FDI_TO_SLOT: dict[int, int] = {}
SLOT_TO_FDI_UPPER: dict[int, int] = {}
SLOT_TO_FDI_LOWER: dict[int, int] = {}
for _i, (_u, _l) in enumerate(zip(UPPER_TEETH_FDI, LOWER_TEETH_FDI)):
    FDI_TO_SLOT[_u] = _i + 1
    FDI_TO_SLOT[_l] = _i + 1
    SLOT_TO_FDI_UPPER[_i + 1] = _u
    SLOT_TO_FDI_LOWER[_i + 1] = _l


def slot_to_fdi(slot: int, jaw: str) -> int:
    """Convert 3DTeethSAM position slot (1-16) back to FDI number."""
    table = SLOT_TO_FDI_UPPER if jaw.lower() == "upper" else SLOT_TO_FDI_LOWER
    return table.get(slot, 0)


# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(name)s | %(levelname)s | %(message)s")

    loader = Teeth3DSLoader()

    # Check what's available
    for zname in loader.DATA_ZIPS + loader.LANDMARK_ZIPS + [loader.SAMPLE_ZIP]:
        zpath = loader.root / zname
        status = "Y" if zpath.exists() else "N"
        size_mb = zpath.stat().st_size / 1e6 if zpath.exists() else 0
        print(f"  {status}  {zname:45s}  {size_mb:>8.1f} MB")

    # Try extracting the sample
    try:
        loader.extract_sample()
        catalogue = loader.build_catalogue()
        for rec in catalogue[:5]:
            print(f"  {rec.case_id} | {rec.jaw:5s} | {rec.obj_path.name}")
    except FileNotFoundError as e:
        print(f"  Sample not available: {e}")
