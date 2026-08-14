# EM connectome neuron terms

Consolidated, script-driven generation of FBbt neuron terms from EM connectome
datasets (FlyWire/FAFB, hemibrain, MANC, male-CNS, optic-lobe). Replaces the
previous per-connectome notebook + manual `robot template` workflow with offline
build scripts (run from committed data) that produce a single consolidated
component, `components/EM_neurons.owl`.

> **Scope:** EM-connectome neuron terms only. `VNC_neurons/` (Feng/Ehrhardt) is
> **not** EM-derived and is out of scope — it keeps its own component
> (`components/VNC_new_cells.owl`). BANC cross-dataset identity axioms stay in
> their own `components/banc_identical_to.owl`.

## Layout

```
EM_neurons/
├── lib/EM_common.py        # shared helpers used by all build scripts
├── sources/                # committed curated inputs, per connectome (relocated
│   │                       #   here from the old per-connectome notebook folders)
│   ├── manc/               # new_cell_FBbt_ids, typing_info (committed cache), *_FBbt_map, ...
│   ├── hemibrain/          # new_cell_types, new_ALLNs, hemibrain_1-1_ROI_mapping, glomerulus_names
│   ├── flywire/            # FBbt_ID-cell_type, neuropil_map, superclasses, lineage_map,
│   │                       #   + gitignored: Supplemental_file1_neuron_annotations.tsv, *.feather
│   ├── male_cns/           # new_types, broad_type_map
│   └── optic_lobe/         # new_types, broad_type_map, OL_ROI_mapping
├── fetch/                  # opt-in neuPrint/FlyWire fetch scripts (need a token)
│   ├── neuprint_common.py
│   └── fetch_{hemibrain,male_cns,optic_lobe,flywire_neuropils}.py
├── data/                   # evidence caches (gitignored) + PROVENANCE.tsv (tracked)
├── builds/                 # offline per-connectome build scripts (no network)
│   └── build_{manc,hemibrain_cells,hemibrain_allns,flywire,male_cns,optic_lobe}.py
└── README.md
```

The FlyWire optic-lobe mapping (`OL_FBbt_mapping.tsv`) and the male-CNS region
mapping (`EM_neuropils/male-cns_regions.tsv`) are still read from their existing
homes (the sibling `neuprint_optic_lobe_curation` repo and the `EM_neuropils`
project) rather than copied here, to keep a single source of truth.

## Two build modes

**Normal / release build** uses the committed `components/EM_neurons.owl` and
needs none of this — the component is a checked-in build input.

**Regeneration** (occasional, by a curator) has two steps:

1. **Fetch** connectome evidence into `data/` (needs a neuPrint token; FlyWire
   also needs `fafbseg` and the committed feather files). Opt-in, not part of
   the normal build:
   ```sh
   cd fetch
   NEUPRINT_TOKEN=<token> python3 fetch_hemibrain.py
   NEUPRINT_TOKEN=<token> python3 fetch_male_cns.py     # pinned male-cns:v0.9
   NEUPRINT_TOKEN=<token> python3 fetch_optic_lobe.py
   python3 fetch_flywire_neuropils.py
   ```
   (MANC needs no fetch — it reads the committed `sources/manc/typing_info.tsv`.)
2. **Build** each connectome's ROBOT template from committed data + the caches,
   then `robot template` + `robot merge` into `EM_neurons.owl` (see `builds/`).
   Generators that use quoted relation labels (`build_hemibrain_cells`,
   `build_male_cns`, `build_optic_lobe`, and the FlyWire hemibrain cross-gen)
   need `robot template --input fbbt.owl` for label resolution; `build_manc` and
   FlyWire-own use `RO:` CURIEs and do not. `build_male_cns` / `build_optic_lobe`
   also need `tmp/fbbt-merged.db` (OAK part-of pruning).

## Evidence caches and provenance

The `data/*_roiinfo.tsv`, `data/*_hemilineage.tsv` and
`data/flywire_neuropil_volumes.tsv` caches are **gitignored** (like the FlyWire
feather files): they are only needed to regenerate the component and are treated
as curator-local. `data/PROVENANCE.tsv` **is** committed and records, per cache,
the connectome dataset, version, source, fetch date and row count — the durable
record of what each regeneration was based on. The `fetch/` scripts update it
automatically on every fetch (`record_provenance`).

Current pinned versions: hemibrain v1.2.1, optic-lobe v1.1, male-CNS **v0.9**
(v1.0 is a planned follow-up), FlyWire FAFB v783, MANC v1.2.1.

## Status

- **Done:** shared library; fetch scripts; offline build scripts for all six EM
  generators. Each reproduces its current committed component (manc, FlyWire-own,
  male_cns byte-identical; hemibrain, ALLNs, optic_lobe axiom-identical), and the
  merged `EM_neurons.owl` is axiom-identical to the union of the six components
  (11,210 terms, 0 diffs).
- **Done (Phase 2):** `EM_neurons.owl` is wired into the ODK build (`fbbt-odk.yaml`,
  `catalog-v001.xml`, `fbbt-edit.obo` imports, `Makefile` `OTHER_SRC`/recreate
  lists) in place of the six per-connectome components (VNC and BANC kept
  separate); the `components/EM_neurons.owl` Makefile goal (in `fbbt.Makefile`)
  regenerates it — running the `builds/` scripts to make templates, then
  `$(ROBOT) template` + `$(ROBOT) merge` (validated byte-identical).
  `README-editors.md` and the
  `move-to-edit` skill are updated. The build scripts still read curated source
  TSVs from the old per-connectome project folders (relocating them into this
  folder is optional follow-up cleanup).
- **Later (Phase 3):** unified generator producing one term per cell type,
  merging evidence across every connectome where the type appears.
- **Later (Phase 4):** an opt-in `refresh-EM-data` Makefile goal wrapping the
  `fetch/` scripts.
