---
name: oncat-metadata-catalog
description: Query, search, and automate retrieval of proposal numbers, run metadata, sample environments, and data paths across ORNL SNS and HFIR facilities using the ONCAT REST API and pyoncat client.
---

# ONCAT Metadata Catalog Skill

## Overview

**ONCAT** ([oncat.ornl.gov](https://oncat.ornl.gov)) is Oak Ridge National Laboratory's central data catalog and metadata indexing service for neutron scattering experiments conducted at the **Spallation Neutron Source (SNS)** and the **High Flux Isotope Reactor (HFIR)**.

It provides programmatic and web-based access to:
- Proposal (IPTS) numbers, titles, and team rosters.
- Experimental run logs, incident energies ($E_i$), chopper frequencies, and run durations.
- Sample environment telemetry (temperature sensors, magnetic field, pressure).
- Absolute physical storage paths for raw NeXus files and autoreduced datasets on GPFS.

---

## 1. Authentication & Client Setup

### Python Client Installation
The official Python client `pyoncat` communicates with the ONCAT v1 REST API:

```bash
# In local Python or on analysis.sns.gov
pip install pyoncat
```

### Authentication Mechanics
ONCAT utilizes OAuth2 authentication backed by ORNL UCAMS / XCAMS credentials.

```python
from oncat import ONCat

# Initialize client targeting the production endpoint
oncat = ONCat(
    "https://oncat.ornl.gov",
    client_id="<client_id>",         # Available from ORNL Software Portal
    client_secret="<client_secret>"  # or provided via environment variables
)

# Interactive / Scripted Login with UCAMS
oncat.login(username="<ucams_username>", password="<ucams_password>")
```

### Environment Variable Standards
Store non-interactive credentials securely in environment variables or `~/.oncat/credentials`:
```bash
export ONCAT_CLIENT_ID="<client_id>"
export ONCAT_CLIENT_SECRET="<client_secret>"
export ONCAT_USER="<ucams_username>"
```

---

## 2. API Hierarchy & Key Endpoints

ONCAT structures data under a strict hierarchy:
`Facility` $\rightarrow$ `Instrument` $\rightarrow$ `Experiment (IPTS)` $\rightarrow$ `Datafile / Run`

| Entity | Endpoint / Method | Purpose |
| :--- | :--- | :--- |
| **Facilities** | `oncat.facilities.list()` | List facilities (`SNS`, `HFIR`). |
| **Instruments** | `oncat.instruments.list(facility="SNS")` | List beamlines (`ARCS`, `SEQUOIA`, `CNCS`, etc.). |
| **Experiments** | `oncat.experiments.list(facility=..., instrument=...)` | Query IPTS proposals by title, date, or user. |
| **Runs / Datafiles**| `oncat.datafiles.list(facility=..., instrument=..., experiment=...)` | Enumerate run numbers, events, and NeXus paths. |

---

## 3. High-Value Search Recipes

### Recipe 1: Finding Proposals by User or Keyword
Search for all proposals on an instrument matching a specific sample compound (e.g., `"FeS"`):

```python
from oncat import ONCat
import os

oncat = ONCat("https://oncat.ornl.gov")
oncat.login(os.environ["ONCAT_USER"], os.environ["ONCAT_PASS"])

# Search ARCS experiments for 'FeS' or 'iron sulfide'
proposals = oncat.experiments.list(
    facility="SNS",
    instrument="ARCS",
    projection=["id", "title", "users", "created", "shared_directory"],
    sort_by=["created"],
    order="descending"
)

# Filter by keyword in title
matching = [p for p in proposals if "FeS" in p.title.upper()]
for p in matching:
    print(f"IPTS: {p.id} | Title: {p.title}")
    print(f"Shared Dir: {p.shared_directory}\n")
```

---

### Recipe 2: Locating Runs by Incident Energy ($E_i$) and Temperature ($T$)
Query specific run numbers within an IPTS proposal for a given incident energy and temperature range:

```python
# Query runs under IPTS-XXXXX
runs = oncat.datafiles.list(
    facility="SNS",
    instrument="ARCS",
    experiment="IPTS-XXXXX",
    projection=[
        "run_number",
        "location",
        "metadata.spallation_incident_energy",
        "metadata.sample_temp",
        "metadata.duration"
    ]
)

for r in runs:
    ei = r.metadata.get("spallation_incident_energy", None)
    temp = r.metadata.get("sample_temp", None)
    run_num = r.run_number
    file_path = r.location
    print(f"Run {run_num}: Ei = {ei} meV, T = {temp} K -> {file_path}")
```

---

### Recipe 3: Mapping Proposal to Filesystem Mounts on `analysis.sns.gov`
ONCAT metadata directly links to physical GPFS paths on the analysis cluster:

```python
def resolve_cluster_paths(ipts_number, instrument="ARCS", facility="SNS"):
    """
    Constructs standardized cluster directory paths on analysis.sns.gov.
    """
    base_user = f"/SNS/users/{os.environ.get('USER', '<user>')}/data/{facility}/{instrument}/{ipts_number}"
    base_gpfs = f"/gpfs/neutronsfs/instruments/{instrument}/{ipts_number}"
    
    return {
        "user_mount": base_user,
        "shared": f"{base_gpfs}/shared",
        "mde": f"{base_gpfs}/shared/MDE",
        "nexus": f"{base_gpfs}/nexus",
        "scripts": f"{base_gpfs}/shared/scripts/gemini"
    }
```

---

## 4. Integration with Mantid & Reduction Pipelines

Combine ONCAT search directly with Mantid loading routines:

```python
# 1. Use ONCAT to find run numbers for 5 K, 75 meV measurement
# 2. Feed resolved paths into Mantid Load or LoadMD
from mantid.simpleapi import LoadMD

target_mde = f"{shared_dir}/MDE/ARCS_FeS_75meV_5K_complete_shiver_UB.nxs"
ws = LoadMD(Filename=target_mde, MetadataOnly=True, OutputWorkspace="meta")
```
