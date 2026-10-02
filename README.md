# ORNL Neutron Scattering Agent Skills

This repository contains specialized skills and workflow blueprints for performing automated experiment planning, data reduction, and reciprocal-space visualization across ORNL neutron scattering facilities (SNS & HFIR) using `analysis.sns.gov`.

## Included Skills

| Skill | Description | Primary Instruments |
| :--- | :--- | :--- |
| [**`dgs-experiment-planner`**](./dgs-experiment-planner/SKILL.md) | Plan, simulate, and optimize single-crystal and powder inelastic neutron scattering experiments, reciprocal-space (HKL/Q) coverage, crystal orientation engineering, and chopper configurations using Mantid IDFs and analytical kinematics. | ARCS, SEQUOIA, CNCS, HYSPEC, MERLIN, MAPS, LET, IN5 |
| [**`shiver-data-reduction`**](./shiver-data-reduction/SKILL.md) | Single-crystal inelastic neutron scattering data reduction, MDE slicing, vanadium normalization, and physically isotropic reciprocal-space plotting via SHIVER & Mantid. | ARCS, SEQUOIA, CNCS, HYSPEC |
| [**`sns-analysis-remote`**](./sns-analysis-remote/SKILL.md) | Remote cluster execution etiquette, centralized Pixi environment mechanics, directory hierarchy navigation, and resilient headless job execution on `analysis.sns.gov`. | SNS & HFIR Facility-wide |
| [**`oncat-metadata-catalog`**](./oncat-metadata-catalog/SKILL.md) | Query, search, and automate retrieval of proposal numbers, run metadata, sample environments, and data paths via the ONCAT REST API and pyoncat. | SNS & HFIR Facility-wide |

---

## Directory Hierarchy & Scope

```text
├── README.md
├── dgs-experiment-planner/
│   ├── SKILL.md
│   ├── references/
│   │   ├── experiment_planning_checklist.md
│   │   ├── kinematics_and_projections.md
│   │   └── mantid_coverage_recipes.md
│   └── scripts/
│       └── simulate_dgs_coverage.py
├── oncat-metadata-catalog/
│   └── SKILL.md
├── shiver-data-reduction/
│   └── SKILL.md
└── sns-analysis-remote/
    └── SKILL.md
```
