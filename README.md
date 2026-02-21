# GingivaGen 2.0 — Autonomous Multi-Ink Gingival Scaffold Pipeline

<p align="center">
  <strong>From intraoral 3D scan → multi-material bioprinter G-code, fully autonomous.</strong>
</p>

GingivaGen 2.0 is an autonomous computational pipeline that converts raw intraoral `.obj`/`.stl` surface scans into multi-material, implantable hybrid gingival scaffolds with bioprinter-ready G-code. Given a 3D scan of a gingival recession defect, the pipeline segments the anatomy, reconstructs the ideal tissue volume via RBF interpolation, and generates a layered scaffold comprising a rigid PCL+BAG armor shell, a porous anisotropic GelMA gyroid core with embedded chitosan nanoparticles, and sacrificial Pluronic F-127 vascular channels — all exported as multi-head G-code for extrusion-based bioprinting.

An **interactive portfolio website** built with React Three Fiber is included for 3D visualization of every pipeline stage.

> **🔬 Live Demo:** [gingivagen-portfolio/](gingivagen-portfolio/) — run `cd gingivagen-portfolio && npm run dev` to explore the 3D scaffold viewer locally.

---

## The Clinical Problem

**Gingival recession** (Miller Class I–III) exposes the tooth root surface, causing sensitivity, aesthetic concerns, and progressive attachment loss. Current treatments — connective tissue grafts, acellular dermal matrices — require a donor site, have limited availability, and produce inconsistent outcomes.

GingivaGen 2.0 replaces the donor tissue with a **computationally designed, multi-material bioprinted scaffold** that:
- Matches the patient's defect geometry exactly (scan-to-scaffold)
- Provides mechanical protection during healing (PCL+BAG armor)
- Guides oriented tissue regeneration through anisotropic pore architecture (PDL-aligned gyroid)
- Establishes vascular supply through sacrificial channel perfusion
- Modulates the immune response toward regeneration via chitosan nanoparticles

---

## Triple-Threat Biological Strategy

| Layer | Material | Biological Function |
|---|---|---|
| **Mechanical Defense** | 0.5 mm PCL + 10 wt% Bioactive Glass (45S5) | Prevents suture tearing and mastication collapse. BAG releases Si⁴⁺/Ca²⁺ ions → bactericidal pH elevation + osteogenic signaling. |
| **Bio-Grafting Core** | Anisotropic Schoen Gyroid GelMA (325 µm pores) + **chitosan nanoparticles** | PDL-aligned channels guide fibroblast migration and Sharpey's fiber ingrowth. Stiffness held below 15 KPa to prevent YAP/TAZ-driven myofibroblast differentiation. |
| **Vascular/Immune Support** | Sacrificial Pluronic F-127 channels (400 µm) | Dissolved post-fabrication at 4 °C to leave open lumens for capillary sprouting and pre-vascularization. |

### Chitosan Nanoparticle Immunomodulation

Chitosan nanoparticles are embedded throughout the GelMA hydrogel matrix to provide a sustained immunomodulatory effect:

- **Antimicrobial activity** — Positively charged chitosan disrupts bacterial membranes (broad-spectrum activity against oral pathogens including *P. gingivalis* and *A. actinomycetemcomitans*)
- **M2 macrophage polarization** — Chitosan promotes the shift from pro-inflammatory M1 macrophages to pro-regenerative M2 phenotype, reducing chronic inflammation at the graft site
- **Soft-tissue integration** — Chitosan degradation products (glucosamine, N-acetylglucosamine) serve as building blocks for glycosaminoglycan synthesis, accelerating extracellular matrix remodeling and epithelial attachment

This creates a self-regulating immunological microenvironment: infection is suppressed while the tissue regeneration program is actively promoted.

---

## Multi-Ink Bioprinting Architecture

The scaffold is fabricated using a **3-head extrusion bioprinter** with sequential material deposition per layer. The PCL+BAG armor prints first as a retaining wall to contain the soft GelMA hydrogel.

### Print Head Configuration

| Head | Material | Pressure | Speed | Nozzle | Temperature |
|---|---|---|---|---|---|
| **T0** | PCL + 10% BAG (45S5) | 300 kPa | 3 mm/s | 0.41 mm | 65 °C (melt) |
| **T1** | GelMA + chitosan nanoparticles | 45 kPa | 5 mm/s | 0.25 mm | RT (photocurable) |
| **T2** | Pluronic F-127 (sacrificial) | 60 kPa | 8 mm/s | 0.41 mm | RT |

### Print Sequence (per layer)

```
1. T0: PCL+BAG armor shell  → rigid retaining wall
2. T1: GelMA gyroid core    → fills interior with porous hydrogel
3. T2: Pluronic channels    → sacrificial vascular template
```

**Bed temperature:** 37 °C (maintained for cell viability in GelMA bio-ink)

### Post-Processing

