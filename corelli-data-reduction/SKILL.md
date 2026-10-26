---
name: corelli-data-reduction
description: Single-crystal elastic and diffuse neutron scattering data reduction, 3D/4D reciprocal-space normalization, Bragg and satellite peak integration, and Jana2020/SHELX export for CORELLI (BL-9) and SNS Single Crystal Diffraction (SCD) instruments using garnet and /SNS/software/scd/reduce.sh.
---

# CORELLI Data Reduction & Integration Skill (`garnet`)

## Overview

**CORELLI** (BL-9 at the ORNL Spallation Neutron Source) is a statistical chopper spectrometer designed for single-crystal elastic and diffuse neutron scattering with elastic discrimination via a pseudo-random cross-correlation chopper.

Data reduction at CORELLI (as well as SNS single-crystal diffraction instruments **TOPAZ**, **MANDI**, and **SNAP**) is powered by **`garnet`**, invoked via the facility wrapper script `/SNS/software/scd/reduce.sh`. The pipeline supports two primary workflows:
1. **Normalization (`-n`)**: Converts raw event NeXus files into vanadium/flux-normalized and background-subtracted 3D $(H, K, L, I)$ reciprocal-space histograms (`MDHistoWorkspace`) for diffuse scattering visualization and slicing.
2. **Integration (`-i`)**: Performs 3D profile-fitted Bragg and satellite peak integration (supporting up to 3 modulation vectors and arbitrary harmonic orders) and exports reflection files (`.int`, `.hkl`, `.cif`, `.mat`) for structural refinement in **Jana2020**, **SHELX**, or **FullProf**.

---

## 1. Execution Environment & Wrapper Mechanics (`/SNS/software/scd/reduce.sh`)

On `analysis.sns.gov`, `/SNS/software/scd/reduce.sh` dispatches `/SNS/software/scd/garnet/src/garnet/workflow.py` inside a centralized Pixi environment:
- **Wrapper Script**: `/SNS/software/scd/reduce.sh`
- **Pixi Manifest**: `/usr/local/pixi/scd-reduction-tools`
- **Underlying Engine**: `/SNS/software/scd/garnet/src/garnet/workflow.py`
- **Developer Engine (`-d` flag)**: `/SNS/software/scd/garnet-tools/src/garnet/workflow.py`

### Command-Line Usage & Flags

```bash
# 1. Run Normalization (-n) to produce 3D (H,K,L,I) reciprocal-space volumes
/SNS/software/scd/reduce.sh -n /path/to/config.yaml <num_processes>

# 2. Run Integration (-i) to produce Bragg/satellite reflection tables for Jana2020/SHELX
/SNS/software/scd/reduce.sh -i /path/to/config.yaml <num_processes>

# 3. Run Parametrization (-p) to track reciprocal-space cuts vs sample log (e.g. temperature)
/SNS/software/scd/reduce.sh -p /path/to/config.yaml <num_processes>

# 4. Generate a blank template YAML (-t) for an instrument (corelli, topaz, mandi, snap)
/SNS/software/scd/reduce.sh -t /path/to/new_template.yaml corelli
```

> [!NOTE]
> **Parallel Process Allocation (`<num_processes>`) & SSH Session Management**:
> `garnet` uses Python `multiprocess` (`spawn`) and automatically caps `n_proc` at `min(os.cpu_count(), len(Runs))`. A typical setting on `analysis.sns.gov` is `8` to `16` processes. Always launch long reduction runs detached using `nohup ... < /dev/null > run.log 2>&1 &` per the `sns-analysis-remote` standard.
> If the SSH connection fails or prompts for credentials (due to an expired ControlMaster multiplexing socket), immediately notify the user to renew their login in an external terminal (`ssh analysis.sns.gov`) rather than running automated diagnostic retries.

---

## 2. Proposal Directory Hierarchy & Output Path Resolution

Within a CORELLI proposal directory (`/SNS/CORELLI/IPTS-<number>/shared/`):

