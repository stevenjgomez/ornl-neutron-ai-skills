---
name: dgs-experiment-planner
description: Plan, simulate, and optimize single-crystal and powder inelastic neutron scattering experiments, reciprocal-space (HKL/Q) coverage, crystal orientation engineering, and chopper configurations for direct-geometry spectrometers (ARCS, SEQUOIA, CNCS, HYSPEC, MERLIN, MAPS, LET, IN5) using Mantid IDFs and analytical kinematics.
---

# Direct Geometry Spectrometer (DGS) Experiment Planner

## 1. Overview & Capability Scope

This skill provides comprehensive workflows for planning and simulating time-of-flight inelastic neutron scattering (INS) experiments on Direct Geometry Spectrometers (DGS). It supports:
- **Reciprocal-Space Coverage Modeling**: Simulating accessible $(Q, E)$ and $(H, K, L)$ kinematic volumes for arbitrary sample orientations and full $360^\circ$ goniometer rotations ($\psi$).
- **Instrument Definition Awareness**: Dynamically querying official Mantid Instrument Definition Files (IDFs) for flight paths ($L_1, L_2$), detector angular ranges ($2\theta, \phi$), and physical masks without relying on stale, hardcoded tables.
- **Orientation Engineering & Goniometer Tilts**: Analytically computing sample tilts to rotate arbitrary reciprocal-space directions (e.g. $[1/3, 1/3, 0]$ or specific symmetry directions) directly into the horizontal scattering plane.
- **Multi-Repetition Rate Multiplication (RRM)**: Calculating secondary incident energies ($E_{i,m}$) and chopper harmonics for instruments supporting RRM (MERLIN, LET, CNCS).
- **Publication-Quality Visualization**: Enforcing strict physical aspect ratio isotropy ($\text{aspect} = |\mathbf{q}_y| / |\mathbf{q}_x|$), integer-only tick marks, discrete $\psi$-angle colormaps, and $E_{i,\max}$-referenced bounding boxes.

### Supported Facilities & Spectrometers
- **ORNL SNS**: **ARCS** (thermal/epithermal), **SEQUOIA** (fine resolution), **CNCS** (cold), **HYSPEC** (polarized/focusing).
- **ISIS RAL**: **MERLIN** (intermediate/RRM), **MAPS** (epithermal/single-crystal), **LET** (cold/RRM).
- **ILL Grenoble**: **IN5** (cold time-of-flight), **PANTHER** (thermal time-of-flight).

---

## 2. Execution Architecture: Remote Mantid vs Local Analytical

To support flexible execution across different compute environments, this skill operates via two complementary execution paths:

| Mode | Environment | Primary Engine | Key Tools / Scripts |
| :--- | :--- | :--- | :--- |
| **Path A: Headless Mantid (Recommended)** | Analysis Cluster (`analysis.sns.gov`) | Mantid `CalculateCoverageDGS` + IDFs | Python via `/usr/local/pixi/shiver/.pixi/envs/default/bin/python` |
| **Path B: Analytical Kinematics** | Local Machine (Mac / Linux without Mantid) | Pure NumPy Busing-Levy kinematics | Local Python (`~/miniconda3/envs/nxs/bin/python`) |

### When to Use Path A (Mantid / Cluster)
- Authoritative detector pixel coordinates, real tube gaps, and exact beamstop shadow masks are required.
- Working directly on `analysis.sns.gov` with the `shiver` Pixi environment.
- Generating output NeXus/MD workspaces for downstream Mantid / SHIVER reduction.
- Refer to [`references/mantid_coverage_recipes.md`](references/mantid_coverage_recipes.md) for complete scripts and offline algorithm introspection.

### When to Use Path B (Analytical Kinematics)
- Fast local exploratory work on personal machines without Mantid installed.
- Deriving analytical tilt angles, coordinate transformations, and customized projection plotting.
- Refer to [`references/kinematics_and_projections.md`](references/kinematics_and_projections.md) for full mathematical definitions and derivations.

---

## 3. Goniometer Orientation Engineering & Sample Tilts

A frequent planning requirement is orienting a specific crystallographic direction $\mathbf{h}_{\text{target}}$ into the horizontal scattering plane ($y_{\text{lab}} = 0$).

### Tilt Solution Workflow
1. **Compute Target in Current Lab Coordinates**:
   $$\mathbf{q}_{\text{cart}} = 2\pi \mathbf{UB}_{\text{orig}} \mathbf{h}_{\text{target}}$$
2. **Determine Lab Out-of-Plane Component**:
   The vertical component $q_y = \mathbf{q}_{\text{cart}} \cdot \hat{\mathbf{y}}_{\text{lab}}$ defines the deviation from the horizontal scattering plane.
3. **Compute Tilt Angle $\theta_{\text{tilt}}$**:
   To rotate the target direction into the plane without altering the primary in-plane zone, determine the rotation axis (commonly a reciprocal axis like $c^*$ or $\mathbf{u} \times \mathbf{v}$) and solve for the rotation angle that brings $q_y \to 0$.
4. **Transform UB Matrix**:
   $$\mathbf{UB}_{\text{new}} = \mathbf{R}_{\text{axis}}(\theta_{\text{tilt}}) \mathbf{UB}_{\text{orig}}$$