1. **UV crosslinking** — GelMA photopolymerization (405 nm, 30 s per layer or bulk post-print)
2. **Channel dissolution** — Cool to 4 °C for 30 min → Pluronic F-127 liquefies and is flushed out, leaving open 400 µm vascular channels
3. **Cell seeding** — Perfuse gingival fibroblasts + endothelial cells through the vascular network

### G-code Generation

G-code is generated autonomously from the voxel grid using [FullControl](https://github.com/FullControlXYZ/fullcontrol). Each layer is sliced, and voxels are grouped by material. Tool changes insert the appropriate pressure, speed, and nozzle diameter commands:

```gcode
; === GingivaGen 2.0 Multi-Material Scaffold ===
G28          ; home
G90          ; absolute positioning
M83          ; relative extrusion
; --- Layer 0  z=0.050 mm ---
; Switch to PCL+BAG (T0)
T0
M42 S300     ; pressure 300 kPa
; ... serpentine raster of armor voxels ...
; Switch to GelMA (T1)
T1
M42 S45      ; pressure 45 kPa
; ... gyroid core fill ...
```

---

## Pipeline Phases

The pipeline runs 6 autonomous phases from scan input to G-code output:

### Phase 1 — Neural Segmentation
Segment the intraoral scan into teeth and gingiva using [3DTeethSAM](https://github.com/SJTUzhou/3DTeethSAM) (multi-view neural inference) or a geometric height-percentile fallback. Isolates the recession defect region by identifying the cemento-enamel junction and exposed root surface.

### Phase 2 — Ideal Volume Reconstruction
Interpolate the healthy gingival contour across the recession gap using **SciPy RBFInterpolator** (thin-plate-spline kernel). The scaffold volume is the boolean difference between the ideal surface and the exposed root.

### Phase 3 — Armor Shell Generation
Generate a dense 0.5 mm PCL + BAG outer shell via binary erosion (`scipy.ndimage`) or meshlib voxel offset. This rigid wall contains the soft hydrogel during printing and provides suture retention under masticatory load.

### Phase 4 — Anisotropic Gyroid Core
Fill the interior with a **Schoen Gyroid** TPMS lattice (cell size = 2.0 mm) whose pore direction is stretched along the root-normal axis using the PDL anisotropy transform:

```
z' = z × (1 + (k−1) · exp(−d/λ))
```

where `k = 3.0` (stretch factor at root surface) and `λ = 2.0 mm` (exponential decay length). This produces elongated pores near the root that guide Sharpey's fiber alignment, transitioning to isotropic pores deeper in the scaffold. The gyroid isovalue is solved via **Brentq root-finding** to hit the 325 µm pore target, verified by **PoreSpy EDT** local thickness measurement.

A 100 µm high-density GelMA bio-glue sub-layer bonds the scaffold to the denuded root surface.

### Phase 5 — Vascular Channels
Boolean-OR a sparse grid of 400 µm Pluronic F-127 cylinders (2.0 mm spacing) into the core region. Post-fabrication: cool to 4 °C → Pluronic liquefies → flush to create open vascular channels for capillary sprouting.

### Phase 6 — Multi-Material G-code Export
Slice the voxel grid layer-by-layer into 3-head bioprinter G-code using [FullControl](https://github.com/FullControlXYZ/fullcontrol). Print order per layer: PCL+BAG armor first (retaining wall), then GelMA core, then Pluronic channels.

---

## Validation

The validation engine (`validation_engine.py`) enforces biologically-motivated thresholds:

| Metric | Target | Method | Rationale |
|---|---|---|---|
| **Pore size** | 325 ± 25 µm | PoreSpy EDT local thickness | Optimal for fibroblast migration (Karageorgiou & Kaplan 2005) |
| **Scaffold stiffness** | < 15 KPa | Gibson-Ashby cellular-solid model | Below the YAP/TAZ nuclear translocation threshold — prevents myofibroblast differentiation and fibrotic scarring |
| **Armor thickness** | ≥ 0.5 mm | Binary erosion depth | Required for suture retention under masticatory load (Schmitt 2020) |

---

## Installation

### Pipeline (Python)

```bash
pip install -r requirements.txt
```

#### Optional: LisbonTPMS

For higher-fidelity TPMS lattice generation:

```bash
git clone https://github.com/SoftwareImpacts/SIMPAC-2025-26.git LisbonTPMStool
```

The pipeline falls back to an inline Schoen Gyroid evaluation if LisbonTPMS is not installed.

### Portfolio Website

```bash
cd gingivagen-portfolio
npm install
npm run dev
```

Build for production:

```bash
npm run build    # outputs to gingivagen-portfolio/dist/
npm run preview  # preview the production build
```

---

## Usage

### Single scan

```bash
python cli.py run patient_scan.obj -o output/
```

### Batch processing (Teeth3DS+ dataset)

```bash
python cli.py batch --dataset D:/Teeth3DS+ --max 10
```

### Validate a saved scaffold

```bash
python cli.py validate output/material_grid.npy
```

### Visualize output

```bash
python cli.py viz output/ --meshes
python cli.py viz output/ --cross-section z --position 2.5
```

### Self-test (no data needed)

```bash
python orchestrator.py
```

Generates a synthetic recession mesh and runs the full 6-phase pipeline.

---

## Configuration

All parameters are controlled via [`config.yaml`](config.yaml):

| Section | Key Parameters |
|---|---|
| **Resolution** | `voxel_size_mm: 0.05` (50 µm isotropic) |
| **Segmentation** | `model: geometric` or `3dteethsam` |
| **Armor** | `thickness_mm: 0.5`, `bag_wt_percent: 10` |
| **Core** | `target_pore_um: 325`, `cell_size_mm: 2.0`, `pdl_anisotropy_k: 3.0` |
| **Vascular** | `channel_diameter_mm: 0.4`, `channel_spacing_mm: 2.0` |
| **G-code** | 3-head config (pressure, speed, nozzle per tool) |

---

## Project Structure

```
├── orchestrator.py              # Master pipeline — 6-phase scaffold generation
├── validation_engine.py         # PoreSpy EDT pore-size + Gibson-Ashby stiffness validation
├── mesh_exporter.py             # Marching-cubes mesh export (STL/OBJ per material)
├── cli.py                       # Command-line interface
├── data_loader.py               # Teeth3DS+ dataset extraction and batch catalogue
├── visualization.py             # PyVista/Matplotlib visualization utilities
├── config.yaml                  # Default configuration
├── requirements.txt             # Python dependencies
├── kaggle_notebook.ipynb        # Kaggle notebook for cloud execution
├── tests/                       # Pytest test suite
│
└── gingivagen-portfolio/        # Interactive 3D portfolio website
    ├── src/
    │   ├── components/
    │   │   ├── ScanViewer.tsx    # 3D jaw segmentation viewer (teeth/gingiva/defect/scaffold)
    │   │   ├── ScaffoldViewer.tsx # Multi-material scaffold viewer (armor/core/channels)
    │   │   ├── GyroidViewer.tsx  # Gradient anisotropy gyroid visualization
    │   │   ├── DataSection.tsx   # Cross-sections, material charts, G-code, bio cards
    │   │   └── ...
    │   └── App.tsx
    ├── public/
    │   ├── models/               # Pre-generated 3D meshes (derived, safe to share)
    │   └── images/               # Pipeline output visualizations
    ├── scripts/
    │   ├── prepare_jaw_meshes.py     # Jaw segmentation + recession simulation + RBF
    │   └── generate_preview_meshes.py # Dome scaffold mesh generation
    └── package.json
```

---

## Dataset

This project uses the [**Teeth3DS+**](https://github.com/abenhamadou/3DTeethSeg22_challenge) dataset from the MICCAI 2022 3DTeethLand challenge for intraoral scan segmentation labels.

> **⚠️ Patient data is NOT included in this repository.** The Teeth3DS+ dataset contains real intraoral scans and is subject to its own license. Download it separately from the challenge organizers. The pre-processed meshes in `gingivagen-portfolio/public/models/` are derived/anonymized geometry safe for sharing.

---

## Open Source Credits

This project builds on the work of several open-source projects and datasets:

| Project | Use in GingivaGen | License |
|---|---|---|
| [**Teeth3DS+**](https://github.com/abenhamadou/3DTeethSeg22_challenge) | Intraoral scan data with per-tooth segmentation labels | Dataset license |
| [**LisbonTPMS**](https://github.com/SoftwareImpacts/SIMPAC-2025-26) | Schoen Gyroid TPMS lattice computation | [SIMPAC](https://github.com/SoftwareImpacts/SIMPAC-2025-26) |
| [**FullControl**](https://github.com/FullControlXYZ/fullcontrol) | Multi-material G-code generation | MIT |
| [**SciPy**](https://scipy.org/) | RBFInterpolator (thin-plate-spline), binary erosion, Brentq solver | BSD |
| [**scikit-image**](https://scikit-image.org/) | Marching cubes mesh extraction | BSD |
| [**PoreSpy**](https://porespy.org/) | EDT-based pore-size analysis | MIT |
| [**trimesh**](https://trimesh.org/) | Mesh I/O and processing | MIT |
| [**NumPy**](https://numpy.org/) | Core numerical computing | BSD |
| [**React Three Fiber**](https://github.com/pmndrs/react-three-fiber) | 3D rendering for portfolio site | MIT |
| [**Three.js**](https://threejs.org/) | WebGL 3D engine | MIT |
| [**Tailwind CSS v4**](https://tailwindcss.com/) | Portfolio styling | MIT |
| [**Framer Motion**](https://www.framer.com/motion/) | Portfolio animations | MIT |
| [**Vite**](https://vite.dev/) | Portfolio build tooling | MIT |

---

## License

MIT — see repository for details.