```text
/SNS/CORELLI/IPTS-<number>/shared/
├── CORELLI_IPTS-<number>_runsummary.csv   # Symlink to autoreduce run summary log
├── autoreduce/                            # Facility automated reduction (CORELLI_<run>_elastic.nxs)
├── scripts/                               # UB finding (01_findub.py), masks (CCR.xml, SlimSAM.xml), and *.mat files
│   ├── 01_findub.py
│   ├── CCR.xml
│   ├── SlimSAM.xml
│   └── <Sample>_<T>K.mat                  # ISAW UB orientation matrices
├── normalization/                         # Normalization YAML configs and output subfolders
│   ├── <Sample>_<T>K.yaml
│   └── <Sample>_<T>K_normalization/
└── integration/                           # Integration YAML configs and output subfolders
    ├── <Sample>_<T>K.yaml
    └── <Sample>_<T>K_integration/
```

### Critical Rule: How `garnet` Resolves Output Directories

In `garnet.reduction.plan.ReductionPlan.set_output(filename)`:
```python
OutputPath = os.path.dirname(os.path.abspath(filename))
OutputName = os.path.splitext(os.path.basename(filename))[0]
```
- **Outputs are always written alongside the input `.yaml` file**:
  - Running `reduce.sh -n /path/to/Sample.yaml` creates `/path/to/Sample_normalization/`.
  - Running `reduce.sh -i /path/to/Sample.yaml` creates `/path/to/Sample_integration/`.
- **YAML files in `shared/integration/` are NOT auto-generated**:
  - Calling `reduce.sh -i` on a YAML located inside `shared/normalization/` will **not** copy or generate a YAML in `shared/integration/`; instead, it will create `<Sample>_integration/` inside `shared/normalization/`.
  - **Best Practice**: When preparing an integration run, explicitly place (or copy and customize) the `.yaml` file inside `/SNS/CORELLI/IPTS-<number>/shared/integration/` before running `reduce.sh -i`.

---

## 3. YAML Configuration Schema & Section Stripping

A single `garnet` YAML file can contain `Integration`, `Normalization`, and `Parametrization` blocks simultaneously. At runtime, `workflow.py` inspects the active mode (`-n`, `-i`, or `-p`) and pops the unused blocks from memory before executing.

### Complete Annotated YAML Reference

