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
Use an Ed25519 key with SSH multiplexing (`ControlMaster`) for low-latency command execution and persistent sessions across both the generic hostname and individual analysis nodes:

```ssh-config
Host analysis.sns.gov analysis-node*.sns.gov
  User <ucams_username>
  IdentityFile ~/.ssh/id_ed25519_sns
  IdentitiesOnly yes
  AddKeysToAgent yes
  UseKeychain yes
  ControlMaster auto
  ControlPath ~/.ssh/cm-%r@%h:%p
  ControlPersist 1h
```

### DNS Round-Robin vs. Cluster Node Process Tables
- **Round-Robin Routing**: `analysis.sns.gov` distributes incoming SSH connections across 24 worker nodes (`analysis-node01.sns.gov` through `analysis-node24.sns.gov`).
- **Process Table Localization**: Background processes (e.g., jobs launched with PID `123456`) reside strictly on the local Linux kernel process table of the specific node where they were spawned. Querying `ps -ef` on a new connection that lands on a different node will not show the process.
- **Shared GPFS Storage**: The underlying filesystem (`/SNS/CORELLI/IPTS-.../` or `/gpfs/neutronsfs/...`) is shared across all nodes. Inspecting file sizes, directory contents, and log tails is completely node-agnostic.
- **Node-Targeted Execution**: When tracking a specific running process PID, SSH directly to that specific host (e.g., `ssh analysis-node01.sns.gov "ps -p <PID>"`) using the wildcard SSH configuration above.

### Mandatory Protocol: Immediate User Notification on SSH Failure
Whenever an SSH command to `analysis.sns.gov` fails (due to an expired ControlMaster socket, `Permission denied`, or a blocking interactive password/2FA prompt):
> [!IMPORTANT]
> **DO NOT PERFORM FURTHER AUTOMATED CHECKS OR RETRIES.**
> Because ORNL requires two-factor authentication (UCAMS / Duo / tokencode) for establishing master connections, automated background processes cannot complete interactive authentication.
> **Action**: Immediately stop and prompt the user to establish a master session in an external terminal:
> ```bash
> ssh analysis.sns.gov
> ```
> Once the user logs in, the `ControlMaster` socket (`~/.ssh/cm-...`) is recreated, allowing automated commands to proceed seamlessly without prompts.

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
> **Strict Read-Only Data Policy**: Never overwrite, delete, or modify existing raw NeXus, autoreduced files, or original MDE workspaces. All new scripts, logs, and derived files must be created strictly within `shared/scripts/agents/` or `$HOME`.

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
cd /SNS/users/<user>/data/SNS/<beamline>/IPTS-<number>/shared/scripts/agents
nohup /usr/local/pixi/shiver/.pixi/envs/default/bin/python -u script.py < /dev/null > run.log 2>&1 &
echo "PID: $!"
```

### Checking Process Status
Verify whether the job is running in the process table:
```bash
ps -ef | grep <script_name>.py | grep -v grep
```

### 4.2 Autonomous Kernel-Level Job Chaining (`tail --pid`)

On shared nodes without an active batch queue (Slurm/SGE), sequential workflows (such as running multi-temperature integrations or queuing downstream jobs after an active task finishes) can be chained cleanly using Linux kernel-level PID tracking via `tail --pid`:

```bash
nohup bash -c "tail --pid=<TARGET_PID> -f /dev/null && bash /path/to/next_job.sh" < /dev/null > chain.log 2>&1 &
echo "Chained Runner PID: $!"
```

- **Mechanism**: `tail --pid=<PID> -f /dev/null` blocks until the kernel reports that `<TARGET_PID>` has terminated (by completion, kill, or failure), then immediately executes the chained command.
- **Efficiency**: Consumes **0% CPU** and requires zero active polling loops or human intervention.
- **Resilience**: The chained runner is fully detached (`nohup`) and executes reliably on the remote node even if the client machine disconnects, sleeps, or reboots.

---

## 5. Execution Etiquette & Runtime Budgets

### 5.1 Anti-Polling Etiquette & Predictive Runtime Budgets
Do **not** poll remote log files or process tables with repetitive `tail` or `ps` commands in loops or frequent conversational turns. Mantid and facility reduction algorithms are compute-bound and highly predictable in runtime:
- **`LoadMD` on raw MDE (10–50 GB)**: ~45–75 seconds.
- **`MakeSlice` single 2D cut**: ~20–25 seconds.
- **`LoadMD` on intermediate slice (~800 MB)**: ~10–12 seconds.
- **Figure generation (3x3 grid)**: ~15–20 seconds.
- **`garnet` Normalization (`-n`)**: ~15–25 seconds per run sweep (16 cores).
- **`garnet` Peak Integration (`-i`)**: ~20 minutes per run chunk (~16 runs completed every 20 min across 16 cores). For 120 runs: $\approx \lceil 120 / 16 \rceil \times 20\text{ min} \approx 2.5\text{ hours}$.

**Predictive Formula**:
$$\text{Estimated Runtime} \approx T_{\text{init}} + \frac{N_{\text{tasks}}}{\text{Throughput Rate}}$$

---

### 5.2 Predicted Timeline Scheduling Protocol (`schedule` Tool)

Whenever launching or managing a long-running remote job (expected duration $> 5$ minutes):
1. **Estimate Total Duration ($T_{\text{est}}$)**:
   Calculate the expected time based on algorithmic throughput. If empirical throughput is unknown, calibrate after the first 1–2 minutes of execution.
2. **Schedule a One-Shot Wakeup Timer**:
   Use the `schedule` tool with `DurationSeconds` set to the estimated remaining duration (or an 80–90% checkpoint):
   ```json
   schedule(
     DurationSeconds: 1800,
     Prompt: "Estimated completion time reached for remote integration job. Check process status, verify logs, and inspect output artifacts."
   )
   ```
3. **End the Turn Immediately**:
   Do **not** poll in loops or keep querying the remote node. Call no further tools and end the turn, allowing the system to sleep.
4. **Reactive Wakeup & Verification**:
   When the timer fires, the agent receives a high-priority notification and reactively wakes up to:
   - Check if the process (`PID`) has terminated cleanly.
   - Inspect the final lines of the log for success keywords or errors.
   - Verify that output files (`.nxs`, `.int`, `.hkl`) were generated and have non-zero size.
   - Proceed with downstream tasks (data synchronization, next integration run, or user notification).


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
4. Synchronize resulting figures and slices in bulk with `scp` or streaming `tar` (see below).

### 6.1 High-Throughput Streaming File Synchronization (`tar` over SSH)

When synchronizing dozens or hundreds of reduced reflection files (`.int`, `.hkl`), UB matrices (`.mat`), text logs, and diagnostic plots (`.pdf`), sequential `scp` wildcard operations often stall, fail with `No such file or directory` over SSH multiplexed connections, or cause latency bottlenecks.

**Streaming Standard**:
Stream a compressed `tar` archive through the SSH pipe directly to the local unpacker:

```bash
ssh analysis.sns.gov "cd <remote_directory> && tar -czf - *.int *.hkl *.mat *.pdf *_stats.txt *_symm.txt 2>/dev/null" | tar -xzf - -C <local_directory>/
```

- **Single Atomic Operation**: Opens a single SSH stream and transfers all matching files in seconds.
- **Compression**: Drastically reduces network bandwidth over wide-area connections.
- **Preserved Attributes**: Automatically preserves original file timestamps, modes, and directory trees without intermediate temporary files on disk.
