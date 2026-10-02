#!/usr/bin/env python3
"""
simulate_dgs_coverage.py

General-purpose Direct Geometry Spectrometer (DGS) reciprocal-space coverage simulator.
Computes accessible kinematic volumes across arbitrary sample orientations, goniometer sweeps,
incident energies, and projection planes.

Enforces publication standards:
  1. Strict physical aspect ratio (isotropy via reciprocal metric tensor g*).
  2. Integer-only tick marks (minor ticks with MultipleLocator(1)).
  3. Discrete psi-angle colormap.
  4. Row-wise limits referenced to maximum Ei.
"""

import os
import sys
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MultipleLocator

# Physical constant: k = sqrt(2 m_n / hbar^2 * E)
C_K = np.sqrt(0.4825961)  # ~0.694691 A^-1 meV^-0.5

# Standard instrument presets (approximate boundaries for analytical mode)
INSTRUMENT_PRESETS = {
    "MERLIN": {
        "two_theta_min": -45.0, "two_theta_max": 135.0,
        "phi_min": -30.0, "phi_max": 30.0,
        "beamstop": (-2.5, 2.5),
        "L1": 11.8, "L2": 2.5
    },
    "ARCS": {
        "two_theta_min": -28.0, "two_theta_max": 134.0,
        "phi_min": -27.0, "phi_max": 27.0,
        "beamstop": (-2.5, 2.5),
        "L1": 13.6, "L2": 3.0
    },
    "SEQUOIA": {
        "two_theta_min": -30.0, "two_theta_max": 60.0,
        "phi_min": -18.0, "phi_max": 18.0,
        "beamstop": (-2.0, 2.0),
        "L1": 18.0, "L2": 5.5
    },
    "CNCS": {
        "two_theta_min": -50.0, "two_theta_max": 140.0,
        "phi_min": -16.0, "phi_max": 16.0,
        "beamstop": (-2.0, 2.0),
        "L1": 36.2, "L2": 3.5
    },
    "HYSPEC": {
        "two_theta_min": 0.0, "two_theta_max": 60.0,
        "phi_min": -7.5, "phi_max": 7.5,
        "beamstop": (-1.5, 1.5),
        "L1": 36.0, "L2": 1.4
    }
}


def compute_b_matrix(a, b, c, alpha_deg, beta_deg, gamma_deg):
    """Computes Busing-Levy B matrix from lattice parameters."""
    alpha = np.radians(alpha_deg)
    beta = np.radians(beta_deg)
    gamma = np.radians(gamma_deg)

    vol = a * b * c * np.sqrt(
        1.0 - np.cos(alpha)**2 - np.cos(beta)**2 - np.cos(gamma)**2
        + 2.0 * np.cos(alpha) * np.cos(beta) * np.cos(gamma)
    )

    b1 = 2.0 * np.pi * b * c * np.sin(alpha) / vol
    b2 = 2.0 * np.pi * a * c * np.sin(beta) / vol
    b3 = 2.0 * np.pi * a * b * np.sin(gamma) / vol

    cos_gamma_star = (np.cos(alpha) * np.cos(beta) - np.cos(gamma)) / (np.sin(alpha) * np.sin(beta))
    sin_gamma_star = np.sqrt(max(0.0, 1.0 - cos_gamma_star**2))

    # B converts HKL into Cartesian Q (A^-1) such that Q = B * [H, K, L]^T
    B = np.array([
        [b1, b2 * cos_gamma_star, 0.0],
        [0.0, b2 * sin_gamma_star, 0.0],
        [0.0, 0.0, b3]
    ])
    return B


def compute_metric_tensor(B):
    """Computes reciprocal metric tensor g* = B^T * B."""
    return np.matmul(B.T, B)


def vector_length_q(vec, g_star):
    """Computes physical length in A^-1 for a reciprocal vector."""
    vec = np.asarray(vec, dtype=float)
    return np.sqrt(np.dot(vec, np.dot(g_star, vec)))