```yaml
Instrument: CORELLI
IPTS: 37759
Runs: 536005:536124                                # Range "start:stop", step "start:stop;step", or comma-separated list
UBFile: /SNS/CORELLI/IPTS-37759/shared/scripts/YMn6Sn6_320K.mat

# --- PEAK INTEGRATION BLOCK (Used with -i) ---
Integration:
  Cell: Hexagonal                                  # Triclinic, Monoclinic, Orthorhombic, Tetragonal, Rhombohedral, Hexagonal, Cubic
  Centering: P                                     # P, I, F, A, B, C, R
  ModVec1: [0.0, 0.0, 0.0]                         # Primary modulation vector q1 = [dh, dk, dl] for satellite peaks
  ModVec2: [0.0, 0.0, 0.0]                         # Secondary modulation vector q2
  ModVec3: [0.0, 0.0, 0.0]                         # Tertiary modulation vector q3
  MaxOrder: 0                                      # Maximum harmonic order m for satellites (0 = nuclear/fundamental only; 1, 2, ...)
  CrossTerms: false                                # Include cross-term combinations (m1*q1 + m2*q2) when multiple ModVecs are active
  MinD: 0.7                                        # Minimum d-spacing (Angstroms) for main Bragg reflections
  SatMinD: 1.0                                     # Minimum d-spacing (Angstroms) for satellite reflections (when MaxOrder > 0)
  Radius: 0.2                                      # Peak integration radius in Q-space (Angstrom^-1). See radius criterion below.
  OptimizeUB: false                                # Optional: refine UB orientation prior to integration
  OptimizePeaks: false                             # Optional: re-center peak positions prior to ellipsoid fitting
  ProfileFit: true                                 # Enable 3D Stoica-Wilkinson resolution ellipsoid profile fitting

> [!TIP]
> **Satellite Integration Radius Criterion**:
> The default integration radius `Radius: 0.20` $\text{\AA}^{-1}$ is suitable for well-separated fundamental Bragg peaks. In modulated structures where satellites lie in close proximity to fundamentals or other satellites (e.g. $|\Delta \mathbf{q}| < 0.1\text{ r.l.u.}$), the integration sphere radius must be chosen to avoid peak contamination or overlap:
> $$\text{Radius} \le \frac{1}{2} \Delta Q_{\min} \approx \frac{1}{2} |\Delta \mathbf{q}| c^*$$
> For example, in $\text{YMn}_6\text{Sn}_6$ with $c^* \approx 0.698\text{ \AA}^{-1}$ and $\Delta q \approx 0.061$, the separation is $\Delta Q \approx 0.043\text{ \AA}^{-1}$; setting $\text{Radius} = 0.10\text{ \AA}^{-1}$ or smaller ensures clean, non-overlapping integration spheres.

# --- RECIPROCAL VOLUME NORMALIZATION BLOCK (Used with -n) ---
Normalization:
  Symmetry: null                                   # Point/Laue group for symmetrization (e.g. "6/mmm", "-3m", or null for un-symmetrized)
  Projections:                                     # Three linearly independent reciprocal projection vectors [D0, D1, D2]
  - [1, 0, 0]                                      # Axis D0 (e.g. [H, 0, 0])
  - [0, 0, 1]                                      # Axis D1 (e.g. [0, 0, L])
  - [0, 1, 0]                                      # Axis D2 (e.g. [0, K, 0])
  Extents:                                         # [min, max] bounds in r.l.u. corresponding to [D0, D1, D2]
  - [-6.0, 5.0]
  - [-10.0, 10.0]
  - [-2.0, 2.0]
  Bins: [501, 501, 81]                             # Number of histogram bins [N_D0, N_D1, N_D2]

# --- PARAMETRIZATION BLOCK (Used with -p) ---
Parametrization:
  LogName: sample_temperature
  LogExtents: [5.0, 300.0]
  LogBins: 60
  MillerIndex: null
  Projections:
  - [1, 0, 0]
  - [0, 1, 0]
  - [0, 0, 1]
  Extents:
  - [-0.1, 0.1]
  - [-0.1, 0.1]
  - [0.5, 1.5]
  Bins: [1, 1, 51]

# --- INSTRUMENT & CALIBRATION PARAMETERS ---
Wavelength: [0.6, 2.5]                             # Incident neutron wavelength band (Angstroms)
Elastic: false                                     # false = total scattering (all correlation chopper states); true = elastic cross-correlation only
Grouping: 1x1                                      # Detector pixel grouping
BackgroundFile: /SNS/CORELLI/shared/Vanadium/2026B_0804_CCR/background.nxs
DetectorCalibration: /SNS/CORELLI/shared/calibration/2026B/calibration.DetCal
TubeCalibration: /SNS/CORELLI/shared/calibration/tube/calibration_corelli_20200109.nxs.h5
FluxFile: /SNS/CORELLI/shared/Vanadium/2026B_0804_CCR/flux.nxs
VanadiumFile: /SNS/CORELLI/shared/Vanadium/2026B_0804_CCR/solid_angle.nxs
```

### Optional Crystallographic & Absorption Blocks for Integration (`Material` & `Sample`)

When running `-i`, after peak integration completes, `Integration.write()` invokes `/SNS/software/scd/garnet/src/garnet/utilities/structure.py`. If `Material` and `Sample` blocks are present in the YAML, `structure.py` performs ellipsoid absorption corrections and preliminary nuclear structure refinement:

