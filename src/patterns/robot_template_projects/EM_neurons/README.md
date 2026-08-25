# EM connectome neuron terms

Consolidated, script-driven generation of FBbt neuron terms from EM connectome
datasets (FlyWire/FAFB, hemibrain, MANC, male-CNS, optic-lobe). Replaces the
previous per-connectome notebook + manual `robot template` workflow with offline
build scripts (run from committed data) that produce a single consolidated
component, `components/EM_neurons.owl`, from a **single ROBOT template**.

> **Scope:** EM-connectome neuron terms only. `VNC_neurons/` (Feng/Ehrhardt) is
> **not** EM-derived and is out of scope — it keeps its own component
> (`components/VNC_new_cells.owl`). BANC cross-dataset identity axioms stay in
> their own `components/banc_identical_to.owl`.

## Layout

```
EM_neurons/
├── lib/
│   ├── EM_common.py        # shared helpers (name_lister, #1105 TYPE rows, NT->GO,
│   │                       #   laterality/connectivity filter, curation_path, ...)
│   └── EM_unified.py       # the single unified ROBOT-template schema + per-connectome
│                           #   native->unified column maps + the row collector
├── build_EM_neurons.py     # THE generator: runs the six row builders, unifies +
│                           #   registry-filters them, writes one template.tsv
├── registry/
│   ├── build_registry.py   # (re)build the registry from source lists + curation bridges
│   └── EM_neuron_registry.tsv   # committed: one row per FBbt id (single ID source;
│                                 #   move-to-edit removal target)
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
├── builds/                 # offline per-connectome row generators (no network)
│   └── build_{manc,hemibrain_cells,hemibrain_allns,flywire,male_cns,optic_lobe}.py
└── README.md
```

Cross-dataset FBbt mapping bridges are read from the consolidated
`../connectome-curation` repo (`datasets/<connectome>/resources/…`) via
`EM_common.curation_path`. The male-CNS region mapping
(`EM_neuropils/male-cns_regions.tsv`) is read from the in-repo `EM_neuropils`
project.

## Build

The six `builds/build_*.py` are the tested, faithful per-connectome row
generators. `build_EM_neurons.py` drives them, re-expresses every connectome's
output on the one `EM_unified.UNIFIED_HEADER` schema (RO CURIEs throughout, so
**no `robot template --input` is needed**), filters to the FBbt ids in
`registry/EM_neuron_registry.tsv`, appends the ROBOT issue-#1105 TYPE rows once,
and writes a single `template.tsv` that the Makefile turns into
`EM_neurons.owl` with one `robot template`.

**Normal / release build** uses the committed `components/EM_neurons.owl` and
needs none of this — the component is a checked-in build input.

**Regeneration** (occasional, by a curator) has two steps:

1. **Fetch** connectome evidence into `data/` (needs a neuPrint token; FlyWire
   also needs `fafbseg` and the committed feather files). Opt-in, not part of
   the normal build:
   ```sh
   cd fetch
   NEUPRINT_TOKEN=<token> python3 fetch_hemibrain.py
   NEUPRINT_TOKEN=<token> python3 fetch_male_cns.py     # pinned male-cns:v1.0
   NEUPRINT_TOKEN=<token> python3 fetch_optic_lobe.py
   python3 fetch_flywire_neuropils.py
   ```
   (MANC needs no fetch — it reads the committed `sources/manc/typing_info.tsv`.)
2. **Build**: `make components/EM_neurons.owl` (from `src/ontology`) runs
   `build_EM_neurons.py` + one `robot template`. `build_male_cns` /
   `build_optic_lobe` need `tmp/fbbt-merged.db` (OAK part-of pruning of region
   terms); run a normal build first if it is absent. Add a new term by editing
   the relevant `sources/<connectome>/` id-list and re-running
   `registry/build_registry.py`; remove one with `/move-to-edit` (which deletes
   its registry row).

## Evidence caches and provenance

The `data/*_roiinfo.tsv`, `data/*_hemilineage.tsv` and
`data/flywire_neuropil_volumes.tsv` caches are **gitignored** (like the FlyWire
feather files): they are only needed to regenerate the component and are treated
as curator-local. `data/PROVENANCE.tsv` **is** committed and records, per cache,
the connectome dataset, version, source, fetch date and row count — the durable
record of what each regeneration was based on. The `fetch/` scripts update it
automatically on every fetch (`record_provenance`).

Current pinned versions: hemibrain v1.2.1, optic-lobe v1.1, male-CNS **v1.0**,
FlyWire FAFB v783, MANC v1.2.1.

## Status

- **Done (Phase 1):** shared library; fetch scripts; offline row generators for
  all six EM connectomes, each reproducing its current committed content.
- **Done (Phase 2):** `EM_neurons.owl` wired into the ODK build (`fbbt-odk.yaml`,
  `catalog-v001.xml`, `fbbt-edit.obo` imports, `Makefile` `OTHER_SRC`/recreate
  lists) in place of the six per-connectome components (VNC and BANC kept
  separate); `README-editors.md` and the `move-to-edit` skill updated.
- **Done (Phase 3, Stage A):** single **registry** (`registry/EM_neuron_registry.tsv`,
  11,206 ids), single **generator** (`build_EM_neurons.py`) and single unified
  **template** (`lib/EM_unified.py`, RO CURIEs — no `robot template --input`, no
  `robot merge`). `robot diff` of the regenerated `EM_neurons.owl` vs the previous
  committed component: **identical**. Curation bridges now read from
  `../connectome-curation`. Cross-dataset identity is recorded in the registry's
  `name_in_*` columns but not yet emitted into terms.
- **Later (Phase 3, Stage B/C):** emit `name_in_*` as dataset-tagged synonyms +
  provenance (identity merge), then reconcile connectome evidence across every
  connectome where a type appears (evidence merge). `EM_synonyms.owl` stays a
  separate asset for now.
- **Later (Phase 4):** an opt-in `refresh-EM-data` Makefile goal wrapping the
  `fetch/` scripts.
