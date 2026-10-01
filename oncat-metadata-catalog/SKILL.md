---
name: oncat-metadata-catalog
description: Query, search, and automate retrieval of proposal numbers, run metadata, sample environments, and data paths across ORNL SNS and HFIR facilities using the ONCAT REST API and pyoncat client.
---

# ONCAT Metadata Catalog Skill

## Overview

**ONCAT** ([oncat.ornl.gov](https://oncat.ornl.gov)) is Oak Ridge National Laboratory's central data catalog and metadata indexing service for neutron scattering experiments conducted at the **Spallation Neutron Source (SNS)** and the **High Flux Isotope Reactor (HFIR)**.

On `analysis.sns.gov`, `pyoncat` is pre-installed within the centralized SHIVER Pixi environment:
- **Python Binary**: `/usr/local/pixi/shiver/.pixi/envs/default/bin/python`
- **Module Name**: `pyoncat` (`from pyoncat import ONCat`)

---

## 1. Authentication & Client Initialization

### Public Client ID
ORNL provides a standard public client ID for scientific workflows and SHIVER:
```python
ONCAT_URL = "https://oncat.ornl.gov"
ONCAT_CLIENT_ID = "eaeb036a-2602-4bb9-8530-0bb5812da7a1"
```

### Unauthenticated Mode (Open Catalog Metadata)
Basic experiment listings, facility instruments, and run numbers do **not** require human login:

```python
from pyoncat import ONCat

# Connect directly to the production catalog
client = ONCat("https://oncat.ornl.gov")

# List facilities
facilities = client.Facility.list()  # ['HFIR', 'SNS']

# List instruments
instruments = client.Instrument.list(facility="SNS")
```

### Authenticated Mode (Device Authorization Flow)
Access to proposal details, users, and protected run logs uses the OAuth2 Device Authorization Grant:

```python
import pyoncat
from pyoncat import ONCat

client = ONCat(
    "https://oncat.ornl.gov",
    client_id="eaeb036a-2602-4bb9-8530-0bb5812da7a1",
    flow=pyoncat.DEVICE_AUTHORIZATION_FLOW,
    scopes=["api:read"]
)

# Prompts with verification URL and one-time code to approve in browser
client.login()
```

---

## 2. API Hierarchy & Key Endpoints

PyONCat exposes uppercase resource accessors on the `ONCat` instance:

| Entity Accessor | Method | Example Usage |
| :--- | :--- | :--- |
| **`client.Facility`** | `.list()` | `client.Facility.list()` |
| **`client.Instrument`** | `.list(facility=...)` | `client.Instrument.list(facility="SNS")` |
| **`client.Experiment`** | `.list(facility=..., instrument=...)` | `client.Experiment.list(facility="SNS", instrument="ARCS")` |
| **`client.Experiment`** | `.retrieve(identifier, facility=..., instrument=...)` | `client.Experiment.retrieve("IPTS-38312", facility="SNS", instrument="ARCS")` |
| **`client.Datafile`** | `.list(facility=..., instrument=..., experiment=...)` | `client.Datafile.list(facility="SNS", instrument="ARCS", experiment="IPTS-38312")` |

---

## 3. High-Value Query Recipes

### Recipe 1: Inspecting an Experiment / IPTS Proposal
Retrieve acquisition dates, total indexed files, and run number ranges:

```python
from pyoncat import ONCat

client = ONCat("https://oncat.ornl.gov")
exp = client.Experiment.retrieve("IPTS-38312", facility="SNS", instrument="ARCS")

print(f"IPTS: {exp.id}")
print(f"Instrument: {exp.instrument}")
print(f"Run ranges: {exp.indexed['run_number']['ranges']}")
print(f"Total files: {exp.size}")
print(f"Acquisition dates: {exp.activity['acquisition']}")
```

---

### Recipe 2: Enumerate NeXus Datafiles and Locations
List the raw NeXus event files and autoreduced paths for an experiment:

```python
from pyoncat import ONCat

client = ONCat("https://oncat.ornl.gov")
files = client.Datafile.list(facility="SNS", instrument="ARCS", experiment="IPTS-38312")

for f in files:
    location = f.get("location")
    run_num = f.get("indexed", {}).get("run_number")
    if location and location.endswith(".nxs.h5"):
        print(f"Run {run_num} -> {location}")
```

---

### Recipe 3: Cluster Path Resolution
Map IPTS numbers directly to standard cluster GPFS directories on `analysis.sns.gov`:

```python
def get_ipts_paths(ipts_id, instrument="ARCS", facility="SNS"):
    """Returns filesystem paths for an IPTS proposal."""
    base_gpfs = f"/gpfs/neutronsfs/instruments/{instrument}/{ipts_id}"
    return {
        "nexus": f"{base_gpfs}/nexus",
        "shared": f"{base_gpfs}/shared",
        "mde": f"{base_gpfs}/shared/MDE",
        "autoreduce": f"{base_gpfs}/shared/autoreduce",
        "scripts": f"{base_gpfs}/shared/scripts/gemini"
    }
```