```yaml
Material:
  ChemicalFormula: Cr1-V1-I6                       # Hyphen-separated stoichiometry for Mantid SetSampleMaterial
  ZParameter: 3.0                                  # Formula units per unit cell
  SpaceGroup: R3                                   # Hermann-Mauguin symbol
  Sites:                                           # [Element, x, y, z, occupancy]
  - [Cr, 0.0, 0.0, 0.333333, 1.0]
  - [V, 0.0, 0.0, 0.666667, 1.0]
  - [I, 0.0115, 0.344, 0.0789, 1.0]
  - [I, 0.9885, 0.656, 0.9211, 1.0]
  TwinLaws:                                        # Optional 3x3 twin matrices
  - [[0, -1, 0], [-1, 0, 0], [0, 0, -1]]
Sample:
  ThicknessWidthHeight: [0.1, 0.5, 0.5]            # Crystal dimensions in cm (if > 0, enables ellipsoid absorption correction)
  UVector: [0, 0, 1]                               # Crystal orienting vector u
  VVector: [1, 0, 0]                               # Crystal orienting vector v
```

> [!NOTE]
> **Omitting `Material` and `Sample` for Jana2020 Refinements**:
> When processing single-crystal datasets intended for Jana2020, omitting the `Material` and `Sample` blocks is standard practice. `garnet` smoothly defaults transmission to 1.0 and exports raw profile-fitted intensities and sigmas directly to `.int` and `.hkl`. This allows Jana2020 to apply its own rigorous numerical Gaussian or analytical face-indexed absorption corrections based on the exact optical crystal face indexing.

---

## 4. Normalization Outputs & HDF5 Data Layout (`-n`)

Inside `<OutputName>_normalization/`, `garnet` writes:

| File / Folder | Description |
| :--- | :--- |
| `<Name>_<Proj>_<Extents>_<Bins>.nxs` | Normalized 3D reciprocal volume ($\text{data} / \text{norm}$), without background subtraction. |
| `<Name>_<Proj>_<Extents>_<Bins>_bkg.nxs` | Normalized ambient background volume ($\text{bkg\_data} / \text{bkg\_norm}$). |
| **`<Name>_<Proj>_<Extents>_<Bins>_sub_bkg.nxs`** | **Background-subtracted normalized volume ($\text{result} - \text{bkg\_result}$). Primary file for analysis.** |
| `<Name>_..._plots/slice_*.pdf` | Automated multi-page PDFs showing 2D slices at every integer value along each projection axis. |
| `<Name>_..._diagnostics/` | Raw accumulated event (`_data.nxs`) and solid-angle/flux (`_norm.nxs`) histograms. |
| `<Name>_normalization.json` | Full JSON record of the reduction parameters and parallel worker process map. |

### Reading Normalized `.nxs` Files Directly with `h5py`

Normalized `.nxs` files are Mantid `MDHistoWorkspace` HDF5 archives with the following internal hierarchy:

```text
/MDHistoWorkspace/
├── coordinate_system                              # Dataset {1}
├── visual_normalization                           # Dataset {1}
├── experiment0/                                   # Sample logs, oriented lattice, and UB matrix
└── data/
    ├── D0                                         # Bin edges for Projection 0, shape (N0 + 1,), attrs: frame, long_name, units
    ├── D1                                         # Bin edges for Projection 1, shape (N1 + 1,), attrs: frame, long_name, units
    ├── D2                                         # Bin edges for Projection 2, shape (N2 + 1,), attrs: frame, long_name, units
    ├── signal                                     # Normalized intensity array, shape (N2, N1, N0)
    ├── errors_squared                             # Variance array, shape (N2, N1, N0)
    ├── mask                                       # Boolean mask array, shape (N2, N1, N0)
    └── num_events                                 # Contributing event counts, shape (N2, N1, N0)
```

