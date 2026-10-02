# Mathematical Foundations of DGS Kinematics & Projections

This document details the mathematical formulations for simulating direct-geometry inelastic neutron scattering coverage, crystal rotations, arbitrary projection slicing, and physically isotropic visualization.

---

## 1. Direct Geometry Neutron Kinematics

In a direct geometry spectrometer, incident neutron energy $E_i$ is fixed by choppers before the sample, and scattered energy $E_f$ is determined by time-of-flight to detector pixels.

### Energy Transfer & Wavenumbers
$$k_i = \sqrt{\frac{2m_n}{\hbar^2} E_i} \approx 0.694691 \sqrt{E_i\ [\text{meV}]}\quad (\text{\AA}^{-1})$$
$$k_f = \sqrt{\frac{2m_n}{\hbar^2} (E_i - \Delta E)} \approx 0.694691 \sqrt{(E_i - \Delta E)\ [\text{meV}]}\quad (\text{\AA}^{-1})$$

### Momentum Transfer in the Laboratory Frame
Taking the incident beam along $+z$, the vertical axis along $+y$, and horizontal scattering perpendicular to beam along $+x$:
$$\mathbf{k}_i = \begin{bmatrix} 0 \\ 0 \\ k_i \end{bmatrix},\quad
\mathbf{k}_f = \begin{bmatrix} k_f \sin(2\theta) \cos(\phi) \\ k_f \sin(\phi) \\ k_f \cos(2\theta) \cos(\phi) \end{bmatrix}$$

The wavevector transfer $\mathbf{Q}_{\text{lab}} = \mathbf{k}_i - \mathbf{k}_f$ is:
$$\mathbf{Q}_{\text{lab}} = \begin{bmatrix} -k_f \sin(2\theta) \cos(\phi) \\ -k_f \sin(\phi) \\ k_i - k_f \cos(2\theta) \cos(\phi) \end{bmatrix}$$

Kinematic horizons:
$$Q_{\min} = |k_i - k_f|,\quad Q_{\max} = k_i + k_f$$

---

## 2. Sample Rotation & Busing-Levy Crystallography

### Goniometer Rotation
When the sample stage rotates by an angle $\psi$ about the vertical goniometer axis $\hat{\mathbf{y}}$:
$$\mathbf{Q}_{\text{sample}}(\psi) = \mathbf{R}_y(\psi) \mathbf{Q}_{\text{lab}} = \begin{bmatrix} \cos\psi & 0 & -\sin\psi \\ 0 & 1 & 0 \\ \sin\psi & 0 & \cos\psi \end{bmatrix} \mathbf{Q}_{\text{lab}}$$

### Busing-Levy UB Matrix
In crystallographic convention (Busing & Levy, 1967):
$$\mathbf{Q}_{\text{sample}} = 2\pi \mathbf{U} \mathbf{B} \mathbf{h} = 2\pi \mathbf{UB} \begin{bmatrix} H \\ K \\ L \end{bmatrix}$$

To convert a scattered wavevector $\mathbf{Q}_{\text{sample}}$ into Miller indices $\mathbf{h} = [H, K, L]^T$:
$$\mathbf{h} = \frac{1}{2\pi} (\mathbf{UB})^{-1} \mathbf{Q}_{\text{sample}}$$

---

## 3. Projection into Arbitrary Crystallographic Planes

To analyze coverage on a 2D plane defined by in-plane basis vectors $\mathbf{q}_0$ (horizontal) and $\mathbf{q}_1$ (vertical), and out-of-plane normal vector $\mathbf{q}_2$:

1. Construct the basis matrix $\mathbf{M}$:
   $$\mathbf{M} = \begin{bmatrix} \mathbf{q}_0 & \mathbf{q}_1 & \mathbf{q}_2 \end{bmatrix} \in \mathbb{R}^{3 \times 3}$$

2. The projection coordinates $\boldsymbol{\xi} = [\xi_0, \xi_1, \xi_2]^T$ are given by:
   $$\boldsymbol{\xi} = \mathbf{M}^{-1} \mathbf{h} = \mathbf{M}^{-1} \left( \frac{1}{2\pi} \mathbf{UB}^{-1} \mathbf{Q}_{\text{sample}} \right)$$

