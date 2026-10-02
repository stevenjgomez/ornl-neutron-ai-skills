# DGS Experiment Planning Standards & Checklist

This checklist defines the required verification steps and standards for planning single-crystal inelastic neutron scattering experiments on direct geometry spectrometers.

---

## 1. Pre-Flight Setup & Crystal Verification

- [ ] **Lattice Constants**: Obtain lattice lengths ($a, b, c$) and angles ($\alpha, \beta, \gamma$) from X-ray diffraction, neutron alignment, or literature.
- [ ] **Crystal Orientation**: Verify the source of the UB matrix:
  - Existing ISAW `.mat` file from prior runs or sample alignment.
  - Two non-collinear reference vectors $\mathbf{u}$ and $\mathbf{v}$ with known angles relative to the beam and goniometer.
- [ ] **Target Reflections / Zones**: Identify the physical zones of interest (e.g. $[H, H, L]$, $[H, 0, L]$, $[H, K, 0]$).
- [ ] **Rotation Axis Alignment**: Determine whether the crystal needs an orientation tilt (e.g. tilting by an angle $\theta$ about a crystal axis) so that target reflection vectors lie directly in the horizontal scattering plane.

---

## 2. Spectrometer Selection & IDF Loading

- [ ] **Spectrometer Match**: Select the instrument matching the required energy transfer and resolution:
  - Thermal / Epithermal: **ARCS** (SNS), **MAPS** (ISIS).
  - High Resolution / Intermediate: **SEQUOIA** (SNS), **MERLIN** (ISIS).
  - Cold Neutrons ($\le 30\text{ meV}$): **CNCS** (SNS), **LET** (ISIS), **IN5** (ILL).
  - Polarized / Focusing: **HYSPEC** (SNS).
- [ ] **IDF Loading (Cluster)**: Use Mantid's `LoadEmptyInstrument` to load authoritative pixel arrays, flight paths ($L_1, L_2$), and detector mask boundaries rather than hardcoded approximations.
- [ ] **Detector Obstructions**: Check for direct beamstop shadows ($\pm 2.0^\circ$ to $\pm 2.5^\circ$) and out-of-plane elevation limits ($\phi$).

---

## 3. Repetition Rate Multiplication (RRM) Evaluation

For chopper spectrometers supporting multi-rep mode (e.g., **MERLIN**, **LET**, **CNCS**):
- [ ] Calculate secondary incident energies $E_{i,m}$ transmitted through subsequent chopper openings:
  $$t_m = t_0 + m \cdot \Delta t_{\text{chopper}},\quad E_{i,m} = \left(\frac{2286.26 \cdot L_1}{t_m}\right)^2$$
- [ ] Report available secondary reps in a clear reference table.
- [ ] Confine secondary reps to reports unless the user explicitly requests full multi-energy simulations.

---

## 4. Visual Presentation Standards

Any generated coverage plot MUST adhere to the following publication standards:

1. **Strict Reciprocal Space Physical Isotropy**:
   - Calculate basis vector magnitudes using the reciprocal metric tensor:
     $$|\mathbf{q}_x| = \sqrt{\mathbf{q}_0^T \mathbf{g}^* \mathbf{q}_0},\quad |\mathbf{q}_y| = \sqrt{\mathbf{q}_1^T \mathbf{g}^* \mathbf{q}_1}$$
   - Apply `ax.set_aspect(aspect_q, adjustable='box')` where:
     $$\text{aspect\_q} = \frac{|\mathbf{q}_y|}{|\mathbf{q}_x|}$$
   - **Never use `aspect='auto'`** on reciprocal space slices, as it stretches physical dimensions non-isotropically.

2. **Strict Integer Ticking Policy**:
   - All axis tick marks must represent integer values. Decimal tick marks are strictly prohibited.
   - **Minor Ticks**: Set `MultipleLocator(1)` along **both** axes so every integer unit has a tick mark.
   - **Major Ticks**: Spaced by integer multiples (e.g., step 5 along wide axes; step 2 or 1 along narrow axes).
   - **Styling**: Inward tick marks (`direction='in'`) enabled on all four subplot borders (`top=True, right=True`).

3. **Multi-Energy Coverage Reference**:
   - Bounding box limits for each row must be defined by the maximum accessible coverage at the highest incident energy ($E_{i,\max}$).
   - Textboxes on each panel must state both:
     - Absolute coverage percentage of the bounding box.
     - Relative coverage percentage relative to the $E_{i,\max}$ accessible span.

4. **Discrete Angle Colormap**:
   - Sample rotation angles $\psi \in [0^\circ, 360^\circ]$ must be colored using a discrete colormap (e.g. `turbo` resampled to $15^\circ$ or $20^\circ$ bins) so users can immediately distinguish which sample orientation covers each region of reciprocal space.