> [!WARNING]
> **Axis Ordering in `/MDHistoWorkspace/data/signal`**:
> While the YAML specifies projections in order `[D0, D1, D2]` with bin counts `[N0, N1, N2]`, Mantid stores the 3D HDF5 dataset `signal` in **reversed index order `(N2, N1, N0)`** (i.e. `[D2, D1, D0]`).
> Always inspect `/MDHistoWorkspace/data/D0`, `D1`, and `D2` (`long_name` attribute and length) when slicing `signal` with `h5py` or NumPy:
> ```python
> import h5py
> import numpy as np
>
> with h5py.File(nxs_path, "r") as f:
>     data_grp = f["MDHistoWorkspace/data"]
>     d0_edges = data_grp["D0"][:]  # length N0 + 1 -> corresponds to axis 2 of signal
>     d1_edges = data_grp["D1"][:]  # length N1 + 1 -> corresponds to axis 1 of signal
>     d2_edges = data_grp["D2"][:]  # length N2 + 1 -> corresponds to axis 0 of signal
>     d0_label = data_grp["D0"].attrs["long_name"].decode() if isinstance(data_grp["D0"].attrs["long_name"], bytes) else str(data_grp["D0"].attrs["long_name"])
>     d1_label = data_grp["D1"].attrs["long_name"].decode() if isinstance(data_grp["D1"].attrs["long_name"], bytes) else str(data_grp["D1"].attrs["long_name"])
>     d2_label = data_grp["D2"].attrs["long_name"].decode() if isinstance(data_grp["D2"].attrs["long_name"], bytes) else str(data_grp["D2"].attrs["long_name"])
>     signal = data_grp["signal"][:]  # shape: (len(d2_edges)-1, len(d1_edges)-1, len(d0_edges)-1)
> ```

---

## 5. Integration Outputs & Downstream Refinement Files (`-i`)

Inside `<OutputName>_integration/`, `garnet` produces two distinct filename conventions depending on the artifact type:

> [!IMPORTANT]
> **Filename Schema Distinction**:
> 1. **Master Peaks NeXus and UB Matrices (`.nxs`, `.mat`) include the modulation vector**:
>    `<OutputName>_<Cell>_<Centering>_(<ModVec>)_d(min)=<MinD>_r(max)=<Radius>.nxs`
>    *(Example: `YMn6Sn6_320K_IC1_Hexagonal_P_(0.0,0.0,0.3547)_d(min)=0.70_r(max)=0.10.nxs`)*
> 2. **Reflection Tables and Text Summaries (`.int`, `.hkl`, `_symm.txt`, `_stats.txt`) omit the modulation vector**:
>    `<OutputName>_<Cell>_<Centering>_d(min)=<MinD>_r(max)=<Radius>.int`
>    *(Example: `YMn6Sn6_320K_IC1_Hexagonal_P_d(min)=0.70_r(max)=0.10.int`)*
> Any downstream scripts parsing reflection tables must search without the `_(<ModVec>)_` infix.

| Extension / Suffix | Purpose & Downstream Software |
| :--- | :--- |
| **`*.int`** | **Jana2020** reflection file (`SaveReflections(Format="Jana")`), including $(h, k, l, m, n, p)$ indices when modulated. |
| **`*.hkl`** | **SHELX / Jana** reflection file (`SaveHKL` with direction cosines, intensities, $\sigma(I)$, and wavelength). |
| **`*_nuc.hkl` & `*_sat.hkl`** | Generated automatically when `MaxOrder > 0`: cleanly separated fundamental ($m=n=p=0$) and satellite ($m^2+n^2+p^2 > 0$) reflection files. |
| **`*_sat_k=1.hkl` & `*_sat_k=2.hkl`** | **Partitioned Multi-Modulation Satellites**: In $(3+2)\text{D}$ or multi-vector models (`ModVec1`, `ModVec2`), `garnet` automatically separates satellites belonging to $\mathbf{q}_1$ (`_sat_k=1`) and $\mathbf{q}_2$ (`_sat_k=2`), along with their corresponding UB matrices (`_sat_k=1.mat`). |
| **`*.mat` (`*_nuc.mat`, `*_sat.mat`)** | Refined ISAW UB matrix files after lattice optimization. |
| **`*.cif`** | Crystallographic Information File summarizing cell parameters, integration statistics, and absorption parameters. |
| **`*.nxs` & `*_corr.nxs`** | Mantid `PeaksWorkspace` NeXus files (uncorrected and absorption/scale corrected). |
| **`*_symm.txt` & `*_stats.txt`** | Laue symmetry equivalence ($R_{\text{int}}$, $R_{\text{pim}}$, redundancy) and completeness statistics across resolution shells. |
| **`*_res.pdf`, `*_res.txt`, `*_res.csv`** | Stoica-Wilkinson 3D resolution ellipsoid fit diagnostics and per-peak covariance radii. |
| **`*_sn.pdf`, `*_stat.pdf`, `*_rate.pdf`, `*_volfrac.pdf`** | Diagnostic plots of signal-to-noise vs $d$-spacing, intensity statistics, count rates, and volume fractions. |
| **`*_plots/` & `*_diagnostics/`** | Per-peak 2D/3D ellipsoid integration profile plots and individual run peak workspaces (`run#<run>_peaks.nxs`). |