5. **Verify New Goniometer Rotation Axis**:
   $$\mathbf{u}_{\text{rot}} = \mathbf{UB}_{\text{new}}^{-1} \hat{\mathbf{y}}_{\text{lab}}$$
6. **Save ISAW `.mat` File**:
   Export the new orientation matrix so beamline scientists can align the goniometer stage accurately before the experiment.

---

## 4. Repetition Rate Multiplication (RRM) Evaluation

For chopper spectrometers (e.g. MERLIN, LET, CNCS) using high-frequency Fermi or disk choppers:
1. Neutrons with primary incident energy $E_{i,0}$ arrive at the chopper opening at time $t_0$:
   $$t_0 = \frac{2286.26 \cdot L_1}{\sqrt{E_{i,0}}}\quad (\mu\text{s})$$
2. Secondary sub-pulses pass through subsequent openings separated by the chopper period $\Delta t_{\text{chopper}} = \frac{10^6}{2 f_{\text{chopper}}}$ (for double-slit Fermi / disk chopper slots):
   $$t_m = t_0 + m \cdot \Delta t_{\text{chopper}},\quad E_{i,m} = \left(\frac{2286.26 \cdot L_1}{t_m}\right)^2\quad (\text{meV})$$
3. In experiment reports, provide an RRM overview table detailing candidate incident energies, chopper frequencies, and estimated elastic resolutions.

---

## 5. Mandatory Publication-Quality Plotting Standards

Every reciprocal-space coverage visualization produced by this skill MUST strictly adhere to these four publication standards:

### 1. Strict Physical Aspect Ratio (Isotropy)
Reciprocal space must be physically isotropic so that circular constant-$|\mathbf{Q}|$ scattering shells are not distorted into ellipses.
- Calculate the physical magnitude of the horizontal basis vector $\mathbf{q}_x$ and vertical basis vector $\mathbf{q}_y$ using the reciprocal metric tensor $\mathbf{g}^*$:
  $$|\mathbf{q}_x| = \sqrt{\mathbf{q}_0^T \mathbf{g}^* \mathbf{q}_0},\quad |\mathbf{q}_y| = \sqrt{\mathbf{q}_1^T \mathbf{g}^* \mathbf{q}_1}$$
- Enforce in Matplotlib:
  ```python
  aspect_q = abs_qy / abs_qx
  ax.set_aspect(aspect_q, adjustable='box')
  ```
- **NEVER use `aspect='auto'`** on reciprocal space slices.

### 2. Strict Integer-Only Ticking Policy
- **Minor Ticks**: Set `MultipleLocator(1)` along **both** axes so every integer unit has a tick mark:
  ```python
  from matplotlib.ticker import MultipleLocator
  ax.xaxis.set_minor_locator(MultipleLocator(1))
  ax.yaxis.set_minor_locator(MultipleLocator(1))
  ```
- **Major Ticks**: Use clean integer multiples (e.g. step 5 or 2 for wide spans; step 1 for narrow spans). Decimal labels (e.g. `2.5`, `7.5`) are strictly forbidden.
- **Tick Styling**: Inward tick marks on all four borders (`ax.tick_params(direction='in', which='both', top=True, right=True)`).

### 3. Multi-Energy Coverage Normalization
When comparing coverage across incident energies (e.g. $30, 50, 75\text{ meV}$):
- Set the axis limits ($x_{\min}, x_{\max}, y_{\min}, y_{\max}$) of each row according to the **maximum accessible coverage at $E_{i,\max}$**.
- Add an informational textbox to each panel stating both:
  - **Absolute coverage** of the bounding box.
  - **Relative coverage** compared to the $E_{i,\max}$ accessible area.

### 4. Discrete $\psi$-Angle Colormap
- Resample continuous colormaps (e.g. `turbo`) into discrete bins (e.g., $15^\circ$ or $20^\circ$ increments).
- Display a discrete colorbar labeled with clean integer degrees ($0^\circ, 60^\circ, 120^\circ, \dots, 360^\circ$) so readers can visually correlate reciprocal-space arcs with the specific goniometer angle.

---

## 6. Detailed Reference Guides

For complete formulas, checklists, and code templates, consult the specialized references:
- **Headless Mantid & Cluster Automation**: [`references/mantid_coverage_recipes.md`](references/mantid_coverage_recipes.md)
  - `CalculateCoverageDGS` parameters and syntax.
  - Extracting detector geometry and flight paths from IDFs.
  - Inspecting algorithm docstrings and property definitions offline.
- **Mathematical Formulations**: [`references/kinematics_and_projections.md`](references/kinematics_and_projections.md)
  - Laboratorary momentum transfer $\mathbf{Q}_{\text{lab}}$.
  - Goniometer rotation $\mathbf{R}_y(\psi)$ and Busing-Levy UB matrix relations.
  - Arbitrary projection basis matrix $\mathbf{M} = [\mathbf{q}_0, \mathbf{q}_1, \mathbf{q}_2]$.
  - Reciprocal metric tensor $\mathbf{g}^*$ for all crystal systems.
- **Standardized Execution Checklist**: [`references/experiment_planning_checklist.md`](references/experiment_planning_checklist.md)
  - Step-by-step verification protocol for pre-flight crystal setup, instrument selection, RRM analysis, and figure validation.
