---
name: shiver-data-reduction
description: Automate single-crystal inelastic neutron scattering data reduction, 4D MDE slicing, vanadium normalization, and physically isotropic reciprocal-space plotting using SHIVER and Mantid for direct-geometry time-of-flight spectrometers (ARCS, SEQUOIA, CNCS, HYSPEC).
---

# SHIVER Data Reduction & Slicing Skill

## Overview

**SHIVER** (*Spectroscopy HIstogram Visualizer for Event Reduction*) is a Python/Mantid-based tool developed at ORNL/BNL for analyzing 4D single-crystal inelastic neutron scattering datasets on direct-geometry time-of-flight spectrometers (**ARCS**, **SEQUOIA**, **CNCS**, and **HYSPEC**).

While users frequently interact with SHIVER via its Qt GUI, the underlying Mantid algorithms (`MakeSlice`, `MDNorm`) can be fully automated headlessly via Python scripts.

---

## 1. Environment & Execution

On `analysis.sns.gov`, SHIVER is deployed via Pixi:
- **Python Binary**: `/usr/local/pixi/shiver/.pixi/envs/default/bin/python`
- **Package Location**: `/usr/local/pixi/shiver/.pixi/envs/default/lib/python3.12/site-packages/shiver/`

To make SHIVER's algorithms available to Mantid, import `shiver.models.makeslice` **before** importing `MakeSlice` from `mantid.simpleapi`:

```python
import shiver.models.makeslice
from mantid.simpleapi import Load, LoadMD, MakeSlice, SaveMD, mtd
```

---

## 2. Fast Metadata Probing (`MetadataOnly=True`)

Multi-angle combined MDE files (e.g., `..._complete_shiver_UB.nxs`) are often 50–100+ GB. Ingesting full event lists takes 5–7 minutes over network filesystems.

**Always probe metadata first** to retrieve coordinate bounds, UB matrices, and lattice constants in seconds:

```python
from mantid.simpleapi import LoadMD

ws_meta = LoadMD(Filename=data_path, MetadataOnly=True, OutputWorkspace="ws_meta")

# Inspect oriented lattice and UB matrix
ei = ws_meta.getExperimentInfo(0)
ol = ei.sample().getOrientedLattice()
print(f"Lattice: a={ol.a():.4f}, b={ol.b():.4f}, c={ol.c():.4f}, gamma={ol.gamma():.1f}")
print("UB Matrix:\n", ol.getUB())
```

---

## 3. Vanadium Normalization

Vanadium normalization corrects for detector efficiency variations and solid angle across the detector bank.

- Located in the proposal directory: `.../shared/van<run_number>.nxs`
- Load as a `MatrixWorkspace` with `Load`:
  ```python
  Load(Filename=van_path, OutputWorkspace="van_norm")
  ```
- Pass to `MakeSlice` using `NormalizationWorkspace="van_norm"`. Under the hood, `MakeSlice` forwards this to `MDNorm` as `SolidAngleWorkspace`.

---

## 4. Arbitrary Plane Slicing & Orthogonal Integration Geometry

In reciprocal space, arbitrary slicing planes are defined by two in-plane basis vectors $\vec{q}_0$ and $\vec{q}_1$. The third axis $\vec{q}_2$ **must be perpendicular to the plane in physical Cartesian momentum space ($\text{Å}^{-1}$)** to prevent skew integration that mixes in-plane momentum components.

### Non-Orthogonal Lattices & Cartesian Cross Product
In non-orthogonal crystal systems (e.g. hexagonal, monoclinic, triclinic), $(H, K, L)$ coordinates are not mutually orthogonal. 
For instance, in a hexagonal crystal ($a = b, \gamma = 120^\circ \implies \gamma^* = 60^\circ$):
- Slicing the $(H, 0, L)$ plane uses in-plane axes $\vec{q}_0 = [1, 0, 0]$ and $\vec{q}_1 = [0, 0, 1]$.
- Simply picking $[0, 1, 0]$ as the integration axis is **incorrect** because $\vec{b}^*$ forms a $60^\circ$ angle with $\vec{a}^*$. Integrating along $[0, 1, 0]$ introduces an unwanted $H$ component into the cut.
- In Cartesian space, the true vector perpendicular to both $[1, 0, 0]$ and $[0, 0, 1]$ is parallel to **$[-0.5, 1, 0]$**.

### Universal Calculation of the Orthogonal Axis ($\vec{q}_2$)
To determine $\vec{q}_2$ for any arbitrary plane and crystal geometry, transform the Miller vectors to Cartesian coordinates using the crystal orientation / Busing-Levy matrix $T$ (where $\vec{Q}_{\text{cart}} = T \cdot \vec{q}_{\text{hkl}}$, $T = 2\pi \cdot UB$ or $B$), compute the vector cross product, and transform back:

