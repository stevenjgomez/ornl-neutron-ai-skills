---
name: sns-analysis-remote
description: Remote cluster execution etiquette, centralized Pixi environment mechanics, directory hierarchy navigation, and resilient headless job execution across the ORNL SNS and HFIR analysis infrastructure (analysis.sns.gov).
---

# SNS Analysis Remote Cluster Workflow

## Overview

`analysis.sns.gov` is the high-performance compute analysis cluster at Oak Ridge National Laboratory (ORNL) supporting the Spallation Neutron Source (SNS) and High Flux Isotope Reactor (HFIR). 

This skill defines connection mechanics, filesystem organization, software deployment standards, and headless execution etiquette.

---

## 1. SSH Authentication & Connection Multiplexing

`analysis.sns.gov` routes to load-balanced analysis nodes (`analysis-node01` through `analysis-node24`).

### Recommended `~/.ssh/config`
Use an Ed25519 key with SSH multiplexing (`ControlMaster`) for low-latency command execution and persistent sessions:

```ssh-config
Host analysis.sns.gov
  HostName analysis.sns.gov
  User <ucams_username>
  IdentityFile ~/.ssh/id_ed25519_sns
  IdentitiesOnly yes
  AddKeysToAgent yes
  UseKeychain yes
  ControlMaster auto
  ControlPath ~/.ssh/cm-%r@%h:%p
  ControlPersist 1h
```

---

## 2. Filesystem Hierarchy & Directory Conventions

Data at SNS and HFIR are indexed by facility, beamline, and proposal (IPTS) number:

### Primary Data Mounts
- **Home directory**: `/SNS/users/<username>/` (or `~`)
- **Facility Data Tree**:
  - `~/data/SNS/<beamline>/IPTS-<number>/`
  - `~/data/HFIR/<beamline>/IPTS-<number>/`
- **Underlying GPFS Path**:
  - `/gpfs/neutronsfs/instruments/<beamline>/IPTS-<number>/`

### Proposal Subdirectories
Inside each proposal folder (`.../IPTS-<number>/`):
- `nexus/`: Raw time-of-flight event NeXus files.
- `shared/`: Shared reduced data, calibration files, and scripts accessible by proposal team members:
  - `shared/autoreduce/`: Automated facility reduction outputs.
  - `shared/MDE/`: Multi-dimensional event (MDE) single-crystal datasets.
  - `shared/van*.nxs`: Detector vanadium sensitivity calibration workspaces.
  - `shared/*.mat` or `shared/**/<name>.mat`: **ISAW UB matrix orientation files (always inside `shared/` or its subfolders, never outside `shared/`)**.
  - `shared/scripts/agents/`: **Dedicated workspace for agent-generated scripts, intermediate slices, and figures.**

### Safety & Permission Rules
> [!IMPORTANT]
> **Strict Read-Only Data Policy**: Never overwrite, delete, or modify existing raw NeXus, autoreduced files, or original MDE workspaces. All new scripts, logs, and derived files must be created strictly within `shared/scripts/gemini/` or `$HOME`.

---

## 3. Centralized Pixi Software Deployments

Scientific software on `analysis.sns.gov` is deployed via central Pixi environments under `/usr/local/pixi/`:

| Software | Environment Prefix | Python Binary |
| :--- | :--- | :--- |
| **SHIVER** | `/usr/local/pixi/shiver/` | `/usr/local/pixi/shiver/.pixi/envs/default/bin/python` |
| **Mantid Workbench** | Central Mantid modules | Integrated within tool Pixi envs or `mantidworkbench` |

To run Python scripts in a specific environment:
```bash
/usr/local/pixi/<tool>/.pixi/envs/default/bin/python script.py
```

---

## 4. Resilient Detached Job Execution (`nohup`)

Because event MDE datasets are typically 50–100+ GB, operations such as Mantid's `LoadMD` take 5–10 minutes over network storage.

If an SSH connection drops or an idle timeout occurs, any foreground process running under that SSH session will receive a `SIGHUP` and terminate immediately.

### Execution Standard
Always execute heavy data reduction or slicing jobs detached using `nohup` with `< /dev/null` (to prevent SSH pseudo-terminal retention) and Python `-u` (for unbuffered logging):

```bash
cd /SNS/users/<user>/data/SNS/<beamline>/IPTS-<number>/shared/scripts/gemini
nohup /usr/local/pixi/shiver/.pixi/envs/default/bin/python -u script.py < /dev/null > run.log 2>&1 &
echo "PID: $!"
```

### Checking Process Status
Verify whether the job is running in the process table:
```bash
ps -ef | grep <script_name>.py | grep -v grep
```

---

## 5. Execution Etiquette & Runtime Budgets

### Anti-Polling Etiquette
Do **not** poll remote log files with repetitive `tail` commands every few seconds. Mantid reduction algorithms are compute-bound and deterministic in runtime:
- **`LoadMD` on raw MDE (10–50 GB)**: ~45–75 seconds.
- **`MakeSlice` single 2D cut**: ~20–25 seconds.
- **`LoadMD` on intermediate slice (~800 MB)**: ~10–12 seconds.
- **Figure generation (3x3 grid)**: ~15–20 seconds.

**Standard**: Calculate the estimated runtime budget based on the number of cuts:
$$\text{Estimated Runtime} \approx T_{\text{LoadMDE}} + N_{\text{slices}} \times T_{\text{MakeSlice}} + N_{\text{loads}} \times T_{\text{LoadSlice}} + T_{\text{plot}}$$
Set a single one-shot timer or wait for that duration, and perform a single status check upon completion.

---

## 6. Remote Script Staging Policy

Never transmit complex, multi-line Python scripts via inline SSH heredocs (`ssh host "cat << 'EOF'..."`). Inline heredocs frequently mangle LaTeX symbols (`\Delta`, `\xi`, `\AA`), raw strings (`r"..."`), math symbols (`$`), and nested quote characters.

**Standard**:
1. Author and validate scripts locally in `<workspace>/scratch/script_name.py`.
2. Transfer via `scp`:
   ```bash
   scp scratch/script_name.py analysis.sns.gov:/SNS/users/<user>/data/SNS/<beamline>/IPTS-<number>/shared/scripts/gemini/
   ```
3. Execute remotely using the detached unbuffered standard.
4. Synchronize resulting figures and slices in bulk with `scp`.
