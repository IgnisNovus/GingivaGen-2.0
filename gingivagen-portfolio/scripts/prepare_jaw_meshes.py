"""
Pre-process the upper jaw OBJ with segmentation labels.

Pipeline
--------
1. Remove scanning block artifact (flat base below tooth roots)
2. Classify teeth vs gingiva from per-vertex labels
3. Simulate Miller Class I recession on FDI 13 (upper right canine)
4. Reconstruct ideal gingival surface via RBF thin-plate-spline
5. Export sub-meshes for the portfolio 3D viewer

Outputs (in public/models/jaw_parts/):
    teeth.obj           – all 14 teeth (white)
    gingiva.obj         – full gingiva, block removed (pink, normal view)
    gingiva_healthy.obj – gingiva with recession hole (pink, defect view)
    defect.obj          – recession zone faces (cyan highlight)
    ideal_volume.obj    – RBF-reconstructed scaffold surface (green)
"""

import json
import numpy as np
from pathlib import Path
from scipy.interpolate import RBFInterpolator
from scipy.spatial import Delaunay

# ── Paths (run from project root: c:/.../Ging 2.0) ─────────────────────
SRC_OBJ = Path("Teeth3DS+/extracted/teeth3ds_sample/01F4JV8X/01F4JV8X_upper.obj")
SRC_LABELS = Path("Teeth3DS+/extracted/teeth3ds_sample/01F4JV8X/01F4JV8X_upper.json")
OUT_DIR = Path("gingivagen-portfolio/public/models/jaw_parts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Vertex colors (RGB 0-1) ────────────────────────────────────────────
COLOR_TEETH = (0.96, 0.96, 0.94)
COLOR_GINGIVA = (0.83, 0.42, 0.54)
COLOR_DEFECT = (0.0, 0.83, 1.0)
COLOR_SCAFFOLD = (0.2, 0.9, 0.5)

# ── Recession parameters ───────────────────────────────────────────────
RECESSION_FDI = 13          # Upper right canine — most common site
RECESSION_RADIUS_MM = 8.0   # Sphere radius around tooth
ARCH_CENTER_XY = np.array([1.0, 0.0])  # Approximate palate centre
MAX_EDGE_MM = 3.0           # Remove gingiva faces with edges longer than this


# ════════════════════════════════════════════════════════════════════════
# I/O helpers
# ════════════════════════════════════════════════════════════════════════

def load_obj(path):
    """Parse OBJ → (verts Nx3, faces Mx3) with 0-based indices."""
    verts, faces = [], []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                parts = line.split()
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith("f "):
                idx = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
                if len(idx) >= 3:
                    faces.append(idx[:3])
    return np.array(verts, dtype=np.float64), np.array(faces, dtype=np.int64)


def write_submesh(filepath, verts, faces, mask, color):
    """Write OBJ containing only faces selected by *mask*, re-indexing."""
    sel = faces[mask]
    if len(sel) == 0:
        print(f"  Skipped {filepath.name}: 0 faces")
        return
    used = np.unique(sel.ravel())
    remap = np.full(len(verts), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    r, g, b = color
    with open(filepath, "w") as f:
        f.write(f"# GingivaGen 2.0 — {filepath.stem}\n")
        for vi in used:
            v = verts[vi]
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {r:.4f} {g:.4f} {b:.4f}\n")
        for tri in sel:
            f.write(f"f {remap[tri[0]]+1} {remap[tri[1]]+1} {remap[tri[2]]+1}\n")
    kb = filepath.stat().st_size / 1024
    print(f"  {filepath.name}: {len(used):,} verts, {len(sel):,} faces, {kb:.0f} KB")


def write_raw_obj(filepath, pts, tris, color):
    """Write OBJ from explicit vertices (Nx3) and triangle indices (Mx3)."""
    r, g, b = color
    with open(filepath, "w") as f:
        f.write(f"# GingivaGen 2.0 — {filepath.stem} (RBF reconstruction)\n")
        for v in pts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {r:.4f} {g:.4f} {b:.4f}\n")
        for t in tris:
            f.write(f"f {t[0]+1} {t[1]+1} {t[2]+1}\n")
    kb = filepath.stat().st_size / 1024
    print(f"  {filepath.name}: {len(pts):,} verts, {len(tris):,} faces, {kb:.0f} KB")


# ════════════════════════════════════════════════════════════════════════
# Main pipeline
# ════════════════════════════════════════════════════════════════════════

def main():
    # ── 1. Load ─────────────────────────────────────────────────────────
    print("Loading mesh + labels ...")
    verts, faces = load_obj(SRC_OBJ)
    with open(SRC_LABELS) as fh:
        labels = np.array(json.load(fh)["labels"], dtype=np.int32)
    print(f"  {len(verts):,} verts, {len(faces):,} faces, z in [{verts[:,2].min():.1f}, {verts[:,2].max():.1f}]")

    # ── 2. Remove block artifact ────────────────────────────────────────
    print("\nRemoving block artifact ...")
    teeth_z_min = verts[labels > 0][:, 2].min()
    block_cutoff = teeth_z_min - 1.0          # 1 mm below deepest root
    face_z_min = verts[faces][:, :, 2].min(axis=1)
    keep_mask = face_z_min >= block_cutoff
    n_removed = (~keep_mask).sum()
    print(f"  Teeth z_min={teeth_z_min:.1f}, cutoff={block_cutoff:.1f} -> removed {n_removed:,} faces")

    cfaces = faces[keep_mask]                 # clean faces

    # ── 2b. Remove spike artifacts (long-edge gingiva faces) ────────────
    print("\nRemoving spike artifacts (max edge > %.1f mm) ..." % MAX_EDGE_MM)
    fv = verts[cfaces]                        # (M, 3, 3)
    e0 = np.linalg.norm(fv[:, 1] - fv[:, 0], axis=1)
    e1 = np.linalg.norm(fv[:, 2] - fv[:, 1], axis=1)
    e2 = np.linalg.norm(fv[:, 0] - fv[:, 2], axis=1)
    max_edge = np.maximum(np.maximum(e0, e1), e2)

    # Only filter gingiva faces (teeth faces are fine)
    fl_pre = labels[cfaces]
    is_gingiva_pre = (fl_pre > 0).sum(axis=1) < 2
    spike_mask = is_gingiva_pre & (max_edge > MAX_EDGE_MM)
    cfaces = cfaces[~spike_mask]
    n_spikes = spike_mask.sum()
    print(f"  Removed {n_spikes:,} spike faces")

    # ── 2c. Remove small disconnected gingiva islands ─────────────────
    print("\nRemoving disconnected gingiva islands ...")
    fl_pre2 = labels[cfaces]
    is_gin2 = (fl_pre2 > 0).sum(axis=1) < 2
    gin_indices = np.where(is_gin2)[0]

    # Build adjacency via shared edges among gingiva faces
    from collections import defaultdict
    edge_to_face = defaultdict(list)
    for i, fi in enumerate(gin_indices):
        f = cfaces[fi]
        for ea, eb in [(f[0], f[1]), (f[1], f[2]), (f[2], f[0])]:
            edge_to_face[tuple(sorted((ea, eb)))].append(i)

    # BFS connected components
    adj = defaultdict(set)
    for nbrs in edge_to_face.values():
        for a in nbrs:
            for b in nbrs:
                if a != b:
                    adj[a].add(b)

    visited = np.zeros(len(gin_indices), dtype=bool)
    components = []
    for start in range(len(gin_indices)):
        if visited[start]:
            continue
        comp = []
        stack = [start]
        while stack:
            node = stack.pop()
            if visited[node]:
                continue
            visited[node] = True
            comp.append(node)
            stack.extend(adj[node] - set(comp))
        components.append(comp)

    components.sort(key=len, reverse=True)
    # Keep only the largest component
    keep_set = set(components[0]) if components else set()
    island_faces = {gin_indices[i] for i in range(len(gin_indices)) if i not in keep_set}
    n_islands = len(island_faces)
    n_comps = len(components)
    keep_clean = np.array([i not in island_faces for i in range(len(cfaces))])
    cfaces = cfaces[keep_clean]
    print(f"  Found {n_comps} components, removed {n_islands:,} island faces (kept largest)")

    # ── 3. Classify teeth / gingiva ─────────────────────────────────────
    print("\nClassifying ...")
    fl = labels[cfaces]                       # (M, 3)
    tooth_per_face = (fl > 0).sum(axis=1)
    teeth_mask = tooth_per_face >= 2
    gingiva_mask = ~teeth_mask
    print(f"  Teeth: {teeth_mask.sum():,}  Gingiva: {gingiva_mask.sum():,}")

    # ── 4. Simulate recession on FDI 13 ─────────────────────────────────
    print(f"\nSimulating recession (FDI {RECESSION_FDI}) ...")
    tv = verts[labels == RECESSION_FDI]
    tc = tv.mean(axis=0)                      # tooth centroid
    tz_min, tz_max = tv[:, 2].min(), tv[:, 2].max()
    cej_z = tz_max - (tz_max - tz_min) * 0.35  # ≈ crown-root junction
    print(f"  Tooth centroid: ({tc[0]:.1f}, {tc[1]:.1f}, {tc[2]:.1f})")
    print(f"  z in [{tz_min:.1f}, {tz_max:.1f}], CEJ ~ {cej_z:.1f}")

    # Buccal direction (outward from palate centre through tooth)
    tooth_dir = tc[:2] - ARCH_CENTER_XY
    radial_hat = tooth_dir / np.linalg.norm(tooth_dir)
    tooth_r = np.dot(tooth_dir, radial_hat)

    # Evaluate gingiva faces
    gin_idx = np.where(gingiva_mask)[0]
    gin_faces = cfaces[gingiva_mask]
    gin_centroids = verts[gin_faces].mean(axis=1)   # (N, 3)

    # Distance from tooth centroid
    dist = np.linalg.norm(gin_centroids - tc, axis=1)
    near = dist < RECESSION_RADIUS_MM

    # Buccal filter: radial projection exceeds tooth_r - 4 mm (relaxed)
    xy = gin_centroids[:, :2] - ARCH_CENTER_XY
    radial_proj = xy @ radial_hat
    buccal = radial_proj > (tooth_r - 4.0)

    # Z band around CEJ (wider range for visible recession)
    z_ok = (gin_centroids[:, 2] > tz_min - 3.0) & (gin_centroids[:, 2] < cej_z + 3.0)

    recession_local = near & buccal & z_ok
    if recession_local.sum() < 20:
        print("  Relaxing buccal filter ...")
        recession_local = near & z_ok

    # Map to cfaces-level mask
    recession_mask = np.zeros(len(cfaces), dtype=bool)
    recession_mask[gin_idx[recession_local]] = True
    print(f"  Recession faces: {recession_mask.sum():,}")

    # ── 5. RBF ideal-volume reconstruction ──────────────────────────────
    print("\nRBF ideal-volume reconstruction ...")

    # Boundary ring = vertices shared between recession and remaining gingiva
    rec_verts = set(cfaces[recession_mask].ravel())
    rest_gin = gingiva_mask & ~recession_mask
    rest_verts = set(cfaces[rest_gin].ravel())
    ring_idx = np.array(sorted(rec_verts & rest_verts))
    print(f"  Boundary ring: {len(ring_idx)} vertices")

    ideal_ok = False
    if len(ring_idx) >= 15:
        ring_pts = verts[ring_idx]

        # Local PCA coordinate system
        cen = ring_pts.mean(axis=0)
        centered = ring_pts - cen
        _, _, Vt = np.linalg.svd(centered, full_matrices=False)
        axes = Vt   # rows = principal directions; last row ≈ normal

        local_ring = centered @ axes.T            # (N, 3) → (u, v, w)

        # Fit RBF: w = f(u, v)
        rbf = RBFInterpolator(
            local_ring[:, :2],
            local_ring[:, 2],
            kernel="thin_plate_spline",
            smoothing=0.8,
        )

        # Dense grid inside the boundary polygon
        uv = local_ring[:, :2]
        margin = 0.3
        u_lo, v_lo = uv.min(axis=0) - margin
        u_hi, v_hi = uv.max(axis=0) + margin
        N = 50
        uu = np.linspace(u_lo, u_hi, N)
        vv = np.linspace(v_lo, v_hi, N)
        U, V = np.meshgrid(uu, vv)
        grid_uv = np.column_stack([U.ravel(), V.ravel()])

        # Keep points inside boundary convex hull
        hull_del = Delaunay(uv)
        inside = hull_del.find_simplex(grid_uv) >= 0
        grid_uv = grid_uv[inside]

        if len(grid_uv) >= 3:
            W = rbf(grid_uv)
            local_pts = np.column_stack([grid_uv, W])
            world_pts = local_pts @ axes + cen      # back to world coords

            # Triangulate in UV space
            tri = Delaunay(grid_uv)
            triangles = tri.simplices

            write_raw_obj(OUT_DIR / "ideal_volume.obj",
                          world_pts, triangles, COLOR_SCAFFOLD)
            ideal_ok = True
            print(f"  Surface: {len(world_pts):,} verts, {len(triangles):,} tris")
        else:
            print("  WARNING: too few interior grid points for triangulation")

    if not ideal_ok:
        # Fallback: export the original recession faces as the ideal surface
        print("  Fallback: using original recession faces as ideal volume")
        write_submesh(OUT_DIR / "ideal_volume.obj", verts, cfaces,
                      recession_mask, COLOR_SCAFFOLD)

    # ── 6. Export sub-meshes ────────────────────────────────────────────
    print("\nWriting sub-meshes ...")
    write_submesh(OUT_DIR / "teeth.obj",           verts, cfaces, teeth_mask, COLOR_TEETH)
    write_submesh(OUT_DIR / "gingiva.obj",         verts, cfaces, gingiva_mask, COLOR_GINGIVA)
    write_submesh(OUT_DIR / "gingiva_healthy.obj", verts, cfaces,
                  gingiva_mask & ~recession_mask, COLOR_GINGIVA)
    write_submesh(OUT_DIR / "defect.obj",          verts, cfaces, recession_mask, COLOR_DEFECT)

    print("\nDone! All meshes written to", OUT_DIR)


if __name__ == "__main__":
    main()