```python
def calculate_orthogonal_q2(q0, q1, T, normalize=True):
    """
    Calculate the reciprocal vector q2 perpendicular to q0 and q1
    in physical Cartesian momentum space (A^-1).
    
    T: Transformation matrix from (H, K, L) to Cartesian Q (A^-1),
       e.g., T = 2 * np.pi * UB or the Busing-Levy B matrix.
    """
    q0_cart = np.matmul(T, q0)
    q1_cart = np.matmul(T, q1)
    
    # Cartesian cross product guarantees perpendicularity
    cross_cart = np.cross(q0_cart, q1_cart)
    
    # Map back to (H, K, L) basis
    q2 = np.matmul(np.linalg.inv(T), cross_cart)
    
    if normalize:
        non_zero = q2[np.where(q2 != 0)]
        if len(non_zero) > 0:
            q2 = q2 / np.max(np.abs(non_zero))
            
    return q2
```

### Configuring `MakeSlice`
When setting up `MakeSlice`:
- `QDimension0`: in-plane axis 1 ($\vec{q}_0$)
- `QDimension1`: out-of-plane orthogonal integration axis ($\vec{q}_2 = \vec{q}_0 \times_{\text{cart}} \vec{q}_1$)
- `QDimension2`: in-plane axis 2 ($\vec{q}_1$)

```python
# Example: (H, 0, L) plane in hexagonal FeS
q0 = [1, 0, 0]
q1 = [0, 0, 1]
q2_perp = calculate_orthogonal_q2(q0, q1, T=2 * np.pi * ol.getUB())
# Result: q2_perp = [-0.5, 1.0, 0.0]

MakeSlice(
    InputWorkspace=mde_name,
    NormalizationWorkspace="van_norm",
    OutputWorkspace="slice_ws",
    QDimension0=q0,                      # [1, 0, 0] (In-plane H)
    QDimension1=q2_perp,                 # [-0.5, 1, 0] (Perpendicular integration axis)
    QDimension2=q1,                      # [0, 0, 1] (In-plane L)
    Dimension0Name="QDimension0",
    Dimension0Binning="-8.5,0.05,8.5",   # In-plane H binned
    Dimension1Name="QDimension2",
    Dimension1Binning="-15.6,0.06,15.6", # In-plane L binned
    Dimension2Name="QDimension1",
    Dimension2Binning="-0.1,0.1",        # Integrated strictly perpendicular to (H,0,L)
    Dimension3Name="DeltaE",
    Dimension3Binning="4.0,6.0",         # Integrated Energy Transfer
)
```

### Common Plane Configurations
| Target Plane | In-Plane $\vec{q}_0$ | In-Plane $\vec{q}_1$ | Orthogonal Integration Axis $\vec{q}_2$ (Hexagonal) |
| :--- | :--- | :--- | :--- |
| **$(H, 0, L)$** | $[1, 0, 0]$ | $[0, 0, 1]$ | **$[-0.5, 1, 0]$** (orthogonal to $a^*$ and $c^*$) |
| **$(H, K, 0)$** | $[1, 0, 0]$ | $[0, 1, 0]$ | **$[0, 0, 1]$** (orthogonal to $a^*b^*$ plane) |
| **$(H, H, L)$** | $[1, 1, 0]$ | $[0, 0, 1]$ | **$[-1, 1, 0]$** (orthogonal to $[1, 1, 0]$ and $c^*$) |
| **$(0, K, L)$** | $[0, 1, 0]$ | $[0, 0, 1]$ | **$[1, -0.5, 0]$** (orthogonal to $b^*$ and $c^*$) |

---

## 5. Physical $Q$-Vector Aspect Ratio Scaling

When plotting in reciprocal lattice units (r.l.u.), unit lengths along different crystal axes rarely correspond to equal physical distances in $\text{\AA}^{-1}$. 

For hexagonal/non-cubic lattices, displaying plots with a 1:1 r.l.u. ratio stretches or compresses reciprocal space, distorting Debye–Scherrer powder rings into ellipses.

**Rule**: Always scale the plot aspect ratio using the physical reciprocal vector lengths:

$$\text{Aspect Ratio } \left(\frac{\text{screen height per unit } L}{\text{screen width per unit } H}\right) = \frac{|\vec{c}^*|}{|\vec{a}^*|}$$

```python
ol = mtd[mde_name].getExperimentInfo(0).sample().getOrientedLattice()
aspect_q = ol.cstar() / ol.astar()
ax.set_aspect(aspect_q, adjustable='box')
```

This guarantees:
- Isotropic reciprocal space representation.
- True circular curvature for all powder and background rings.

---

## 6. Persisting Intermediate Slices

Full MDE loads take 5–7 minutes, but an extracted 2D/3D slice is typically only a few megabytes.

**Always save the sliced MDHistoWorkspace**:
```python
SaveMD(InputWorkspace="slice_ws", Filename=".../shared/scripts/gemini/<name>_slice.nxs")
```
Subsequent plotting, cut extractions, or colorbar adjustments can then reload the `.nxs` slice in < 1 second with `LoadMD(Filename=..., OutputWorkspace="slice_ws")`.

---

## 7. Extracting & Visualizing Arrays