> [!NOTE]
> **Scope of Symmetry Statistics in `_symm.txt`**:
> Mantid's `StatisticsOfPeaksWorkspace` algorithm requires integer Miller indices $(h, k, l)$ and fails on fractional satellite coordinates. Consequently, `garnet` filters out all satellite peaks ($m^2+n^2+p^2 > 0$) before computing symmetry statistics. The $R_{\text{merge}}$, $R_{\text{pim}}$, and redundancy values in `_symm.txt` report quality strictly for the **fundamental Bragg reflections**. Satellite reflections are exported directly to `.int` and `_sat.hkl` with individual integrated intensities and $\sigma(I)$ uncertainties from the 3D resolution ellipsoid fits.
> Only peaks passing the signal-to-noise filter ($\text{Signal/Noise} \ge 2$) before and after intensity rescaling are exported to `.int` and `.hkl`.

---

## 6. Hexagonal & Non-Orthogonal Reciprocal-Space Visualization Standards

In non-orthogonal crystal systems, displaying reciprocal data on naive rectangular Cartesian axes $(H, K)$ distorts physical reciprocal space, compressing circular powder rings and diffuse scattering shells into ellipses and obscuring $n$-fold point-group symmetries.

### 6.1 Hexagonal Reciprocal Geometry
For hexagonal crystals ($a = b, \gamma = 120^\circ \implies \gamma^* = 60^\circ$):
$$\mathbf{a}^* = a^* \hat{\mathbf{x}},\quad \mathbf{b}^* = a^* \left(\cos 60^\circ \hat{\mathbf{x}} + \sin 60^\circ \hat{\mathbf{y}}\right) = a^* \left(\frac{1}{2} \hat{\mathbf{x}} + \frac{\sqrt{3}}{2} \hat{\mathbf{y}}\right)$$
Any in-plane vector is:
$$\mathbf{q} = H \mathbf{a}^* + K \mathbf{b}^* = \left(H + \frac{1}{2} K\right) a^* \hat{\mathbf{x}} + \left(\frac{\sqrt{3}}{2} K\right) a^* \hat{\mathbf{y}}$$

---

### 6.2 Primary Standard: Orthogonal $(1, 0, 0)$ vs. $(-0.5, 1, 0)$ Projection

To maintain standard rectangular axes, conventional plotting boxes, and physical isotropy without shear artifacts, project the in-plane scattering onto two mutually perpendicular Cartesian axes:
1. **Horizontal axis ($\mathbf{q}_x$)**: $\mathbf{a}^* = [1, 0, 0]$, with length $|\mathbf{q}_x| = a^*$.
2. **Vertical axis ($\mathbf{q}_y$)**: Vector in the $a^*b^*$ plane perpendicular to $\mathbf{a}^*$. Setting $q_x = 0 \implies H + 0.5 K = 0 \implies H = -0.5 K$. Choosing $K = 1$ yields **$[-0.5, 1, 0]$** (or $[01\bar{1}0]$ in 4-index Miller-Bravais notation), with length:
   $$|\mathbf{q}_y| = \frac{\sqrt{3}}{2} a^* \approx 0.866025 a^*$$
3. **Calibrated Physical Aspect Ratio**:
   $$\text{Aspect Ratio } \left(\frac{\text{height per unit } [-0.5, 1, 0]}{\text{width per unit } [1, 0, 0]}\right) = \frac{|\mathbf{q}_y|}{|\mathbf{q}_x|} = \frac{\sqrt{3}}{2} \approx 0.866025$$

