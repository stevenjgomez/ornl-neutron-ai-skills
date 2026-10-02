# Headless Mantid DGS Coverage Recipes

This reference details how to automate direct-geometry time-of-flight neutron spectrometer coverage calculations headlessly using Mantid on `analysis.sns.gov` (or local Mantid installations).

---

## 1. Remote Execution Environment

On `analysis.sns.gov`, execute scripts using the centralized SHIVER Pixi environment:
```bash
/usr/local/pixi/shiver/.pixi/envs/default/bin/python my_coverage_script.py
```
This Python environment has the complete Mantid package, IDF database, and offline algorithm documentation pre-installed.

---

## 2. Headless DGS Coverage via `CalculateCoverageDGS`

The **DGSPlanner** graphical user interface in Mantid Workbench is a front-end wrapper for the algorithm `CalculateCoverageDGS`. It can be run fully headlessly in Python.

### Algorithm Signature & Properties
```python
from mantid.simpleapi import CalculateCoverageDGS, LoadEmptyInstrument, SetUB

# 1. Initialize empty instrument workspace (loads authoritative IDF)
ws_inst = LoadEmptyInstrument(InstrumentName="MERLIN") # or ARCS, SEQUOIA, CNCS, HYSPEC

# 2. Attach crystal lattice and orientation (UB matrix)
# From ISAW .mat file:
from mantid.simpleapi import LoadIsawUB
LoadIsawUB(InputWorkspace=ws_inst, Filename="sample_reference.mat")

# Or directly from lattice parameters:
SetUB(
    Workspace=ws_inst,
    a=3.4460, b=3.4460, c=5.6605,
    alpha=90, beta=90, gamma=120,
    u="1,0,0", v="0,0,1"  # u along beam, v in scattering plane at zero goniometer
)

# 3. Execute coverage calculation
# Output is an MDHistoWorkspace or MDEventWorkspace representing coverage
cov_md = CalculateCoverageDGS(
    InputWorkspace=ws_inst,
    Ei=75.0,
    EnergyTransfer=5.0,
    PsiMin=0.0,
    PsiMax=360.0,
    PsiStep=1.5,
    GoniometerAxis="0,1,0",  # Lab-frame rotation axis (typically vertical Y)
    OutputWorkspace="coverage_output"
)
```

---

## 3. Extracting Physical Instrument Geometry from IDFs

Instead of hardcoding angular limits or flight paths, query the instrument object loaded from Mantid's authoritative Instrument Definition Files (IDFs):

```python
import numpy as np
from mantid.simpleapi import LoadEmptyInstrument

ws = LoadEmptyInstrument(InstrumentName="ARCS")
inst = ws.getInstrument()
source = inst.getSource()
sample = inst.getSample()

# Moderator-to-sample distance (L1)
L1 = sample.getDistance(source)

# Iterate detector pixels to extract exact physical limits
det_info = ws.detectorInfo()
two_thetas = []
phis = []
l2_distances = []

for i in range(len(det_info)):
    if det_info.isMasked(i) or det_info.isMonitor(i):
        continue
    two_thetas.append(np.degrees(det_info.twoTheta(i)))
    phis.append(np.degrees(det_info.signedAzimuthalAngle(i)))
    l2_distances.append(det_info.l2(i))

two_thetas = np.array(two_thetas)
phis = np.array(phis)
l2_distances = np.array(l2_distances)

print(f"2Theta span: [{two_thetas.min():.1f}°, {two_thetas.max():.1f}°]")
print(f"Elevation phi span: [{phis.min():.1f}°, {phis.max():.1f}°]")
print(f"Mean L2 distance: {l2_distances.mean():.2f} m")
```

---

## 4. Querying Algorithm Properties Offline

When web documentation is inaccessible or URLs return 404, inspect Mantid algorithms directly via Python introspection:

```python
from mantid.api import AlgorithmManager

def inspect_algorithm(alg_name):
    alg = AlgorithmManager.createUnmanaged(alg_name)
    alg.initialize()
    print(f"=== {alg_name} (v{alg.version()}) ===")
    print(alg.getWikiDescription())
    print("\nProperties:")
    for prop in alg.getProperties():
        req = " [REQUIRED]" if prop.isRequired() else ""
        print(f"  - {prop.name()}: {prop.type()} (default: {prop.value()}){req}")
        print(f"      {prop.documentation()}")

inspect_algorithm("CalculateCoverageDGS")
```