`IMDHistoWorkspace` retains 1-bin singleton dimensions for integrated axes. Always squeeze the array before passing to Matplotlib:

```python
signal = np.squeeze(mdh.getSignalArray().copy())
num_events = np.squeeze(mdh.getNumEventsArray().copy())

# Mask empty/unmeasured bins
mask = (num_events == 0) | np.isnan(signal) | (signal <= 0)
signal[mask] = np.nan

# Matplotlib pcolormesh requires C with shape (n_y, n_x) -> signal.T
mesh = ax.pcolormesh(H_edges, L_edges, signal.T, cmap='viridis', norm=LogNorm(vmin=vmin, vmax=vmax))
```

---

## 8. Hexagonal Symmetry-Equivalent Reciprocal Planes

In hexagonal crystals ($P6_3/mmc$, $P6_3mc$, etc.), the 3-fold rotation operator $C_{3z}$ around $\mathbf{c}^* = (0, 0, 1)$ transforms Miller coordinates according to:
$$C_{3z}(H, K, L) = (-H - K, H, L)$$

For any chosen slicing plane spanned by in-plane vectors $\mathbf{q}_0$ and $\mathbf{q}_1 = (0, 0, L)$, there are two symmetry-equivalent planes obtained by applying $C_{3z}$ and $C_{3z}^2$:

| Plane | Zone Axis | In-Plane $\mathbf{q}_0$ | In-Plane $\mathbf{q}_1$ | Orthogonal Integration Axis $\mathbf{q}_2$ |
| :--- | :--- | :--- | :--- | :--- |
| **Plane 1: $(H, H, L)$** | $[1, \bar{1}, 0, 0]$ | $(\frac{1}{3}, \frac{1}{3}, 0)$ | $(0, 0, \frac{1}{2})$ | $(-\frac{1}{3}, \frac{1}{3}, 0)$ |
| **Plane 2: $(-2K, K, L)$** | $[0, 1, \bar{1}, 0]$ | $(-\frac{2}{3}, \frac{1}{3}, 0)$ | $(0, 0, \frac{1}{2})$ | $(0, -\frac{1}{3}, 0)$ |
| **Plane 3: $(H, -2H, L)$** | $[\bar{1}, 0, 1, 0]$ | $(\frac{1}{3}, -\frac{2}{3}, 0)$ | $(0, 0, \frac{1}{2})$ | $(\frac{1}{3}, 0, 0)$ |

### Invariant Quantities Across Symmetry Planes
- $|\mathbf{q}_0|$, $|\mathbf{q}_1|$, and $|\mathbf{q}_2|$ are invariant under $C_{3z}$.
- The physical aspect ratio $\frac{|\mathbf{q}_1|}{|\mathbf{q}_0|}$ is identical across all three planes.
- Using identical integration binning along $\mathbf{q}_2$ ensures rigorous intensity equivalence across zones.

---

## 9. Bose-Factor Thermal Population Correction

For inelastic cuts ($\Delta E > 0$), remove thermal phonon population using the Bose-Einstein factor:
$$n(\Delta E, T) = \frac{1}{\exp\left(\frac{\Delta E}{k_B T}\right) - 1},\quad k_B = 0.08617333\ \text{meV/K}$$

The corrected intensity proportional to the dynamical susceptibility is:
$$S_{\text{corr}}(Q, \Delta E) = \frac{S(Q, \Delta E)}{1 + n(\Delta E, T)} = S(Q, \Delta E) \cdot \left[1 - \exp\left(-\frac{\Delta E}{k_B T}\right)\right]$$

```python
kB = 0.08617333  # meV / K
bose_factor = 1.0 / (np.exp(delta_E / (kB * T)) - 1.0)
s_corr = signal / (1.0 + bose_factor)
err_corr = err / (1.0 + bose_factor)
```

---

## 10. Colormap Scaling & Multi-Panel Master Grids

### Contrast Scaling
- **Linear Scale ($v_{\min} = 0.0$)**: Never use raw `np.max` (Bragg cores blow out dynamic range). Set `vmax = np.percentile(valid_signal, 98.5)`:
  ```python
  norm = Normalize(vmin=0.0, vmax=np.percentile(vals, 98.5))
  ```
- **Log Scale**: Clip near-zero background:
  ```python
  norm = LogNorm(vmin=2.0e-3, vmax=np.percentile(vals, 99.0))
  ```

### Multi-Panel Subplot Layout
To prevent Matplotlib from distorting physical aspect ratios when adding colorbars, use `fig.subplots_adjust` and a dedicated colorbar axis:
```python
fig, axes = plt.subplots(3, 3, figsize=(18, 18), sharex=True, sharey=True, dpi=180)
# Configure aspect ratio per axis
for ax in axes.flat:
    ax.set_aspect(aspect_q, adjustable='box')

fig.subplots_adjust(left=0.06, right=0.91, bottom=0.06, top=0.93, hspace=0.10, wspace=0.12)
cbar_ax = fig.add_axes([0.925, 0.10, 0.015, 0.80])
fig.colorbar(pcm, cax=cbar_ax)
```