3. **In-Plane Selection**:
   A detector event or simulation ray belongs to the target 2D slice if its out-of-plane coordinate satisfies:
   $$|\xi_2| \le \delta$$
   where $\delta$ is the slice integration thickness (typically $\delta \approx 0.05 \text{ to } 0.15 \text{ r.l.u.}$).

---

## 4. Reciprocal Metric Tensor & Basis Vector Magnitudes

The reciprocal metric tensor $\mathbf{g}^*$ defines scalar products in reciprocal space for any crystal system:
$$\mathbf{g}^* = (2\pi)^2 \mathbf{B}^T \mathbf{B}$$

For a general basis vector $\mathbf{q} = [q_h, q_k, q_l]^T$, its physical length in $\text{\AA}^{-1}$ is:
$$|\mathbf{q}| = \sqrt{\mathbf{q}^T \mathbf{g}^* \mathbf{q}}$$

### Hexagonal System ($a = b, \gamma = 120^\circ, c \perp a, b$)
$$|\mathbf{Q}(H, K, L)|^2 = (2\pi)^2 \left[ \frac{4}{3a^2} (H^2 + HK + K^2) + \frac{L^2}{c^2} \right]$$

---

## 5. Strict Physical Aspect Ratio for Isotropic Plotting

When plotting $\xi_1$ (vertical axis) versus $\xi_0$ (horizontal axis):
* 1 data unit along $x$ corresponds to $|\mathbf{q}_0| \text{ \AA}^{-1}$.
* 1 data unit along $y$ corresponds to $|\mathbf{q}_1| \text{ \AA}^{-1}$.

To ensure physical isotropy (so that scattering shells of constant $|\mathbf{Q}|$ appear as undistorted circles):
$$\text{aspect\_ratio} = \frac{\text{pixel height per data unit in } y}{\text{pixel width per data unit in } x} = \frac{|\mathbf{q}_1|}{|\mathbf{q}_0|} = \frac{\sqrt{\mathbf{q}_1^T \mathbf{g}^* \mathbf{q}_1}}{\sqrt{\mathbf{q}_0^T \mathbf{g}^* \mathbf{q}_0}}$$

### Example: Hexagonal FeS with Scaled Basis
For in-plane vector $\mathbf{q}_0 = (\frac{1}{3}, \frac{1}{3}, 0)$ and out-of-plane vector $\mathbf{q}_1 = (0, 0, \frac{1}{2})$:
$$|\mathbf{q}_0| = \frac{4\pi}{3a},\quad |\mathbf{q}_1| = \frac{\pi}{c}$$
$$\text{aspect} = \frac{|\mathbf{q}_1|}{|\mathbf{q}_0|} = \frac{\pi / c}{4\pi / (3a)} = \frac{3a}{4c}$$

In Matplotlib, this is enforced strictly with:
```python
aspect_q = (3.0 * a) / (4.0 * c)
ax.set_aspect(aspect_q, adjustable='box')
```

---

## 6. Orientation Engineering & Axis Tilting

To rotate a specific reciprocal direction $\mathbf{h}_{\text{target}}$ into the horizontal scattering plane:
1. Determine the current lab coordinates of the target reflection:
   $$\mathbf{q}_{\text{cart}} = 2\pi \mathbf{UB} \mathbf{h}_{\text{target}}$$
2. Calculate the tilt angle $\theta_{\text{tilt}}$ required about an orthogonal crystal axis (e.g. $c^*$) to null the out-of-plane component ($y_{\text{lab}} = 0$).
3. Compute the new orientation matrix:
   $$\mathbf{UB}_{\text{new}} = \mathbf{R}_{\text{tilt}} \mathbf{UB}_{\text{orig}}$$
4. Verify the new rotation axis $\mathbf{u}_{\text{rot}} = \mathbf{UB}_{\text{new}}^{-1} \hat{\mathbf{y}}_{\text{lab}}$.