#### Python Interpolation Recipe:
```python
import numpy as np
from scipy.interpolate import RegularGridInterpolator

# Given a 2D slice on regular (K, H) grid:
# Q_x = H + 0.5 * K (in units of a*)
# Q_y = (sqrt(3)/2) * K (in units of a*)
# Inverse mapping:
# K = (2 / sqrt(3)) * Q_y
# H = Q_x - (1 / sqrt(3)) * Q_y

interp = RegularGridInterpolator((k_centers, h_centers), signal_2d, bounds_error=False, fill_value=np.nan)

qx_grid = np.linspace(qx_min, qx_max, n_qx)
qy_grid = np.linspace(qy_min, qy_max, n_qy)
QX, QY = np.meshgrid(qx_grid, qy_grid)

H_eval = QX - (1.0 / np.sqrt(3.0)) * QY
K_eval = (2.0 / np.sqrt(3.0)) * QY

points = np.stack([K_eval.ravel(), H_eval.ravel()], axis=-1)
signal_ortho = interp(points).reshape(QX.shape)

# Plotting:
ax.pcolormesh(qx_grid, qy_grid, signal_ortho, cmap='viridis', norm=norm, shading='auto')
ax.set_aspect(np.sqrt(3) / 2.0, adjustable='box')
ax.set_xlabel(r"$[H, 0, 0]$ (r.l.u.)")
ax.set_ylabel(r"$[-0.5, 1, 0]$ (r.l.u.)")
```

---

### 6.3 Alternative Standard: Standalone 60° Affine Skew (`plot_slice` Style)

When direct display along the oblique crystallographic axes $(H, K)$ at their native $60^\circ$ angle is desired, apply a single-pass Matplotlib `Affine2D` shear without requiring external packages on read-only cluster nodes:

```python
from matplotlib.transforms import Affine2D

def plot_hex_skew_slice(ax, H_edges, K_edges, data_2d, skew_angle=60.0, norm=None, cmap='viridis', **kwargs):
    """
    Plot a 2D hexagonal slice skewed by skew_angle (default 60 deg)
    using pure Matplotlib Affine2D transforms.
    """
    shear_angle = 90.0 - skew_angle  # 30 degrees for hexagonal
    
    # Base quadmesh
    p = ax.pcolormesh(H_edges, K_edges, data_2d, shading='flat', norm=norm, cmap=cmap, **kwargs)
    
    # Affine shear transform
    t = Affine2D()
    t += Affine2D().scale(1.0, np.cos(np.radians(shear_angle)))
    t += Affine2D().skew_deg(shear_angle, 0.0)
    t += Affine2D().scale(1.0, np.cos(np.radians(shear_angle))).inverted()
    
    ymin, ymax = K_edges.min(), K_edges.max()
    p.set_transform(t + Affine2D().translate(-ymin * np.sin(np.radians(shear_angle)), 0.0) + ax.transData)
    
    # Adjust x-limits and aspect ratio for the shear
    xmin, xmax = H_edges.min(), H_edges.max()
    ax.set_xlim(xmin, xmax + (ymax - ymin) / np.tan(np.radians(90.0 - shear_angle)))
    ax.set_ylim(ymin, ymax)
    ax.set_aspect(np.cos(np.radians(shear_angle)))
    
    ax.tick_params(direction='in', which='both', top=True, right=True)
    ax.set_xlabel(r"$H$ (r.l.u.)")
    ax.set_ylabel(r"$K$ (r.l.u.)")
    return p
```

### 6.4 When to Choose Orthogonal vs. Skewed
- **Use Orthogonal $(1, 0, 0)$ vs. $(-0.5, 1, 0)$ (Recommended)**: For multi-panel figures, publication-quality Cartesian plots, isotropic reciprocal features (circular diffuse rings), and clean integration boxes.
- **Use 60° Skewed**: When direct inspection of integer Miller indices $(H, K)$ on the rhombic lattice is specifically requested or for quick visual comparison with real-space Kagome unit cells.

---

## 7. Predictive Runtime Budgets & Scheduling Protocol (`schedule`)