def load_isaw_mat(mat_file):
    """Parses an ISAW .mat file and returns UB matrix (1/A) and lattice parameters."""
    with open(mat_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    # First 3 lines are UB matrix
    ub_rows = []
    for i in range(3):
        ub_rows.append([float(x) for x in lines[i].split()[:3]])
    UB = np.array(ub_rows)
    
    # Line 4 or 6 typically contains lattice parameters
    lattice = [float(x) for x in lines[3].split()[:6]]
    return UB, lattice


def save_isaw_mat(filename, UB, lattice):
    """Exports orientation and lattice parameters to ISAW .mat format."""
    a, b, c, alpha, beta, gamma = lattice
    with open(filename, 'w') as f:
        for row in UB:
            f.write(f"{row[0]:12.8f} {row[1]:12.8f} {row[2]:12.8f}\n")
        f.write(f"{a:10.4f} {b:10.4f} {c:10.4f} {alpha:10.4f} {beta:10.4f} {gamma:10.4f}\n")
        f.write(f"{1.0:10.4f} {1.0:10.4f} {1.0:10.4f} {90.0:10.4f} {90.0:10.4f} {90.0:10.4f}\n")


def simulate_plane_coverage(UB, plane_basis, Ei, DeltaE, psi_range, inst_params,
                            delta_out_of_plane=0.10, n_2theta=200, n_phi=70):
    """
    Simulates reciprocal-space coverage for a specified plane and incident energy.

    Parameters:
        UB: 3x3 orientation matrix (1/A)
        plane_basis: tuple of (q0, q1, q2) defining in-plane and out-of-plane directions
        Ei: Incident neutron energy in meV
        DeltaE: Energy transfer in meV
        psi_range: 1D array of goniometer rotation angles in degrees
        inst_params: dict with instrument angular ranges
        delta_out_of_plane: slice thickness in r.l.u.
    """
    q0, q1, q2 = plane_basis
    M = np.column_stack([q0, q1, q2])
    M_inv = np.linalg.inv(M)
    UB_inv = np.linalg.inv(UB)

    Ef = Ei - DeltaE
    if Ef <= 0:
        return np.array([]), np.array([]), np.array([])

    ki = C_K * np.sqrt(Ei)
    kf = C_K * np.sqrt(Ef)

    # Generate detector pixel grid
    two_thetas_deg = np.linspace(inst_params["two_theta_min"], inst_params["two_theta_max"], n_2theta)
    if "beamstop" in inst_params:
        bs_min, bs_max = inst_params["beamstop"]
        two_thetas_deg = two_thetas_deg[(two_thetas_deg < bs_min) | (two_thetas_deg > bs_max)]

    phis_deg = np.linspace(inst_params["phi_min"], inst_params["phi_max"], n_phi)
    TT, PP = np.meshgrid(np.radians(two_thetas_deg), np.radians(phis_deg))
    tt_flat = TT.flatten()
    pp_flat = PP.flatten()

    # Laboratory frame momentum transfer Q_lab = ki - kf
    Q_lab_x = -kf * np.sin(tt_flat) * np.cos(pp_flat)
    Q_lab_y = -kf * np.sin(pp_flat)
    Q_lab_z = ki - kf * np.cos(tt_flat) * np.cos(pp_flat)
    Q_lab = np.vstack([Q_lab_x, Q_lab_y, Q_lab_z])  # 3 x N_pixels

    all_xi0 = []
    all_xi1 = []
    all_psi = []

    # Loop over goniometer angles psi
    for psi_deg in psi_range:
        psi_rad = np.radians(psi_deg)
        cos_p = np.cos(psi_rad)
        sin_p = np.sin(psi_rad)
        # Rotation about lab vertical axis y
        R_psi = np.array([
            [cos_p, 0.0, -sin_p],
            [0.0,   1.0,  0.0],
            [sin_p, 0.0,  cos_p]
        ])

        Q_sample = np.matmul(R_psi, Q_lab)
        HKL = np.matmul(UB_inv / (2.0 * np.pi), Q_sample)
        XI = np.matmul(M_inv, HKL)

        # In-plane filtering: |xi2| <= delta_out_of_plane
        in_plane_mask = np.abs(XI[2, :]) <= delta_out_of_plane
        if np.any(in_plane_mask):
            all_xi0.append(XI[0, in_plane_mask])
            all_xi1.append(XI[1, in_plane_mask])
            all_psi.append(np.full(np.sum(in_plane_mask), psi_deg))

    if all_xi0:
        return np.concatenate(all_xi0), np.concatenate(all_xi1), np.concatenate(all_psi)
    return np.array([]), np.array([]), np.array([])


def plot_dgs_coverage_matrix(results_dict, output_png, lattice, discrete_bins=18):
    """
    Renders a publication-quality multi-panel coverage matrix.

    results_dict: {
        (plane_name, Ei): {
            'xi0': array, 'xi1': array, 'psi': array,
            'q0': list, 'q1': list, 'q2': list,
            'aspect_q': float, 'xlabel': str, 'ylabel': str
        }
    }
    """
    planes = sorted(list(set(k[0] for k in results_dict.keys())))
    energies = sorted(list(set(k[1] for k in results_dict.keys())))
    Ei_max = max(energies)

    n_rows = len(planes)
    n_cols = len(energies)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5.5 * n_cols, 4.8 * n_rows), squeeze=False)
    plt.subplots_adjust(wspace=0.28, hspace=0.32, top=0.93, bottom=0.08, left=0.08, right=0.90)

    # Discrete colormap for psi
    cmap_base = plt.get_cmap('turbo', discrete_bins)
    norm = BoundaryNorm(np.linspace(0, 360, discrete_bins + 1), ncolors=discrete_bins)

    # Determine row-wise bounding limits based on Ei_max
    row_limits = {}
    for r, plane in enumerate(planes):
        ref_data = results_dict.get((plane, Ei_max))
        if ref_data and len(ref_data['xi0']) > 0:
            pad_x = 0.5
            pad_y = 0.5
            xmin = np.floor(ref_data['xi0'].min() - pad_x)
            xmax = np.ceil(ref_data['xi0'].max() + pad_x)
            ymin = np.floor(ref_data['xi1'].min() - pad_y)
            ymax = np.ceil(ref_data['xi1'].max() + pad_y)
            row_limits[plane] = (xmin, xmax, ymin, ymax)
        else:
            row_limits[plane] = (-5, 5, -5, 5)

    last_sc = None
    for r, plane in enumerate(planes):
        xmin, xmax, ymin, ymax = row_limits[plane]
        area_ref = (xmax - xmin) * (ymax - ymin)

        for c, Ei in enumerate(energies):
            ax = axes[r, c]
            data = results_dict.get((plane, Ei))

            if data and len(data['xi0']) > 0:
                sc = ax.scatter(
                    data['xi0'], data['xi1'], c=data['psi'],
                    cmap=cmap_base, norm=norm, s=1.5, alpha=0.6, rasterized=True
                )
                last_sc = sc

                # Calculate bounding coverage
                dx_cov = data['xi0'].max() - data['xi0'].min()
                dy_cov = data['xi1'].max() - data['xi1'].min()
                cov_area = dx_cov * dy_cov
                pct_ref = (cov_area / area_ref) * 100.0

                ax.text(
                    0.04, 0.94, f"Cov span: {pct_ref:.1f}%\n$\\Delta E = 5$ meV",
                    transform=ax.transAxes, fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='gray')
                )

            # Strictly isotropic physical aspect ratio
            aspect_q = data['aspect_q']
            ax.set_aspect(aspect_q, adjustable='box')

            # Strict integer ticking policy
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)
            ax.xaxis.set_minor_locator(MultipleLocator(1))
            ax.yaxis.set_minor_locator(MultipleLocator(1))
            ax.tick_params(direction='in', which='both', top=True, right=True, labelsize=9)

            if r == 0:
                ax.set_title(f"$E_i = {Ei}$ meV", fontsize=12, fontweight='bold', pad=10)
            if c == 0:
                ax.set_ylabel(f"{plane}\n{data['ylabel']}", fontsize=11, fontweight='bold')
            else:
                ax.set_ylabel(data['ylabel'], fontsize=10)

            if r == n_rows - 1:
                ax.set_xlabel(data['xlabel'], fontsize=11, fontweight='bold')

    # Colorbar
    if last_sc is not None:
        cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.70])
        cbar = fig.colorbar(last_sc, cax=cbar_ax)
        cbar.set_label('Goniometer Rotation Angle $\\psi$ (degrees)', fontsize=11, fontweight='bold')
        cbar.set_ticks(np.linspace(0, 360, 7))
        cbar.ax.tick_params(labelsize=9)

    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved publication coverage matrix to: {output_png}")


if __name__ == "__main__":
    print("DGS Coverage Simulator Module Loaded Successfully.")