Large-scale single-crystal data reduction (`reduce.sh -n` and `reduce.sh -i`) on `analysis.sns.gov` involves compute times ranging from 15 minutes to several hours depending on run counts and peak densities.

### 7.1 Quantitative Throughput Benchmarks
Empirical benchmarks on `analysis.sns.gov` (using 16 parallel processes):
- **Parallelization Model & Worker Architecture**:
  `garnet` parallelizes across raw goniometer sweeps (`Runs: start:stop`), partitioning the list into $N_{\text{runs}} / N_{\text{proc}}$ runs per worker process (`_p0` through `_p15`).
  - Each worker outputs intermediate chunk workspaces: `<OutputName>_p<N>_<Cell>_<Centering>_...nxs` (~56 MB each).
  - In `_diagnostics/`, each completed run writes an individual peak workspace: `run#<run>_peaks.nxs`.
  - **Quantitative Real-Time Progress Metric**:
    $$\text{Progress} = \frac{\text{count}(*\_diagnostics/\text{run\#*\_peaks.nxs})}{N_{\text{total\_runs}}}$$
    Counting completed peak files provides an exact percentage progress without parsing massive runtime logs.
  - Final aggregation: Only after all $N_{\text{proc}}$ workers finish does `combine_parallel` execute to merge all chunks, refine the unified lattice, export `.int` / `.hkl` tables, and delete the intermediate `_p*.nxs` chunk files.
- **Normalization (`reduce.sh -n`)**:
  - Event loading, solid-angle & flux correction, and histogram binning: **~15–25 seconds per run**.
  - 70-run sweep (one temperature, e.g. 320 K): **~18–25 minutes**.
  - 120-run sweep (full series): **~30–45 minutes**.
- **Peak Integration (`reduce.sh -i`)**:
  - For each run, the detector geometry is loaded, peaks intersecting the detector (~100–150 peaks per orientation) are predicted, and 3D Stoica-Wilkinson resolution ellipsoids (`ProfileFit: true`) and `MDNorm` diagnostic cuts are computed.
  - Profile fitting throughput: **~20 minutes per individual run** on a single worker core.
  - With $N_{\text{proc}} = 16$, 16 runs are processed simultaneously, yielding an effective cluster throughput of **16 runs completed every ~20 minutes** (~1.25 min/run effective across the cluster).
  - Predictive formula:
    $$T_{\text{int}} \approx \left\lceil \frac{N_{\text{runs}}}{N_{\text{proc}}} \right\rceil \times T_{\text{run\_fit}} + T_{\text{combine}}$$
  - For a typical 120-run single-crystal sweep:
    $$T_{\text{int}} \approx \left\lceil \frac{120}{16} \right\rceil \times 20\text{ min} = 8 \times 20\text{ min} \approx 160\text{ minutes} \approx 2.5\text{ hours per model}$$


### 7.2 Strict Anti-Polling Rule & Wakeup Scheduling
> [!IMPORTANT]
> **Zero Polling Loops**:
> Never poll remote logs with repeated `tail` or shell loops in rapid active turns. Continuous polling wastes computational context, triggers rate limits, and clutters user transcripts.

**Mandatory Procedure**:
1. **Calibrate Throughput**: If needed, take a single sample of the peak/run count at $t = 1$ minute to confirm the active rate.
2. **Calculate Expected Finish Time**:
   $$T_{\text{remaining}} = \frac{N_{\text{total}} - N_{\text{current}}}{\text{Rate}}$$
3. **Schedule a One-Shot Wakeup Timer**:
   Call the `schedule` tool with `DurationSeconds` set to the estimated remaining time:
   ```json
   schedule(
     DurationSeconds: 1500,
     Prompt: "CORELLI integration job estimated completion reached. Check process PID, inspect log, and verify reflection files."
   )
   ```
4. **End Turn**: Stop calling tools and allow the agent to sleep until the schedule notification wakes it reactively.
5. **Inspect & Proceed**: Upon wakeup, verify `PID` completion, check log tails, validate reflection file non-zero sizes (`.int`, `.hkl`), and proceed to downstream tasks.


